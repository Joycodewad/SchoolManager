import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { downloadTimetablePdf, getMyTimetable, MyTimetable as MyTimetableData } from "../api/timetable";

const DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"];

const shortTime = (value: string) => value.slice(0, 5);

export default function MyTimetable() {
  const { schoolId = "" } = useParams();
  const [data, setData] = useState<MyTimetableData | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!schoolId) return;
    setLoading(true);
    getMyTimetable(schoolId)
      .then(setData)
      .catch((issue) => setError(issue.message))
      .finally(() => setLoading(false));
  }, [schoolId]);

  const dayCount = data?.timetable?.days_per_week ?? 5;

  // La grille suit les créneaux paramétrés, pauses comprises : une journée se
  // lit d'un bloc, sans trou inexpliqué.
  const times = useMemo(() => (data?.periods ?? [])
    .map((period) => ({
      start: period.start_time, end: period.end_time,
      kind: period.kind, label: period.label,
    }))
    .sort((a, b) => a.start.localeCompare(b.start)), [data]);

  // Un enseignant qui réunit plusieurs classes n'assure qu'un cours : les
  // classes concernées sont rassemblées dans la même case.
  const cell = (day: number, start: string) => {
    const matching = (data?.slots ?? []).filter(
      (slot) => slot.day === day && slot.start_time === start,
    );
    if (!matching.length) return null;
    return {
      subject: matching[0].subject,
      classes: [...new Set(matching.map((slot) => slot.class_name))].sort().join(", "),
    };
  };

  // Deux classes réunies au même créneau comptent pour une seule heure.
  const hours = useMemo(
    () => new Set((data?.slots ?? []).map((slot) => `${slot.day}-${slot.start_time}`)).size,
    [data],
  );

  const exportPdf = async () => {
    setBusy(true); setError("");
    try {
      await downloadTimetablePdf(schoolId, "teachers", []);
    } catch (issue) {
      setError(issue instanceof Error ? issue.message : "Le PDF n’a pas pu être généré.");
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <div className="school-page"><p className="parents-empty">Chargement…</p></div>;

  return <div className="school-page">
    <div className="school-page-header">
      <div>
        <h1>Mon emploi du temps</h1>
        <p className="school-page-subtitle">
          {hours ? `${hours} heure(s) de cours par semaine.` : "Aucun cours ne vous est encore attribué."}
        </p>
      </div>
      {hours > 0 && <button className="btn-primary" type="button" onClick={exportPdf} disabled={busy}>
        {busy ? "Préparation…" : "Éditer en PDF"}
      </button>}
    </div>

    {error && <div className="form-error">{error}</div>}

    {!data?.timetable
      ? <section className="school-panel">
          <h2>Aucun emploi du temps</h2>
          <p className="parents-empty">
            L’emploi du temps de cette année scolaire n’a pas encore été généré.
          </p>
        </section>
      : hours === 0
        ? <section className="school-panel">
            <h2>Aucune heure attribuée</h2>
            <p className="parents-empty">
              Vous n’apparaissez dans aucun créneau de cet emploi du temps.
            </p>
          </section>
        : <div className="timetable-grid-wrapper">
            <table className="timetable-grid">
              <thead><tr><th>Horaire</th>{DAYS.slice(0, dayCount).map((day) => <th key={day}>{day}</th>)}</tr></thead>
              <tbody>{times.map((time) => time.kind === "pause"
                ? <tr key={time.start} className="timetable-break-row">
                    <th className="timetable-time">{shortTime(time.start)}<br />{shortTime(time.end)}</th>
                    <td colSpan={dayCount} className="timetable-break-cell">{time.label || "Pause"}</td>
                  </tr>
                : <tr key={time.start}>
                    <th className="timetable-time">{shortTime(time.start)}<br />{shortTime(time.end)}</th>
                    {DAYS.slice(0, dayCount).map((day, index) => {
                      const slot = cell(index, time.start);
                      return <td key={day}>{slot
                        ? <div className="timetable-slot">
                            <span className="timetable-subject">{slot.subject}</span>
                            <span className="timetable-teacher">{slot.classes}</span>
                          </div>
                        : <span className="timetable-free">—</span>}</td>;
                    })}
                  </tr>)}</tbody>
            </table>
          </div>}
  </div>;
}
