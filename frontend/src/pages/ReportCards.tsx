import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getGradeContexts, GradeContext } from "../api/grades";
import {
  CategoryOrderRule, downloadReportCards, generateReportCards, getReportCards, getReportCardSettings,
  getReportCardStatus, ReportCardAppreciation, ReportCards as ReportCardsData,
  ReportCardSettings, ReportCardStatus, ReportCardStudent, ReportCardTemplate,
  ReportCardWatermark, saveReportCardSettings, WatermarkDensity,
} from "../api/reportCards";

/** Aperçus des filigranes, dans l'ordre proposé au paramétrage. */
const WATERMARK_PREVIEWS: Array<{
  value: ReportCardWatermark; label: string; hint: string;
}> = [
  {
    value: "mosaique", label: "Mosaïque",
    hint: "Le texte répété sur toute la page, comme sur un bulletin officiel.",
  },
  {
    value: "diagonale", label: "Diagonale",
    hint: "Un seul bandeau en travers de la page : plus discret, plus moderne.",
  },
  { value: "logo", label: "Logo", hint: "Le logo de l’établissement, très pâle, au centre." },
];

/** Lignes et colonnes de la vignette, par densité : le PDF resserre de même. */
const DENSITY_GRID: Record<WatermarkDensity, { rows: number; columns: number }> = {
  normale: { rows: 9, columns: 3 },
  pleine: { rows: 14, columns: 5 },
  max: { rows: 21, columns: 8 },
};

/**
 * Vignette du fond imprimé : les marques cochées sont superposées, comme
 * elles le seront sur le bulletin. Sans aucune marque, la feuille reste nue.
 */
function WatermarkPreview({ kinds, text, density = "normale" }: {
  kinds: ReportCardWatermark[]; text: string; density?: WatermarkDensity;
}) {
  const grid = DENSITY_GRID[density] ?? DENSITY_GRID.normale;
  const rows = Array.from({ length: grid.rows }, (_, index) => index);
  const columns = Array.from({ length: grid.columns }, (_, index) => index);
  return <div className="wm-preview">
    {kinds.includes("mosaique") && <div className={`wm-tiles wm-tiles-${density}`}>
      {rows.map((row) => <div key={row} className="wm-tile-row">
        {columns.map((column) => <span key={column}>{text}</span>)}
      </div>)}
    </div>}
    {kinds.includes("diagonale") && <span className="wm-band">{text}</span>}
    {kinds.includes("logo") && <span className="wm-logo-mark" />}
    <div className="wm-sheet"><span /><span /><span /><span /></div>
  </div>;
}

/**
 * Aperçus des modèles : une maquette réduite du PDF, remplie de valeurs
 * d'exemple. Elle ne montre que la disposition — le contenu réel dépend des
 * options cochées plus bas et des notes de l'élève.
 */
const TEMPLATE_PREVIEWS: Array<{
  value: ReportCardTemplate; label: string; summary: string; points: string[];
}> = [
  {
    value: "standard",
    label: "Standard",
    summary: "Le modèle actuel : bandeau officiel, encadré d’identité, tableau des matières puis synthèse.",
    points: [
      "En-tête sur deux colonnes avec le logo au centre",
      "Bloc d’identité encadré (nom, naissance, sexe, matricule, classe, effectif)",
      "Synthèse séparée : moyenne, rang et repères de la classe",
    ],
  },
  {
    value: "officiel",
    label: "Officiel (compact)",
    summary: "La maquette administrative : une seule grille de notes et un pied récapitulatif sur trois colonnes.",
    points: [
      "Nom de l’élève et classe sur une même ligne, sans encadré",
      "Grille unique close par une ligne « TOTAUX » (coefficients et note définitive)",
      "Pied de page : trimestres, repères de classe et relevé de vie scolaire",
    ],
  },
];

