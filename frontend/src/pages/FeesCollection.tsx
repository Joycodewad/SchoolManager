import { FormEvent, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { listClasses, SchoolClass } from "../api/classes";
import { Enrollment, listEnrollments } from "../api/enrollments";
import { ComplianceReport, createPayment, FeePayment, FeePlan, getCompliance, listFeePlans, listPayments } from "../api/finance";

type Tab = "payments" | "compliance";
const money = (value: string | number) => `${Number(value || 0).toLocaleString("fr-FR")} FCFA`;

export default function FeesCollection() {
  const { schoolId = "" } = useParams();
  const [tab, setTab] = useState<Tab>("payments");
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [enrollments, setEnrollments] = useState<Enrollment[]>([]);
  const [plans, setPlans] = useState<FeePlan[]>([]);
  const [payments, setPayments] = useState<FeePayment[]>([]);
  const [classId, setClassId] = useState<number>(0);
  const [target, setTarget] = useState("");
  const [paymentItemId, setPaymentItemId] = useState(0);
  const [paymentEnrollmentId, setPaymentEnrollmentId] = useState(0);
  const [paymentInstallmentId, setPaymentInstallmentId] = useState(0);
  const [studentSearch, setStudentSearch] = useState("");
  const [studentPickerOpen, setStudentPickerOpen] = useState(false);
  const [report, setReport] = useState<ComplianceReport | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "ok" | "late">("all");
  const [showPayment, setShowPayment] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const load = async () => {
    try {
      const [classRows, enrollmentRows, planRows, paymentRows] = await Promise.all([
        listClasses(schoolId), listEnrollments(schoolId), listFeePlans(schoolId), listPayments(schoolId),
      ]);
      setClasses(classRows); setEnrollments(enrollmentRows); setPlans(planRows); setPayments(paymentRows);
      setClassId((current) => current || classRows[0]?.id || 0);
    } catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };
  useEffect(() => { void load(); }, [schoolId]);

  const selectedPlan = plans.find((plan) => plan.school_class === classId) ?? null;
  const classEnrollments = enrollments.filter((item) => item.school_class === classId && item.status === "active");
  const normalizedStudentSearch = studentSearch.trim().toLocaleLowerCase("fr");
  const filteredClassEnrollments = classEnrollments.filter((item) => !normalizedStudentSearch ||
    item.student_name.toLocaleLowerCase("fr").includes(normalizedStudentSearch) ||
    item.enrollment_number.toLocaleLowerCase("fr").includes(normalizedStudentSearch));
  const selectedEnrollment = classEnrollments.find((item) => item.id === paymentEnrollmentId) ?? null;
  const baseAmount = (item: NonNullable<FeePlan["items"]>[number]) => Number(selectedEnrollment?.student_gender === "F" ? item.female_amount : item.male_amount);
  const paidAmount = (itemId: number, installmentId?: number) => payments.filter((row) => row.enrollment === selectedEnrollment?.id && row.class_fee === itemId && (installmentId === undefined || row.installment === installmentId)).reduce((sum, row) => sum + Number(row.amount), 0);
  const itemRemaining = (item: NonNullable<FeePlan["items"]>[number]) => Math.max(0, baseAmount(item) - paidAmount(item.id));
  const availableItems = selectedPlan?.items.filter((item) => itemRemaining(item) > 0) ?? [];
  const selectedPaymentItem = availableItems.find((item) => item.id === paymentItemId) ?? availableItems[0] ?? null;
  const installmentRemaining = (installment: NonNullable<typeof selectedPaymentItem>["installments"][number]) => Math.max(0, baseAmount(selectedPaymentItem!) * Number(installment.percentage) / 100 - paidAmount(selectedPaymentItem!.id, installment.id));
  const availableInstallments = selectedPaymentItem?.installments.filter((row) => installmentRemaining(row) > 0) ?? [];
  const selectedInstallment = availableInstallments.find((row) => row.id === paymentInstallmentId) ?? availableInstallments[0] ?? null;
  const expectedPayment = selectedPaymentItem ? (selectedPaymentItem.payable_in_installments && selectedInstallment ? baseAmount(selectedPaymentItem) * Number(selectedInstallment.percentage) / 100 : baseAmount(selectedPaymentItem)) : 0;
  const alreadyPaid = selectedPaymentItem ? (selectedPaymentItem.payable_in_installments && selectedInstallment ? paidAmount(selectedPaymentItem.id, selectedInstallment.id) : paidAmount(selectedPaymentItem.id)) : 0;
  const paymentRemaining = Math.max(0, expectedPayment - alreadyPaid);
  const filteredReport = report?.students.filter((row) => statusFilter === "all" || (statusFilter === "ok" ? row.is_compliant : !row.is_compliant)) ?? [];
  const collected = useMemo(() => payments.reduce((sum, row) => sum + Number(row.amount), 0), [payments]);

  useEffect(() => {
    const firstItem = selectedPlan?.items[0];
    if (!firstItem) { setTarget(""); setPaymentItemId(0); return; }
    setTarget(`item:${firstItem.id}`); setPaymentItemId(firstItem.id);
  }, [selectedPlan?.id]);

  useEffect(() => {
    if (!classId || !target || tab !== "compliance") return;
    setReport(null); setError("");
    void getCompliance(schoolId, classId, target).then(setReport).catch((e) => setError(e instanceof Error ? e.message : "Rapport impossible."));
  }, [schoolId, classId, target, tab, plans.length, payments.length]);

  const submitPayment = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); const form = new FormData(event.currentTarget);
    try {
      await createPayment(schoolId, {
        enrollment: Number(form.get("enrollment")), class_fee: Number(form.get("class_fee")),
        installment: selectedPaymentItem?.payable_in_installments ? selectedInstallment?.id : null,
        amount: Number(form.get("amount")), paid_on: String(form.get("paid_on")), method: String(form.get("method")),
        reference: String(form.get("reference") ?? ""), notes: String(form.get("notes") ?? ""),
      });
      setShowPayment(false); setMessage("Paiement enregistré avec succès."); await load();
    } catch (e) { setError(e instanceof Error ? e.message : "Paiement impossible."); }
  };

  return <div className="fc-root">
    <div className="fc-page-head"><div><h1>Gestion de la scolarité</h1><p>Barèmes, tranches, encaissements et suivi des élèves.</p></div><button className="btn-primary" onClick={() => { setStudentSearch(""); setStudentPickerOpen(false); setPaymentEnrollmentId(0); setPaymentItemId(0); setPaymentInstallmentId(0); setShowPayment(true); }} disabled={!plans.length}>+ Enregistrer un paiement</button></div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    <div className="fc-summary">
      <div><span>Montant encaissé</span><strong>{money(collected)}</strong></div><div><span>Paiements enregistrés</span><strong>{payments.length}</strong></div><div><span>Classes configurées</span><strong>{plans.length} / {classes.length}</strong></div>
    </div>
    <div className="fc-tabs"><button className={tab === "payments" ? "active" : ""} onClick={() => setTab("payments")}>Paiements</button><button className={tab === "compliance" ? "active" : ""} onClick={() => setTab("compliance")}>En règle / non en règle</button></div>

    {tab === "payments" && <section className="fc-table-section"><div className="fc-table-header"><span className="fc-chart-title">Historique des paiements</span></div><div className="fc-table-wrap"><table className="fc-table"><thead><tr><th>Date</th><th>Élève</th><th>Classe</th><th>Rubrique</th><th>Tranche</th><th>Montant</th><th>Mode</th><th>Référence</th></tr></thead><tbody>{payments.map((row) => <tr key={row.id}><td>{row.paid_on}</td><td><b>{row.student_name}</b><small className="fc-block">{row.enrollment_number}</small></td><td>{row.class_name}</td><td>{row.module_name}</td><td>{row.installment_name ?? "—"}</td><td className="fc-amount">{money(row.amount)}</td><td>{row.method_label}</td><td>{row.reference || "—"}</td></tr>)}</tbody></table>{!payments.length && <p className="fc-empty">Aucun paiement enregistré.</p>}</div></section>}

    {tab === "compliance" && <section className="fc-table-section"><div className="fc-table-header"><span className="fc-chart-title">Situation des élèves</span><div className="fc-table-controls"><select className="fc-select" value={classId} onChange={(e) => setClassId(Number(e.target.value))}>{classes.map((row) => <option value={row.id} key={row.id}>{row.level_name} {row.series} — {row.name}</option>)}</select><select className="fc-select" value={target} onChange={(e) => setTarget(e.target.value)}>{selectedPlan?.items.flatMap((item) => [<option value={`item:${item.id}`} key={`item-${item.id}`}>{item.module_name} — total</option>, ...item.installments.map((row) => <option value={`installment:${row.id}`} key={`installment-${row.id}`}>{item.module_name} — {row.name}</option>)])}</select><select className="fc-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}><option value="all">Tous</option><option value="ok">En règle</option><option value="late">Non en règle</option></select></div></div>{report && <div className="fc-compliance-counts"><span className="ok">{report.compliant_count} en règle</span><span className="late">{report.non_compliant_count} non en règle</span><b>{report.target}</b></div>}<div className="fc-table-wrap"><table className="fc-table"><thead><tr><th>Matricule</th><th>Élève</th><th>Genre</th><th>Statut</th><th>À payer</th><th>Payé</th><th>Reste</th><th>Situation</th></tr></thead><tbody>{filteredReport.map((row) => <tr key={row.enrollment}><td>{row.enrollment_number}</td><td><b>{row.student_name}</b></td><td>{row.gender}</td><td>{row.student_status}</td><td>{money(row.expected)}</td><td>{money(row.paid)}</td><td>{money(row.balance)}</td><td><span className={`fc-status ${row.is_compliant ? "is-ok" : "is-late"}`}>{row.is_compliant ? "En règle" : "Non en règle"}</span></td></tr>)}</tbody></table></div></section>}

    {showPayment && <div className="teacher-modal-backdrop" onMouseDown={() => setShowPayment(false)}><form className="teacher-modal fc-modal" onSubmit={submitPayment} onMouseDown={(e) => e.stopPropagation()}><button type="button" className="modal-close" onClick={() => setShowPayment(false)}>×</button><h2>Enregistrer un paiement</h2><label>Classe<select className="form-select" value={classId} onChange={(e) => { setClassId(Number(e.target.value)); setStudentSearch(""); setStudentPickerOpen(false); setPaymentEnrollmentId(0); setPaymentItemId(0); setPaymentInstallmentId(0); }}>{plans.map((plan) => <option value={plan.school_class} key={plan.id}>{plan.level_name} {plan.series} — {plan.class_name}</option>)}</select></label><label className="fc-full">Élève<div className={`fc-searchable-select${studentPickerOpen ? " open" : ""}`}><input className="form-input" value={studentSearch} onFocus={() => setStudentPickerOpen(true)} onBlur={() => window.setTimeout(() => setStudentPickerOpen(false), 150)} onChange={(e) => { setStudentSearch(e.target.value); setStudentPickerOpen(true); setPaymentEnrollmentId(0); setPaymentItemId(0); setPaymentInstallmentId(0); }} placeholder="Rechercher par nom, prénom ou matricule…" autoComplete="off" required /><span className="fc-select-chevron">⌄</span>{studentPickerOpen && <div className="fc-searchable-options">{filteredClassEnrollments.map((row) => <button type="button" key={row.id} className={row.id === paymentEnrollmentId ? "selected" : ""} onMouseDown={(e) => e.preventDefault()} onClick={() => { setPaymentEnrollmentId(row.id); setStudentSearch(`${row.student_name} — ${row.enrollment_number}`); setPaymentItemId(0); setPaymentInstallmentId(0); setStudentPickerOpen(false); }}><b>{row.student_name}</b><small>{row.enrollment_number}</small></button>)}{!filteredClassEnrollments.length && <span className="fc-no-option">Aucun élève trouvé</span>}</div>}</div><input type="hidden" name="enrollment" value={selectedEnrollment?.id ?? ""} /></label><label>Rubrique<select className="form-select" name="class_fee" value={selectedPaymentItem?.id ?? ""} onChange={(e) => { setPaymentItemId(Number(e.target.value)); setPaymentInstallmentId(0); }} required>{selectedPlan?.items.map((item) => { const paid = itemRemaining(item) <= 0; return <option value={item.id} key={item.id} disabled={paid}>{item.module_name}{paid ? " — Payée" : ` — reste ${money(itemRemaining(item))}`}</option>; })}</select></label><label>Tranche<select className="form-select" name="installment" value={selectedInstallment?.id ?? ""} onChange={(e) => setPaymentInstallmentId(Number(e.target.value))} disabled={!selectedPaymentItem?.payable_in_installments} required={Boolean(selectedPaymentItem?.payable_in_installments)}>{selectedPaymentItem?.installments.map((row) => { const paid = installmentRemaining(row) <= 0; return <option value={row.id} key={row.id} disabled={paid}>{row.name} ({row.percentage} %){paid ? " — Payée" : ` — reste ${money(installmentRemaining(row))}`}</option>; })}</select></label><div className="fc-payment-due fc-full"><span>Montant à payer</span><strong>{money(expectedPayment)}</strong><small>Déjà payé : {money(alreadyPaid)} · Reste : {money(paymentRemaining)}</small></div><label>Montant<input key={`${selectedEnrollment?.id}-${selectedPaymentItem?.id}-${selectedInstallment?.id}-${paymentRemaining}`} className="form-input" name="amount" type="number" min="1" max={paymentRemaining} step="0.01" defaultValue={paymentRemaining || ""} required disabled={!paymentRemaining} /></label><label>Date<input className="form-input" name="paid_on" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required /></label><label>Mode<select className="form-select" name="method"><option value="especes">Espèces</option><option value="mobile_money">Mobile Money</option><option value="banque">Banque</option><option value="autre">Autre</option></select></label><label>Référence<input className="form-input" name="reference" /></label><label className="fc-full">Notes<textarea className="form-input" name="notes" /></label>{selectedEnrollment && !availableItems.length && <div className="form-success fc-full">Toutes les rubriques de cet élève sont entièrement payées.</div>}<button className="btn-primary fc-full" disabled={!selectedEnrollment || !paymentRemaining}>Enregistrer</button></form></div>}

  </div>;
}
