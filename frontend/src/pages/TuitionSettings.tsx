import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { listClasses, SchoolClass } from "../api/classes";
import { copyFeePlan, FeePlan, listFeePlans, saveFeePlan } from "../api/finance";
import { useAuth } from "../hooks/AuthContext";

type InstallmentDraft = { name: string; percentage: number; due_date: string; order: number };
type ItemDraft = { module_name: string; male_amount: number; female_amount: number; payable_in_installments: boolean; installments: InstallmentDraft[] };
const money = (value: string | number) => `${Number(value || 0).toLocaleString("fr-FR")} FCFA`;
const newItem = (): ItemDraft => ({ module_name: "", male_amount: 0, female_amount: 0, payable_in_installments: false, installments: [] });

export default function TuitionSettings() {
  const { schoolId = "" } = useParams();
  const { user, activeSchool } = useAuth();
  const role = activeSchool?.user_role ?? user?.role;
  const canConfigure = Boolean(user?.is_superuser || ["proprietaire", "censeur", "proviseur"].includes(role ?? ""));
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [plans, setPlans] = useState<FeePlan[]>([]);
  const [editingPlan, setEditingPlan] = useState<FeePlan | null>(null);
  const [selectedClass, setSelectedClass] = useState(0);
  const [items, setItems] = useState<ItemDraft[]>([newItem()]);
  const [showForm, setShowForm] = useState(false);
  const [copySource, setCopySource] = useState<FeePlan | null>(null);
  const [copyTargets, setCopyTargets] = useState<Set<number>>(new Set());
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const load = async () => {
    try { const [classRows, planRows] = await Promise.all([listClasses(schoolId), listFeePlans(schoolId)]); setClasses(classRows); setPlans(planRows); }
    catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };
  useEffect(() => { if (canConfigure) void load(); }, [schoolId, canConfigure]);
  if (!canConfigure) return <div className="content-inner"><div className="form-error">Accès refusé. Seuls le propriétaire, le censeur ou le proviseur peuvent définir les frais scolaires.</div></div>;

  const openPlan = (schoolClass: SchoolClass, plan?: FeePlan) => {
    setSelectedClass(schoolClass.id); setEditingPlan(plan ?? null);
    setItems(plan?.items.map((item) => ({ module_name: item.module_name, male_amount: Number(item.male_amount), female_amount: Number(item.female_amount), payable_in_installments: item.payable_in_installments, installments: item.installments.map((row) => ({ name: row.name, percentage: Number(row.percentage), due_date: row.due_date ?? "", order: row.order })) })) ?? [newItem()]);
    setShowForm(true); setError(""); setMessage("");
  };
  const updateItem = (index: number, change: Partial<ItemDraft>) => setItems(items.map((item, i) => i === index ? { ...item, ...change } : item));
  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    try {
      await saveFeePlan(schoolId, { school_class: editingPlan?.school_class ?? selectedClass, items: items.map((item) => ({ ...item, installments: item.installments.map((row, index) => ({ ...row, order: index + 1, due_date: row.due_date || null })) })) }, editingPlan?.id);
      setShowForm(false); setMessage("Composition des frais scolaires enregistrée."); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Enregistrement impossible."); }
  };
  const submitCopy = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError("");
    if (!copySource || !copyTargets.size) { setError("Sélectionnez au moins une classe cible."); return; }
    try {
      await copyFeePlan(schoolId, copySource.id, [...copyTargets]);
      setCopySource(null); setCopyTargets(new Set()); setMessage(`Configuration copiée vers ${copyTargets.size} classe(s).`); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Copie impossible."); }
  };

  return <div className="fc-root">
    <div className="fc-page-head"><div><h1>Composition des frais scolaires</h1><p>Créez librement les rubriques et fixez leurs montants par classe et par genre.</p></div></div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    <section className="fc-table-section"><div className="fc-table-header"><div><span className="fc-chart-title">Frais par classe</span><p className="fc-help">Exemples de rubriques : Inscription, Bibliothèque, Écolage, Cotisation parallèle, Cantine.</p></div></div><div className="fc-plan-grid">{classes.map((row) => { const plan = plans.find((entry) => entry.school_class === row.id); const maleTotal = plan?.items.reduce((sum, item) => sum + Number(item.male_amount), 0) ?? 0; const femaleTotal = plan?.items.reduce((sum, item) => sum + Number(item.female_amount), 0) ?? 0; return <article key={row.id} className="fc-plan-card"><h3>{row.level_name} {row.series} — {row.name}</h3>{plan ? <><p>Masculin <strong>{money(maleTotal)}</strong></p><p>Féminin <strong>{money(femaleTotal)}</strong></p><small>{plan.items.length} rubrique(s) de frais</small><div className="fc-plan-actions"><button onClick={() => openPlan(row, plan)}>Modifier</button><button onClick={() => { setCopySource(plan); setCopyTargets(new Set()); }}>Copier vers…</button></div></> : <><p className="fc-muted">Aucun frais défini</p><button onClick={() => openPlan(row)}>Composer les frais</button></>}</article>; })}</div></section>

    {showForm && <div className="teacher-modal-backdrop" onMouseDown={() => setShowForm(false)}><form className="teacher-modal fc-plan-modal" onSubmit={submit} onMouseDown={(e) => e.stopPropagation()}><button type="button" className="modal-close" onClick={() => setShowForm(false)}>×</button><h2>Frais — {classes.find((row) => row.id === selectedClass)?.level_name} {classes.find((row) => row.id === selectedClass)?.name}</h2><div className="fc-gender-head"><span>Rubrique créée par l’utilisateur</span><b>Masculin</b><b>Féminin</b><span>Tranches</span></div>
      {items.map((item, itemIndex) => <div className="fc-fee-module" key={itemIndex}><div className="fc-fee-module-row"><input className="form-input" value={item.module_name} onChange={(e) => updateItem(itemIndex, { module_name: e.target.value })} placeholder="Ex. Bibliothèque" required /><input className="form-input" type="number" min="0" value={item.male_amount} onChange={(e) => updateItem(itemIndex, { male_amount: Number(e.target.value) })} required /><input className="form-input" type="number" min="0" value={item.female_amount} onChange={(e) => updateItem(itemIndex, { female_amount: Number(e.target.value) })} required /><label className="fc-inline-check"><input type="checkbox" checked={item.payable_in_installments} onChange={(e) => updateItem(itemIndex, { payable_in_installments: e.target.checked, installments: e.target.checked ? (item.installments.length ? item.installments : [{ name: "1ère tranche", percentage: 100, due_date: "", order: 1 }]) : [] })} /> Oui</label><button type="button" className="fc-remove" disabled={items.length === 1} onClick={() => setItems(items.filter((_, i) => i !== itemIndex))}>×</button></div>
        {item.payable_in_installments && <div className="fc-module-installments"><div className="fc-config-title"><small>Tranches de {item.module_name || "cette rubrique"}</small><button type="button" onClick={() => updateItem(itemIndex, { installments: [...item.installments, { name: `Tranche ${item.installments.length + 1}`, percentage: 0, due_date: "", order: item.installments.length + 1 }] })}>+ Tranche</button></div>{item.installments.map((row, installmentIndex) => <div className="fc-config-row" key={installmentIndex}><input className="form-input" value={row.name} onChange={(e) => updateItem(itemIndex, { installments: item.installments.map((entry, i) => i === installmentIndex ? { ...entry, name: e.target.value } : entry) })} required /><input className="form-input" type="number" min="0.01" max="100" step="0.01" value={row.percentage} onChange={(e) => updateItem(itemIndex, { installments: item.installments.map((entry, i) => i === installmentIndex ? { ...entry, percentage: Number(e.target.value) } : entry) })} required /><input className="form-input" type="date" value={row.due_date} onChange={(e) => updateItem(itemIndex, { installments: item.installments.map((entry, i) => i === installmentIndex ? { ...entry, due_date: e.target.value } : entry) })} /><button type="button" disabled={item.installments.length === 1} onClick={() => updateItem(itemIndex, { installments: item.installments.filter((_, i) => i !== installmentIndex) })}>×</button></div>)}<p className="fc-help">Total : {item.installments.reduce((sum, row) => sum + Number(row.percentage), 0)} %</p></div>}
      </div>)}
      <button type="button" className="fc-add-module" onClick={() => setItems([...items, newItem()])}>+ Ajouter une rubrique de frais</button><div className="fc-composition-total"><span>Total masculin : <b>{money(items.reduce((sum, item) => sum + item.male_amount, 0))}</b></span><span>Total féminin : <b>{money(items.reduce((sum, item) => sum + item.female_amount, 0))}</b></span></div><button className="btn-primary">Enregistrer la composition</button></form></div>}
    {copySource && <div className="teacher-modal-backdrop" onMouseDown={() => setCopySource(null)}><form className="teacher-modal fc-copy-modal" onSubmit={submitCopy} onMouseDown={(e) => e.stopPropagation()}><button type="button" className="modal-close" onClick={() => setCopySource(null)}>×</button><h2>Copier la configuration</h2><p>Copier les rubriques, montants par genre et tranches de <b>{copySource.level_name} {copySource.series} — {copySource.class_name}</b>.</p><div><b>Classes cibles</b><p className="fc-help">Cliquez pour sélectionner. Cliquez à nouveau pour désélectionner.</p></div><div className="fc-copy-class-grid">{classes.filter((row) => row.id !== copySource.school_class).map((row) => { const selected = copyTargets.has(row.id); return <button type="button" key={row.id} className={selected ? "selected" : ""} onClick={() => setCopyTargets((current) => { const next = new Set(current); if (next.has(row.id)) next.delete(row.id); else next.add(row.id); return next; })}><span className="fc-copy-check">{selected ? "✓" : ""}</span><span>{row.level_name} {row.series} — {row.name}</span>{plans.some((plan) => plan.school_class === row.id) && <small>Configuration existante</small>}</button>; })}</div><p className="fc-copy-selection">{copyTargets.size} classe(s) sélectionnée(s)</p><p className="fc-copy-warning">Les configurations existantes sans paiement seront remplacées. Aucune copie ne sera faite si une cible possède déjà des paiements.</p><button className="btn-primary" disabled={!copyTargets.size}>Copier vers les classes sélectionnées</button></form></div>}
  </div>;
}
