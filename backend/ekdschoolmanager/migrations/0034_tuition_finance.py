import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("ekdschoolmanager", "0033_delete_academicperiod"),
    ]

    operations = [
        migrations.CreateModel(name="TuitionFeePlan", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("tuition_fee", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="écolage")),
            ("registration_fee", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="frais d’inscription")),
            ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
            ("academic_year", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tuition_fee_plans", to="ekdschoolmanager.academicyear")),
            ("school", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tuition_fee_plans", to="ekdschoolmanager.school")),
            ("school_class", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="tuition_fee_plan", to="ekdschoolmanager.schoolclass")),
        ], options={"ordering": ["school_class__level__order", "school_class__group"], "verbose_name": "barème de scolarité", "verbose_name_plural": "barèmes de scolarité"}),
        migrations.CreateModel(name="TuitionFeeRule", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("student_status", models.CharField(blank=True, choices=[("nouveau", "Nouveau"), ("redoublant", "Redoublant"), ("abandon", "Abandon"), ("bachelier", "Bachelier")], max_length=12, verbose_name="statut")),
            ("gender", models.CharField(blank=True, choices=[("M", "Masculin"), ("F", "Féminin")], max_length=1, verbose_name="genre")),
            ("tuition_fee", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="écolage")),
            ("registration_fee", models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name="frais d’inscription")),
            ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="rules", to="ekdschoolmanager.tuitionfeeplan")),
        ], options={"ordering": ["student_status", "gender"]}),
        migrations.CreateModel(name="TuitionInstallment", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("name", models.CharField(max_length=80, verbose_name="nom")), ("percentage", models.DecimalField(decimal_places=2, max_digits=5, verbose_name="pourcentage")),
            ("due_date", models.DateField(blank=True, null=True, verbose_name="échéance")), ("order", models.PositiveSmallIntegerField(verbose_name="ordre")),
            ("plan", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="installments", to="ekdschoolmanager.tuitionfeeplan")),
        ], options={"ordering": ["order"]}),
        migrations.CreateModel(name="TuitionPayment", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("fee_type", models.CharField(choices=[("inscription", "Frais d’inscription"), ("ecolage", "Écolage")], max_length=12, verbose_name="type de frais")),
            ("amount", models.DecimalField(decimal_places=2, max_digits=12, verbose_name="montant")), ("paid_on", models.DateField(verbose_name="date de paiement")),
            ("method", models.CharField(choices=[("especes", "Espèces"), ("mobile_money", "Mobile Money"), ("banque", "Banque"), ("autre", "Autre")], default="especes", max_length=20, verbose_name="mode de paiement")),
            ("reference", models.CharField(blank=True, max_length=100, verbose_name="référence")), ("notes", models.TextField(blank=True, verbose_name="notes")), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("enrollment", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="tuition_payments", to="ekdschoolmanager.studentenrollment")),
            ("installment", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="payments", to="ekdschoolmanager.tuitioninstallment")),
            ("received_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="received_tuition_payments", to=settings.AUTH_USER_MODEL)),
        ], options={"ordering": ["-paid_on", "-created_at"]}),
        migrations.AddConstraint(model_name="tuitionfeeplan", constraint=models.CheckConstraint(condition=models.Q(("tuition_fee__gte", 0)), name="tuition_fee_non_negative")),
        migrations.AddConstraint(model_name="tuitionfeeplan", constraint=models.CheckConstraint(condition=models.Q(("registration_fee__gte", 0)), name="registration_fee_non_negative")),
        migrations.AddConstraint(model_name="tuitionfeerule", constraint=models.UniqueConstraint(fields=("plan", "student_status", "gender"), name="unique_tuition_rule_criteria")),
        migrations.AddConstraint(model_name="tuitionfeerule", constraint=models.CheckConstraint(condition=models.Q(("gender", ""), ("student_status", ""), _negated=True), name="tuition_rule_has_criterion")),
        migrations.AddConstraint(model_name="tuitionfeerule", constraint=models.CheckConstraint(condition=models.Q(("tuition_fee__gte", 0)), name="rule_tuition_fee_non_negative")),
        migrations.AddConstraint(model_name="tuitionfeerule", constraint=models.CheckConstraint(condition=models.Q(("registration_fee__gte", 0)), name="rule_registration_fee_non_negative")),
        migrations.AddConstraint(model_name="tuitioninstallment", constraint=models.UniqueConstraint(fields=("plan", "order"), name="unique_installment_order_per_plan")),
        migrations.AddConstraint(model_name="tuitioninstallment", constraint=models.CheckConstraint(condition=models.Q(("percentage__gt", 0), ("percentage__lte", 100)), name="installment_percentage_range")),
        migrations.AddConstraint(model_name="tuitionpayment", constraint=models.CheckConstraint(condition=models.Q(("amount__gt", 0)), name="tuition_payment_amount_positive")),
        migrations.AddConstraint(model_name="tuitionpayment", constraint=models.CheckConstraint(condition=models.Q(models.Q(("fee_type", "ecolage"), ("installment__isnull", False)), models.Q(("fee_type", "inscription"), ("installment__isnull", True)), _connector="OR"), name="payment_installment_matches_fee_type")),
    ]
