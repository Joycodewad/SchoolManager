from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AcademicYear, CustomUser, School, SchoolLevel, SchoolMembership, StudentEnrollment, Subject


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    ordering = ("last_name", "first_name")
    list_display = ("last_name", "first_name", "phone", "role", "is_active", "is_archived")
    search_fields = ("last_name", "first_name", "email", "phone")
    list_filter = ("role", "gender", "is_active", "is_archived")
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Identité", {"fields": ("last_name", "first_name", "email", "phone", "gender")}),
        ("Établissement", {"fields": ("role", "subjects", "primary_subject", "is_archived")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "owner", "is_active")
    search_fields = ("name", "code", "owner__phone")


@admin.register(SchoolMembership)
class SchoolMembershipAdmin(admin.ModelAdmin):
    list_display = ("school", "user", "role", "is_active")
    list_filter = ("school", "role", "is_active")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "school", "is_active")
    list_filter = ("school", "is_active")
    search_fields = ("name", "code")


@admin.register(AcademicYear)
class AcademicYearAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "start_date", "end_date", "is_active", "is_closed")
    list_filter = ("school", "is_active", "is_closed")


@admin.register(StudentEnrollment)
class StudentEnrollmentAdmin(admin.ModelAdmin):
    list_display = ("enrollment_number", "student", "school", "academic_year", "status", "enrolled_at")
    list_filter = ("school", "academic_year", "status")
    search_fields = ("enrollment_number", "student__last_name", "student__first_name")


@admin.register(SchoolLevel)
class SchoolLevelAdmin(admin.ModelAdmin):
    list_display = ("name", "stage", "school", "order", "is_active")
    list_filter = ("school", "stage", "is_active")
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("username", "password1", "password2", "role", "is_staff", "is_active")}),
    )
