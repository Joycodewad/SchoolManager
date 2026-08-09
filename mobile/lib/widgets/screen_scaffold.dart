import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/theme.dart';
import '../state/session_state.dart';
import 'common.dart';

/// Ossature commune aux écrans : titre, école et année en cours, contenu.
///
/// Le contexte (école, année) est affiché partout parce qu'il change le sens
/// de tout ce qui est à l'écran : les mêmes notes n'ont pas la même portée
/// d'une année à l'autre.
class ScreenScaffold extends StatelessWidget {
  const ScreenScaffold({
    super.key,
    required this.title,
    required this.child,
    this.subtitle,
    this.actions,
    this.floatingActionButton,
    this.requiresYear = true,
  });

  final String title;
  final String? subtitle;
  final Widget child;
  final List<Widget>? actions;
  final Widget? floatingActionButton;

  /// L'écran a besoin d'une année académique. La plupart des vues Django
  /// exigent `X-Academic-Year-ID` et échouent sans elle : mieux vaut le dire
  /// clairement que laisser passer une erreur technique.
  final bool requiresYear;

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();
    final blocked = requiresYear && session.year == null;

    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title),
            if (subtitle != null)
              Text(
                subtitle!,
                style: const TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                  color: AppColors.muted,
                ),
              )
            else if (session.school != null)
              Text(
                [
                  session.school!.name,
                  if (session.year != null) session.year!.name,
                ].join(' · '),
                style: const TextStyle(
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                  color: AppColors.muted,
                ),
              ),
          ],
        ),
        actions: actions,
      ),
      floatingActionButton: blocked ? null : floatingActionButton,
      body: blocked
          ? const EmptyState(
              icon: Icons.event_busy_outlined,
              title: 'Aucune année académique',
              message:
                  'Sélectionnez une année dans votre profil pour consulter '
                  'cet écran.',
            )
          : child,
    );
  }
}