/** Maquette du modèle standard. */
function StandardPreview() {
  return <div className="template-preview">
    <div className="tp-head">
      <div className="tp-state"><span /><span /><span /><span /></div>
      <div className="tp-logo" />
      <div className="tp-state tp-right"><span /><b /><span /></div>
    </div>
    <div className="tp-identity">
      <div><span /><span /><span /></div>
      <div><span /><span /><span /></div>
    </div>
    <div className="tp-title">BULLETIN DE NOTES</div>
    <table className="tp-table">
      <thead><tr><th>Matières</th><th>Moy.</th><th>Coef</th><th>Professeur</th></tr></thead>
      <tbody>
        <tr className="tp-group"><td colSpan={4}>LITTÉRAIRES</td></tr>
        <tr><td>Français</td><td>13,80</td><td>3</td><td>—</td></tr>
        <tr><td>Anglais</td><td>14,50</td><td>2</td><td>—</td></tr>
        <tr className="tp-group"><td colSpan={4}>SCIENTIFIQUES</td></tr>
        <tr><td>Maths</td><td>11,50</td><td>3</td><td>—</td></tr>
        <tr className="tp-total"><td colSpan={3}>TOTAL DES COEFFICIENTS</td><td>18</td></tr>
      </tbody>
    </table>
    <div className="tp-summary">
      <div><b>Moyenne générale</b><span>12,81</span></div>
      <div><b>Rang</b><span>23</span></div>
      <div><b>Appréciation</b><span>Assez Bien</span></div>
    </div>
    <div className="tp-footer"><div>Décision du conseil</div><div>Le Proviseur</div></div>
  </div>;
}

/** Maquette du modèle officiel, calquée sur le bulletin administratif. */
function OfficialPreview() {
  return <div className="template-preview">
    <div className="tp-head tp-head-official">
      <div className="tp-state"><span /><span /><span /><span /></div>
      <div className="tp-logo" />
      <div className="tp-school">LYCÉE</div>
    </div>
    <div className="tp-title-row">
      <div className="tp-title">BULLETIN DE NOTES<small>TROISIÈME TRIMESTRE</small></div>
      <div className="tp-facts"><span>Effectif : 78</span><span>2025-2026</span><b>Sexe</b><b>Matricule</b></div>
    </div>
    <div className="tp-name"><b>KPITI Akana</b><b>4 ème A</b></div>
    <table className="tp-table tp-table-dense">
      <thead><tr>
        <th>Matière</th><th>INTER</th><th>DEV</th><th>MOY</th><th>Coef</th>
        <th>Déf.</th><th>Rang</th><th>Chargé du cours</th><th>Sign.</th>
      </tr></thead>
      <tbody>
        <tr><td>Français</td><td>16</td><td>13</td><td>13,8</td><td>3</td><td>41,4</td><td>11è</td><td>—</td><td /></tr>
        <tr><td>Anglais</td><td>15</td><td>15</td><td>14,5</td><td>2</td><td>29</td><td>23è</td><td>—</td><td /></tr>
        <tr><td>Maths</td><td>12</td><td>12</td><td>11,5</td><td>3</td><td>34,5</td><td>16è</td><td>—</td><td /></tr>
        <tr className="tp-total"><td colSpan={4}>TOTAUX</td><td>18</td><td>230,50</td><td colSpan={3} /></tr>
      </tbody>
    </table>
    {/* Les lignes de sessions sont celles de la classe : le bulletin n'imprime
        que les sessions déjà éditées, et la moyenne annuelle à la dernière. */}
    <div className="tp-recap">
      <div><span>Moy. 1er Trim.</span><span>Moy. 2ème Trim.</span><span>Moy. 3ème Trim.</span><span>Moy. annuelle</span></div>
      <div><span>Moy. la plus forte</span><span>Moy. la plus faible</span><span>Moy. de la classe</span><span>Appréciation</span></div>
      <div><span>Absence</span><span>Retard</span><span>Punition</span><span>Blâme</span></div>
    </div>
    <div className="tp-decision">Décision et observation du conseil de classe</div>
    <div className="tp-footer"><div>Professeur titulaire</div><div>Le Proviseur</div></div>
  </div>;
}

/**
 * Disposition des matières dans la grille de notes : séparées par type, ou
 * toutes à la suite. Le réglage porte un seul booléen côté serveur, mais le
 * choix se présente en deux options nommées : « regrouper » seul ne disait pas
 * ce que donne la case décochée.
 */
