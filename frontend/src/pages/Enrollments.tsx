import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { cancelEnrollment, createEnrollment, Enrollment, importEnrollments, listEnrollments, listSchoolLevels, SchoolLevel, suggestEnrollmentNumber } from "../api/enrollments";
import { useAuth } from "../hooks/AuthContext";

export default function Enrollments() {
  const { schoolId = "" } = useParams();
  const { activeAcademicYear } = useAuth();
  const [items, setItems] = useState<Enrollment[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [levels, setLevels] = useState<SchoolLevel[]>([]);
  const [enrollmentNumber, setEnrollmentNumber] = useState("");
  const [formError, setFormError] = useState("");
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const load = async () => {
    if (!activeAcademicYear) { setItems([]); return; }
    try { setItems(await listEnrollments(schoolId)); }
    catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };
  useEffect(() => {
    void load();
    void listSchoolLevels(schoolId).then(setLevels).catch((e) => setError(e.message));
  }, [schoolId, activeAcademicYear?.id]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setFormError(""); setMessage("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      const created = await createEnrollment(schoolId, {
        enrollment_number: enrollmentNumber.trim(),
        last_name: String(form.get("last_name")).trim(), first_names: String(form.get("first_names")).trim(),
        gender: String(form.get("gender")) as "M" | "F", date_of_birth: String(form.get("date_of_birth")), address: String(form.get("address")).trim(),
        level: Number(form.get("level")),
      });
      setItems((current) => [created, ...current]); formElement.reset(); setShowForm(false); setMessage(`Élève inscrit avec le matricule ${created.enrollment_number}.`);
    } catch (e) { setFormError(e instanceof Error ? e.message : "Inscription impossible."); }
  };

  const openForm = async () => {
    setError(""); setFormError("");
    try {
      setEnrollmentNumber(await suggestEnrollmentNumber(schoolId));
      setShowForm(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Impossible de générer le matricule.");
    }
  };

  const cancel = async (item: Enrollment) => {
    if (!window.confirm(`Annuler l’inscription de ${item.student_name} ?`)) return;
    try { await cancelEnrollment(schoolId, item.id); setItems((current) => current.filter((row) => row.id !== item.id)); }
    catch (e) { setError(e instanceof Error ? e.message : "Annulation impossible."); }
  };

  const importFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setError(""); setMessage(""); setImporting(true);
    try {
      const result = await importEnrollments(schoolId, file);
      setMessage(result.message);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import impossible.");
    } finally { setImporting(false); }
  };

  return <div className="content-inner">
    <div className="page-header"><div><h1 className="page-title">Inscriptions</h1><p className="page-context">Année : {activeAcademicYear?.name ?? "Aucune année sélectionnée"}</p></div>
      <div className="page-actions">
        <input ref={fileInputRef} type="file" accept=".xlsx,.csv" hidden onChange={(event) => void importFile(event)} />
        <button className="btn-secondary" disabled={importing || !activeAcademicYear?.is_active || activeAcademicYear?.is_closed} onClick={() => fileInputRef.current?.click()}>{importing ? "Import en cours…" : "Importer Excel"}</button>
        <button className="btn-primary" disabled={!activeAcademicYear?.is_active || activeAcademicYear?.is_closed} onClick={() => void openForm()}>Inscrire un élève</button>
      </div></div>
    <p className="import-hint">Colonnes attendues : matricule (optionnel), nom, prenoms, genre, date_naissance, niveau, adresse (optionnel).</p>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    {activeAcademicYear && (!activeAcademicYear.is_active || activeAcademicYear.is_closed) && <div className="form-error">Cette année est inactive ou clôturée : aucune nouvelle inscription n’est autorisée.</div>}
    {!activeAcademicYear ? <div className="empty-state"><p className="empty-title">Sélectionnez une année académique</p></div> :
      items.length === 0 ? <div className="empty-state"><p className="empty-title">Aucune inscription pour cette année</p></div> :
      <div className="teachers-table-wrap"><table className="teachers-table"><thead><tr><th>Matricule</th><th>Nom</th><th>Identifiant</th><th>Niveau</th><th>Genre</th><th>Naissance</th><th>Action</th></tr></thead>
        <tbody>{items.map((item) => <tr key={item.id}><td><strong>{item.enrollment_number}</strong></td><td>{item.student_name}</td><td>{item.student_username}</td><td><span className="level-badge">{item.level_name}</span></td><td>{item.gender_label}</td><td>{item.date_of_birth_display}</td>
          <td><button className="subject-delete-btn" onClick={() => void cancel(item)}>Annuler</button></td></tr>)}</tbody></table></div>}

    {showForm && <div className="teacher-modal-backdrop" onMouseDown={() => setShowForm(false)}><form className="teacher-modal enrollment-form" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="modal-close" onClick={() => setShowForm(false)}>×</button><h2>Inscrire un élève</h2>
      {formError && <div className="form-error enrollment-form-error" role="alert">{formError}</div>}
      <label>Nom *<input className="form-input" name="last_name" required /></label><label>Prénoms *<input className="form-input" name="first_names" required /></label>
      <label>Numéro matricule *<input className="form-input" name="enrollment_number" value={enrollmentNumber}
        onChange={(event) => setEnrollmentNumber(event.target.value.toUpperCase().replace(/\s/g, ""))} required />
        <span className="form-hint">Généré automatiquement, mais modifiable.</span></label>
      <label>Genre *<select className="form-select" name="gender" required><option value="">Choisir</option><option value="M">Masculin</option><option value="F">Féminin</option></select></label>
      <label>Niveau *<select className="form-select" name="level" required><option value="">Choisir un niveau</option>
        {(["primaire", "college", "lycee"] as const).map((stage) => <optgroup key={stage} label={levels.find((level) => level.stage === stage)?.stage_label ?? stage}>
          {levels.filter((level) => level.stage === stage).map((level) => <option key={level.id} value={level.id}>{level.name}</option>)}
        </optgroup>)}</select></label>
      <label>Date de naissance *<input className="form-input" name="date_of_birth" type="date" required /></label>
      <label className="enrollment-address">Adresse<textarea className="form-input" name="address" /></label>
      <button className="btn-primary" type="submit">Enregistrer l’inscription</button>
    </form></div>}
  </div>;
}
