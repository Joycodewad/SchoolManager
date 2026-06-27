import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { AcademicYear, closeAcademicPeriod, closeAcademicYear, createAcademicYear, deleteAcademicYear, listAcademicYears, updateAcademicYear } from "../api/academicYears";
import { useAuth } from "../hooks/AuthContext";

export default function AcademicYears() {
  const { schoolId = "" } = useParams();
  const { refreshAcademicYears } = useAuth();
  const [years, setYears] = useState<AcademicYear[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editingYear, setEditingYear] = useState<AcademicYear | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [division, setDivision] = useState<"trimestre" | "semestre">("trimestre");

  const load = async () => {
    try { setYears(await listAcademicYears(schoolId)); }
    catch (e) { setError(e instanceof Error ? e.message : "Chargement impossible."); }
  };
  useEffect(() => { void load(); }, [schoolId]);

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setError(""); setMessage("");
    const form = new FormData(event.currentTarget);
    try {
      const periodRows = Array.from({ length: division === "trimestre" ? 3 : 2 }, (_, index) => ({
        name: String(form.get(`period_name_${index}`)).trim(),
        start_date: String(form.get(`period_start_${index}`)),
        end_date: String(form.get(`period_end_${index}`)),
      }));
      const enteredDates = periodRows.filter((period) => period.start_date || period.end_date);
      if (enteredDates.length > 0 && !periodRows.every((period) => period.start_date && period.end_date)) {
        throw new Error("Complétez toutes les dates des périodes ou laissez-les toutes vides pour un calcul automatique.");
      }
      const payload = {
        name: String(form.get("name")).trim(), start_date: String(form.get("start_date")), end_date: String(form.get("end_date")),
        division_system: division, is_active: editingYear?.is_active ? true : form.get("is_active") === "on",
        ...(enteredDates.length ? { periods: periodRows } : {}),
      };
      if (editingYear) {
        await updateAcademicYear(schoolId, editingYear.id, payload);
        setMessage("Année académique modifiée avec succès.");
      } else {
        await createAcademicYear(schoolId, payload);
        setMessage("Année académique créée avec ses périodes.");
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

  const closePeriod = async (year: AcademicYear, periodId: number) => {
    if (!window.confirm("Clôturer cette période académique ?")) return;
    try { await closeAcademicPeriod(schoolId, year.id, periodId); await load(); await refreshAcademicYears(); setMessage("Période clôturée."); }
    catch (e) { setError(e instanceof Error ? e.message : "Clôture impossible."); }
  };

  return <div className="content-inner">
    <div className="page-header"><h1 className="page-title">Années académiques</h1><button className="btn-primary" onClick={() => { setEditingYear(null); setDivision("trimestre"); setShowForm(true); }}>Créer une année</button></div>
    {error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}
    <div className="academic-year-grid">{years.map((year) => <article className={`academic-year-card${year.is_active ? " active" : ""}`} key={year.id}>
      <div className="academic-year-heading"><div><h2>{year.name}</h2><span>{year.division_label}</span></div>{year.is_active && <strong>Année active</strong>}</div>
      <p>{year.start_date} → {year.end_date}</p>
      <div className="academic-periods">{year.periods.map((period) => <div className={period.is_active ? "active" : ""} key={period.id}>
        <span><b>{period.name}</b><small>{period.start_date} → {period.end_date}</small></span>
        {period.is_closed ? <em>Clôturée</em> : period.is_active ? <button className="period-close-btn" onClick={() => void closePeriod(year, period.id)}>Clôturer</button> : <em>À venir</em>}
      </div>)}</div>
      <div className="academic-year-actions">{!year.is_active && !year.is_closed && <button className="subject-edit-btn" onClick={() => void activate(year)}>Activer</button>}
        {!year.is_closed && !year.periods.some((period) => period.is_closed) && <button className="subject-edit-btn" onClick={() => { setEditingYear(year); setDivision(year.division_system); setShowForm(true); }}>Modifier</button>}
        {!year.is_active && !year.is_closed && <button className="subject-delete-btn" onClick={() => void remove(year)}>Supprimer</button>}
        {!year.is_closed && <button className="year-close-btn" onClick={() => void closeYear(year)}>Clôturer l’année</button>}</div>
    </article>)}</div>
    {!years.length && <div className="empty-state"><p className="empty-title">Aucune année académique</p></div>}

    {showForm && <div className="teacher-modal-backdrop" onMouseDown={() => setShowForm(false)}><form className="teacher-modal academic-year-form" onSubmit={submit} onMouseDown={(event) => event.stopPropagation()}>
      <button type="button" className="modal-close" onClick={() => { setShowForm(false); setEditingYear(null); }}>×</button><h2>{editingYear ? "Modifier l’année académique" : "Créer une année académique"}</h2>
      <label>Nom *<input className="form-input" name="name" placeholder="2026-2027" defaultValue={editingYear?.name} required /></label>
      <label>Date de début *<input className="form-input" name="start_date" type="date" defaultValue={editingYear?.start_date} required /></label>
      <label>Date de fin *<input className="form-input" name="end_date" type="date" defaultValue={editingYear?.end_date} required /></label>
      <label>Découpage *<select className="form-select" name="division_system" value={division}
        onChange={(event) => setDivision(event.target.value as "trimestre" | "semestre")} disabled={Boolean(editingYear)}><option value="trimestre">3 trimestres</option><option value="semestre">2 semestres</option></select></label>
      <div className="manual-periods"><h3>Périodes</h3><p className="period-help">Dates optionnelles : laissez-les toutes vides pour une répartition automatique.</p>
        {Array.from({ length: division === "trimestre" ? 3 : 2 }, (_, index) => {
          const label = `${index + 1}${index === 0 ? "er" : "e"} ${division}`;
          return <fieldset className="manual-period" key={`${division}-${index}`}><legend>{label}</legend>
            <label>Nom<input className="form-input" name={`period_name_${index}`} defaultValue={editingYear?.periods[index]?.name ?? label} required /></label>
            <label>Début (optionnel)<input className="form-input" name={`period_start_${index}`} type="date" defaultValue={editingYear?.periods[index]?.start_date} /></label>
            <label>Fin (optionnel)<input className="form-input" name={`period_end_${index}`} type="date" defaultValue={editingYear?.periods[index]?.end_date} /></label>
          </fieldset>;
        })}
      </div>
      <label className="academic-active-check"><input type="checkbox" name="is_active" defaultChecked={editingYear?.is_active} disabled={Boolean(editingYear?.is_active)} />
        {editingYear?.is_active ? "Année active — utilisez Clôturer pour la désactiver" : "Définir comme année active"}</label>
      <button className="btn-primary" type="submit">{editingYear ? "Enregistrer les modifications" : "Créer l’année"}</button>
    </form></div>}
  </div>;
}
