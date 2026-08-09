import '../core/roles.dart';

/// Petit utilitaire : le JSON de l'API mêle nombres et chaînes selon les
/// vues (les montants sont des `Decimal` sérialisés en texte).
int? asInt(dynamic value) {
  if (value is int) return value;
  if (value is num) return value.toInt();
  if (value is String) return int.tryParse(value);
  return null;
}

double? asDouble(dynamic value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value);
  return null;
}

String asText(dynamic value) => value == null ? '' : '$value';

/// Utilisateur connecté.
class AuthUser {
  AuthUser({
    required this.id,
    required this.username,
    required this.firstNames,
    required this.lastName,
    required this.role,
    required this.roleLabel,
    required this.isSuperuser,
    this.phone,
    this.email,
  });

  factory AuthUser.fromJson(Map<String, dynamic> json) => AuthUser(
        id: asInt(json['id']) ?? 0,
        username: asText(json['username']),
        firstNames: asText(json['first_names']),
        lastName: asText(json['last_name']),
        role: asText(json['role']),
        roleLabel: asText(json['role_label']),
        isSuperuser: json['is_superuser'] == true,
        phone: json['phone'] as String?,
        email: json['email'] as String?,
      );

  final int id;
  final String username;
  final String firstNames;
  final String lastName;
  final String role;
  final String roleLabel;
  final bool isSuperuser;
  final String? phone;
  final String? email;

  String get fullName {
    final name = '$lastName $firstNames'.trim();
    return name.isEmpty ? username : name;
  }

  /// Initiales pour l'avatar, à partir du nom affiché.
  String get initials {
    final parts = fullName.split(RegExp(r'\s+')).where((p) => p.isNotEmpty);
    if (parts.isEmpty) return '?';
    return parts.take(2).map((part) => part[0].toUpperCase()).join();
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'username': username,
        'first_names': firstNames,
        'last_name': lastName,
        'role': role,
        'role_label': roleLabel,
        'is_superuser': isSuperuser,
        'phone': phone,
        'email': email,
      };
}

/// École accessible, avec le rôle qu'y tient l'utilisateur.
///
/// C'est `user_role` qui compte, pas le rôle global : la même personne peut
/// être enseignante ici et censeur ailleurs.
class SchoolSummary {
  SchoolSummary({
    required this.id,
    required this.name,
    required this.code,
    required this.userRole,
    this.logo,
  });

  factory SchoolSummary.fromJson(Map<String, dynamic> json) => SchoolSummary(
        id: asInt(json['id']) ?? 0,
        name: asText(json['name']),
        code: asText(json['code']),
        userRole: asText(json['user_role']),
        logo: json['logo'] as String?,
      );

  final int id;
  final String name;
  final String code;
  final String userRole;
  final String? logo;

  AppRole get role => AppRole.fromValue(userRole);

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'code': code,
        'user_role': userRole,
        'logo': logo,
      };
}

/// Année académique de l'école sélectionnée.
class AcademicYearSummary {
  AcademicYearSummary({
    required this.id,
    required this.name,
    required this.isActive,
    required this.isClosed,
  });

  factory AcademicYearSummary.fromJson(Map<String, dynamic> json) =>
      AcademicYearSummary(
        id: asInt(json['id']) ?? 0,
        name: asText(json['name']),
        isActive: json['is_active'] == true,
        isClosed: json['is_closed'] == true,
      );

  final int id;
  final String name;
  final bool isActive;
  final bool isClosed;

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'is_active': isActive,
        'is_closed': isClosed,
      };
}