const SUBJECT_LAYOUTS: Array<{
  grouped: boolean; label: string; hint: string; rows: Array<{ group?: string; name?: string }>;
}> = [
  {
    grouped: true,
    label: "Séparées par type",
    hint: "Un bloc par type de matière (littéraires, scientifiques…), avec un sous-total par bloc. L’ordre des blocs se règle plus bas.",
    rows: [
      { group: "LITTÉRAIRES" }, { name: "Français" }, { name: "Anglais" },
      { group: "SCIENTIFIQUES" }, { name: "Maths" }, { name: "SVT" },
    ],
  },
  {
    grouped: false,
    label: "En une seule liste",
    hint: "Toutes les matières à la suite, sans en-tête de type ni sous-total : une grille unique, plus courte.",
    rows: [
      { name: "Français" }, { name: "Anglais" }, { name: "Maths" },
      { name: "SVT" }, { name: "Histoire-Géo" }, { name: "EPS" },
    ],
  },
];

const OPTION_LABELS: Array<{ key: keyof ReportCardSettings; label: string; hint: string }> = [
  { key: "show_score_detail", label: "Détail des notes", hint: "Affiche chaque évaluation (interrogation, devoir…) en plus de la moyenne." },
  { key: "show_rank", label: "Rang de l’élève", hint: "Position dans la classe, à moyenne égale même rang." },
  { key: "show_teacher", label: "Nom du professeur", hint: "Une colonne par matière." },
  { key: "show_appreciation", label: "Appréciations", hint: "Mention littérale selon les seuils définis ci-dessous." },
  { key: "show_class_statistics", label: "Statistiques de classe", hint: "Plus forte, plus faible et moyenne générale de la classe." },
];

/** Champs d'en-tête saisissables : les seules clés textuelles de `school`. */
type SchoolTextField = {
  [K in keyof ReportCardSettings["school"]]:
    ReportCardSettings["school"][K] extends string ? K : never
}[keyof ReportCardSettings["school"]];

type SchoolField = { key: SchoolTextField; label: string; hint?: string };

/** Colonne de gauche du bulletin : les mentions de tutelle, dans l'ordre imprimé. */
const STATE_FIELDS: SchoolField[] = [
  { key: "country", label: "Pays", hint: "ex : République Togolaise" },
  { key: "country_motto", label: "Devise nationale", hint: "ex : Travail — Liberté — Patrie" },
  { key: "ministry", label: "Ministère" },
  { key: "cabinet", label: "Cabinet" },
  { key: "general_secretariat", label: "Secrétariat général" },
  { key: "education_direction", label: "Direction régionale" },
  { key: "direction_city", label: "Ville de la direction", hint: "ex : Plateaux-Est · Atakpamé" },
  { key: "inspection", label: "Inspection" },
];

/** Colonne de droite : l'établissement lui-même. */
const SCHOOL_FIELDS: SchoolField[] = [
  { key: "motto", label: "Devise de l’établissement" },
  { key: "phone", label: "Téléphone" },
  { key: "postal_box", label: "Boîte postale" },
  { key: "city", label: "Ville" },
];

