import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { AcademicSession, AcademicYear, closeAcademicSession, closeAcademicYear, createAcademicSession, createAcademicYear, deleteAcademicYear, listAcademicYears, updateAcademicSession, updateAcademicYear } from "../api/academicYears";
import { useAuth } from "../hooks/AuthContext";
import { listClasses, SchoolClass } from "../api/classes";

export default function AcademicYears() {
  const { schoolId = "" } = useParams();
  const { refreshAcademicYears } = useAuth();
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingYear, setEditingYear] = useState<AcademicYear | null>(null);
  const [sessionYear, setSessionYear] = useState<AcademicYear | null>(null);
  const [editingSession, setEditingSession] = useState<AcademicSession | null>(null);
  const [schoolClasses, setSchoolClasses] = useState<SchoolClass[]>([]);
  const [sessionClassIds, setSessionClassIds] = useState<Set<number>>(new Set());
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const occupiedClassSessions = new Map<number, string>();
  sessionYear?.sessions.filter((session) => session.is_active && session.id !== editingSession?.id).forEach((session) =>
    session.classes.forEach((classId) => occupiedClassSessions.set(classId, session.name)),
  );

  const load = async () => {
    try { setYears(await listAcademicYears(schoolId)); }
    catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };
  useEffect(() => { void load(); void listClasses(schoolId).then(setSchoolClasses).catch(() => setSchoolClasses([])); }, [schoolId]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const payload = {
        name: String(form.get("name")).trim(), start_date: String(form.get("start_date")), end_date: String(form.get("end_date")),
        is_active: editingYear?.is_active ? true : form.get("is_active") === "on",
      };
      if (editingYear) {
        await updateAcademicYear(schoolId, editingYear.id, payload);
        setMessage("Année académique modifiée avec succès.");
      } else {
        await createAcademicYear(schoolId, payload);
        setMessage("Année académique créée avec succès.");
      }
      setShowForm(false); setEditingYear(null); await load(); await refreshAcademicYears();
    } catch (e) { setError(e instanceof Error ? e.message : "Création impossible."); }
  };

  const activate = async (year: AcademicYear) => {
    try { await updateAcademicYear(schoolId, year.id, { is_active: true }); await load(); await refreshAcademicYears(); }
    catch (e) { setError(e instanceof Error ? e.message : "Activation impossible."); }
  };

  const remove = async (year: AcademicYear) => {
    if (!window.confirm(`Supprimer l’année ${year.name} ?`)) return;
    try { await deleteAcademicYear(schoolId, year.id); await load(); await refreshAcademicYears(); }
    catch (e) { setError(e instanceof Error ? e.message : "Suppression impossible."); }
  };

  const closeYear = async (year: AcademicYear) => {
    if (!window.confirm(`Clôturer définitivement l’année ${year.name} ?`)) return;
    try { await closeAcademicYear(schoolId, year.id); await load(); await refreshAcademicYears(); setMessage("Année académique clôturée."); }
    catch (e) { setError(e instanceof Error ? e.message : "Clôture impossible."); }
  };

  const submitSession = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!sessionYear) return; setError(""); setMessage("");
    const form = new FormData(event.currentTarget);
    const payload = { name: String(form.get("name")).trim(), label: String(form.get("label")).trim(), start_date: String(form.get("start_date")), end_date: String(form.get("end_date")), classes: [...sessionClassIds] };
    try {
      if (editingSession) await updateAcademicSession(schoolId, sessionYear.id, editingSession.id, payload);
      else await createAcademicSession(schoolId, sessionYear.id, payload);
      setSessionYear(null); setEditingSession(null); setMessage("Session académique enregistrée."); await load(); await refreshAcademicYears();
    } catch (e) { setError(e instanceof Error ? e.message : "Enregistrement de la session impossible."); }
  };
  const closeSession = async (year: AcademicYear, session: AcademicSession) => {
    if (!window.confirm(`Clôturer définitivement la session « ${session.name} » ?`)) return;
    try { await closeAcademicSession(schoolId, year.id, session.id); await load(); await refreshAcademicYears(); setMessage("Session clôturée."); }
    catch (e) { setError(e instanceof Error ? e.message : "Clôture impossible."); }
  };

  return <div className="content-inner">
    <div className="page-header"><h1 className="page-title">Années académiques</h1><button className="btn-primary" onClick={() => { setEditingYear(null); setShowForm(true); }}>Créer une année</button></div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    <div className="academic-year-grid">{years.map((year) => <article className={`academic-year-card${year.is_active ? " active" : ""}`} key={year.id}>
      <div className="academic-year-heading"><h2>{year.name}</h2>{year.is_active && <strong>Année active</strong>}</div>
      <p>{year.start_date} → {year.end_date}</p>
      <div className="academic-session-list">{year.sessions.map((session) => <div className={`academic-session-item${session.is_active ? " active" : ""}${session.is_closed ? " closed" : ""}`} key={session.id}><div><b>{session.name}<span className="session-label">{session.label}</span></b><small>{session.start_date} → {session.end_date}</small><small className="session-classes">{session.class_names.join(", ") || "Aucune classe"}</small></div><div className="academic-session-actions">{session.is_closed ? <em className="closed">Clôturée</em> : <>{session.is_active && <em>Active</em>}{!year.is_closed && <button onClick={() => { setSessionYear(year); setEditingSession(session); setSessionClassIds(new Set(session.classes)); }}>Modifier</button>}<button className="close-session" onClick={() => void closeSession(year, session)}>Clôturer</button></>}</div></div>)}</div>
      <div className="academic-year-actions">{!year.is_active && !year.is_closed && <button className="subject-edit-btn" onClick={() => void activate(year)}>Activer</button>}
        {year.is_active && !year.is_closed && <button className="subject-edit-btn" onClick={() => { setSessionYear(year); setEditingSession(null); setSessionClassIds(new Set()); }}>+ Session</button>}
        {!year.is_closed && <button className="subject-edit-btn" onClick={() => { setEditingYear(year); setShowForm(true); }}>Modifier</button>}
        {!year.is_active && !year.is_closed && <button className="subject-delete-btn" onClick={() => void remove(year)}>Supprimer</button>}
        {!year.is_closed && <button className="year-close-btn" onClick={() => void closeYear(year)}>Clôturer l’année</button>}</div>
    </article>)}</div>
    {!years.length && <div className="empty-state"><p className="empty-title">Aucune année académique</p></div>}

    {showForm && <div className="teacher-modal-backdrop" onMouseDown={() => setShowForm(false)}><form className="teacher-modal academic-year-form" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="modal-close" onClick={() => { setShowForm(false); setEditingYear(null); }}>×</button><h2>{editingYear ? "Modifier l’année académique" : "Créer une année académique"}</h2>
      <label>Nom *<input className="form-input" name="name" placeholder="2026-2027" defaultValue={editingYear?.name} required /></label>
      <label>Date de début *<input className="form-input" name="start_date" type="date" defaultValue={editingYear?.start_date} required /></label>
      <label>Date de fin *<input className="form-input" name="end_date" type="date" defaultValue={editingYear?.end_date} required /></label>
      <label className="academic-active-check"><input type="checkbox" name="is_active" defaultChecked={editingYear?.is_active} disabled={Boolean(editingYear?.is_active)} />
        {editingYear?.is_active ? "Année active — utilisez Clôturer pour la désactiver" : "Définir comme année active"}</label>
      <button className="btn-primary" type="submit">{editingYear ? "Enregistrer les modifications" : "Créer l’année"}</button>
    </form></div>}
    {sessionYear && <div className="teacher-modal-backdrop" onMouseDown={() => setSessionYear(null)}><form className="teacher-modal academic-year-form academic-session-form" onSubmit={submitSession} onMouseDown={(event) => event.stopPropagation()}><button type="button" className="modal-close" onClick={() => { setSessionYear(null); setEditingSession(null); }}>×</button><h2>{editingSession ? "Modifier" : "Créer"} une session — {sessionYear.name}</h2><label>Nom unique *<input className="form-input" name="name" placeholder="Ex. Premier Trimestre Primaire" defaultValue={editingSession?.name} required /></label><label>Label *<input className="form-input" name="label" placeholder="Ex. Premier Trimestre" defaultValue={editingSession?.label} required /></label><label>Date de début *<input className="form-input" name="start_date" type="date" defaultValue={editingSession?.start_date} required /></label><label>Date de fin *<input className="form-input" name="end_date" type="date" defaultValue={editingSession?.end_date} required /></label><div className="academic-session-class-picker"><b>Classes concernées *</b><small>Cliquez pour sélectionner ou désélectionner une classe. Une classe déjà utilisée dans une session active est indisponible.</small><div>{schoolClasses.map((schoolClass) => { const selected = sessionClassIds.has(schoolClass.id); const occupiedBy = occupiedClassSessions.get(schoolClass.id); return <button type="button" disabled={Boolean(occupiedBy)} className={`${selected ? "selected" : ""}${occupiedBy ? " unavailable" : ""}`} key={schoolClass.id} onClick={() => setSessionClassIds((current) => { const next = new Set(current); if (next.has(schoolClass.id)) next.delete(schoolClass.id); else next.add(schoolClass.id); return next; })}><span>{selected ? "✓" : ""}</span><span>{schoolClass.level_name} {schoolClass.series} — {schoolClass.name}{occupiedBy && <small>Session : {occupiedBy}</small>}</span></button>; })}</div><em>{sessionClassIds.size} classe(s) sélectionnée(s)</em></div>{!editingSession && <p className="form-hint academic-session-auto-active">Le label peut être partagé par plusieurs sessions, mais le nom doit être différent.</p>}<button className="btn-primary" disabled={!sessionClassIds.size}>Enregistrer la session</button></form></div>}
  </div>;
}
