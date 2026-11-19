import stripe

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status

from .billing import PLAN_LIMITS, get_effective_plan
from .models import Subscription, StripeWebhookEvent


PLAN_DETAILS = {
    "free": {"name": "Free", "description": "Get started with the essentials."},
    "pro": {"name": "Pro", "description": "More room for growing teams."},
    "business": {"name": "Business", "description": "Scale your team's project operations."},
}


def stripe_price_for_plan(plan):
    return {
        "pro": settings.STRIPE_PRICE_PRO,
        "business": settings.STRIPE_PRICE_BUSINESS,
    }.get(plan, "")


def frontend_url(path):
    base = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
    return f"{base}{path}"


def sync_subscription(stripe_subscription, event_created=None):
    # Stripe SDK Subscription objects must be converted before dict access.
    if hasattr(stripe_subscription, "to_dict"):
        stripe_subscription = stripe_subscription.to_dict()

    customer_id = stripe_subscription.get("customer")
    if not customer_id:
        return

    subscription = Subscription.objects.filter(
        stripe_customer_id=customer_id
    ).first()

    if subscription and event_created is not None:
        if event_created < subscription.last_stripe_event_created:
            return

    if not subscription:
        metadata = stripe_subscription.get("metadata") or {}
        user_id = metadata.get("user_id")
        if not user_id:
            return
        subscription = Subscription.objects.filter(user_id=user_id).first()
        if not subscription:
            return
        subscription.stripe_customer_id = customer_id

    status_value = stripe_subscription.get("status", "incomplete")
    allowed_statuses = {choice[0] for choice in Subscription.STATUS_CHOICES}
    subscription.status = (
        status_value if status_value in allowed_statuses else "canceled"
    )

    subscription.stripe_subscription_id = stripe_subscription.get("id")

    items = (stripe_subscription.get("items") or {}).get("data") or []
    price_id = None
    if items:
        price_id = (items[0].get("price") or {}).get("id")

    if price_id == settings.STRIPE_PRICE_PRO:
        subscription.plan = "pro"
    elif price_id == settings.STRIPE_PRICE_BUSINESS:
        subscription.plan = "business"

    period_start = stripe_subscription.get("current_period_start")
    period_end = stripe_subscription.get("current_period_end")

    # Newer Stripe API versions may expose periods on subscription items.
    if items:
        period_start = period_start or items[0].get("current_period_start")
        period_end = period_end or items[0].get("current_period_end")

    subscription.current_period_start = (
        timezone.datetime.fromtimestamp(period_start, tz=timezone.get_current_timezone())
        if period_start else None
    )
    subscription.current_period_end = (
        timezone.datetime.fromtimestamp(period_end, tz=timezone.get_current_timezone())
        if period_end else None
    )
    subscription.cancel_at_period_end = bool(
        stripe_subscription.get("cancel_at_period_end", False)
    )
    if event_created is not None:
        subscription.last_stripe_event_created = max(
            subscription.last_stripe_event_created,
            event_created,
        )
    subscription.save()


class BillingPlansView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plans = []
        for plan_id, limits in PLAN_LIMITS.items():
            plans.append({
                "id": plan_id,
                **PLAN_DETAILS[plan_id],
                "limits": limits,
            })
        return Response({"plans": plans})


class BillingOverviewView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        subscription, _ = Subscription.objects.get_or_create(
            user=request.user,
            defaults={"plan": "free", "status": "active"},
        )
        effective_plan = get_effective_plan(request.user)

        return Response({
            "plan": effective_plan,
            "plan_name": PLAN_DETAILS[effective_plan]["name"],
            "status": subscription.status,
            "limits": PLAN_LIMITS[effective_plan],
            "current_period_start": (
                subscription.current_period_start.isoformat()
                if subscription.current_period_start else None
            ),
            "current_period_end": (
                subscription.current_period_end.isoformat()
                if subscription.current_period_end else None
            ),
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "stripe_connected": bool(subscription.stripe_customer_id),
        })


class StripeCheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan = request.data.get("plan")
        if plan not in ("pro", "business"):
            return Response(
                {"detail": "Choose a valid paid plan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Stripe is not configured yet."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        price_id = stripe_price_for_plan(plan)
        if not price_id:
            return Response(
                {"detail": f"Stripe Price ID for {plan} is not configured."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY
        subscription, _ = Subscription.objects.get_or_create(
            user=request.user,
            defaults={"plan": "free", "status": "active"},
        )

        try:
            customer_id = subscription.stripe_customer_id
            if not customer_id:
                customer = stripe.Customer.create(
                    email=request.user.email,
                    name=request.user.get_full_name() or request.user.email,
                    metadata={"user_id": str(request.user.pk)},
                )
                customer_id = customer.id
                subscription.stripe_customer_id = customer_id
                subscription.save(update_fields=["stripe_customer_id"])

            session = stripe.checkout.Session.create(
                mode="subscription",
                customer=customer_id,
                line_items=[{"price": price_id, "quantity": 1}],
                client_reference_id=str(request.user.pk),
                metadata={"user_id": str(request.user.pk), "plan": plan},
                subscription_data={
                    "metadata": {"user_id": str(request.user.pk), "plan": plan}
                },
                success_url=frontend_url("/billing?checkout=success"),
                cancel_url=frontend_url("/billing?checkout=cancelled"),
            )
            return Response({"checkout_url": session.url})

        except stripe.StripeError:
            return Response(
                {"detail": "Unable to start Stripe Checkout. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )


class StripePortalView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        subscription = Subscription.objects.filter(user=request.user).first()
        if not subscription or not subscription.stripe_customer_id:
            return Response(
                {"detail": "No Stripe customer is linked to this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not settings.STRIPE_SECRET_KEY:
            return Response(
                {"detail": "Stripe is not configured yet."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        stripe.api_key = settings.STRIPE_SECRET_KEY
        try:
            session = stripe.billing_portal.Session.create(
                customer=subscription.stripe_customer_id,
                return_url=frontend_url("/billing"),
            )
            return Response({"portal_url": session.url})
        except stripe.StripeError:
            return Response(
                {"detail": "Unable to open the billing portal."},
                status=status.HTTP_502_BAD_GATEWAY,
            )


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        if not settings.STRIPE_WEBHOOK_SECRET:
            return HttpResponse(status=503)

        stripe.api_key = settings.STRIPE_SECRET_KEY
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")

        try:
            event = stripe.Webhook.construct_event(
                request.body,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.SignatureVerificationError):
            return HttpResponse(status=400)

        # Stripe SDK returns an Event object, not a plain dictionary.
        # Convert it before using dictionary access; this also supports
        # dictionary-based mocks in the webhook tests.
        if hasattr(event, "to_dict"):
            event = event.to_dict()

        event_id = event.get("id")
        event_type = event.get("type")
        event_created = event.get("created")
        obj = event.get("data", {}).get("object", {})

        if not event_id:
            return HttpResponse(status=400)

        try:
            with transaction.atomic():
                _, created = StripeWebhookEvent.objects.get_or_create(
                    stripe_event_id=event_id,
                    defaults={"event_type": event_type or "unknown"},
                )

                # Stripe retries the same event; acknowledge without reprocessing.
                if not created:
                    return HttpResponse(status=200)

                if event_type == "checkout.session.completed":
                    stripe_subscription_id = obj.get("subscription")
                    if stripe_subscription_id:
                        stripe_subscription = stripe.Subscription.retrieve(
                            stripe_subscription_id
                        )
                        sync_subscription(
                            stripe_subscription,
                            event_created=event_created,
                        )

                elif event_type in (
                    "customer.subscription.created",
                    "customer.subscription.updated",
                    "customer.subscription.deleted",
                ):
                    sync_subscription(obj, event_created=event_created)

        except stripe.StripeError:
            # The transaction rolls back, allowing Stripe to retry this event.
            return HttpResponse(status=500)

        return HttpResponse(status=200)
