from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import AcademicPeriodCloseView, AcademicYearViewSet, CustomUserViewSet, EnrollmentNumberSuggestionView, LoginView, LogoutView, OwnerViewSet, RoleChoicesView, SchoolClassViewSet, SchoolLevelViewSet, SchoolViewSet, StudentEnrollmentViewSet, SubjectViewSet, TeacherViewSet, UsernameSuggestionView

router = DefaultRouter()
router.register("teachers", TeacherViewSet, basename="teacher")
router.register("users", CustomUserViewSet, basename="user")
router.register("schools", SchoolViewSet, basename="school")
router.register("owners", OwnerViewSet, basename="owner")

urlpatterns = [
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path("usernames/suggest/", UsernameSuggestionView.as_view(), name="username-suggestion"),
    path("roles/", RoleChoicesView.as_view(), name="role-choices"),
    path(
        "schools/<int:school_pk>/teachers/",
        TeacherViewSet.as_view({"get": "list", "post": "create"}),
        name="school-teachers",
    ),
    path(
        "schools/<int:school_pk>/teachers/<int:pk>/",
        TeacherViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="school-teacher-detail",
    ),
    path("schools/<int:school_pk>/teachers/<int:pk>/classes/", TeacherViewSet.as_view({"get": "class_assignments", "post": "class_assignments"}), name="teacher-class-assignments"),
    path("schools/<int:school_pk>/teachers/<int:pk>/unavailability/", TeacherViewSet.as_view({"get": "unavailability", "post": "unavailability"}), name="teacher-unavailability"),
    path(
        "schools/<int:school_pk>/subjects/",
        SubjectViewSet.as_view({"get": "list", "post": "create"}),
        name="school-subjects",
    ),
    path(
        "schools/<int:school_pk>/subjects/<int:pk>/",
        SubjectViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="school-subject-detail",
    ),
    path(
        "schools/<int:school_pk>/academic-years/",
        AcademicYearViewSet.as_view({"get": "list", "post": "create"}),
        name="school-academic-years",
    ),
    path(
        "schools/<int:school_pk>/academic-years/<int:pk>/",
        AcademicYearViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="school-academic-year-detail",
    ),
    path(
        "schools/<int:school_pk>/academic-years/<int:pk>/close/",
        AcademicYearViewSet.as_view({"post": "close"}),
        name="close-academic-year",
    ),
    path(
        "schools/<int:school_pk>/academic-years/<int:year_pk>/periods/<int:period_pk>/close/",
        AcademicPeriodCloseView.as_view(),
        name="close-academic-period",
    ),
    path(
        "schools/<int:school_pk>/enrollments/",
        StudentEnrollmentViewSet.as_view({"get": "list", "post": "create"}),
        name="student-enrollments",
    ),
    path(
        "schools/<int:school_pk>/enrollments/suggest-number/",
        EnrollmentNumberSuggestionView.as_view(),
        name="enrollment-number-suggestion",
    ),
    path(
        "schools/<int:school_pk>/enrollments/import/",
        StudentEnrollmentViewSet.as_view({"post": "import_file"}),
        name="student-enrollments-import",
    ),
    path(
        "schools/<int:school_pk>/enrollments/<int:pk>/",
        StudentEnrollmentViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="student-enrollment-detail",
    ),
    path(
        "schools/<int:school_pk>/levels/",
        SchoolLevelViewSet.as_view({"get": "list"}),
        name="school-levels",
    ),
    path("schools/<int:school_pk>/classes/", SchoolClassViewSet.as_view({"get": "list", "post": "create"}), name="school-classes"),
    path("schools/<int:school_pk>/classes/<int:pk>/", SchoolClassViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}), name="school-class-detail"),
    *router.urls,
]
