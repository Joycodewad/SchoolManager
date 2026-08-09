import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/services.dart';
import '../../core/roles.dart';
import '../../core/theme.dart';
import '../../models/school_data.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';
import 'grade_sheet_screen.dart';

/// Notes : on choisit une session, une classe, puis une matière.
///
/// Le serveur ne renvoie dans les contextes que les classes et matières
/// auxquelles l'utilisateur a droit — un enseignant n'y voit que les siennes.
class GradesScreen extends StatefulWidget {
  const GradesScreen({super.key});

  @override
  State<GradesScreen> createState() => _GradesScreenState();
}

class _GradesScreenState extends State<GradesScreen> {
  Future<List<GradeSession>>? _future;
  int? _loadedFor;
  int _sessionIndex = 0;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = context.watch<SessionState>();
    final key = Object.hash(session.school?.id, session.year?.id);
    if (_loadedFor != key) {
      _loadedFor = key;
      _future = _load(session);
    }
  }

  Future<List<GradeSession>> _load(SessionState session) {
    final schoolId = session.school?.id;
    if (schoolId == null) return Future.value(const []);
    return GradeService(session.client).contexts(schoolId);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();
    final canEnter = session.can(Capability.enterGrades);

    return ScreenScaffold(
      title: 'Notes',
      child: AsyncView<List<GradeSession>>(
        future: _future,
        onRetry: () => setState(() => _future = _load(session)),
        emptyCheck: (data) => data.isEmpty,
        empty: const EmptyState(
          icon: Icons.grading_outlined,
          title: 'Aucune session de notes',
          message:
              'Aucune session académique n’est ouverte, ou aucune classe ne '
              'vous est confiée pour cette année.',
        ),
        builder: (context, sessions) {
          // L'index mémorisé peut dépasser après un changement d'année.
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
                      onSelected: (_) => setState(() => _sessionIndex = i),
                    ),
                  ),
                ),
              Expanded(
                child: current.classes.isEmpty
                    ? const EmptyState(
                        icon: Icons.meeting_room_outlined,
                        title: 'Aucune classe',
                        message:
                            'Cette session ne comporte aucune classe qui vous '
                            'soit accessible.',
                      )
                    : ListView(
                        padding: const EdgeInsets.all(16),
                        children: [
                          for (final klass in current.classes)
                            _ClassBlock(
                              klass: klass,
                              sessionId: current.id,
                              canEnter: canEnter,
                            ),
                        ],
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _ClassBlock extends StatelessWidget {
  const _ClassBlock({
    required this.klass,
    required this.sessionId,
    required this.canEnter,
  });

  final GradeClass klass;
  final int sessionId;
  final bool canEnter;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Card(
        child: Theme(
          // `ExpansionTile` trace ses propres filets, qui doubleraient ceux
          // de la carte.
          data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
          child: ExpansionTile(
            initiallyExpanded: true,
            tilePadding: const EdgeInsets.symmetric(horizontal: 14),
            title: Text(
              klass.name,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 15,
                color: AppColors.navy,
              ),
            ),
            subtitle: Text(
              '${klass.subjects.length} matière'
              '${klass.subjects.length > 1 ? 's' : ''}',
              style: const TextStyle(fontSize: 12, color: AppColors.muted),
            ),
            children: [
              if (klass.subjects.isEmpty)
                const Padding(
                  padding: EdgeInsets.fromLTRB(16, 0, 16, 14),
                  child: Text(
                    'Aucune matière ne vous est confiée dans cette classe.',
                    style: TextStyle(fontSize: 13, color: AppColors.muted),
                  ),
                )
              else
                for (final subject in klass.subjects)
                  ListTile(
                    dense: true,
                    leading: const Icon(Icons.menu_book_outlined, size: 19),
                    title: Text(subject.name,
                        style: const TextStyle(fontSize: 14)),
                    trailing: Icon(
                      canEnter ? Icons.edit_outlined : Icons.chevron_right,
                      size: 18,
                    ),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute<void>(
                        builder: (_) => GradeSheetScreen(
                          sessionId: sessionId,
                          classSubjectId: subject.id,
                          className: klass.name,
                          subjectName: subject.name,
                          canEdit: canEnter,
                        ),
                      ),
                    ),
                  ),
              const SizedBox(height: 6),
            ],
          ),
        ),
      ),
    );
  }
}
