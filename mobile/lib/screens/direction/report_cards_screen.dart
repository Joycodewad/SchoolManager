import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/client.dart';
import '../../api/services.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/school_data.dart';
import '../../models/session.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';

/// Bulletins : état de génération par session, puis consultation par classe.
///
/// L'édition PDF reste sur le web : elle produit un fichier à imprimer, ce
/// qu'on ne fait pas depuis un téléphone. Le mobile sert à vérifier que les
/// bulletins sont générés et à consulter les moyennes.
class ReportCardsScreen extends StatefulWidget {
  const ReportCardsScreen({super.key});

  @override
  State<ReportCardsScreen> createState() => _ReportCardsScreenState();
}

class _ReportCardsScreenState extends State<ReportCardsScreen> {
  Future<List<GradeSession>>? _sessions;
  int? _loadedFor;
  int _sessionIndex = 0;
  int? _classId;
  Future<Map<String, dynamic>>? _cards;
  bool _generating = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = context.watch<SessionState>();
    final key = Object.hash(session.school?.id, session.year?.id);
    if (_loadedFor != key) {
      _loadedFor = key;
      _sessions = _load(session);
      _classId = null;
      _cards = null;
    }
  }

  Future<List<GradeSession>> _load(SessionState session) {
    final schoolId = session.school?.id;
    if (schoolId == null) return Future.value(const []);
    return GradeService(session.client).contexts(schoolId);
  }

  Future<void> _generate(int sessionId, int classId) async {
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) return;

    setState(() => _generating = true);
    try {
      await ReportCardService(session.client).generate(schoolId, sessionId, {
        'scope': 'class',
        'school_class': classId,
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Bulletins générés.')),
      );
      setState(() {
        _generating = false;
        _cards = ReportCardService(session.client)
            .cards(schoolId, sessionId, classId);
      });
    } on ApiException catch (error) {
      if (!mounted) return;
      setState(() => _generating = false);
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(error.message)));
    }
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();

    return ScreenScaffold(
      title: 'Bulletins',
      child: AsyncView<List<GradeSession>>(
        future: _sessions,
        onRetry: () => setState(() => _sessions = _load(session)),
        emptyCheck: (data) => data.isEmpty,
        empty: const EmptyState(
          icon: Icons.description_outlined,
          title: 'Aucune session',
          message: 'Aucune session académique ouverte pour cette année.',
        ),
        builder: (context, sessions) {
          final index = _sessionIndex.clamp(0, sessions.length - 1);
          final current = sessions[index];

          return Column(
            children: [
              if (sessions.length > 1)
                SizedBox(
                  height: 46,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 16, vertical: 6),
                    itemCount: sessions.length,
                    separatorBuilder: (_, _) => const SizedBox(width: 8),
                    itemBuilder: (context, i) => ChoiceChip(
                      label: Text(sessions[i].name),
                      selected: index == i,
                      onSelected: (_) => setState(() {
                        _sessionIndex = i;
                        _classId = null;
                        _cards = null;
                      }),
                    ),
                  ),
                ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
                child: DropdownButtonFormField<int>(
                  initialValue: _classId,
                  isExpanded: true,
                  decoration: const InputDecoration(
                    labelText: 'Classe',
                    isDense: true,
                  ),
                  items: [
                    for (final klass in current.classes)
                      DropdownMenuItem(
                        value: klass.id,
                        child: Text(klass.name, overflow: TextOverflow.ellipsis),
                      ),
                  ],
                  onChanged: (value) {
                    if (value == null) return;
                    final schoolId = session.school?.id;
                    if (schoolId == null) return;
                    setState(() {
                      _classId = value;
                      _cards = ReportCardService(session.client)
                          .cards(schoolId, current.id, value);
                    });
                  },
                ),
              ),
              Expanded(
                child: _classId == null
                    ? const EmptyState(
                        icon: Icons.class_outlined,
                        title: 'Choisissez une classe',
                        message:
                            'Sélectionnez une classe pour consulter ses '
                            'bulletins.',
                      )
                    : AsyncView<Map<String, dynamic>>(
                        future: _cards,
                        builder: (context, data) {
                          final students = (data['students'] as List? ?? [])
                              .cast<Map<String, dynamic>>();
                          if (students.isEmpty) {
                            return EmptyState(
                              icon: Icons.pending_actions_outlined,
                              title: 'Bulletins non générés',
                              message:
                                  'Aucun bulletin figé pour cette classe.',
                              action: session.can(Capability.configureGrades)
                                  ? FilledButton.icon(
                                      onPressed: _generating
                                          ? null
                                          : () => _generate(
                                              current.id, _classId!),
                                      icon: _generating
                                          ? const SizedBox(
                                              height: 16,
                                              width: 16,
                                              child:
                                                  CircularProgressIndicator(
                                                strokeWidth: 2,
                                                color: Colors.white,
                                              ),
                                            )
                                          : const Icon(Icons.play_arrow),
                                      label: const Text('Générer'),
                                    )
                                  : null,
                            );
                          }
                          return _CardsList(
                            students: students,
                            canGenerate:
                                session.can(Capability.configureGrades),
                            generating: _generating,
                            onRegenerate: () =>
                                _generate(current.id, _classId!),
                          );
                        },
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _CardsList extends StatelessWidget {
  const _CardsList({
    required this.students,
    required this.canGenerate,
    required this.generating,
    required this.onRegenerate,
  });

  final List<Map<String, dynamic>> students;
  final bool canGenerate;
  final bool generating;
  final VoidCallback onRegenerate;

  @override
  Widget build(BuildContext context) {
    final averages = students
        .map((student) => asDouble(student['general_average']))
        .whereType<double>()
        .toList();
    final classAverage = averages.isEmpty
        ? null
        : averages.reduce((a, b) => a + b) / averages.length;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 20),
      children: [
        Row(
          children: [
            Expanded(
              child: StatTile(
                label: 'Bulletins',
                value: '${students.length}',
                icon: Icons.description_outlined,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: StatTile(
                label: 'Moyenne de classe',
                value: classAverage == null
                    ? '—'
                    : classAverage.toStringAsFixed(2),
                icon: Icons.analytics_outlined,
                color: AppColors.info,
              ),
            ),
          ],
        ),
        if (canGenerate) ...[
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: generating ? null : onRegenerate,
            icon: generating
                ? const SizedBox(
                    height: 15,
                    width: 15,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Icon(Icons.refresh, size: 18),
            label: const Text('Régénérer les bulletins'),
          ),
        ],
        const SizedBox(height: 16),
        const SectionTitle(title: 'Élèves'),
        for (final student in students)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Card(
              child: ListTile(
                leading: CircleAvatar(
                  backgroundColor: AppColors.tint,
                  child: Text(
                    '${asInt(student['rank']) ?? '—'}',
                    style: const TextStyle(
                      color: AppColors.primaryDark,
                      fontWeight: FontWeight.w700,
                      fontSize: 13,
                    ),
                  ),
                ),
                title: Text(
                  asText(student['student_name']),
                  style: const TextStyle(
                      fontWeight: FontWeight.w600, fontSize: 14),
                ),
                subtitle: Text(
                  asText(student['appreciation']),
                  style: const TextStyle(fontSize: 12),
                ),
                trailing: Text(
                  asText(student['general_average']).isEmpty
                      ? '—'
                      : asText(student['general_average']),
                  style: TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 15,
                    color: (asDouble(student['general_average']) ?? 0) >= 10
                        ? AppColors.success
                        : AppColors.danger,
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
