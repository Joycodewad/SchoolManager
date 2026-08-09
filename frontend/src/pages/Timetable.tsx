import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  deleteTimetable, downloadTimetablePdf, generateTimetable, getTimetable, getTimetableSetup,
  saveTimetableSetup, SubjectRestriction, Timetable as TimetableData,
  TimetableOptions, TimetablePeriod, TimetableSlot, validateTimetable,
} from "../api/timetable";

const DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"];
const shortTime = (value: string) => value.slice(0, 5);

const OPTION_LABELS: Array<{ key: keyof TimetableOptions; label: string; hint: string }> = [
  { key: "skip_primary", label: "Ne pas générer pour le primaire", hint: "Seuls le collège et le lycée reçoivent un emploi du temps." },
  { key: "enforce_single_hour_middle", label: "1h par jour au collège", hint: "Au-delà de 4h par semaine, l’excédent passe en bloc de 2h." },
  { key: "enforce_paired_hours", label: "Blocs de 2h au lycée", hint: "Deux heures consécutives sans pause entre elles. L’EPS reste toujours en 1h." },
  { key: "enforce_max_two_hours", label: "Jamais plus de 2h par jour", hint: "Une même matière ne dépasse pas 2h sur une seule journée." },
  { key: "enforce_day_spacing", label: "Espacer les deux premières séances", hint: "Au moins un jour d’écart (lycée 3-4h, collège 2h)." },
];

type PeriodDraft = { id?: number; label: string; kind: "cours" | "pause"; start_time: string; end_time: string };

