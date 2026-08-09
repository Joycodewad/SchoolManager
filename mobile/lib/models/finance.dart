import 'session.dart';

/// Paiement d'écolage encaissé.
class FeePayment {
  FeePayment({
    required this.id,
    required this.studentName,
    required this.className,
    required this.moduleName,
    required this.amount,
    required this.paidOn,
    required this.methodLabel,
    required this.reference,
    this.installmentName,
    this.receivedByName = '',
  });

  factory FeePayment.fromJson(Map<String, dynamic> json) => FeePayment(
        id: asInt(json['id']) ?? 0,
        studentName: asText(json['student_name']),
        className: asText(json['class_name']),
        moduleName: asText(json['module_name']),
        amount: asDouble(json['amount']) ?? 0,
        paidOn: asText(json['paid_on']),
        methodLabel: asText(json['method_label']),
        reference: asText(json['reference']),
        installmentName: json['installment_name'] as String?,
        receivedByName: asText(json['received_by_name']),
      );

  final int id;
  final String studentName;
  final String className;
  final String moduleName;
  final double amount;
  final String paidOn;
  final String methodLabel;
  final String reference;
  final String? installmentName;
  final String receivedByName;
}

/// Ligne de conformité : ce qu'un élève doit et ce qu'il a versé.
class ComplianceStudent {
  ComplianceStudent({
    required this.enrollment,
    required this.enrollmentNumber,
    required this.studentName,
    required this.expected,
    required this.paid,
    required this.balance,
    required this.isCompliant,
  });

  factory ComplianceStudent.fromJson(Map<String, dynamic> json) =>
      ComplianceStudent(
        enrollment: asInt(json['enrollment']) ?? 0,
        enrollmentNumber: asText(json['enrollment_number']),
        studentName: asText(json['student_name']),
        expected: asDouble(json['expected']) ?? 0,
        paid: asDouble(json['paid']) ?? 0,
        balance: asDouble(json['balance']) ?? 0,
        isCompliant: json['is_compliant'] == true,
      );

  final int enrollment;
  final String enrollmentNumber;
  final String studentName;
  final double expected;
  final double paid;
  final double balance;
  final bool isCompliant;
}

/// Rapport de conformité d'une classe.
class ComplianceReport {
  ComplianceReport({
    required this.compliantCount,
    required this.nonCompliantCount,
    required this.students,
    required this.target,
  });

  factory ComplianceReport.fromJson(Map<String, dynamic> json) =>
      ComplianceReport(
        compliantCount: asInt(json['compliant_count']) ?? 0,
        nonCompliantCount: asInt(json['non_compliant_count']) ?? 0,
        target: asText(json['target']),
        students: (json['students'] as List? ?? [])
            .map((item) => ComplianceStudent.fromJson(item as Map<String, dynamic>))
            .toList(),
      );

  final int compliantCount;
  final int nonCompliantCount;
  final String target;
  final List<ComplianceStudent> students;

  double get collected =>
      students.fold(0.0, (total, student) => total + student.paid);

  double get outstanding => students.fold(
        0.0,
        // Un solde négatif est un trop-perçu : il ne vient pas effacer le
        // reste à recouvrer des autres élèves.
        (total, student) => total + (student.balance > 0 ? student.balance : 0),
      );
}

/// Dépense de l'école.
class SchoolExpense {
  SchoolExpense({
    required this.id,
    required this.label,
    required this.categoryName,
    required this.amount,
    required this.expenseDate,
    required this.methodLabel,
    this.beneficiary = '',
  });

  factory SchoolExpense.fromJson(Map<String, dynamic> json) => SchoolExpense(
        id: asInt(json['id']) ?? 0,
        label: asText(json['label']),
        categoryName: asText(json['category_name']),
        amount: asDouble(json['amount']) ?? 0,
        expenseDate: asText(json['expense_date']),
        methodLabel: asText(json['method_label']),
        beneficiary: asText(json['beneficiary']),
      );

  final int id;
  final String label;
  final String categoryName;
  final double amount;
  final String expenseDate;
  final String methodLabel;
  final String beneficiary;
}

/// Classe dotée d'une grille d'écolage, pour choisir un périmètre.
class FeePlanSummary {
  FeePlanSummary({
    required this.id,
    required this.schoolClass,
    required this.className,
    required this.levelName,
  });

  factory FeePlanSummary.fromJson(Map<String, dynamic> json) => FeePlanSummary(
        id: asInt(json['id']) ?? 0,
        schoolClass: asInt(json['school_class']) ?? 0,
        className: asText(json['class_name']),
        levelName: asText(json['level_name']),
      );

  final int id;
  final int schoolClass;
  final String className;
  final String levelName;
}
