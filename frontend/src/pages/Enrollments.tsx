import { ChangeEvent, FormEvent, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { cancelEnrollment, createEnrollment, Enrollment, GuardianLookupResult, importEnrollments, listEnrollments, listSchoolLevels, lookupGuardian, SchoolLevel, suggestEnrollmentNumber } from "../api/enrollments";
import { useAuth } from "../hooks/AuthContext";
import { listClasses, SchoolClass } from "../api/classes";

export default function Enrollments() {
  const { schoolId = "" } = useParams();
  const { activeAcademicYear } = useAuth();
  const [items, setItems] = useState<Enrollment[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [levels, setLevels] = useState<SchoolLevel[]>([]);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [selectedLevel, setSelectedLevel] = useState("");
  const [selectedCycle, setSelectedCycle] = useState<SchoolLevel["stage"] | "">("");
  const [selectedSeries, setSelectedSeries] = useState("");
  const selectedLevelData = levels.find((level) => level.id === Number(selectedLevel));
  const availableSeries = selectedLevelData?.name === "Seconde" ? ["CD", "A4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "Ti"]
    : selectedLevelData?.name === "Première" || selectedLevelData?.name === "Terminale" ? ["D", "A4", "C4", "G1", "G2", "G3", "F1", "F2", "F3", "F4", "E", "Ti"] : [];
  const [enrollmentNumber, setEnrollmentNumber] = useState("");
  const [formError, setFormError] = useState("");
  const [importing, setImporting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [guardianPhone, setGuardianPhone] = useState("+228");
  const [guardianResult, setGuardianResult] = useState<GuardianLookupResult | null>(null);
  const [checkingGuardian, setCheckingGuardian] = useState(false);

  const formatGuardianPhone = (value: string) => {
    const localDigits = value.replace(/\D/g, "").replace(/^228/, "").slice(0, 8);
    return `+228${localDigits}`;
  };

  const load = async () => {
    if (!activeAcademicYear) { setItems([]); return; }
    try { setItems(await listEnrollments(schoolId)); }
    catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };
  useEffect(() => {
    void load();
    void listSchoolLevels(schoolId).then(setLevels).catch((e) => setError(e.message));
    if (activeAcademicYear) void listClasses(schoolId).then(setClasses).catch((e) => setError(e.message));
  }, [schoolId, activeAcademicYear?.id]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setFormError(""); setMessage("");
    const formElement = event.currentTarget;
    const form = new FormData(formElement);
    try {
      const created = await createEnrollment(schoolId, {
        enrollment_number: enrollmentNumber.trim(),
        last_name: String(form.get("last_name")).trim(), first_names: String(form.get("first_names")).trim(),
        gender: String(form.get("gender")) as "M" | "F", date_of_birth: String(form.get("date_of_birth")), health_information: String(form.get("health_information") ?? "").trim(),
        level: Number(form.get("level")),
        series: selectedSeries,
        student_status: String(form.get("student_status")) as "nouveau" | "redoublant" | "abandon" | "bachelier",
        previous_average: form.get("previous_average") === "" ? null : Number(form.get("previous_average")),
        guardian_phone: guardianPhone,
        guardian_last_name: String(form.get("guardian_last_name") ?? "").trim(),
        guardian_first_names: String(form.get("guardian_first_names") ?? "").trim(),
        guardian_profession: String(form.get("guardian_profession") ?? "").trim(),
        school_class: form.get("school_class") ? Number(form.get("school_class")) : null,
      });
      setItems((current) => [created, ...current]); formElement.reset(); setSelectedCycle(""); setSelectedLevel(""); setSelectedSeries(""); setGuardianPhone("+228"); setGuardianResult(null); setShowForm(false); setMessage(`Élève inscrit avec le matricule ${created.enrollment_number}.`);
    } catch (e) { setFormError(e instanceof Error ? e.message : "Inscription impossible."); }
  };

  const openForm = async () => {
    setError(""); setFormError(""); setSelectedCycle(""); setSelectedLevel(""); setSelectedSeries(""); setGuardianPhone("+228"); setGuardianResult(null);
    try {
      setEnrollmentNumber(await suggestEnrollmentNumber(schoolId));
      setShowForm(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Impossible de générer le matricule.");
    }
  };

  const checkGuardian = async () => {
    setFormError(""); setGuardianResult(null); setCheckingGuardian(true);
    try { setGuardianResult(await lookupGuardian(schoolId, guardianPhone)); }
    catch (reason) { setFormError(reason instanceof Error ? reason.message : "Vérification du tuteur impossible."); }
    finally { setCheckingGuardian(false); }
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

  return <div className="content-inner enrollments-page">
    <div className="page-header"><div><h1 className="page-title">Inscriptions</h1><p className="page-context">Année : {activeAcademicYear?.name ?? "Aucune année sélectionnée"}</p></div>
      <div className="page-actions">
        <input ref={fileInputRef} type="file" accept=".xlsx,.csv" hidden onChange={(event) => void importFile(event)} />
        <button className="btn-secondary" disabled={importing || !activeAcademicYear?.is_active || activeAcademicYear?.is_closed} onClick={() => fileInputRef.current?.click()}>{importing ? "Import en cours…" : "Importer Excel"}</button>
        <button className="btn-primary" disabled={!activeAcademicYear?.is_active || activeAcademicYear?.is_closed} onClick={() => void openForm()}>Inscrire un élève</button>
      </div></div>
    <p className="import-hint">Colonnes attendues : matricule (optionnel), nom, prenoms, genre, date_naissance, moyenne, statut, cycle, niveau, serie, classe (optionnelle), telephone_tuteur, nom_tuteur, prenom_tuteur, profession_tuteur, allergies_et_soucis_de_sante.</p>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    {activeAcademicYear && (!activeAcademicYear.is_active || activeAcademicYear.is_closed) && <div className="form-error">Cette année est inactive ou clôturée : aucune nouvelle inscription n’est autorisée.</div>}
    {!activeAcademicYear ? <div className="empty-state"><p className="empty-title">Sélectionnez une année académique</p></div> :
      items.length === 0 ? <div className="empty-state"><p className="empty-title">Aucune inscription pour cette année</p></div> :
      <div className="teachers-table-wrap"><table className="teachers-table"><thead><tr><th>Matricule</th><th>Nom</th><th>Identifiant</th><th>Cycle</th><th>Niveau</th><th>Série</th><th>Classe</th><th>Genre</th><th>Naissance</th><th>Action</th></tr></thead>
        <tbody>{items.map((item) => <tr key={item.id}><td><strong>{item.enrollment_number}</strong></td><td>{item.student_name}</td><td>{item.student_username}</td><td>{item.level_stage}</td><td><span className="level-badge">{item.level_name}</span></td><td>{item.series || "—"}</td><td>{item.school_class_name || "Non assignée"}</td><td>{item.gender_label}</td><td>{item.date_of_birth_display}</td>
          <td><button className="subject-delete-btn" onClick={() => void cancel(item)}>Annuler</button></td></tr>)}</tbody></table></div>}

    {showForm && <div className="teacher-modal-backdrop" onMouseDown={() => setShowForm(false)}><form className="teacher-modal enrollment-form" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="modal-close" onClick={() => setShowForm(false)}>×</button><h2>Inscrire un élève</h2>
      {formError && <div className="form-error enrollment-form-error" role="alert">{formError}</div>}
      <label>Nom *<input className="form-input" name="last_name" required /></label><label>Prénoms *<input className="form-input" name="first_names" required /></label>
      <label>Numéro matricule *<input className="form-input" name="enrollment_number" value={enrollmentNumber}
        onChange={(event) => setEnrollmentNumber(event.target.value.toUpperCase().replace(/\s/g, ""))} required />
        <span className="form-hint">Généré automatiquement, mais modifiable.</span></label>
      <label>Genre *<select className="form-select" name="gender" required><option value="">Choisir</option><option value="M">Masculin</option><option value="F">Féminin</option></select></label>
      <label>Statut *<select className="form-select" name="student_status" defaultValue="nouveau" required><option value="nouveau">Nouveau</option><option value="redoublant">Redoublant</option><option value="abandon">Abandon</option><option value="bachelier">Bachelier</option></select></label>
      <label>Moyenne de l’année écoulée /20<input className="form-input" name="previous_average" type="number" min="0" max="20" step="0.01" placeholder="Ex. 14,50" /></label>
      <fieldset className="guardian-fields">
        <legend>Informations du tuteur</legend>
        <div className="guardian-phone-row"><label>Numéro du tuteur *<input className="form-input" value={guardianPhone} onChange={(event) => { setGuardianPhone(formatGuardianPhone(event.target.value)); setGuardianResult(null); }} pattern="\+228[0-9]{8}" required /></label><button className="btn-secondary" type="button" disabled={checkingGuardian || guardianPhone.length !== 12} onClick={() => void checkGuardian()}>{checkingGuardian ? "Vérification…" : "Vérifier le numéro"}</button></div>
        {guardianResult?.found && <div className="guardian-found"><strong>Parent retrouvé dans la base</strong><span>{guardianResult.last_name} {guardianResult.first_names}</span><span>{guardianResult.profession || "Profession non renseignée"}</span></div>}
        {guardianResult && !guardianResult.found && <div className="guardian-manual-fields"><p className="form-hint">Aucun parent trouvé : renseignez ses informations.</p><label>Nom du tuteur *<input className="form-input" name="guardian_last_name" required /></label><label>Prénom du tuteur *<input className="form-input" name="guardian_first_names" required /></label><label>Profession<input className="form-input" name="guardian_profession" /></label></div>}
        {!guardianResult && <p className="form-hint">Saisissez les 8 chiffres après +228 puis vérifiez le numéro.</p>}
      </fieldset>
      <label>Cycle *<select className="form-select" value={selectedCycle} onChange={(event) => { setSelectedCycle(event.target.value as SchoolLevel["stage"]); setSelectedLevel(""); setSelectedSeries(""); }} required><option value="">Choisir un cycle</option><option value="primaire">Primaire</option><option value="college">Collège</option><option value="lycee">Lycée</option></select></label>
      <label>Niveau *<select className="form-select" name="level" value={selectedLevel} disabled={!selectedCycle} onChange={(event) => { setSelectedLevel(event.target.value); setSelectedSeries(""); }} required><option value="">{selectedCycle ? "Choisir un niveau" : "Choisissez d’abord le cycle"}</option>
        {levels.filter((level) => level.stage === selectedCycle).map((level) => <option key={level.id} value={level.id}>{level.name}</option>)}</select></label>
      {selectedCycle === "lycee" && <label>Série *<select className="form-select" value={selectedSeries} onChange={(event) => setSelectedSeries(event.target.value)} disabled={!selectedLevel} required><option value="">Choisir une série</option>{availableSeries.map((series) => <option key={series} value={series}>{series}</option>)}</select></label>}
      <label>Classe (optionnelle)<select className="form-select" name="school_class" disabled={!selectedLevel || (selectedCycle === "lycee" && !selectedSeries)}><option value="">Sans classe</option>
        {classes.filter((schoolClass) => schoolClass.level === Number(selectedLevel) && (selectedCycle !== "lycee" || schoolClass.series.toLowerCase() === selectedSeries.toLowerCase())).map((schoolClass) => <option key={schoolClass.id} value={schoolClass.id}>{schoolClass.name}</option>)}
      </select></label>
      <label>Date de naissance *<input className="form-input" name="date_of_birth" type="date" required /></label>
      <label className="enrollment-address">Allergies et soucis de santé<textarea className="form-input" name="health_information" placeholder="Ex. Allergie aux arachides, asthme…" /></label>
      <button className="btn-primary" type="submit">Enregistrer l’inscription</button>
    </form></div>}
  </div>;
}
