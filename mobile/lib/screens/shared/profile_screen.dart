import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../core/theme.dart';
import '../../state/session_state.dart';
import '../../widgets/screen_scaffold.dart';

/// Profil : identité, contexte de travail et déconnexion.
///
/// C'est aussi d'ici qu'on change d'école et d'année — les deux réglages qui
/// commandent tout le reste de l'application.
class ProfileScreen extends StatelessWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();
    final user = session.user;

    return ScreenScaffold(
      title: 'Profil',
      requiresYear: false,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 28,
                    backgroundColor: AppColors.tint,
                    child: Text(
                      user?.initials ?? '?',
                      style: const TextStyle(
                        color: AppColors.primaryDark,
                        fontWeight: FontWeight.w700,
                        fontSize: 18,
                      ),
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          user?.fullName ?? '',
                          style: const TextStyle(
                            fontSize: 16.5,
                            fontWeight: FontWeight.w700,
                            color: AppColors.navy,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          session.role.label,
                          style: const TextStyle(
                              fontSize: 13, color: AppColors.primary),
                        ),
                        if (user?.username != null)
                          Text(
                            '@${user!.username}',
                            style: const TextStyle(
                                fontSize: 12, color: AppColors.muted),
                          ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          if (user?.phone != null || user?.email != null)
            Card(
              child: Column(
                children: [
                  if (user?.phone != null && user!.phone!.isNotEmpty)
                    ListTile(
                      leading: const Icon(Icons.phone_outlined, size: 20),
                      title: const Text('Téléphone',
                          style: TextStyle(fontSize: 12.5, color: AppColors.muted)),
                      subtitle: Text(user.phone!,
                          style: const TextStyle(
                              fontSize: 14, color: AppColors.navy)),
                    ),
                  if (user?.email != null && user!.email!.isNotEmpty)
                    ListTile(
                      leading: const Icon(Icons.mail_outline, size: 20),
                      title: const Text('Courriel',
                          style: TextStyle(fontSize: 12.5, color: AppColors.muted)),
                      subtitle: Text(user.email!,
                          style: const TextStyle(
                              fontSize: 14, color: AppColors.navy)),
                    ),
                ],
              ),
            ),
          const SizedBox(height: 14),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.school_outlined, size: 20),
                  title: const Text('École',
                      style: TextStyle(fontSize: 12.5, color: AppColors.muted)),
                  subtitle: Text(
                    session.school?.name ?? 'Aucune',
                    style: const TextStyle(fontSize: 14, color: AppColors.navy),
                  ),
                  trailing: session.schools.length > 1
                      ? const Icon(Icons.chevron_right)
                      : null,
                  onTap: session.schools.length > 1
                      ? () => _pickSchool(context, session)
                      : null,
                ),
                if (session.years.isNotEmpty) ...[
                  const Divider(height: 1),
                  ListTile(
                    leading: const Icon(Icons.calendar_today_outlined, size: 20),
                    title: const Text('Année académique',
                        style:
                            TextStyle(fontSize: 12.5, color: AppColors.muted)),
                    subtitle: Text(
                      session.year?.name ?? 'Aucune',
                      style:
                          const TextStyle(fontSize: 14, color: AppColors.navy),
                    ),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => _pickYear(context, session),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 22),
          OutlinedButton.icon(
            onPressed: () => _confirmSignOut(context, session),
            icon: const Icon(Icons.logout, color: AppColors.danger),
            label: const Text('Se déconnecter',
                style: TextStyle(color: AppColors.danger)),
            style: OutlinedButton.styleFrom(
              minimumSize: const Size.fromHeight(50),
              side: const BorderSide(color: Color(0xFFFECACA)),
            ),
          ),
        ],
      ),
    );
  }

  void _pickSchool(BuildContext context, SessionState session) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final school in session.schools)
              ListTile(
                title: Text(school.name),
                subtitle: Text(school.role.label),
                trailing: session.school?.id == school.id
                    ? const Icon(Icons.check, color: AppColors.success)
                    : null,
                onTap: () {
                  Navigator.of(sheetContext).pop();
                  session.selectSchool(school);
                },
              ),
          ],
        ),
      ),
    );
  }

  void _pickYear(BuildContext context, SessionState session) {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (sheetContext) => SafeArea(
        child: ListView(
          shrinkWrap: true,
          children: [
            for (final year in session.years)
              ListTile(
                title: Text(year.name),
                subtitle: year.isClosed
                    ? const Text('Clôturée')
                    : year.isActive
                        ? const Text('En cours')
                        : null,
                trailing: session.year?.id == year.id
                    ? const Icon(Icons.check, color: AppColors.success)
                    : null,
                onTap: () {
                  Navigator.of(sheetContext).pop();
                  session.selectYear(year);
                },
              ),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmSignOut(
      BuildContext context, SessionState session) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text('Se déconnecter'),
        content: const Text('Voulez-vous fermer votre session ?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(false),
            child: const Text('Annuler'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(dialogContext).pop(true),
            child: const Text('Déconnexion'),
          ),
        ],
      ),
    );
    if (confirmed == true) await session.signOut();
  }
}
