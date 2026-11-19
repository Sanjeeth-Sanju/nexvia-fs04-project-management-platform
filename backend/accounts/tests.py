from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.hashers import check_password
from django.utils import timezone

from accounts.models import PasswordChangeChallenge


from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient


User = get_user_model()


class RegistrationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("register")

        self.valid_payload = {
            "username": "testuser",
            "email": "test@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "StrongTestPassword!2026",
            "password_confirm": "StrongTestPassword!2026",
        }

    def test_successful_registration(self):
        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username="testuser").exists())

        user = User.objects.get(username="testuser")

        self.assertTrue(
            user.check_password("StrongTestPassword!2026")
        )
        self.assertEqual(
            user.password.split("$")[0],
            "argon2",
        )

        self.assertNotIn("password", response.data["user"])
        self.assertNotIn("password_confirm", response.data["user"])

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            username="existinguser",
            email="test@example.com",
            password="AnotherStrongPassword!2026",
        )

        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_duplicate_username_is_rejected(self):
        User.objects.create_user(
            username="testuser",
            email="existing@example.com",
            password="AnotherStrongPassword!2026",
        )

        response = self.client.post(
            self.url,
            self.valid_payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_mismatch_is_rejected(self):
        payload = self.valid_payload.copy()
        payload["password_confirm"] = "DifferentPassword!2026"

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="testuser").exists())

    def test_weak_password_is_rejected(self):
        payload = self.valid_payload.copy()
        payload["password"] = "123"
        payload["password_confirm"] = "123"

        response = self.client.post(
            self.url,
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="testuser").exists())


from rest_framework_simplejwt.tokens import AccessToken


class LoginAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("login")

        self.password = "StrongLoginPassword!2026"

        self.user = User.objects.create_user(
            username="loginuser",
            email="login@example.com",
            password=self.password,
            first_name="Login",
            last_name="User",
        )

    def test_login_with_username(self):
        response = self.client.post(
            self.url,
            {
                "identifier": "loginuser",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)
        self.assertIn("user", response.data)

    def test_login_with_email(self):
        response = self.client.post(
            self.url,
            {
                "identifier": "login@example.com",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_invalid_password_is_rejected(self):
        response = self.client.post(
            self.url,
            {
                "identifier": "loginuser",
                "password": "WrongPassword!2026",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_inactive_user_cannot_login(self):
        self.user.is_active = False
        self.user.save()

        response = self.client.post(
            self.url,
            {
                "identifier": "loginuser",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_token_is_stored_in_httponly_cookie(self):
        response = self.client.post(
            self.url,
            {
                "identifier": "loginuser",
                "password": self.password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        cookie = response.cookies.get("refresh_token")

        self.assertIsNotNone(cookie)
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Lax")

        self.assertNotIn("refresh_token", response.data)

    def test_access_token_contains_correct_user(self):
        response = self.client.post(
            self.url,
            {
                "identifier": "loginuser",
                "password": self.password,
            },
            format="json",
        )

        token = AccessToken(response.data["access_token"])

        self.assertEqual(
            int(token["user_id"]),
            self.user.id,
        )

class SecureAuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)

        self.user = User.objects.create_user(
            username="secureuser",
            email="secure@example.com",
            password="StrongSecurePassword!2026",
        )

        self.csrf_url = reverse("csrf")
        self.login_url = reverse("login")
        self.refresh_url = reverse("refresh")
        self.logout_url = reverse("logout")
        self.me_url = reverse("current-user")

        # Obtain a CSRF cookie before making unsafe requests.
        self.client.get(self.csrf_url)

        self.csrf_token = self.client.cookies["csrftoken"].value

    def csrf_headers(self):
        return {
            "HTTP_X_CSRFTOKEN": self.csrf_token,
        }

    def login(self):
        response = self.client.post(
            self.login_url,
            {
                "identifier": "secureuser",
                "password": "StrongSecurePassword!2026",
            },
            format="json",
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response

    def test_refresh_returns_new_access_token(self):
        self.login()

        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access_token", response.data)

    def test_refresh_rotates_refresh_cookie(self):
        self.login()

        original_refresh = self.client.cookies[
            "refresh_token"
        ].value

        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            **self.csrf_headers(),
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        rotated_refresh = self.client.cookies[
            "refresh_token"
        ].value

        self.assertNotEqual(original_refresh, rotated_refresh)
        self.assertNotIn("refresh_token", response.data)

    def test_old_refresh_token_cannot_be_reused(self):
        self.login()

        original_refresh = self.client.cookies[
            "refresh_token"
        ].value

        first_response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            **self.csrf_headers(),
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )

        # Simulate an attempt to reuse the old refresh token.
        self.client.cookies["refresh_token"] = original_refresh

        replay_response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            **self.csrf_headers(),
        )

        self.assertEqual(
            replay_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_logout_blacklists_refresh_token(self):
        self.login()

        original_refresh = self.client.cookies[
            "refresh_token"
        ].value

        response = self.client.post(
            self.logout_url,
            {},
            format="json",
            **self.csrf_headers(),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )

        self.assertEqual(
            response.cookies["refresh_token"]["max-age"],
            0,
        )

        # A blacklisted token must not work after logout.
        self.client.cookies["refresh_token"] = original_refresh

        refresh_response = self.client.post(
            self.refresh_url,
            {},
            format="json",
            **self.csrf_headers(),
        )

        self.assertEqual(
            refresh_response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_current_user_with_valid_access_token(self):
        login_response = self.login()

        access_token = login_response.data["access_token"]

        response = self.client.get(
            self.me_url,
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.user.id)
        self.assertEqual(response.data["username"], "secureuser")

    def test_current_user_without_access_token_is_rejected(self):
        response = self.client.get(self.me_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_refresh_rejects_request_without_csrf_token(self):
        self.login()

        response = self.client.post(
            self.refresh_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_logout_rejects_request_without_csrf_token(self):
        self.login()

        response = self.client.post(
            self.logout_url,
            {},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )


class PasswordChangeSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="passworduser",
            email="password@example.com",
            password="StrongOriginalPassword!2026",
        )
        self.client.force_authenticate(user=self.user)

        self.request_url = reverse("password-change-request")
        self.verify_url = reverse("password-change-verify")
        self.confirm_url = reverse("password-change-confirm")

    def request_code(self):
        with patch("accounts.views.send_password_change_email") as send_email:
            response = self.client.post(
                self.request_url,
                {},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            otp = send_email.call_args.args[1]

        return response, otp

    def verify_code(self, otp):
        return self.client.post(
            self.verify_url,
            {"otp": otp},
            format="json",
        )

    def test_request_stores_hashed_otp(self):
        response, otp = self.request_code()

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        challenge = PasswordChangeChallenge.objects.get(user=self.user)

        self.assertTrue(challenge.otp_hash)
        self.assertNotEqual(challenge.otp_hash, otp)
        self.assertTrue(check_password(otp, challenge.otp_hash))
        self.assertEqual(challenge.sent_count, 1)

    def test_email_failure_does_not_create_challenge_or_consume_quota(self):
        with patch(
            "accounts.views.send_password_change_email",
            side_effect=RuntimeError("Email provider unavailable"),
        ):
            failed_response = self.client.post(
                self.request_url,
                {},
                format="json",
            )

        self.assertEqual(
            failed_response.status_code,
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
        self.assertFalse(
            PasswordChangeChallenge.objects.filter(user=self.user).exists()
        )

        # A subsequent request should be allowed immediately.
        self.request_code()

        self.assertEqual(
            PasswordChangeChallenge.objects.filter(user=self.user).count(),
            1,
        )

    def test_resend_cooldown_is_enforced(self):
        self.request_code()

        with patch("accounts.views.send_password_change_email") as send_email:
            response = self.client.post(
                self.request_url,
                {},
                format="json",
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )
        send_email.assert_not_called()

    def test_incorrect_otp_attempts_are_limited(self):
        _, correct_otp = self.request_code()

        wrong_otp = "999999" if correct_otp != "999999" else "000000"

        for _ in range(5):
            response = self.verify_code(wrong_otp)
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
            )

        blocked_response = self.verify_code(wrong_otp)

        self.assertEqual(
            blocked_response.status_code,
            status.HTTP_429_TOO_MANY_REQUESTS,
        )

        challenge = PasswordChangeChallenge.objects.get(user=self.user)
        self.assertEqual(challenge.attempts, 5)

    def test_expired_otp_is_rejected(self):
        _, otp = self.request_code()

        challenge = PasswordChangeChallenge.objects.get(user=self.user)
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save(update_fields=["expires_at"])

        response = self.verify_code(otp)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("expired", response.data["detail"].lower())

    def test_new_request_invalidates_previous_verified_authorization(self):
        _, first_otp = self.request_code()

        first_verify = self.verify_code(first_otp)
        self.assertEqual(first_verify.status_code, status.HTTP_200_OK)

        old_authorization = first_verify.data["authorization"]

        latest = PasswordChangeChallenge.objects.filter(
            user=self.user
        ).latest("created_at")

        later_time = latest.last_sent_at + timedelta(seconds=61)

        with patch("accounts.views.timezone.now", return_value=later_time):
            with patch("accounts.views.send_password_change_email"):
                second_request = self.client.post(
                    self.request_url,
                    {},
                    format="json",
                )

        self.assertEqual(second_request.status_code, status.HTTP_200_OK)

        old_challenge = PasswordChangeChallenge.objects.get(
            pk=latest.pk
        )
        self.assertIsNotNone(old_challenge.consumed_at)

        confirm_response = self.client.post(
            self.confirm_url,
            {
                "authorization": old_authorization,
                "new_password": "DifferentSecurePassword!2026",
                "password_confirm": "DifferentSecurePassword!2026",
            },
            format="json",
        )

        self.assertEqual(
            confirm_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertTrue(
            self.user.check_password("StrongOriginalPassword!2026")
        )

    def test_successful_password_change_consumes_authorization(self):
        _, otp = self.request_code()

        verify_response = self.verify_code(otp)
        self.assertEqual(verify_response.status_code, status.HTTP_200_OK)

        authorization = verify_response.data["authorization"]
        new_password = "DifferentSecurePassword!2026"

        confirm_response = self.client.post(
            self.confirm_url,
            {
                "authorization": authorization,
                "new_password": new_password,
                "password_confirm": new_password,
            },
            format="json",
        )

        self.assertEqual(
            confirm_response.status_code,
            status.HTTP_200_OK,
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))

        challenge = PasswordChangeChallenge.objects.get(user=self.user)
        self.assertIsNotNone(challenge.consumed_at)
        self.assertEqual(challenge.otp_hash, "")

        # The same signed authorization cannot be reused.
        reuse_response = self.client.post(
            self.confirm_url,
            {
                "authorization": authorization,
                "new_password": "AnotherSecurePassword!2026",
                "password_confirm": "AnotherSecurePassword!2026",
            },
            format="json",
        )

        self.assertEqual(
            reuse_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(new_password))
