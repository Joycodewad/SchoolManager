import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';

/// Choix de l'école quand l'utilisateur en dessert plusieurs.
///
/// Le rôle est rappelé sur chaque carte : la même personne peut être
/// enseignante ici et censeur ailleurs, et l'application ne montrera pas les
/// mêmes écrans selon celle qu'elle choisit.
class SchoolPickerScreen extends StatelessWidget {
  const SchoolPickerScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('Choisir une école'),
        actions: [
          IconButton(
            tooltip: 'Se déconnecter',
            icon: const Icon(Icons.logout),
            onPressed: () => session.signOut(),
          ),
        ],
      ),
      body: session.schools.isEmpty
          ? const EmptyState(
              icon: Icons.school_outlined,
              title: 'Aucune école',
              message:
                  'Votre compte n’est rattaché à aucune école active. '
                  'Contactez l’administration de votre établissement.',
            )
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: session.schools.length,
              separatorBuilder: (_, _) => const SizedBox(height: 10),
              itemBuilder: (context, index) {
                final school = session.schools[index];
                final selected = session.school?.id == school.id;
                return Card(
                  child: ListTile(
                    contentPadding:
                        const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
                    leading: CircleAvatar(
                      backgroundColor: AppColors.tint,
                      child: Text(
                        school.code.isEmpty
                            ? '?'
                            : school.code.substring(0, 1).toUpperCase(),
                        style: const TextStyle(
                          color: AppColors.primaryDark,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    title: Text(
                      school.name,
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(school.role.label),
                    trailing: selected
                        ? const Icon(Icons.check_circle,
                            color: AppColors.success)
                        : const Icon(Icons.chevron_right),
                    onTap: () => session.selectSchool(school),
                  ),
                );
              },
            ),
    );
  }
}
