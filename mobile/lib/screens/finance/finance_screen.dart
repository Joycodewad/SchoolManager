import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../api/client.dart';
import '../../api/services.dart';
import '../../core/theme.dart';
import '../../models/finance.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';

/// Écolage : encaissements récents et suivi du recouvrement par classe.
class FinanceScreen extends StatefulWidget {
  const FinanceScreen({super.key});

  @override
  State<FinanceScreen> createState() => _FinanceScreenState();
}

class _FinanceScreenState extends State<FinanceScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 2, vsync: this);
  Future<List<FeePayment>>? _payments;
  Future<List<FeePlanSummary>>? _plans;
  int? _loadedFor;

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = context.watch<SessionState>();
    final key = Object.hash(session.school?.id, session.year?.id);
    if (_loadedFor != key) {
      _loadedFor = key;
      _payments = _loadPayments(session);
      _plans = _loadPlans(session);
    }
  }

  Future<List<FeePayment>> _loadPayments(SessionState session) {
    final schoolId = session.school?.id;
    if (schoolId == null) return Future.value(const []);
    return FinanceService(session.client).payments(schoolId);
  }

  Future<List<FeePlanSummary>> _loadPlans(SessionState session) {
    final schoolId = session.school?.id;
    if (schoolId == null) return Future.value(const []);
    return FinanceService(session.client).plans(schoolId);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();

    return ScreenScaffold(
      title: 'Écolage',
      child: Column(
        children: [
          TabBar(
            controller: _tabs,
            labelColor: AppColors.primary,
            unselectedLabelColor: AppColors.muted,
            indicatorColor: AppColors.primary,
            tabs: const [
              Tab(text: 'Encaissements'),
              Tab(text: 'Recouvrement'),
            ],
          ),
          Expanded(
            child: TabBarView(
              controller: _tabs,
              children: [
                AsyncView<List<FeePayment>>(
                  future: _payments,
                  onRetry: () =>
                      setState(() => _payments = _loadPayments(session)),
                  emptyCheck: (data) => data.isEmpty,
                  empty: const EmptyState(
                    icon: Icons.receipt_outlined,
                    title: 'Aucun encaissement',
                    message: 'Aucun paiement enregistré pour cette année.',
                  ),
                  builder: (context, payments) => _PaymentsList(payments: payments),
                ),
                AsyncView<List<FeePlanSummary>>(
                  future: _plans,
                  onRetry: () => setState(() => _plans = _loadPlans(session)),
                  emptyCheck: (data) => data.isEmpty,
                  empty: const EmptyState(
                    icon: Icons.request_quote_outlined,
                    title: 'Aucune grille d’écolage',
                    message:
                        'Aucune classe n’a de grille définie pour cette année.',
                  ),
                  builder: (context, plans) => _ComplianceTab(plans: plans),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _PaymentsList extends StatelessWidget {
  const _PaymentsList({required this.payments});

  final List<FeePayment> payments;

  @override
  Widget build(BuildContext context) {
    final total = payments.fold<double>(0, (sum, item) => sum + item.amount);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 6),
          child: Row(
            children: [
              Expanded(
                child: StatTile(
                  label: 'Total encaissé',
                  value: formatMoney(total),
                  icon: Icons.savings_outlined,
                  color: AppColors.success,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: StatTile(
                  label: 'Versements',
                  value: '${payments.length}',
                  icon: Icons.receipt_long_outlined,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: ListView.separated(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 20),
            itemCount: payments.length,
            separatorBuilder: (_, _) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final payment = payments[index];
              return Card(
                child: ListTile(
                  title: Text(
                    payment.studentName,
                    style: const TextStyle(
                        fontWeight: FontWeight.w600, fontSize: 14),
                  ),
                  subtitle: Text(
                    [
                      payment.className,
                      payment.moduleName,
                      if (payment.installmentName != null)
                        payment.installmentName!,
                      formatDate(payment.paidOn),
                    ].where((part) => part.isNotEmpty).join(' · '),
                    style: const TextStyle(fontSize: 12),
                  ),
                  trailing: Text(
                    formatMoney(payment.amount),
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      color: AppColors.success,
                      fontSize: 14,
                    ),
                  ),
                ),
              );
            },
          ),
        ),
      ],
    );
  }
}

/// Onglet recouvrement : une classe à la fois, avec ses élèves en retard.
class _ComplianceTab extends StatefulWidget {
  const _ComplianceTab({required this.plans});

  final List<FeePlanSummary> plans;

  @override
  State<_ComplianceTab> createState() => _ComplianceTabState();
}

class _ComplianceTabState extends State<_ComplianceTab> {
  int? _classId;
  Future<ComplianceReport>? _report;
  bool _onlyLate = true;

  Future<ComplianceReport> _load(int classId) {
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) throw ApiException('Aucune école sélectionnée.');
    // `target` vaut « total » : la conformité est jugée sur l'écolage dû à ce
    // jour, tel que la vue Django le calcule.
    return FinanceService(session.client)
        .compliance(schoolId, classId, 'total');
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
          child: DropdownButtonFormField<int>(
            initialValue: _classId,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'Classe',
              isDense: true,
            ),
            items: [
              for (final plan in widget.plans)
                DropdownMenuItem(
                  value: plan.schoolClass,
                  child: Text(
                    plan.className.isEmpty ? plan.levelName : plan.className,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
            ],
            onChanged: (value) {
              if (value == null) return;
              setState(() {
                _classId = value;
                _report = _load(value);
              });
            },
          ),
        ),
        if (_classId == null)
          const Expanded(
            child: EmptyState(
              icon: Icons.fact_check_outlined,
              title: 'Choisissez une classe',
              message:
                  'Sélectionnez une classe pour voir qui est à jour de son '
                  'écolage.',
            ),
          )
        else
          Expanded(
            child: AsyncView<ComplianceReport>(
              future: _report,
              onRetry: () => setState(() => _report = _load(_classId!)),
              builder: (context, report) {
                final students = _onlyLate
                    ? report.students
                        .where((student) => !student.isCompliant)
                        .toList()
                    : report.students;

                return Column(
                  children: [
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 16),
                      child: Row(
                        children: [
                          Expanded(
                            child: StatTile(
                              label: 'À jour',
                              value: '${report.compliantCount}',
                              icon: Icons.check_circle_outline,
                              color: AppColors.success,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: StatTile(
                              label: 'En retard',
                              value: '${report.nonCompliantCount}',
                              icon: Icons.warning_amber_outlined,
                              color: AppColors.danger,
                              hint: formatMoney(report.outstanding),
                            ),
                          ),
                        ],
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      child: SwitchListTile(
                        dense: true,
                        value: _onlyLate,
                        onChanged: (value) => setState(() => _onlyLate = value),
                        title: const Text(
                          'Afficher seulement les retards',
                          style: TextStyle(fontSize: 13),
                        ),
                      ),
                    ),
                    Expanded(
                      child: students.isEmpty
                          ? const EmptyState(
                              icon: Icons.verified_outlined,
                              title: 'Toute la classe est à jour',
                              message:
                                  'Aucun élève de cette classe n’a de solde '
                                  'restant.',
                            )
                          : ListView.separated(
                              padding:
                                  const EdgeInsets.fromLTRB(16, 4, 16, 20),
                              itemCount: students.length,
                              separatorBuilder: (_, _) =>
                                  const SizedBox(height: 8),
                              itemBuilder: (context, index) =>
                                  _ComplianceCard(student: students[index]),
                            ),
                    ),
                  ],
                );
              },
            ),
          ),
      ],
    );
  }
}

class _ComplianceCard extends StatelessWidget {
  const _ComplianceCard({required this.student});

  final ComplianceStudent student;

  @override
  Widget build(BuildContext context) {
    // Le taux sert la barre de progression ; sans montant attendu il n'y a
    // rien à recouvrer, donc la barre est pleine.
    final ratio = student.expected <= 0
        ? 1.0
        : (student.paid / student.expected).clamp(0.0, 1.0);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    student.studentName,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 14,
                      color: AppColors.navy,
                    ),
                  ),
                ),
                StatusPill(
                  label: student.isCompliant ? 'À jour' : 'En retard',
                  color: student.isCompliant
                      ? AppColors.success
                      : AppColors.danger,
                  dense: true,
                ),
              ],
            ),
            const SizedBox(height: 8),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: ratio,
                minHeight: 6,
                backgroundColor: AppColors.border,
                valueColor: AlwaysStoppedAnimation(
                  student.isCompliant ? AppColors.success : AppColors.warning,
                ),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Text(
                  'Versé ${formatMoney(student.paid)}',
                  style: const TextStyle(fontSize: 12, color: AppColors.slate),
                ),
                const Spacer(),
                if (student.balance > 0)
                  Text(
                    'Reste ${formatMoney(student.balance)}',
                    style: const TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: AppColors.danger,
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
