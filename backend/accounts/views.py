
import secrets
from datetime import timedelta

import resend

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect

from rest_framework import generics, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    ProfileUpdateSerializer,
)
from .models import Profile, PasswordChangeChallenge


# --------------------------------------------------
# REFRESH COOKIE CONFIGURATION
# --------------------------------------------------

REFRESH_COOKIE_NAME = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth/"


def set_refresh_cookie(response, token):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=int(
            settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
        ),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )


def clear_refresh_cookie(response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path=REFRESH_COOKIE_PATH,
        samesite="Lax",
    )


def prevent_caching(response):
    response["Cache-Control"] = "no-store"
    return response


# --------------------------------------------------
# REGISTRATION
# --------------------------------------------------

class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        response = Response(
            {
                "message": "Account created successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            },
            status=status.HTTP_201_CREATED,
        )

        return prevent_caching(response)


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        refresh = RefreshToken.for_user(user)
        access = refresh.access_token

        response = Response(
            {
                "message": "Login successful.",
                "access_token": str(access),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                },
            },
            status=status.HTTP_200_OK,
        )

        set_refresh_cookie(response, str(refresh))

        return prevent_caching(response)


# --------------------------------------------------
# REFRESH ACCESS TOKEN
# --------------------------------------------------

@method_decorator(csrf_protect, name="dispatch")
class RefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if not refresh_token:
            response = Response(
                {"detail": "Refresh token is missing."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

            clear_refresh_cookie(response)
            return prevent_caching(response)

        serializer = TokenRefreshSerializer(
            data={"refresh": refresh_token}
        )

        try:
            serializer.is_valid(raise_exception=True)

        except (ValidationError, TokenError):
            response = Response(
                {"detail": "Refresh token is invalid or expired."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

            clear_refresh_cookie(response)
            return prevent_caching(response)

        token_data = serializer.validated_data

        response = Response(
            {
                "access_token": token_data["access"],
            },
            status=status.HTTP_200_OK,
        )

        # SimpleJWT rotates the refresh token when configured.
        # Never expose the refresh token in the response body.
        rotated_refresh = token_data.get("refresh")

        if rotated_refresh:
            set_refresh_cookie(response, rotated_refresh)

        return prevent_caching(response)


# --------------------------------------------------
# LOGOUT
# --------------------------------------------------

@method_decorator(csrf_protect, name="dispatch")
class LogoutView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()

            except TokenError:
                # Invalid or already-blacklisted token.
                # The cookie will still be cleared.
                pass

        response = Response(
            status=status.HTTP_204_NO_CONTENT
        )

        clear_refresh_cookie(response)

        return prevent_caching(response)


# --------------------------------------------------
# CURRENT AUTHENTICATED USER
# --------------------------------------------------

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        response = Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "display_name": (
                    user.profile.display_name
                    if hasattr(user, "profile") and user.profile.display_name
                    else user.get_full_name() or user.username
                ),
                "avatar_url": (
                    request.build_absolute_uri(user.profile.avatar.url)
                    if hasattr(user, "profile") and user.profile.avatar
                    else None
                ),
                "date_joined": user.date_joined.isoformat(),
                "is_active": user.is_active,
            },
            status=status.HTTP_200_OK,
        )

        return prevent_caching(response)


# --------------------------------------------------
# ACCOUNT PROFILE
# --------------------------------------------------

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        profile, _ = Profile.objects.get_or_create(
            user=request.user,
            defaults={
                "display_name": (
                    request.user.get_full_name() or request.user.username
                )
            },
        )

        serializer = ProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()

        avatar_url = (
            request.build_absolute_uri(profile.avatar.url)
            if profile.avatar
            else None
        )

        response = Response(
            {
                "message": "Profile updated successfully.",
                "display_name": profile.display_name,
                "avatar_url": avatar_url,
            },
            status=status.HTTP_200_OK,
        )
        return prevent_caching(response)


# --------------------------------------------------
# SECURE PASSWORD CHANGE WITH EMAIL OTP
# --------------------------------------------------



OTP_LIFETIME = timedelta(minutes=10)
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
OTP_HOURLY_WINDOW = timedelta(hours=1)
OTP_MAX_EMAILS_PER_HOUR = 5
OTP_MAX_ATTEMPTS = 5
PASSWORD_CHANGE_TOKEN_LIFETIME = 300
PASSWORD_CHANGE_TOKEN_SALT = "accounts.password-change.v1"


def send_password_change_email(user, otp):
    subject = "Your Nexvia password change verification code"
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#25352b">
      <h2>Password change verification</h2>
      <p>Use this code to verify your password change request.</p>
      <div style="font-size:30px;font-weight:700;letter-spacing:8px;
                  padding:18px;background:#f2efe7;border-radius:10px;
                  display:inline-block">{otp}</div>
      <p>This code expires in 10 minutes and can only be used once.</p>
      <p>If you did not request this, you can safely ignore this email.</p>
      <p style="color:#718078;font-size:12px">Nexvia Account Security</p>
    </div>
    """

    api_key = getattr(settings, "RESEND_API_KEY", "")
    sender = getattr(
        settings,
        "EMAIL_FROM",
        "Nexvia <onboarding@resend.dev>",
    )

    if api_key:
        resend.api_key = api_key
        resend.Emails.send({
            "from": sender,
            "to": [user.email],
            "subject": subject,
            "html": html,
        })
        return

    # Local development fallback. The OTP appears in the backend console.
    send_mail(
        subject=subject,
        message=f"Your Nexvia password change OTP is {otp}. It expires in 10 minutes.",
        from_email=sender,
        recipient_list=[user.email],
        html_message=html,
        fail_silently=False,
    )


class PasswordChangeRequestView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        if not user.email:
            return Response(
                {"detail": "Your account does not have an email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        # Carry rate-limit state forward across verified and consumed
        # challenges so a new challenge cannot reset the hourly quota.
        latest = (
            PasswordChangeChallenge.objects
            .filter(user=user)
            .order_by("-created_at")
            .first()
        )

        if latest and now - latest.last_sent_at < OTP_RESEND_COOLDOWN:
            remaining = int(
                (
                    OTP_RESEND_COOLDOWN
                    - (now - latest.last_sent_at)
                ).total_seconds()
            )
            return Response(
                {
                    "detail": "Please wait before requesting another code.",
                    "retry_after": max(1, remaining),
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        if latest and now - latest.window_started_at < OTP_HOURLY_WINDOW:
            window_started_at = latest.window_started_at
            sent_count = latest.sent_count
        else:
            window_started_at = now
            sent_count = 0

        if sent_count >= OTP_MAX_EMAILS_PER_HOUR:
            return Response(
                {"detail": "Too many codes requested. Try again later."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp = f"{secrets.randbelow(1_000_000):06d}"

        # Send first. A provider failure must not consume cooldown or quota.
        try:
            send_password_change_email(user, otp)
        except Exception:
            return Response(
                {
                    "detail": (
                        "Unable to send the verification email. "
                        "Please try again later."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Create a fresh challenge ID. This prevents an older signed
        # authorization from becoming valid again after a later OTP verify.
        with transaction.atomic():
            PasswordChangeChallenge.objects.filter(
                user=user,
                consumed_at__isnull=True,
            ).update(
                consumed_at=now,
                otp_hash="",
            )

            PasswordChangeChallenge.objects.create(
                user=user,
                otp_hash=make_password(otp),
                expires_at=now + OTP_LIFETIME,
                last_sent_at=now,
                window_started_at=window_started_at,
                sent_count=sent_count + 1,
                attempts=0,
            )

        return prevent_caching(Response(
            {
                "message": "Verification code sent to your registered email.",
                "email_hint": (
                    user.email[:2] + "***@" + user.email.split("@")[-1]
                    if "@" in user.email else "***"
                ),
                "expires_in": int(OTP_LIFETIME.total_seconds()),
                "resend_after": int(OTP_RESEND_COOLDOWN.total_seconds()),
            },
            status=status.HTTP_200_OK,
        ))


class PasswordChangeVerifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        otp = str(request.data.get("otp", "")).strip()

        if len(otp) != 6 or not otp.isdigit():
            return Response(
                {"detail": "Enter a valid six-digit verification code."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        with transaction.atomic():
            challenge = (
                PasswordChangeChallenge.objects
                .select_for_update()
                .filter(
                    user=request.user,
                    consumed_at__isnull=True,
                    verified_at__isnull=True,
                )
                .order_by("-created_at")
                .first()
            )

            if not challenge or not challenge.otp_hash:
                return Response(
                    {"detail": "No active verification request. Request a new code."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if now >= challenge.expires_at:
                challenge.otp_hash = ""
                challenge.save(update_fields=["otp_hash"])
                return Response(
                    {"detail": "Verification code expired. Request a new one."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if challenge.attempts >= OTP_MAX_ATTEMPTS:
                return Response(
                    {"detail": "Too many incorrect attempts. Request a new code."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

            if not check_password(otp, challenge.otp_hash):
                challenge.attempts += 1
                challenge.save(update_fields=["attempts"])
                return Response(
                    {"detail": "Incorrect verification code."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            challenge.verified_at = now
            challenge.save(update_fields=["verified_at"])

        authorization = signing.dumps(
            {
                "challenge_id": str(challenge.pk),
                "user_id": request.user.pk,
            },
            salt=PASSWORD_CHANGE_TOKEN_SALT,
        )

        return prevent_caching(Response(
            {
                "message": "Email verified. You can now choose a new password.",
                "authorization": authorization,
                "expires_in": PASSWORD_CHANGE_TOKEN_LIFETIME,
            },
            status=status.HTTP_200_OK,
        ))


class PasswordChangeConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        authorization = request.data.get("authorization", "")
        new_password = request.data.get("new_password", "")
        password_confirm = request.data.get("password_confirm", "")

        if not authorization:
            return Response(
                {"detail": "Password change verification is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not new_password or not password_confirm:
            return Response(
                {"detail": "Both password fields are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_password != password_confirm:
            return Response(
                {"password_confirm": ["Passwords do not match."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payload = signing.loads(
                authorization,
                salt=PASSWORD_CHANGE_TOKEN_SALT,
                max_age=PASSWORD_CHANGE_TOKEN_LIFETIME,
            )
        except signing.SignatureExpired:
            return Response(
                {"detail": "Verification expired. Request a new code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except signing.BadSignature:
            return Response(
                {"detail": "Invalid password change authorization."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if str(payload.get("user_id")) != str(request.user.pk):
            return Response(
                {"detail": "This verification does not belong to your account."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            validate_password(new_password, user=request.user)
        except DjangoValidationError as error:
            return Response(
                {"new_password": list(error.messages)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()

        with transaction.atomic():
            challenge = (
                PasswordChangeChallenge.objects
                .select_for_update()
                .filter(
                    pk=payload.get("challenge_id"),
                    user=request.user,
                    verified_at__isnull=False,
                    consumed_at__isnull=True,
                )
                .first()
            )

            if not challenge:
                return Response(
                    {"detail": "This verification has already been used or is invalid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if now - challenge.verified_at > timedelta(
                seconds=PASSWORD_CHANGE_TOKEN_LIFETIME
            ):
                return Response(
                    {"detail": "Verification expired. Request a new code."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = request.user
            user.set_password(new_password)
            user.save(update_fields=["password"])

            challenge.consumed_at = now
            challenge.otp_hash = ""
            challenge.save(update_fields=["consumed_at", "otp_hash"])

            # Revoke every outstanding refresh token for this account.
            outstanding_tokens = OutstandingToken.objects.filter(user=user)

            for outstanding in outstanding_tokens:
                BlacklistedToken.objects.get_or_create(token=outstanding)

        response = Response(
            {
                "message": "Password changed successfully. Please log in again."
            },
            status=status.HTTP_200_OK,
        )
        clear_refresh_cookie(response)
        return prevent_caching(response)


# --------------------------------------------------
# ACCOUNT DELETION
# --------------------------------------------------

class AccountDeletionImpactView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from core.models import WorkspaceMembership

        memberships = (
            WorkspaceMembership.objects
            .filter(user=request.user)
            .select_related("workspace")
            .order_by("workspace__name")
        )

        owned = []
        leaving = []

        for membership in memberships:
            workspace = membership.workspace
            other_members = WorkspaceMembership.objects.filter(
                workspace=workspace
            ).exclude(user=request.user)

            item = {
                "id": workspace.pk,
                "name": workspace.name,
                "other_member_count": other_members.count(),
            }

            if membership.role == "owner":
                owned.append(item)
            else:
                leaving.append({
                    **item,
                    "role": membership.role,
                })

        return Response({
            "owned_workspace_count": len(owned),
            "leaving_workspace_count": len(leaving),
            "owned_workspaces": owned,
            "leaving_workspaces": leaving,
            "confirmation_phrase": "DELETE MY ACCOUNT",
        })


class AccountDeletionConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        from core.models import (
            Workspace,
            WorkspaceMembership,
            IssueComment,
            IssueAttachment,
        )

        user = request.user
        current_password = request.data.get("current_password", "")
        confirmation = request.data.get("confirmation", "")

        if not isinstance(current_password, str) or not current_password:
            return Response(
                {"detail": "Enter your current password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user.check_password(current_password):
            return Response(
                {"detail": "Your current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if confirmation != "DELETE MY ACCOUNT":
            return Response(
                {"detail": "Type DELETE MY ACCOUNT exactly to confirm."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Lock this user's memberships and the workspaces being deleted.
        memberships = list(
            WorkspaceMembership.objects
            .select_for_update()
            .filter(user=user)
            .select_related("workspace")
        )

        owned_ids = [
            membership.workspace_id
            for membership in memberships
            if membership.role == "owner"
        ]

        leaving_ids = [
            membership.workspace_id
            for membership in memberships
            if membership.role != "owner"
        ]

        owned_workspaces = Workspace.objects.filter(
            pk__in=owned_ids
        ).select_for_update()

        # Keep shared project history in workspaces that survive.
        # These records become unattributed rather than being deleted.
        IssueComment.objects.filter(author=user).update(author=None)
        IssueAttachment.objects.filter(uploaded_by=user).update(uploaded_by=None)

        # Delete every workspace this account owns. Workspace-owned
        # records cascade with that workspace, as intended by the owner.
        deleted_workspace_count = owned_workspaces.count()
        owned_workspaces.delete()

        # Leave every other workspace without deleting its data.
        WorkspaceMembership.objects.filter(
            user=user,
            workspace_id__in=leaving_ids,
        ).delete()

        # Revoke outstanding refresh tokens before deleting the account.
        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)

        # The user deletion removes Profile, remaining memberships,
        # project assignments/memberships and password challenges.
        user.delete()

        response = Response(
            {
                "detail": "Your account and owned workspaces have been permanently deleted.",
                "deleted_workspace_count": deleted_workspace_count,
                "left_workspace_count": len(leaving_ids),
            },
            status=status.HTTP_200_OK,
        )
        clear_refresh_cookie(response)
        response["Cache-Control"] = "no-store"
        return response


# --------------------------------------------------
# WORKSPACE DATA EXPORT
# --------------------------------------------------

class WorkspaceDataExportView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        from core.models import WorkspaceMembership
        from core.views import accessible_projects_for_user
        from .data_export import build_workspace_pdf, email_workspace_exports

        workspace_ids = request.data.get("workspace_ids")

        # Backward compatibility with the original single-workspace payload.
        if workspace_ids is None and request.data.get("workspace_id") is not None:
            workspace_ids = [request.data.get("workspace_id")]

        if not isinstance(workspace_ids, list) or not workspace_ids:
            return Response(
                {"detail": "Select at least one workspace to export."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reject duplicate IDs and malformed values before querying.
        normalized_ids = []
        for value in workspace_ids:
            try:
                workspace_id = int(value)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "One or more selected workspace IDs are invalid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if workspace_id <= 0:
                return Response(
                    {"detail": "One or more selected workspace IDs are invalid."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if workspace_id not in normalized_ids:
                normalized_ids.append(workspace_id)

        if len(normalized_ids) > 25:
            return Response(
                {"detail": "You can export up to 25 workspaces in one request."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.email:
            return Response(
                {"detail": "Your account does not have a registered email address."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate ALL memberships before generating any PDF.
        memberships = list(
            WorkspaceMembership.objects
            .filter(user=request.user, workspace_id__in=normalized_ids)
            .select_related("workspace")
        )
        membership_by_id = {m.workspace_id: m for m in memberships}

        if len(membership_by_id) != len(normalized_ids):
            return Response(
                {"detail": "One or more workspaces were not found or access was denied."},
                status=status.HTTP_404_NOT_FOUND,
            )

        exports = []
        export_details = []

        try:
            for workspace_id in normalized_ids:
                membership = membership_by_id[workspace_id]
                workspace = membership.workspace

                projects = accessible_projects_for_user(request.user).filter(
                    workspace_id=workspace.pk
                )

                pdf_bytes = build_workspace_pdf(
                    workspace=workspace,
                    projects=projects,
                    include_admin_data=membership.role in ("owner", "admin"),
                )

                exports.append((workspace, pdf_bytes))
                export_details.append({
                    "workspace_id": workspace.pk,
                    "workspace_name": workspace.name,
                    "filename": f"nexvia-{workspace.slug}-export.pdf",
                })

            delivery = email_workspace_exports(request.user, exports)

        except Exception:
            import logging
            logging.getLogger(__name__).exception(
                "Multi-workspace export failed for user %s and workspace IDs %s",
                request.user.pk,
                normalized_ids,
            )
            return Response(
                {"detail": "The export could not be generated or emailed. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "detail": "Workspace export email accepted successfully.",
                "workspace_count": len(exports),
                "workspaces": export_details,
                "recipient": request.user.email,
                **delivery,
            },
            status=status.HTTP_200_OK,
        )