export default function ReportCards() {
  const { schoolId = "" } = useParams();
  const [context, setContext] = useState<GradeContext | null>(null);
  const [tab, setTab] = useState<"cards" | "settings">("cards");
  const [sessionId, setSessionId] = useState(0);
  const [classId, setClassId] = useState(0);
  const [status, setStatus] = useState<ReportCardStatus | null>(null);
  const [data, setData] = useState<ReportCardsData | null>(null);
  const [detail, setDetail] = useState<ReportCardStudent | null>(null);
  const [settings, setSettings] = useState<ReportCardSettings | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    getGradeContexts(schoolId)
      .then((payload) => { setContext(payload); setSessionId(payload.sessions[0]?.id ?? 0); })
      .catch((e) => setError(e instanceof Error ? e.message : "Chargement impossible."));
  }, [schoolId]);

  const session = useMemo(
    () => context?.sessions.find((row) => row.id === sessionId) ?? null,
    [context, sessionId],
  );

  const refreshStatus = useCallback(() => {
    if (!sessionId) { setStatus(null); return; }
    getReportCardStatus(schoolId, sessionId).then(setStatus).catch(() => setStatus(null));
  }, [schoolId, sessionId]);

  useEffect(() => { setClassId(session?.classes[0]?.id ?? 0); setData(null); setDetail(null); }, [sessionId]);
  useEffect(refreshStatus, [refreshStatus]);
  useEffect(() => {
    if (tab !== "settings") return;
    getReportCardSettings(schoolId).then(setSettings)
      .catch((e) => setError(e instanceof Error ? e.message : "Paramétrage indisponible."));
  }, [schoolId, tab]);

  const run = async (action: () => Promise<unknown>, success: string) => {
    setBusy(true); setError(""); setMessage("");
    try { await action(); setMessage(success); }
    catch (e) { setError(e instanceof Error ? e.message : "Opération impossible."); }
    finally { setBusy(false); }
  };

  const generate = (scope: "school" | "class" | "student", target?: number) => run(async () => {
    await generateReportCards(schoolId, sessionId, {
      scope,
      ...(scope === "class" ? { school_class: target } : {}),
      ...(scope === "student" ? { enrollment: target } : {}),
    });
    refreshStatus();
    if (classId) setData(await getReportCards(schoolId, sessionId, classId));
  }, "Bulletins générés.");

  const consult = () => run(async () => {
    setData(await getReportCards(schoolId, sessionId, classId));
  }, "Bulletins chargés.");

  const exportPdf = (scope: "school" | "class" | "student", target?: number) =>
    run(() => downloadReportCards(schoolId, sessionId, scope, target), "PDF téléchargé.");

  const saveSettings = () => run(async () => {
    if (settings) setSettings(await saveReportCardSettings(schoolId, settings));
  }, "Paramétrage enregistré.");

  const patch = (change: Partial<ReportCardSettings>) =>
    setSettings((current) => current && { ...current, ...change });

  /** Coche ou décoche une marque de fond : les filigranes se cumulent. */
  const toggleWatermark = (kind: ReportCardWatermark) =>
    setSettings((current) => current && {
      ...current,
      watermarks: current.watermarks.includes(kind)
        ? current.watermarks.filter((row) => row !== kind)
        : [...current.watermarks, kind],
    });

  const updateRule = (index: number, change: Partial<CategoryOrderRule>) =>
    setSettings((current) => current && {
      ...current,
      category_orders: current.category_orders.map((row, position) =>
        position === index ? { ...row, ...change } : row),
    });

  /**
   * Types de la règle, complétés par ceux qui manquent : un type créé après
   * la règle doit apparaître, sinon il resterait invisible et non ordonnable.
   */
  const orderedCategories = (rule: CategoryOrderRule) => {
    const known = settings?.categories.map((row) => row.name) ?? [];
    const listed = rule.categories.filter((name) => known.includes(name));
    return [...listed, ...known.filter((name) => !listed.includes(name))];
  };

  const moveCategory = (ruleIndex: number, position: number, step: number) => {
    const rule = settings?.category_orders[ruleIndex];
    if (!rule) return;
    const names = orderedCategories(rule);
    const target = position + step;
    if (target < 0 || target >= names.length) return;
    [names[position], names[target]] = [names[target], names[position]];
    updateRule(ruleIndex, { categories: names });
  };

  const updateAppreciation = (index: number, change: Partial<ReportCardAppreciation>) =>
    setSettings((current) => current && {
      ...current,
      appreciations: current.appreciations.map((row, position) =>
        position === index ? { ...row, ...change } : row),
    });

  const generated = status?.generated ?? false;

  /** Texte que le filigrane imprimera, tel que le PDF le compose. */
  const watermarkText = (
    settings?.watermark_source === "code" ? settings.school.code : settings?.school.name ?? ""
  ).toUpperCase();

  return <div className="content-inner reportcards-page">
    <div className="page-header"><h1 className="page-title">Bulletins</h1></div>
    {error && <div className="form-error">{error}</div>}
    {message && <div className="form-success">{message}</div>}

    <div className="grades-tabs">
      <button className={tab === "cards" ? "active" : ""} onClick={() => { setTab("cards"); setError(""); }}>Bulletins</button>
      {status?.can_configure !== false && (
        <button className={tab === "settings" ? "active" : ""} onClick={() => { setTab("settings"); setError(""); }}>Paramétrage</button>
      )}
    </div>

    {tab === "cards" ? <>
      <section className="school-panel">
        <div className="grades-context">
          <label>Session
            <select className="form-select" value={sessionId} onChange={(e) => setSessionId(Number(e.target.value))}>
              {(context?.sessions ?? []).map((row) => (
                <option key={row.id} value={row.id}>{row.label} — {row.name}</option>
              ))}
            </select>
          </label>
          <label>Classe
            <select className="form-select" value={classId} onChange={(e) => setClassId(Number(e.target.value))}>
              {(session?.classes ?? []).map((row) => <option key={row.id} value={row.id}>{row.name}</option>)}
            </select>
          </label>
        </div>

        {generated ? (
          <p className="timetable-hint">
            Les bulletins de cette session sont générés ({status?.total} au total).
            La génération globale est verrouillée ; corrigez une classe ou un élève en cas d’erreur.
          </p>
        ) : (
          <p className="parents-empty">
            Aucun bulletin généré pour cette session. La génération fige les moyennes et le rang.
          </p>
        )}

        <div className="timetable-actions">
          <button className="btn-primary" type="button" disabled={busy || generated || !sessionId}
            onClick={() => generate("school")}>
            Générer tout l’établissement
          </button>
          <button className="school-edit-btn" type="button" disabled={busy || !classId}
            onClick={() => generate("class", classId)}>
            {generated ? "Corriger cette classe" : "Générer cette classe"}
          </button>
          <button className="school-edit-btn" type="button" disabled={busy || !classId} onClick={consult}>
            Consulter la classe
          </button>
        </div>

        {generated && <div className="timetable-actions">
          <button className="school-edit-btn" type="button" disabled={busy}
            onClick={() => exportPdf("school")}>PDF — tout l’établissement</button>
          <button className="school-edit-btn" type="button" disabled={busy || !classId}
            onClick={() => exportPdf("class", classId)}>PDF — cette classe</button>
        </div>}
      </section>

      {data && <section className="school-panel">
        <h2>{data.school_class.name} — {data.students.length} élève(s)</h2>
        <div className="grade-sheet-wrap">
          <table className="owners-table">
            <thead><tr><th>Rang</th><th>Matricule</th><th>Élève</th><th>Moyenne</th><th></th></tr></thead>
            <tbody>{data.students.map((student) => <tr key={student.enrollment_id}>
              <td>{student.rank ?? "—"}</td>
              <td>{student.matricule}</td>
              <td><b>{student.student_name}</b></td>
              <td><strong>{student.general_average ?? "—"}</strong></td>
              <td className="reportcard-row-actions">
                <button type="button" className="school-edit-btn" onClick={() => setDetail(student)}>Détail</button>
                {generated && <>
                  <button type="button" className="school-edit-btn" disabled={busy}
                    onClick={() => exportPdf("student", student.enrollment_id)}>PDF</button>
                  <button type="button" className="owner-archive-btn" disabled={busy}
                    onClick={() => generate("student", student.enrollment_id)}>Corriger</button>
                </>}
              </td>
            </tr>)}</tbody>
          </table>
        </div>
      </section>}

      {detail && <div className="modal-backdrop" onClick={() => setDetail(null)}>
        <div className="modal-card" onClick={(event) => event.stopPropagation()}>
          <h2>{detail.student_name}</h2>
          <p className="parents-empty">
            Moyenne générale {detail.general_average ?? "—"} · rang {detail.rank ?? "—"}
          </p>
          <table className="owners-table">
            <thead><tr><th>Matière</th><th>Coef.</th><th>Moyenne</th></tr></thead>
            <tbody>{detail.subjects.map((row) => <tr key={row.class_subject_id}>
              <td>{row.subject}</td><td>{row.coefficient}</td><td>{row.average ?? "—"}</td>
            </tr>)}</tbody>
          </table>
          <div className="timetable-actions">
            <button type="button" className="school-edit-btn" onClick={() => setDetail(null)}>Fermer</button>
          </div>
        </div>
      </div>}
    </> : settings && <>
      {!settings.is_configured && <p className="reportcard-defaults-note">
        Ce paramétrage n’a jamais été enregistré : les valeurs ci-dessous sont
        celles d’usage. Enregistrez-le une fois pour le figer — ensuite, plus
        rien ne le modifiera en dehors de cet écran.
      </p>}

      <section className="school-panel">
        <h2>Modèle</h2>
        <p className="parents-empty">
          Choisissez la disposition imprimée. L’aperçu est une maquette réduite :
          les colonnes réellement imprimées dépendent des options ci-dessous.
        </p>
        <div className="template-choices">
          {TEMPLATE_PREVIEWS.map(({ value, label, summary, points }) => {
            const active = settings.template === value;
            return <div key={value}
              className={`template-choice${active ? " active" : ""}`}
              role="radio" aria-checked={active} tabIndex={0}
              onClick={() => settings.can_configure && patch({ template: value })}
              onKeyDown={(e) => {
                if (settings.can_configure && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  patch({ template: value });
                }
              }}>
              <div className="template-choice-head">
                <input type="radio" name="report-card-template" checked={active}
                  disabled={!settings.can_configure} readOnly />
                <div>
                  <strong>{label}</strong>
                  <small>{summary}</small>
                </div>
              </div>
              {value === "standard" ? <StandardPreview /> : <OfficialPreview />}
              <ul className="template-choice-points">
                {points.map((point) => <li key={point}>{point}</li>)}
              </ul>
            </div>;
          })}
        </div>
      </section>

      <section className="school-panel">
        <h2>Filigrane</h2>
        <p className="parents-empty">
          Une marque de fond imprimée derrière le bulletin, qui décourage la
          photocopie sans gêner la lecture des notes. Les marques se cumulent :
          cochez-en plusieurs pour les superposer (mosaïque + diagonale + logo).
        </p>
        <div className="watermark-choices">
          {WATERMARK_PREVIEWS.map(({ value, label, hint }) => {
            const active = settings.watermarks.includes(value);
            const disabled = !settings.can_configure || (value === "logo" && !settings.school.logo);
            return <div key={value}
              className={`watermark-choice${active ? " active" : ""}${disabled ? " disabled" : ""}`}
              role="checkbox" aria-checked={active} tabIndex={disabled ? -1 : 0}
              onClick={() => !disabled && toggleWatermark(value)}
              onKeyDown={(e) => {
                if (!disabled && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  toggleWatermark(value);
                }
              }}>
              {/* La vignette ne montre que cette marque-là ; l'aperçu combiné
                  est affiché plus bas, une fois les choix faits. */}
              <WatermarkPreview kinds={[value]} text={watermarkText}
                density={settings.watermark_density} />
              <span className="watermark-choice-name">
                <input type="checkbox" checked={active} disabled={disabled} readOnly />
                <strong>{label}</strong>
              </span>
              <small>
                {value === "logo" && !settings.school.logo
                  ? "Ajoutez un logo à l’établissement pour utiliser ce filigrane."
                  : hint}
              </small>
            </div>;
          })}
        </div>

        {settings.watermarks.includes("mosaique") && (
          <label className="watermark-source">Densité de la mosaïque
            <select className="form-select" value={settings.watermark_density}
              disabled={!settings.can_configure}
              onChange={(e) => patch({
                watermark_density: e.target.value as ReportCardSettings["watermark_density"],
              })}>
              {settings.watermark_densities.map((row) => (
                <option key={row.value} value={row.value}>{row.label}</option>
              ))}
            </select>
            <small>Plus le motif est serré, plus il est pâle : le bulletin reste lisible.</small>
          </label>
        )}

        {settings.watermarks.some((kind) => kind !== "logo") && (
          <label className="watermark-source">Texte du filigrane
            <select className="form-select" value={settings.watermark_source}
              disabled={!settings.can_configure}
              onChange={(e) => patch({
                watermark_source: e.target.value as ReportCardSettings["watermark_source"],
              })}>
              {settings.watermark_sources.map((row) => (
                <option key={row.value} value={row.value}>{row.label}</option>
              ))}
            </select>
            <small>Imprimé : « {watermarkText} »</small>
          </label>
        )}

        <div className="watermark-result">
          <strong>Fond imprimé</strong>
          <WatermarkPreview kinds={settings.watermarks} text={watermarkText}
            density={settings.watermark_density} />
          <small>
            {settings.watermarks.length === 0
              ? "Aucune marque : le bulletin est imprimé sur fond blanc."
              : `Marques superposées : ${settings.watermarks
                  .map((kind) => WATERMARK_PREVIEWS.find((row) => row.value === kind)?.label ?? kind)
                  .join(" + ")}.`}
          </small>
        </div>
      </section>

      <section className="school-panel">
        <h2>Disposition des matières</h2>
        <p className="parents-empty">
          Les matières peuvent être séparées en blocs par type, ou rester
          groupées telles quelles dans une grille unique.
        </p>
        <div className="layout-choices">
          {SUBJECT_LAYOUTS.map(({ grouped, label, hint, rows }) => {
            const active = settings.group_by_category === grouped;
            return <div key={label}
              className={`layout-choice${active ? " active" : ""}${settings.can_configure ? "" : " disabled"}`}
              role="radio" aria-checked={active} tabIndex={settings.can_configure ? 0 : -1}
              onClick={() => settings.can_configure && patch({ group_by_category: grouped })}
              onKeyDown={(e) => {
                if (settings.can_configure && (e.key === "Enter" || e.key === " ")) {
                  e.preventDefault();
                  patch({ group_by_category: grouped });
                }
              }}>
              <div className="layout-choice-head">
                <input type="radio" name="subject-layout" checked={active}
                  disabled={!settings.can_configure} readOnly />
                <strong>{label}</strong>
              </div>
              <table className="tp-table layout-preview">
                <thead><tr><th>Matières</th><th>Moy.</th><th>Coef</th></tr></thead>
                <tbody>
                  {rows.map((row, index) => row.group
                    ? <tr key={index} className="tp-group"><td colSpan={3}>{row.group}</td></tr>
                    : <tr key={index}><td>{row.name}</td><td>—</td><td>—</td></tr>)}
                </tbody>
              </table>
              <small>{hint}</small>
            </div>;
          })}
        </div>
      </section>

      <section className="school-panel">
        <h2>Contenu du bulletin</h2>
        <p className="parents-empty">
          La moyenne générale reste une moyenne pondérée par les coefficients ;
          ces réglages portent sur ce qui est imprimé.
        </p>
        <div className="timetable-options">
          {OPTION_LABELS.map(({ key, label, hint }) => <label key={key} className="timetable-option">
            <input type="checkbox" checked={Boolean(settings[key])}
              disabled={!settings.can_configure}
              onChange={(e) => patch({ [key]: e.target.checked } as Partial<ReportCardSettings>)} />
            <span><strong>{label}</strong><small>{hint}</small></span>
          </label>)}
        </div>
      </section>

      <section className="school-panel">
        <h2>Appréciations</h2>
        <p className="parents-empty">
          La mention retenue est celle du seuil le plus élevé que la moyenne atteint.
        </p>
        <table className="owners-table">
          <thead><tr><th>Libellé</th><th>À partir de</th><th></th></tr></thead>
          <tbody>{settings.appreciations.map((row, index) => <tr key={index}>
            <td><input className="form-input" value={row.label} disabled={!settings.can_configure}
              onChange={(e) => updateAppreciation(index, { label: e.target.value })} /></td>
            <td><input className="form-input" type="number" min="0" max="20" step="0.01"
              value={row.minimum} disabled={!settings.can_configure}
              onChange={(e) => updateAppreciation(index, { minimum: e.target.value })} /></td>
            <td>{settings.can_configure && <button type="button" className="owner-archive-btn"
              onClick={() => patch({ appreciations: settings.appreciations.filter((_, p) => p !== index) })}
            >Retirer</button>}</td>
          </tr>)}</tbody>
        </table>
        {settings.can_configure && <button type="button" className="school-edit-btn"
          onClick={() => patch({ appreciations: [...settings.appreciations, { label: "", minimum: "0" }] })}
        >+ Appréciation</button>}
      </section>

      <section className="school-panel">
        <h2>Ordre des types de matières</h2>
        <p className="parents-empty">
          Fixez la place de chaque bloc sur le bulletin. Une règle peut viser tout l’établissement,
          un cycle, une série ou des classes précises — la plus précise l’emporte.
        </p>

        {settings.category_orders.length === 0
          ? <p className="parents-empty">Aucune règle : les blocs suivent l’ordre alphabétique.</p>
          : settings.category_orders.map((rule, index) => <div key={index} className="category-order-rule">
              <div className="category-order-head">
                <input className="form-input" value={rule.name} placeholder="Nom de la règle"
                  disabled={!settings.can_configure}
                  onChange={(e) => updateRule(index, { name: e.target.value })} />
                <select className="form-select" value={rule.scope} disabled={!settings.can_configure}
                  onChange={(e) => updateRule(index, {
                    scope: e.target.value as CategoryOrderRule["scope"],
                    stage: "", series: "", classes: [],
                  })}>
                  <option value="ecole">Tout l’établissement</option>
                  <option value="cycle">Un cycle</option>
                  <option value="serie">Une série</option>
                  <option value="classes">Des classes choisies</option>
                </select>

                {rule.scope === "cycle" && <select className="form-select" value={rule.stage}
                  disabled={!settings.can_configure}
                  onChange={(e) => updateRule(index, { stage: e.target.value })}>
                  <option value="">Choisir…</option>
                  {settings.stages.map((row) => <option key={row.value} value={row.value}>{row.label}</option>)}
                </select>}

                {rule.scope === "serie" && <select className="form-select" value={rule.series}
                  disabled={!settings.can_configure}
                  onChange={(e) => updateRule(index, { series: e.target.value })}>
                  <option value="">Choisir…</option>
                  {settings.series.map((row) => <option key={row} value={row}>{row}</option>)}
                </select>}

                {settings.can_configure && <button type="button" className="owner-archive-btn"
                  onClick={() => patch({ category_orders: settings.category_orders.filter((_, p) => p !== index) })}
                >Retirer</button>}
              </div>

              {rule.scope === "classes" && <div className="timetable-options category-order-classes">
                {(session?.classes ?? []).map((row) => <label key={row.id} className="timetable-option">
                  <input type="checkbox" checked={rule.classes.includes(row.id)}
                    disabled={!settings.can_configure}
                    onChange={(e) => updateRule(index, {
                      classes: e.target.checked
                        ? [...rule.classes, row.id]
                        : rule.classes.filter((id) => id !== row.id),
                    })} />
                  <span><strong>{row.name}</strong></span>
                </label>)}
              </div>}

              <ol className="category-order-list">
                {orderedCategories(rule).map((name, position) => <li key={name}>
                  <span>{name}</span>
                  {settings.can_configure && <span className="category-order-actions">
                    <button type="button" className="school-edit-btn" disabled={position === 0}
                      onClick={() => moveCategory(index, position, -1)}>↑</button>
                    <button type="button" className="school-edit-btn"
                      disabled={position === orderedCategories(rule).length - 1}
                      onClick={() => moveCategory(index, position, 1)}>↓</button>
                  </span>}
                </li>)}
              </ol>
            </div>)}

        {settings.can_configure && <button type="button" className="school-edit-btn"
          onClick={() => patch({
            category_orders: [...settings.category_orders, {
              name: "", scope: "ecole", stage: "", series: "", classes: [],
              categories: settings.categories.map((row) => row.name),
            }],
          })}
        >+ Règle d’ordre</button>}
      </section>

      <section className="school-panel">
        <h2>En-tête du bulletin</h2>
        <p className="parents-empty">
          Tout l’en-tête est modifiable. Un champ laissé vide n’est pas imprimé :
          la ligne disparaît sans laisser de blanc.
        </p>

        <h3 className="timetable-subtitle">Mentions officielles (colonne de gauche)</h3>
        <div className="school-form">
          {STATE_FIELDS.map(({ key, label, hint }) => <label key={key}>{label}
            <input className="form-input" value={settings.school[key]} placeholder={hint}
              disabled={!settings.can_configure}
              onChange={(e) => patch({ school: { ...settings.school, [key]: e.target.value } })} />
          </label>)}
        </div>

        <h3 className="timetable-subtitle">Établissement (colonne de droite)</h3>
        <div className="school-form">
          {SCHOOL_FIELDS.map(({ key, label, hint }) => <label key={key}>{label}
            <input className="form-input" value={settings.school[key]} placeholder={hint}
              disabled={!settings.can_configure}
              onChange={(e) => patch({ school: { ...settings.school, [key]: e.target.value } })} />
          </label>)}
        </div>
        <label className="timetable-days" style={{ maxWidth: "none" }}>Mention du conseil
          <textarea className="form-input" rows={3} value={settings.council_note}
            disabled={!settings.can_configure}
            onChange={(e) => patch({ council_note: e.target.value })} />
        </label>
      </section>

      {settings.can_configure && <div className="timetable-actions">
        <button className="btn-primary" type="button" disabled={busy} onClick={saveSettings}>
          Enregistrer le paramétrage
        </button>
      </div>}
    </>}
  </div>;
}
