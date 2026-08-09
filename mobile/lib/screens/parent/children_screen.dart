import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';
import 'demo_data.dart';

/// Suivi des enfants, côté parent.
///
/// ATTENTION — écran alimenté par des données de démonstration.
///
/// Le backend n'expose aujourd'hui aucun accès parent : `accessible_schools()`
/// ne reconnaît que les propriétaires et les membres du personnel, et un
/// parent n'est rattaché à une école que par `StudentEnrollment.guardian`.
/// Aucun endpoint ne renvoie « mes enfants ».
///
/// L'écran est donc construit sur la forme que prendront ces données, pour que
/// le branchement se limite à remplacer `demoChildren` par un appel de
/// service. Le bandeau ci-dessous empêche de prendre ces chiffres pour vrais.
class ChildrenScreen extends StatefulWidget {
  const ChildrenScreen({super.key});

  @override
  State<ChildrenScreen> createState() => _ChildrenScreenState();
}

class _ChildrenScreenState extends State<ChildrenScreen> {
  int _selected = 0;

  @override
  Widget build(BuildContext context) {
    final children = demoChildren;
    final child = children[_selected];

    return ScreenScaffold(
      title: 'Mes enfants',
      requiresYear: false,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 24),
        children: [
          const _DemoBanner(),
          const SizedBox(height: 14),
          if (children.length > 1)
            SizedBox(
              height: 42,
              child: ListView.separated(
                scrollDirection: Axis.horizontal,
                itemCount: children.length,
                separatorBuilder: (_, _) => const SizedBox(width: 8),
                itemBuilder: (context, index) => ChoiceChip(
                  label: Text(children[index].name),
                  selected: _selected == index,
                  onSelected: (_) => setState(() => _selected = index),
                ),
              ),
            ),
          const SizedBox(height: 14),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 26,
                    backgroundColor: AppColors.tint,
                    child: Text(
                      child.name.substring(0, 1),
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
                          child.name,
                          style: const TextStyle(
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                            color: AppColors.navy,
                          ),
                        ),
                        Text(
                          '${child.className} · ${child.matricule}',
                          style: const TextStyle(
                              fontSize: 12.5, color: AppColors.muted),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 14),
          Row(
            children: [
              Expanded(
                child: StatTile(
                  label: 'Moyenne',
                  value: child.average.toStringAsFixed(2),
                  icon: Icons.school_outlined,
                  color: child.average >= 10
                      ? AppColors.success
                      : AppColors.danger,
                  hint: 'Rang ${child.rank}',
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: StatTile(
                  label: 'Absences',
                  value: '${child.absences}',
                  icon: Icons.event_busy_outlined,
                  color: AppColors.warning,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Row(
            children: [
              Expanded(
                child: StatTile(
                  label: 'Écolage versé',
                  value: formatMoney(child.paid),
                  icon: Icons.payments_outlined,
                  color: AppColors.success,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: StatTile(
                  label: 'Reste à payer',
                  value: formatMoney(child.balance),
                  icon: Icons.account_balance_wallet_outlined,
                  color:
                      child.balance > 0 ? AppColors.danger : AppColors.success,
                ),
              ),
            ],
          ),
          const SizedBox(height: 20),
          const SectionTitle(title: 'Notes par matière'),
          Card(
            child: Column(
              children: [
                for (var i = 0; i < child.subjects.length; i++) ...[
                  if (i > 0) const Divider(height: 1),
                  ListTile(
                    dense: true,
                    title: Text(
                      child.subjects[i].name,
                      style: const TextStyle(fontSize: 13.5),
                    ),
                    subtitle: Text(
                      'Coefficient ${child.subjects[i].coefficient}',
                      style: const TextStyle(fontSize: 11.5),
                    ),
                    trailing: Text(
                      child.subjects[i].average.toStringAsFixed(2),
                      style: TextStyle(
                        fontWeight: FontWeight.w700,
                        fontSize: 14,
                        color: child.subjects[i].average >= 10
                            ? AppColors.success
                            : AppColors.danger,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 20),
          const SectionTitle(title: 'Vie scolaire'),
          if (child.events.isEmpty)
            const Card(
              child: Padding(
                padding: EdgeInsets.all(16),
                child: Text(
                  'Aucun incident signalé.',
                  style: TextStyle(fontSize: 13, color: AppColors.slate),
                ),
              ),
            )
          else
            Card(
              child: Column(
                children: [
                  for (var i = 0; i < child.events.length; i++) ...[
                    if (i > 0) const Divider(height: 1),
                    ListTile(
                      dense: true,
                      leading: const Icon(Icons.flag_outlined,
                          size: 18, color: AppColors.warning),
                      title: Text(
                        child.events[i].label,
                        style: const TextStyle(fontSize: 13.5),
                      ),
                      subtitle: Text(
                        formatDate(child.events[i].date),
                        style: const TextStyle(fontSize: 11.5),
                      ),
                    ),
                  ],
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class _DemoBanner extends StatelessWidget {
  const _DemoBanner();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: const Color(0xFFFFFBEB),
        border: Border.all(color: const Color(0xFFFDE68A)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: const Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(Icons.science_outlined, size: 18, color: AppColors.warning),
          SizedBox(width: 9),
          Expanded(
            child: Text(
              'Données de démonstration. L’espace parent attend ses '
              'endpoints côté serveur : ces chiffres sont fictifs.',
              style: TextStyle(fontSize: 12.5, color: Color(0xFF92400E)),
            ),
          ),
        ],
      ),
    );
  }
}
