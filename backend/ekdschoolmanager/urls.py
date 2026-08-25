from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import AcademicSessionDetailView, AcademicSessionListView, AcademicYearViewSet, AnnouncementDetailView, AnnouncementListView, AssignmentSettingsView, AttendanceSessionListView, AttendanceSheetView, CarriedDebtListView, ConversationDetailView, ConversationListView, MessageRecipientsView, CustomUserViewSet, DisciplineRecordListView, EnrollmentNumberSuggestionView, ExpenseCategoryListView, GradeContextView, GradeSchemeSourceView, GradeSchemeView, GradeSheetView, LoginView, LogoutView, MySignatureView, MyTimetableView, OwnerViewSet, ParentListView, PromotionThresholdView, YearEndDecisionView, ReportCardExportView, ReportCardGenerationView, ReportCardSettingsView, ReportCardView, RoleChoicesView, SchoolClassViewSet, SchoolExpenseDetailView, SchoolExpenseListView, SchoolLevelViewSet, SchoolViewSet, StudentEnrollmentViewSet, StudentJourneyView, SubjectCategoryViewSet, SubjectViewSet, TeacherViewSet, TimetableExportView, TimetableSetupView, TimetableValidationView, TimetableView, TuitionComplianceView, TuitionFeePlanDetailView, TuitionFeePlanListView, TuitionPaymentListView, UsernameSuggestionView

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
    path("me/signature/", MySignatureView.as_view(), name="my-signature"),
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
        "schools/<int:school_pk>/subject-categories/",
        SubjectCategoryViewSet.as_view({"get": "list", "post": "create"}),
        name="school-subject-categories",
    ),
    path(
        "schools/<int:school_pk>/subject-categories/<int:pk>/",
        SubjectCategoryViewSet.as_view({"get": "retrieve", "patch": "partial_update", "delete": "destroy"}),
        name="school-subject-category-detail",
    ),
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
        "schools/<int:school_pk>/academic-years/<int:pk>/reopen/",
        AcademicYearViewSet.as_view({"post": "reopen"}),
        name="reopen-academic-year",
    ),
    path(
        "schools/<int:school_pk>/academic-years/<int:pk>/closure-preview/",
        AcademicYearViewSet.as_view({"get": "closure_preview"}),
        name="academic-year-closure-preview",
    ),
    path("schools/<int:school_pk>/academic-years/<int:year_pk>/sessions/", AcademicSessionListView.as_view(), name="academic-sessions"),
    path("schools/<int:school_pk>/academic-years/<int:year_pk>/sessions/<int:pk>/", AcademicSessionDetailView.as_view(), name="academic-session-detail"),
    path("schools/<int:school_pk>/academic-years/<int:year_pk>/sessions/<int:pk>/close/", AcademicSessionDetailView.as_view(), name="academic-session-close"),
    path(
        "schools/<int:school_pk>/enrollments/",
        StudentEnrollmentViewSet.as_view({"get": "list", "post": "create"}),
        name="student-enrollments",
    ),
    path("schools/<int:school_pk>/students/journey/", StudentJourneyView.as_view(), name="student-journey"),
    path(
        "schools/<int:school_pk>/enrollments/assignment-settings/",
        AssignmentSettingsView.as_view(),
        name="assignment-settings",
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
        "schools/<int:school_pk>/enrollments/unassigned/",
        StudentEnrollmentViewSet.as_view({"get": "unassigned"}),
        name="student-enrollments-unassigned",
    ),
    path(
        "schools/<int:school_pk>/enrollments/guardian-lookup/",
        StudentEnrollmentViewSet.as_view({"get": "guardian_lookup"}),
        name="student-enrollments-guardian-lookup",
    ),
    path(
        "schools/<int:school_pk>/enrollments/auto-assign/",
        StudentEnrollmentViewSet.as_view({"post": "auto_assign"}),
        name="student-enrollments-auto-assign",
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
    path("schools/<int:school_pk>/finance/tuition-plans/", TuitionFeePlanListView.as_view(), name="tuition-fee-plans"),
    path("schools/<int:school_pk>/finance/tuition-plans/<int:pk>/", TuitionFeePlanDetailView.as_view(), name="tuition-fee-plan-detail"),
    path("schools/<int:school_pk>/finance/tuition-plans/<int:pk>/copy/", TuitionFeePlanDetailView.as_view(), name="tuition-fee-plan-copy"),
    path("schools/<int:school_pk>/finance/payments/", TuitionPaymentListView.as_view(), name="tuition-payments"),
    path("schools/<int:school_pk>/finance/compliance/", TuitionComplianceView.as_view(), name="tuition-compliance"),
    path("schools/<int:school_pk>/finance/carried-debts/", CarriedDebtListView.as_view(), name="carried-debts"),
    path("schools/<int:school_pk>/finance/expense-categories/", ExpenseCategoryListView.as_view(), name="expense-categories"),
    path("schools/<int:school_pk>/finance/expenses/", SchoolExpenseListView.as_view(), name="school-expenses"),
    path("schools/<int:school_pk>/finance/expenses/<int:pk>/", SchoolExpenseDetailView.as_view(), name="school-expense-detail"),
    path("schools/<int:school_pk>/discipline/records/", DisciplineRecordListView.as_view(), name="discipline-records"),
    path("schools/<int:school_pk>/attendance/sessions/", AttendanceSessionListView.as_view(), name="attendance-sessions"),
    path("schools/<int:school_pk>/attendance/sheet/", AttendanceSheetView.as_view(), name="attendance-sheet"),
    path("schools/<int:school_pk>/announcements/", AnnouncementListView.as_view(), name="announcements"),
    path("schools/<int:school_pk>/announcements/<int:pk>/", AnnouncementDetailView.as_view(), name="announcement-detail"),
    path("schools/<int:school_pk>/conversations/", ConversationListView.as_view(), name="conversations"),
    path("schools/<int:school_pk>/conversations/<int:pk>/", ConversationDetailView.as_view(), name="conversation-detail"),
    path("schools/<int:school_pk>/conversations/recipients/", MessageRecipientsView.as_view(), name="message-recipients"),
    path("schools/<int:school_pk>/grades/contexts/", GradeContextView.as_view(), name="grade-contexts"),
    path("schools/<int:school_pk>/grades/scheme-sources/", GradeSchemeSourceView.as_view(), name="grade-scheme-sources"),
    path("schools/<int:school_pk>/grades/sessions/<int:session_pk>/scheme/", GradeSchemeView.as_view(), name="grade-scheme"),
    path("schools/<int:school_pk>/grades/sessions/<int:session_pk>/subjects/<int:class_subject_pk>/", GradeSheetView.as_view(), name="grade-sheet"),
    path("schools/<int:school_pk>/parents/", ParentListView.as_view(), name="school-parents"),
    path("schools/<int:school_pk>/timetable/", TimetableView.as_view(), name="school-timetable"),
    path("schools/<int:school_pk>/timetable/setup/", TimetableSetupView.as_view(), name="school-timetable-setup"),
    path("schools/<int:school_pk>/timetable/validate/", TimetableValidationView.as_view(), name="school-timetable-validate"),
    path("schools/<int:school_pk>/timetable/export/", TimetableExportView.as_view(), name="school-timetable-export"),
    path("schools/<int:school_pk>/timetable/mine/", MyTimetableView.as_view(), name="school-timetable-mine"),
    path("schools/<int:school_pk>/report-cards/sessions/<int:session_pk>/classes/<int:class_pk>/", ReportCardView.as_view(), name="report-cards"),
    path("schools/<int:school_pk>/report-cards/settings/", ReportCardSettingsView.as_view(), name="report-card-settings"),
    path("schools/<int:school_pk>/report-cards/promotion/", PromotionThresholdView.as_view(), name="promotion-thresholds"),
    path("schools/<int:school_pk>/report-cards/sessions/<int:session_pk>/year-end/", YearEndDecisionView.as_view(), name="year-end-decisions"),
    path("schools/<int:school_pk>/report-cards/sessions/<int:session_pk>/generate/", ReportCardGenerationView.as_view(), name="report-card-generate"),
    path("schools/<int:school_pk>/report-cards/sessions/<int:session_pk>/export/", ReportCardExportView.as_view(), name="report-card-export"),
    *router.urls,
]
