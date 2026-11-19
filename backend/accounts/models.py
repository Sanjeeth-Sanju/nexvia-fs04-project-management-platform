from django.conf import settings
from django.db import models


def profile_avatar_upload_path(instance, filename):
    return f"avatars/user_{instance.user_id}/{filename}"


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    display_name = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(
        upload_to=profile_avatar_upload_path,
        blank=True,
        null=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile: {self.user}"


# --------------------------------------------------
# PASSWORD CHANGE OTP CHALLENGE
# --------------------------------------------------

import uuid


class PasswordChangeChallenge(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_change_challenges",
    )
    otp_hash = models.CharField(max_length=128, blank=True)
    expires_at = models.DateTimeField()
    last_sent_at = models.DateTimeField()
    window_started_at = models.DateTimeField()
    sent_count = models.PositiveSmallIntegerField(default=1)
    attempts = models.PositiveSmallIntegerField(default=0)
    verified_at = models.DateTimeField(null=True, blank=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]

    def __str__(self):
        return f"Password change challenge for user {self.user_id}"
