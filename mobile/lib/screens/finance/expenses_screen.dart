import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../api/client.dart';
import '../../api/services.dart';
import '../../core/theme.dart';
import '../../models/finance.dart';
import '../../models/school_data.dart';
import '../../state/session_state.dart';
import '../../widgets/common.dart';
import '../../widgets/screen_scaffold.dart';

/// Dépenses de l'école : consultation et saisie.
class ExpensesScreen extends StatefulWidget {
  const ExpensesScreen({super.key});

  @override
  State<ExpensesScreen> createState() => _ExpensesScreenState();
}

class _ExpensesScreenState extends State<ExpensesScreen> {
  Future<List<SchoolExpense>>? _future;
  int? _loadedFor;

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

  Future<List<SchoolExpense>> _load(SessionState session) {
    final schoolId = session.school?.id;
    if (schoolId == null) return Future.value(const []);
    return FinanceService(session.client).expenses(schoolId);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionState>();

    return ScreenScaffold(
      title: 'Dépenses',
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _openForm(context, session),
        icon: const Icon(Icons.add),
        label: const Text('Dépense'),
      ),
      child: AsyncView<List<SchoolExpense>>(
        future: _future,
        onRetry: () => setState(() => _future = _load(session)),
        emptyCheck: (data) => data.isEmpty,
        empty: const EmptyState(
          icon: Icons.receipt_long_outlined,
          title: 'Aucune dépense',
          message: 'Aucune dépense enregistrée pour cette année.',
        ),
        builder: (context, expenses) {
          final total =
              expenses.fold<double>(0, (sum, item) => sum + item.amount);

          // Regroupement par catégorie, pour voir où part l'argent.
          final byCategory = <String, double>{};
          for (final expense in expenses) {
            byCategory[expense.categoryName] =
                (byCategory[expense.categoryName] ?? 0) + expense.amount;
          }
          final top = byCategory.entries.toList()
            ..sort((a, b) => b.value.compareTo(a.value));

          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 90),
            children: [
              Row(
                children: [
                  Expanded(
                    child: StatTile(
                      label: 'Total dépensé',
                      value: formatMoney(total),
                      icon: Icons.trending_down,
                      color: AppColors.danger,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: StatTile(
                      label: 'Écritures',
                      value: '${expenses.length}',
                      icon: Icons.list_alt_outlined,
                    ),
                  ),
                ],
              ),
              if (top.isNotEmpty) ...[
                const SizedBox(height: 18),
                const SectionTitle(title: 'Par catégorie'),
                Card(
                  child: Column(
                    children: [
                      for (var i = 0; i < top.take(5).length; i++) ...[
                        if (i > 0) const Divider(height: 1),
                        ListTile(
                          dense: true,
                          title: Text(
                            top[i].key.isEmpty ? 'Sans catégorie' : top[i].key,
                            style: const TextStyle(fontSize: 13.5),
                          ),
                          trailing: Text(
                            formatMoney(top[i].value),
                            style: const TextStyle(
                              fontWeight: FontWeight.w600,
                              fontSize: 13,
                              color: AppColors.navy,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ],
              const SizedBox(height: 18),
              const SectionTitle(title: 'Historique'),
              for (final expense in expenses)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Card(
                    child: ListTile(
                      title: Text(
                        expense.label,
                        style: const TextStyle(
                            fontWeight: FontWeight.w600, fontSize: 14),
                      ),
                      subtitle: Text(
                        [
                          expense.categoryName,
                          if (expense.beneficiary.isNotEmpty)
                            expense.beneficiary,
                          formatDate(expense.expenseDate),
                        ].where((part) => part.isNotEmpty).join(' · '),
                        style: const TextStyle(fontSize: 12),
                      ),
                      trailing: Text(
                        formatMoney(expense.amount),
                        style: const TextStyle(
                          fontWeight: FontWeight.w700,
                          fontSize: 14,
                          color: AppColors.danger,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _openForm(BuildContext context, SessionState session) async {
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => const _ExpenseForm(),
    );
    if (saved == true && mounted) {
      setState(() => _future = _load(session));
    }
  }
}

class _ExpenseForm extends StatefulWidget {
  const _ExpenseForm();

  @override
  State<_ExpenseForm> createState() => _ExpenseFormState();
}

class _ExpenseFormState extends State<_ExpenseForm> {
  final _formKey = GlobalKey<FormState>();
  final _label = TextEditingController();
  final _amount = TextEditingController();
  final _beneficiary = TextEditingController();
  String? _category;
  String _method = 'especes';
  DateTime _date = DateTime.now();
  Future<List<LabeledValue>>? _categories;
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId != null) {
      _categories = FinanceService(session.client).expenseCategories(schoolId);
    }
  }

  @override
  void dispose() {
    _label.dispose();
    _amount.dispose();
    _beneficiary.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_category == null) {
      setState(() => _error = 'Choisissez une catégorie.');
      return;
    }
    final session = context.read<SessionState>();
    final schoolId = session.school?.id;
    if (schoolId == null) return;

    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await FinanceService(session.client).createExpense(schoolId, {
        'category': int.parse(_category!),
        'label': _label.text.trim(),
        'amount': double.parse(_amount.text.replaceAll(',', '.')),
        'expense_date': DateFormat('yyyy-MM-dd').format(_date),
        'method': _method,
        'beneficiary': _beneficiary.text.trim(),
      });
      if (mounted) Navigator.of(context).pop(true);
    } on ApiException catch (error) {
      if (mounted) {
        setState(() {
          _error = error.message;
          _saving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 16,
        bottom: MediaQuery.of(context).viewInsets.bottom + 16,
      ),
      child: SingleChildScrollView(
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Text(
                'Nouvelle dépense',
                style: TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                  color: AppColors.navy,
                ),
              ),
              const SizedBox(height: 16),
              FutureBuilder<List<LabeledValue>>(
                future: _categories,
                builder: (context, snapshot) => DropdownButtonFormField<String>(
                  initialValue: _category,
                  isExpanded: true,
                  decoration: const InputDecoration(labelText: 'Catégorie'),
                  items: [
                    for (final item in snapshot.data ?? const <LabeledValue>[])
                      DropdownMenuItem(
                        value: item.value,
                        child: Text(item.label, overflow: TextOverflow.ellipsis),
                      ),
                  ],
                  onChanged: (value) => setState(() => _category = value),
                ),
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _label,
                decoration: const InputDecoration(labelText: 'Libellé'),
                validator: (value) => (value ?? '').trim().isEmpty
                    ? 'Indiquez à quoi correspond la dépense.'
                    : null,
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _amount,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                decoration: const InputDecoration(
                  labelText: 'Montant',
                  suffixText: 'F',
                ),
                validator: (value) {
                  final amount =
                      double.tryParse((value ?? '').replaceAll(',', '.'));
                  if (amount == null || amount <= 0) {
                    return 'Saisissez un montant supérieur à 0.';
                  }
                  return null;
                },
              ),
              const SizedBox(height: 12),
              TextFormField(
                controller: _beneficiary,
                decoration: const InputDecoration(
                  labelText: 'Bénéficiaire (facultatif)',
                ),
              ),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                initialValue: _method,
                decoration: const InputDecoration(labelText: 'Mode de paiement'),
                // Valeurs de `SchoolExpense.Method` : une valeur inconnue
                // serait refusée par le sérialiseur.
                items: const [
                  DropdownMenuItem(value: 'especes', child: Text('Espèces')),
                  DropdownMenuItem(
                      value: 'mobile_money', child: Text('Mobile Money')),
                  DropdownMenuItem(value: 'banque', child: Text('Banque')),
                  DropdownMenuItem(value: 'cheque', child: Text('Chèque')),
                  DropdownMenuItem(value: 'autre', child: Text('Autre')),
                ],
                onChanged: (value) =>
                    setState(() => _method = value ?? 'especes'),
              ),
              const SizedBox(height: 12),
              InkWell(
                onTap: () async {
                  final picked = await showDatePicker(
                    context: context,
                    initialDate: _date,
                    firstDate:
                        DateTime.now().subtract(const Duration(days: 365)),
                    lastDate: DateTime.now(),
                    locale: const Locale('fr'),
                  );
                  if (picked != null) setState(() => _date = picked);
                },
                child: InputDecorator(
                  decoration: const InputDecoration(labelText: 'Date'),
                  child: Text(DateFormat('d MMMM yyyy', 'fr_FR').format(_date)),
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                ErrorBanner(message: _error!),
              ],
              const SizedBox(height: 18),
              FilledButton(
                onPressed: _saving ? null : _submit,
                child: _saving
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(
                            strokeWidth: 2.2, color: Colors.white),
                      )
                    : const Text('Enregistrer'),
              ),
              const SizedBox(height: 8),
            ],
          ),
        ),
      ),
    );
  }
}
