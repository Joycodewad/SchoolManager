import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { createExpense, createExpenseCategory, deleteExpense, ExpenseCategory, listExpenseCategories, listExpenses, SchoolExpense, updateExpense } from "../api/finance";

const money = (value: string | number) => `${Number(value || 0).toLocaleString("fr-FR")} FCFA`;

export default function SchoolExpenses() {
  const { schoolId = "" } = useParams();
  const [expenses, setExpenses] = useState<SchoolExpense[]>([]);
  const [categories, setCategories] = useState<ExpenseCategory[]>([]);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState(0);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<SchoolExpense | null>(null);
  const [newCategory, setNewCategory] = useState("");
  const [selectedCategory, setSelectedCategory] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    try { const [expenseRows, categoryRows] = await Promise.all([listExpenses(schoolId), listExpenseCategories(schoolId)]); setExpenses(expenseRows); setCategories(categoryRows); }
    catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };
  useEffect(() => { void load(); }, [schoolId]);

  const filtered = useMemo(() => expenses.filter((row) => {
    const query = search.trim().toLocaleLowerCase("fr");
    return (!query || `${row.label} ${row.beneficiary} ${row.reference}`.toLocaleLowerCase("fr").includes(query))
      && (!categoryFilter || row.category === categoryFilter)
      && (!dateFrom || row.expense_date >= dateFrom) && (!dateTo || row.expense_date <= dateTo);
  }), [expenses, search, categoryFilter, dateFrom, dateTo]);
  const total = filtered.reduce((sum, row) => sum + Number(row.amount), 0);
  const currentMonth = new Date().toISOString().slice(0, 7);
  const monthTotal = expenses.filter((row) => row.expense_date.startsWith(currentMonth)).reduce((sum, row) => sum + Number(row.amount), 0);

  const openForm = (expense?: SchoolExpense) => {
    setEditing(expense ?? null); setSelectedCategory(expense?.category ?? categories[0]?.id ?? 0);
    setNewCategory(""); setError(""); setMessage(""); setShowForm(true);
  };
  const addCategory = async () => {
    if (!newCategory.trim()) return;
    try { const category = await createExpenseCategory(schoolId, newCategory.trim()); setCategories((current) => [...current, category].sort((a, b) => a.name.localeCompare(b.name))); setSelectedCategory(category.id); setNewCategory(""); }
    catch (e) { setError(e instanceof Error ? e.message : "Création de catégorie impossible."); }
  };
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); const form = new FormData(event.currentTarget);
    try {
      const payload = { category: selectedCategory, label: String(form.get("label")).trim(), description: String(form.get("description") ?? "").trim(), beneficiary: String(form.get("beneficiary") ?? "").trim(), amount: Number(form.get("amount")), expense_date: String(form.get("expense_date")), method: String(form.get("method")), reference: String(form.get("reference") ?? "").trim() };
      if (editing) await updateExpense(schoolId, editing.id, payload); else await createExpense(schoolId, payload);
      setShowForm(false); setMessage(editing ? "Dépense modifiée." : "Dépense enregistrée."); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Enregistrement impossible."); }
  };
  const remove = async (expense: SchoolExpense) => {
    if (!window.confirm(`Supprimer la dépense « ${expense.label} » ?`)) return;
    try { await deleteExpense(schoolId, expense.id); setExpenses((current) => current.filter((row) => row.id !== expense.id)); setMessage("Dépense supprimée."); }
    catch (e) { setError(e instanceof Error ? e.message : "Suppression impossible."); }
  };

  return <div className="fc-root">
    <div className="fc-page-head"><div><h1>Dépenses scolaires</h1><p>Enregistrez et suivez toutes les dépenses de l’établissement.</p></div><button className="btn-primary" onClick={() => openForm()}>+ Nouvelle dépense</button></div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    <div className="fc-summary"><div><span>Total affiché</span><strong>{money(total)}</strong></div><div><span>Dépenses ce mois</span><strong>{money(monthTotal)}</strong></div><div><span>Nombre de dépenses</span><strong>{filtered.length}</strong></div></div>
    <section className="fc-table-section"><div className="fc-table-header"><span className="fc-chart-title">Historique des dépenses</span><div className="fc-table-controls"><input className="fc-expense-search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Libellé, bénéficiaire, référence…" /><select className="fc-select" value={categoryFilter} onChange={(e) => setCategoryFilter(Number(e.target.value))}><option value={0}>Toutes les catégories</option>{categories.map((row) => <option value={row.id} key={row.id}>{row.name}</option>)}</select><input className="fc-date-filter" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} title="Du" /><input className="fc-date-filter" type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} title="Au" /></div></div><div className="fc-table-wrap"><table className="fc-table"><thead><tr><th>Date</th><th>Libellé</th><th>Catégorie</th><th>Bénéficiaire</th><th>Montant</th><th>Mode</th><th>Référence</th><th>Enregistrée par</th><th>Actions</th></tr></thead><tbody>{filtered.map((row) => <tr key={row.id}><td>{row.expense_date}</td><td><b>{row.label}</b>{row.description && <small className="fc-block">{row.description}</small>}</td><td>{row.category_name}</td><td>{row.beneficiary || "—"}</td><td className="fc-amount">{money(row.amount)}</td><td>{row.method_label}</td><td>{row.reference || "—"}</td><td>{row.recorded_by_name || "—"}</td><td><div className="fc-actions"><button className="fc-action-btn" onClick={() => openForm(row)} title="Modifier">✎</button><button className="fc-action-btn danger" onClick={() => void remove(row)} title="Supprimer">×</button></div></td></tr>)}</tbody></table>{!filtered.length && <p className="fc-empty">Aucune dépense trouvée.</p>}</div></section>

    {showForm && <div className="teacher-modal-backdrop" onMouseDown={() => setShowForm(false)}><form className="teacher-modal fc-modal" onSubmit={submit} onMouseDown={(e) => e.stopPropagation()}><button type="button" className="modal-close" onClick={() => setShowForm(false)}>×</button><h2>{editing ? "Modifier la dépense" : "Nouvelle dépense"}</h2><label>Libellé *<input className="form-input" name="label" defaultValue={editing?.label} placeholder="Ex. Achat de fournitures" required /></label><label>Montant *<input className="form-input" name="amount" type="number" min="1" step="0.01" defaultValue={editing?.amount} required /></label><label>Catégorie *<select className="form-select" value={selectedCategory} onChange={(e) => setSelectedCategory(Number(e.target.value))} required><option value="" disabled>Choisir</option>{categories.map((row) => <option value={row.id} key={row.id}>{row.name}</option>)}</select></label><label>Créer une catégorie<div className="fc-inline-create"><input className="form-input" value={newCategory} onChange={(e) => setNewCategory(e.target.value)} placeholder="Nouvelle catégorie" /><button type="button" onClick={() => void addCategory()}>Ajouter</button></div></label><label>Date *<input className="form-input" name="expense_date" type="date" defaultValue={editing?.expense_date ?? new Date().toISOString().slice(0, 10)} required /></label><label>Mode de paiement<select className="form-select" name="method" defaultValue={editing?.method ?? "especes"}><option value="especes">Espèces</option><option value="mobile_money">Mobile Money</option><option value="banque">Banque</option><option value="cheque">Chèque</option><option value="autre">Autre</option></select></label><label>Bénéficiaire / fournisseur<input className="form-input" name="beneficiary" defaultValue={editing?.beneficiary} /></label><label>Référence<input className="form-input" name="reference" defaultValue={editing?.reference} /></label><label className="fc-full">Description<textarea className="form-input" name="description" defaultValue={editing?.description} rows={3} /></label><button className="btn-primary fc-full" disabled={!selectedCategory}>{editing ? "Enregistrer les modifications" : "Enregistrer la dépense"}</button></form></div>}
  </div>;
}
