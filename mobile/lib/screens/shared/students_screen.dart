import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/services.dart';
import '../../core/theme.dart';
import '../../models/session.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';

/// Annuaire des élèves : recherche par nom ou matricule, filtre par classe.
class StudentsScreen extends StatefulWidget {
  const StudentsScreen({super.key});

  @override
  State<StudentsScreen> createState() => _StudentsScreenState();
}

class _StudentsScreenState extends State<StudentsScreen> {
  Future<_Roster>? _future;
  int? _loadedFor;
  final _search = TextEditingController();
  int? _classFilter;

  @override
  void dispose() {
    _search.dispose();
    super.dispose();
  }

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

  Future<_Roster> _load(SessionState session) async {
    final schoolId = session.school?.id;
    if (schoolId == null) return _Roster(const [], const []);
    final directory = DirectoryService(session.client);
    final classes = await directory.classes(schoolId);
    final students = await directory.enrollments(schoolId);
    return _Roster(classes, students);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();
    final query = _search.text.trim().toLowerCase();

    return ScreenScaffold(
      title: 'Élèves',
      child: AsyncView<_Roster>(
        future: _future,
        onRetry: () => setState(() => _future = _load(session)),
        builder: (context, roster) {
          final filtered = roster.students.where((student) {
            if (_classFilter != null &&
                asInt(student['school_class']) != _classFilter) {
              return false;
            }
            if (query.isEmpty) return true;
            final name = asText(student['student_name']).toLowerCase();
            final number = asText(student['enrollment_number']).toLowerCase();
            return name.contains(query) || number.contains(query);
          }).toList();

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: TextField(
                  controller: _search,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    hintText: 'Rechercher un nom ou un matricule',
                    prefixIcon: const Icon(Icons.search, size: 20),
                    suffixIcon: query.isEmpty
                        ? null
                        : IconButton(
                            icon: const Icon(Icons.close, size: 18),
                            onPressed: () {
                              _search.clear();
                              setState(() {});
                            },
                          ),
                  ),
                ),
              ),
              if (roster.classes.isNotEmpty)
                SizedBox(
                  height: 44,
                  child: ListView(
                    scrollDirection: Axis.horizontal,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    children: [
                      Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          label: const Text('Toutes'),
                          selected: _classFilter == null,
                          onSelected: (_) =>
                              setState(() => _classFilter = null),
                        ),
                      ),
                      for (final klass in roster.classes)
                        Padding(
                          padding: const EdgeInsets.only(right: 8),
                          child: ChoiceChip(
                            label: Text(asText(klass['group'])),
                            selected: _classFilter == asInt(klass['id']),
                            onSelected: (_) => setState(
                                () => _classFilter = asInt(klass['id'])),
                          ),
                        ),
                    ],
                  ),
                ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 6),
                child: Row(
                  children: [
                    Text(
                      '${filtered.length} élève${filtered.length > 1 ? 's' : ''}',
                      style: const TextStyle(
                        fontSize: 12.5,
                        color: AppColors.muted,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: filtered.isEmpty
                    ? EmptyState(
                        icon: Icons.person_search_outlined,
                        title: roster.students.isEmpty
                            ? 'Aucun élève inscrit'
                            : 'Aucun résultat',
                        message: roster.students.isEmpty
                            ? 'Aucune inscription pour cette année.'
                            : 'Aucun élève ne correspond à cette recherche.',
                      )
                    : ListView.separated(
                        padding: const EdgeInsets.fromLTRB(16, 0, 16, 20),
                        itemCount: filtered.length,
                        separatorBuilder: (_, _) => const SizedBox(height: 8),
                        itemBuilder: (context, index) =>
                            _StudentCard(data: filtered[index]),
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Roster {
  _Roster(this.classes, this.students);

  final List<Map<String, dynamic>> classes;
  final List<Map<String, dynamic>> students;
}

class _StudentCard extends StatelessWidget {
  const _StudentCard({required this.data});

  final Map<String, dynamic> data;

  @override
  Widget build(BuildContext context) {
    final name = asText(data['student_name']);
    // Le sérialiseur d'inscription nomme la classe `school_class_name`, à la
    // différence des vues discipline et appel qui disent `class_name`.
    final klass = asText(data['school_class_name']);
    return Card(
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: AppColors.tint,
          child: Text(
            name.isEmpty ? '?' : name.substring(0, 1).toUpperCase(),
            style: const TextStyle(
              color: AppColors.primaryDark,
              fontWeight: FontWeight.w700,
              fontSize: 15,
            ),
          ),
        ),
        title: Text(
          name,
          style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14.5),
        ),
        subtitle: Text(
          [
            if (asText(data['enrollment_number']).isNotEmpty)
              asText(data['enrollment_number']),
            if (klass.isNotEmpty) klass,
          ].join(' · '),
          style: const TextStyle(fontSize: 12.5),
        ),
      ),
    );
  }
}
