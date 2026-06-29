from django.contrib import admin

from accounts.models import OTP, PhoneNumber, User, UserProfile


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "phone", "email", "is_staff", "is_active")
    search_fields = ("username", "phone", "email")
    list_filter = ("is_staff", "is_active")


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "sex", "dob", "role", "sub_role")
    search_fields = ("user__username",)
    list_filter = ("role", "sub_role", "sex")


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("pk", "phone", "email", "expires_at")
    search_fields = ("phone", "email")


@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display = ("phone", "user", "verified", "primary")
    search_fields = ("phone",)
    list_filter = ("verified", "primary")
