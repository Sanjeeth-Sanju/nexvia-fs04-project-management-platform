
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