export default function Timetable() {
  const { schoolId = "" } = useParams();
  const [tab, setTab] = useState<"grid" | "setup">("grid");
  const [timetable, setTimetable] = useState<TimetableData | null>(null);
  const [canManage, setCanManage] = useState(false);
  const [unplaced, setUnplaced] = useState<string[]>([]);
  const [relaxed, setRelaxed] = useState<Array<{ constraint: string; classes: string[] }>>([]);
  const [diagnostic, setDiagnostic] = useState<{ attempts: number; overloaded: Record<string, number> } | null>(null);
  const [classId, setClassId] = useState(0);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  // Paramétrage
  const [subjects, setSubjects] = useState<Array<{ id: number; name: string; code: string }>>([]);
  const [periods, setPeriods] = useState<PeriodDraft[]>([]);
  const [options, setOptions] = useState<TimetableOptions | null>(null);
  const [days, setDays] = useState(5);
  const [closedAfternoons, setClosedAfternoons] = useState<number[]>([]);
  const [maxClassHours, setMaxClassHours] = useState(0);
  const [restrictions, setRestrictions] = useState<SubjectRestriction[]>([]);
  const [classList, setClassList] = useState<Array<{ id: number; name: string; level: string }>>([]);
  const [classTeachers, setClassTeachers] = useState<Record<string, { id: number; name: string }>>({});
  const [excludedClasses, setExcludedClasses] = useState<Array<{ subject: number; classes: number[] }>>([]);
  const [classGroups, setClassGroups] = useState<Array<{ subject: number; classes: number[] }>>([]);
  const [groupSubject, setGroupSubject] = useState(0);
  const [groupClasses, setGroupClasses] = useState<number[]>([]);
  const [excludeSubject, setExcludeSubject] = useState(0);
  const [excludeClasses, setExcludeClasses] = useState<number[]>([]);
  const [pdfClasses, setPdfClasses] = useState<number[]>([]);
  const [pdfTeachers, setPdfTeachers] = useState<number[]>([]);

  const teacherFor = (classId: number, subjectId: number) =>
    classTeachers[`${classId}-${subjectId}`];

  const loadSetup = (data: TimetableData) => {
    setOptions(data.options);
    setDays(data.days_per_week);
    setClosedAfternoons(data.days_without_afternoon ?? []);
    setMaxClassHours(data.max_class_hours ?? 0);
    setPeriods(data.periods.map((period) => ({
      id: period.id, label: period.label, kind: period.kind,
      start_time: shortTime(period.start_time), end_time: shortTime(period.end_time),
    })));
    setRestrictions(data.restrictions);
    setExcludedClasses((data.excluded_classes ?? []).map((exclusion) => ({
      subject: exclusion.subject, classes: exclusion.classes,
    })));
    setClassGroups((data.class_groups ?? []).map((group) => ({
      subject: group.subject, classes: group.classes,
    })));
  };

  useEffect(() => {
    setLoading(true);
    getTimetableSetup(schoolId)
      .then((data) => {
        setSubjects(data.subjects);
        setClassList(data.classes ?? []);
        setClassTeachers(data.class_subject_teachers ?? {});
        setCanManage(data.can_manage);
        loadSetup(data.timetable);
        return getTimetable(schoolId).then((current) => setTimetable(current.timetable));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Chargement impossible."))
      .finally(() => setLoading(false));
  }, [schoolId]);

  const classes = useMemo(() => {
    const rows = new Map<number, string>();
    (timetable?.slots ?? []).forEach((slot) => rows.set(slot.class_id, slot.class_name));
    return [...rows.entries()].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
  }, [timetable]);

  // Enseignants réellement présents dans la grille : eux seuls ont un emploi
  // du temps à éditer.
  const teachers = useMemo(() => {
    const rows = new Map<number, string>();
    (timetable?.slots ?? []).forEach((slot) => {
      if (slot.teacher_id && slot.teacher) rows.set(slot.teacher_id, slot.teacher);
    });
    return [...rows.entries()].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
  }, [timetable]);

  useEffect(() => { if (classes.length && !classes.some((row) => row.id === classId)) setClassId(classes[0].id); }, [classes]);

  const slots = useMemo(
    () => (timetable?.slots ?? []).filter((slot) => slot.class_id === classId),
    [timetable, classId],
  );

  // La grille suit les créneaux paramétrés — pauses comprises — et non les
  // seules heures occupées, sinon les pauses disparaîtraient de l'affichage.
  const times = useMemo(() => {
    const rows = (timetable?.periods ?? []).map((period) => ({
      start: period.start_time,
      end: period.end_time,
      kind: period.kind,
      label: period.label,
    }));
    if (rows.length) return rows.sort((a, b) => a.start.localeCompare(b.start));
    const unique = new Map<string, { start: string; end: string; kind: "cours"; label: string }>();
    slots.forEach((slot) => unique.set(slot.start_time, {
      start: slot.start_time, end: slot.end_time, kind: "cours", label: "",
    }));
    return [...unique.values()].sort((a, b) => a.start.localeCompare(b.start));
  }, [timetable, slots]);

  const cell = (day: number, start: string): TimetableSlot | undefined =>
    slots.find((slot) => slot.day === day && slot.start_time === start);

  // Autres classes que l'enseignant réunit sur ce même créneau.
  const sharedWith = (slot: TimetableSlot): string[] =>
    (timetable?.slots ?? [])
      .filter((other) => other.class_id !== slot.class_id
        && other.day === slot.day
        && other.start_time === slot.start_time
        && other.teacher !== null
        && other.teacher === slot.teacher)
      .map((other) => other.class_name);

  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true); setError(""); setMessage("");
    try { await action(); setMessage(success); }
    catch (e) { setError(e instanceof Error ? e.message : "Opération impossible."); }
    finally { setBusy(false); }
  };

  const saveSetup = () => run(async () => {
    const saved = await saveTimetableSetup(schoolId, {
      ...options, days_per_week: days, days_without_afternoon: closedAfternoons,
      periods: periods.map((period) => ({ ...period })),
      restrictions: restrictions.map(({ subject, period, day }) => ({ subject, period, day })),
      excluded_classes: excludedClasses,
      class_groups: classGroups,
    });
    loadSetup(saved);
  }, "Paramétrage enregistré.");

  const generate = () => run(async () => {
    const saved = await saveTimetableSetup(schoolId, {
      ...options, days_per_week: days, days_without_afternoon: closedAfternoons,
      periods: periods.map((period) => ({ ...period })),
      restrictions: restrictions.map(({ subject, period, day }) => ({ subject, period, day })),
      excluded_classes: excludedClasses,
      class_groups: classGroups,
    });
    loadSetup(saved);
    const data = await generateTimetable(schoolId);
    setTimetable(data.timetable);
    setUnplaced(data.unplaced ?? []);
    setRelaxed(data.relaxed ?? []);
    setDiagnostic({ attempts: data.attempts ?? 1, overloaded: data.overloaded_classes ?? {} });
    setTab("grid");
  }, "Emploi du temps généré.");

  const validate = () => run(async () => {
    setTimetable(await validateTimetable(schoolId));
  }, "Emploi du temps validé. Il ne peut plus être régénéré.");

  const exportPdf = (scope: "classes" | "teachers", ids: number[]) => run(
    () => downloadTimetablePdf(schoolId, scope, ids),
    "PDF téléchargé.",
  );

  const remove = () => {
    const slotCount = timetable?.slots.length ?? 0;
    const confirmation = `Vider l’emploi du temps de cette année pour les ${classes.length} classes `
      + `(${slotCount} créneaux) ?\n\nVotre paramétrage est conservé : créneaux horaires, contraintes, `
      + `interdictions, exclusions et regroupements. Seules les cases générées sont effacées.`;
    if (!window.confirm(confirmation)) return;
    return run(async () => {
      await deleteTimetable(schoolId);
      // Le paramétrage survit à la suppression : on le relit plutôt que de
      // vider l'écran, sinon l'utilisateur croirait l'avoir perdu.
      const setup = await getTimetableSetup(schoolId);
      loadSetup(setup.timetable);
      setTimetable(null); setUnplaced([]); setRelaxed([]);
    }, "Grille vidée. Votre paramétrage est conservé.");
  };

  const updatePeriod = (index: number, patch: Partial<PeriodDraft>) =>
    setPeriods((current) => current.map((period, position) => position === index ? { ...period, ...patch } : period));

  const addPeriod = (kind: "cours" | "pause") => {
    const last = periods[periods.length - 1];
    setPeriods((current) => [...current, {
      label: kind === "pause" ? "Pause" : `${current.length + 1}e heure`,
      kind, start_time: last?.end_time ?? "06:55", end_time: last?.end_time ?? "07:55",
    }]);
  };

  const dayCount = timetable?.days_per_week ?? days;
  const coursePeriods = periods.filter((period) => period.kind === "cours");

  // La pause déjeuner est la plus longue interruption : elle sépare matin et après-midi.
  const capacityWarning = useMemo(() => {
    const minutes = (value: string) => Number(value.slice(0, 2)) * 60 + Number(value.slice(3, 5));
    const breaks = periods.filter((period) => period.kind === "pause");
    if (!breaks.length) return "";
    const lunch = breaks.reduce((longest, period) =>
      minutes(period.end_time) - minutes(period.start_time) > minutes(longest.end_time) - minutes(longest.start_time)
        ? period : longest);
    const lunchStart = minutes(lunch.start_time);
    const morning = coursePeriods.filter((period) => minutes(period.start_time) < lunchStart).length;
    const afternoon = coursePeriods.length - morning;
    const capacity = coursePeriods.length * days - afternoon * closedAfternoons.length;
    return maxClassHours && capacity < maxClassHours
      ? `Attention : ${capacity} h par semaine et par classe seulement, alors que la classe la plus chargée `
        + `demande ${maxClassHours} h. Des heures resteront non placées.`
      : "";
  }, [periods, coursePeriods, days, closedAfternoons, maxClassHours]);

  return <div className="content-inner timetable-page">
    <div className="page-header">
      <h1 className="page-title">Emploi du temps</h1>
      {timetable && <span className={`timetable-badge ${timetable.is_validated ? "is-validated" : "is-draft"}`}>
        {timetable.status_label}
      </span>}
    </div>

    <div className="timetable-tabs">
      <button type="button" className={`timetable-tab${tab === "grid" ? " active" : ""}`} onClick={() => setTab("grid")}>Grille</button>
      <button type="button" className={`timetable-tab${tab === "setup" ? " active" : ""}`} onClick={() => setTab("setup")}>Paramétrage</button>
    </div>

    {error && <div className="form-error">{error}</div>}
    {message && <div className="form-success">{message}</div>}
    {unplaced.length > 0 && <div className="form-error">
      <p>Heures non placées :</p>
      <ul className="timetable-relaxed-list">
        {unplaced.map((row) => <li key={row}>{row}</li>)}
      </ul>
      {diagnostic && diagnostic.attempts > 1 && <p className="timetable-diagnostic">
        {diagnostic.attempts} combinaisons essayées ; celle-ci est la meilleure trouvée.
      </p>}
      {diagnostic && Object.keys(diagnostic.overloaded).length > 0 && <p className="timetable-diagnostic">
        Capacité insuffisante pour {Object.entries(diagnostic.overloaded)
          .map(([group, hours]) => `${group} (${hours} h de trop)`).join(", ")}.
        Rouvrez un après-midi, ajoutez un créneau ou une journée.
      </p>}
    </div>}
    {relaxed.length > 0 && <div className="timetable-warning">
      <p>Contraintes assouplies pour tout placer :</p>
      <ul className="timetable-relaxed-list">
        {relaxed.map((item) => <li key={item.constraint}>
          <strong>{item.constraint}</strong> — {item.classes.length} classe(s) :{" "}
          {item.classes.join(" · ")}
        </li>)}
      </ul>
    </div>}

    {loading ? <p className="parents-empty">Chargement…</p> : tab === "setup" ? <>
      <section className="school-panel">
        <h2>Contraintes pédagogiques</h2>
        <p className="parents-empty">Décochez celles qui ne s’appliquent pas à votre établissement.</p>
        <div className="timetable-options">
          {OPTION_LABELS.map(({ key, label, hint }) => <label key={key} className="timetable-option">
            <input
              type="checkbox"
              checked={options?.[key] ?? false}
              disabled={!canManage || timetable?.is_validated}
              onChange={(event) => setOptions((current) => current && { ...current, [key]: event.target.checked })}
            />
            <span><strong>{label}</strong><small>{hint}</small></span>
          </label>)}
        </div>
        <label className="timetable-days">Jours par semaine
          <input
            className="form-input" type="number" min={1} max={7} value={days}
            disabled={!canManage || timetable?.is_validated}
            onChange={(event) => setDays(Number(event.target.value))}
          />
        </label>

        <h3 className="timetable-subtitle">Après-midi sans cours</h3>
        <p className="parents-empty">
          Cochez les jours où l’établissement ne fait pas cours après la pause déjeuner.
        </p>
        <div className="timetable-options">
          {DAYS.slice(0, days).map((label, index) => <label key={label} className="timetable-option">
            <input
              type="checkbox"
              checked={closedAfternoons.includes(index)}
              disabled={!canManage || timetable?.is_validated}
              onChange={(event) => setClosedAfternoons((current) => event.target.checked
                ? [...current, index].sort((a, b) => a - b)
                : current.filter((day) => day !== index))}
            />
            <span><strong>{label} après-midi fermé</strong></span>
          </label>)}
        </div>
        {capacityWarning && <div className="timetable-warning">{capacityWarning}</div>}
      </section>

      <section className="school-panel">
        <h2>Créneaux horaires</h2>
        <p className="parents-empty">
          Les créneaux de type « pause » ne reçoivent aucun cours et empêchent deux heures voisines de former un bloc de 2h.
        </p>
        <table className="owners-table">
          <thead><tr><th>Libellé</th><th>Type</th><th>Début</th><th>Fin</th><th></th></tr></thead>
          <tbody>{periods.map((period, index) => <tr key={period.id ?? `new-${index}`}>
            <td><input className="form-input" value={period.label} disabled={!canManage || timetable?.is_validated}
              onChange={(event) => updatePeriod(index, { label: event.target.value })} /></td>
            <td><select className="form-select" value={period.kind} disabled={!canManage || timetable?.is_validated}
              onChange={(event) => updatePeriod(index, { kind: event.target.value as "cours" | "pause" })}>
              <option value="cours">Cours</option><option value="pause">Pause</option>
            </select></td>
            <td><input className="form-input" type="time" value={period.start_time} disabled={!canManage || timetable?.is_validated}
              onChange={(event) => updatePeriod(index, { start_time: event.target.value })} /></td>
            <td><input className="form-input" type="time" value={period.end_time} disabled={!canManage || timetable?.is_validated}
              onChange={(event) => updatePeriod(index, { end_time: event.target.value })} /></td>
            <td>{canManage && !timetable?.is_validated && <button type="button" className="owner-archive-btn"
              onClick={() => setPeriods((current) => current.filter((_, position) => position !== index))}>Retirer</button>}</td>
          </tr>)}</tbody>
        </table>
        {canManage && !timetable?.is_validated && <div className="timetable-actions">
          <button type="button" className="school-edit-btn" onClick={() => addPeriod("cours")}>+ Créneau de cours</button>
          <button type="button" className="school-edit-btn" onClick={() => addPeriod("pause")}>+ Pause</button>
        </div>}
      </section>

      <section className="school-panel">
        <h2>Matières exclues de la génération</h2>
        <p className="parents-empty">
          Choisissez une matière puis les classes pour lesquelles elle ne doit pas être programmée.
          Les autres matières de ces classes restent placées normalement.
        </p>

        {excludedClasses.length > 0 && <table className="owners-table">
          <thead><tr><th>Matière</th><th>Classes exclues</th><th></th></tr></thead>
          <tbody>{excludedClasses.map((exclusion, index) => <tr key={index}>
            <td>{subjects.find((item) => item.id === exclusion.subject)?.name ?? "—"}</td>
            <td>{exclusion.classes.map((id) => classList.find((row) => row.id === id)?.name ?? id).join(" · ")}</td>
            <td>{canManage && !timetable?.is_validated && <button
              type="button" className="owner-archive-btn"
              onClick={() => setExcludedClasses((current) => current.filter((_, position) => position !== index))}
            >Retirer</button>}</td>
          </tr>)}</tbody>
        </table>}

        {canManage && !timetable?.is_validated && <div className="timetable-group-builder">
          <label>Matière
            <select
              className="form-select" value={excludeSubject}
              onChange={(event) => { setExcludeSubject(Number(event.target.value)); setExcludeClasses([]); }}
            >
              <option value={0}>Choisir…</option>
              {subjects
                .filter((subject) => !excludedClasses.some((item) => item.subject === subject.id))
                .map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
            </select>
          </label>

          {excludeSubject > 0 && <>
            <p className="parents-empty">
              Classes où cette matière est enseignée :
            </p>
            <div className="timetable-options">
              {classList.filter((row) => teacherFor(row.id, excludeSubject)).map((row) => <label
                key={row.id} className="timetable-option"
              >
                <input
                  type="checkbox" checked={excludeClasses.includes(row.id)}
                  onChange={(event) => setExcludeClasses((current) => event.target.checked
                    ? [...current, row.id]
                    : current.filter((id) => id !== row.id))}
                />
                <span><strong>{row.name}</strong><small>{row.level}</small></span>
              </label>)}
            </div>
            <button
              type="button" className="btn-primary" disabled={excludeClasses.length === 0}
              onClick={() => {
                setExcludedClasses((current) => [...current, { subject: excludeSubject, classes: excludeClasses }]);
                setExcludeClasses([]); setExcludeSubject(0);
              }}
            >Exclure ces {excludeClasses.length || ""} classes</button>
          </>}
        </div>}
      </section>

      <section className="school-panel">
        <h2>Classes réunies pour un même cours</h2>
        <p className="parents-empty">
          Choisissez une matière puis les classes qui la suivent ensemble, au même créneau.
          Seules les classes ayant le <strong>même enseignant</strong> pour cette matière peuvent être réunies.
        </p>

        {classGroups.length > 0 && <table className="owners-table">
          <thead><tr><th>Matière</th><th>Classes réunies</th><th>Enseignant</th><th></th></tr></thead>
          <tbody>{classGroups.map((group, index) => <tr key={index}>
            <td>{subjects.find((item) => item.id === group.subject)?.name ?? "—"}</td>
            <td>{group.classes.map((id) => classList.find((row) => row.id === id)?.name ?? id).join(" · ")}</td>
            <td>{teacherFor(group.classes[0], group.subject)?.name ?? "—"}</td>
            <td>{canManage && !timetable?.is_validated && <button
              type="button" className="owner-archive-btn"
              onClick={() => setClassGroups((current) => current.filter((_, position) => position !== index))}
            >Retirer</button>}</td>
          </tr>)}</tbody>
        </table>}

        {canManage && !timetable?.is_validated && <div className="timetable-group-builder">
          <label>Matière
            <select
              className="form-select" value={groupSubject}
              onChange={(event) => { setGroupSubject(Number(event.target.value)); setGroupClasses([]); }}
            >
              <option value={0}>Choisir…</option>
              {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
            </select>
          </label>

          {groupSubject > 0 && <>
            <p className="parents-empty">
              Classes disponibles, regroupées par enseignant :
            </p>
            <div className="timetable-options">
              {classList.filter((row) => teacherFor(row.id, groupSubject)).map((row) => {
                const teacher = teacherFor(row.id, groupSubject);
                const chosen = groupClasses.includes(row.id);
                // Une fois une classe choisie, seules celles du même enseignant restent cochables.
                const lockedTo = groupClasses.length
                  ? teacherFor(groupClasses[0], groupSubject)?.id
                  : null;
                const blocked = lockedTo !== null && teacher?.id !== lockedTo;
                return <label key={row.id} className={`timetable-option${blocked ? " is-blocked" : ""}`}>
                  <input
                    type="checkbox" checked={chosen} disabled={blocked && !chosen}
                    onChange={(event) => setGroupClasses((current) => event.target.checked
                      ? [...current, row.id]
                      : current.filter((id) => id !== row.id))}
                  />
                  <span><strong>{row.name}</strong><small>{teacher?.name}</small></span>
                </label>;
              })}
            </div>
            <button
              type="button" className="btn-primary" disabled={groupClasses.length < 2}
              onClick={() => {
                setClassGroups((current) => [...current, { subject: groupSubject, classes: groupClasses }]);
                setGroupClasses([]); setGroupSubject(0);
              }}
            >Réunir ces {groupClasses.length || ""} classes</button>
          </>}
        </div>}
      </section>

      <section className="school-panel">
        <h2>Matières interdites sur certains créneaux</h2>
        {restrictions.length === 0
          ? <p className="parents-empty">Aucune interdiction. Toutes les matières peuvent occuper tous les créneaux de cours.</p>
          : <table className="owners-table">
              <thead><tr><th>Matière</th><th>Créneau</th><th>Jour</th><th></th></tr></thead>
              <tbody>{restrictions.map((restriction, index) => <tr key={index}>
                <td>{subjects.find((subject) => subject.id === restriction.subject)?.name ?? "—"}</td>
                <td>{(() => {
                  const period = periods.find((row) => row.id === restriction.period);
                  return period ? `${period.label} (${period.start_time})` : "—";
                })()}</td>
                <td>{restriction.day === null ? "Tous les jours" : DAYS[restriction.day]}</td>
                <td>{canManage && !timetable?.is_validated && <button type="button" className="owner-archive-btn"
                  onClick={() => setRestrictions((current) => current.filter((_, position) => position !== index))}>Retirer</button>}</td>
              </tr>)}</tbody>
            </table>}

        {canManage && !timetable?.is_validated && coursePeriods.length > 0 && <form className="school-form" onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const dayValue = String(form.get("day"));
          setRestrictions((current) => [...current, {
            subject: Number(form.get("subject")),
            period: Number(form.get("period")),
            day: dayValue === "" ? null : Number(dayValue),
          }]);
        }}>
          <label>Matière<select className="form-select" name="subject" required>
            {subjects.map((subject) => <option key={subject.id} value={subject.id}>{subject.name}</option>)}
          </select></label>
          <label>Créneau<select className="form-select" name="period" required>
            {coursePeriods.filter((period) => period.id).map((period) => <option key={period.id} value={period.id}>
              {period.label} ({period.start_time}–{period.end_time})
            </option>)}
          </select></label>
          <label>Jour<select className="form-select" name="day" defaultValue="">
            <option value="">Tous les jours</option>
            {DAYS.slice(0, days).map((day, index) => <option key={day} value={index}>{day}</option>)}
          </select></label>
          <button className="btn-primary" type="submit">Ajouter l’interdiction</button>
        </form>}
      </section>

      {canManage && !timetable?.is_validated && <div className="timetable-actions">
        <button className="school-edit-btn" type="button" onClick={saveSetup} disabled={busy}>Enregistrer le paramétrage</button>
        <button className="btn-primary" type="button" onClick={generate} disabled={busy}>
          {busy ? "Génération en cours…" : "Enregistrer et générer"}
        </button>
      </div>}
      {timetable?.is_validated && <p className="timetable-hint">
        L’emploi du temps est validé : le paramétrage est verrouillé. Supprimez-le pour le modifier.
      </p>}
    </> : !timetable ? <section className="school-panel">
      <h2>Aucun emploi du temps pour cette année</h2>
      <p className="parents-empty">
        Vérifiez d’abord le paramétrage (créneaux horaires, contraintes, interdictions), puis lancez la génération.
      </p>
      {canManage
        ? <div className="timetable-actions">
            <button className="school-edit-btn" type="button" onClick={() => setTab("setup")}>Ouvrir le paramétrage</button>
            <button className="btn-primary" type="button" onClick={generate} disabled={busy}>
              {busy ? "Génération en cours…" : "Générer l’emploi du temps"}
            </button>
          </div>
        : <p className="parents-empty">Seuls le propriétaire, l’administrateur, le censeur ou le proviseur peuvent le générer.</p>}
    </section> : <>
      <div className="timetable-toolbar">
        <label>Classe
          <select className="form-select" value={classId} onChange={(event) => setClassId(Number(event.target.value))}>
            {classes.map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
          </select>
        </label>
        {canManage && <div className="timetable-actions">
          {!timetable.is_validated && <>
            <button className="btn-primary" type="button" onClick={generate} disabled={busy}>Régénérer</button>
            <button className="btn-primary" type="button" onClick={validate} disabled={busy}>Valider</button>
          </>}
          <button className="owner-archive-btn" type="button" onClick={remove} disabled={busy}>
            Vider la grille (paramétrage conservé)
          </button>
        </div>}
      </div>

      {timetable.is_validated && <p className="timetable-hint">
        Cet emploi du temps est validé : il ne peut plus être régénéré. Supprimez-le pour en créer un nouveau.
      </p>}

      <div className="timetable-grid-wrapper">
        <table className="timetable-grid">
          <thead><tr><th>Horaire</th>{DAYS.slice(0, dayCount).map((day) => <th key={day}>{day}</th>)}</tr></thead>
          <tbody>{times.map((time) => time.kind === "pause"
            ? <tr key={time.start} className="timetable-break-row">
                <th className="timetable-time">{shortTime(time.start)}<br />{shortTime(time.end)}</th>
                <td colSpan={dayCount} className="timetable-break-cell">
                  {time.label || "Pause"}
                </td>
              </tr>
            : <tr key={time.start}>
                <th className="timetable-time">{shortTime(time.start)}<br />{shortTime(time.end)}</th>
                {DAYS.slice(0, dayCount).map((day, index) => {
                  const slot = cell(index, time.start);
                  const shared = slot ? sharedWith(slot) : [];
                  return <td key={day}>{slot
                    ? <div className="timetable-slot">
                        <span className="timetable-subject">{slot.subject}</span>
                        <span className="timetable-teacher">{slot.teacher ?? "Non affecté"}</span>
                        {shared.length > 0 && <span className="timetable-shared">
                          avec {shared.join(", ")}
                        </span>}
                      </div>
                    : <span className="timetable-free">—</span>}</td>;
                })}
              </tr>)}</tbody>
        </table>
      </div>

      {canManage && <section className="school-panel">
        <h2>Éditer en PDF</h2>
        <p className="parents-empty">
          Une page par classe ou par enseignant. Sans sélection, tout est édité.
        </p>

        <div className="timetable-export">
          <div className="timetable-export-block">
            <h3 className="timetable-subtitle">Par classe</h3>
            <div className="timetable-options">
              {classes.map((row) => <label key={row.id} className="timetable-option">
                <input
                  type="checkbox" checked={pdfClasses.includes(row.id)}
                  onChange={(event) => setPdfClasses((current) => event.target.checked
                    ? [...current, row.id]
                    : current.filter((id) => id !== row.id))}
                />
                <span><strong>{row.name}</strong></span>
              </label>)}
            </div>
            <div className="timetable-actions">
              <button type="button" className="school-edit-btn"
                onClick={() => setPdfClasses(pdfClasses.length === classes.length ? [] : classes.map((row) => row.id))}>
                {pdfClasses.length === classes.length ? "Tout décocher" : "Tout sélectionner"}
              </button>
              <button type="button" className="btn-primary" disabled={busy}
                onClick={() => exportPdf("classes", pdfClasses)}>
                {pdfClasses.length ? `Éditer ${pdfClasses.length} classe(s)` : "Éditer toutes les classes"}
              </button>
            </div>
          </div>

          <div className="timetable-export-block">
            <h3 className="timetable-subtitle">Par enseignant</h3>
            <div className="timetable-options">
              {teachers.map((row) => <label key={row.id} className="timetable-option">
                <input
                  type="checkbox" checked={pdfTeachers.includes(row.id)}
                  onChange={(event) => setPdfTeachers((current) => event.target.checked
                    ? [...current, row.id]
                    : current.filter((id) => id !== row.id))}
                />
                <span><strong>{row.name}</strong></span>
              </label>)}
            </div>
            <div className="timetable-actions">
              <button type="button" className="school-edit-btn"
                onClick={() => setPdfTeachers(pdfTeachers.length === teachers.length ? [] : teachers.map((row) => row.id))}>
                {pdfTeachers.length === teachers.length ? "Tout décocher" : "Tout sélectionner"}
              </button>
              <button type="button" className="btn-primary" disabled={busy}
                onClick={() => exportPdf("teachers", pdfTeachers)}>
                {pdfTeachers.length ? `Éditer ${pdfTeachers.length} enseignant(s)` : "Éditer tous les enseignants"}
              </button>
            </div>
          </div>
        </div>
      </section>}
    </>}
  </div>;
}
