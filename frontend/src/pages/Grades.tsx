import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { getGradeContexts, getGradeScheme, getGradeSheet, GradeContext, GradeSchemePayload, GradeSheet, saveGrades, saveGradeScheme } from "../api/grades";

type Method = GradeSchemePayload["calculation_method"];
type LineDraft = { name: string; weight: number; max_score: number };
type GroupDraft = { name: string; weight: number; lines: LineDraft[] };
const emptyLine = (name = ""): LineDraft => ({ name, weight: 0, max_score: 20 });
const equalPercentage = (index: number, count: number) => {
  const share = Math.floor((100 / count) * 100) / 100;
  return index === count - 1 ? Number((100 - share * (count - 1)).toFixed(2)) : share;
};

export default function Grades() {
  const { schoolId = "" } = useParams();
  const [context, setContext] = useState<GradeContext | null>(null);
  const [tab, setTab] = useState<"entry" | "config">("entry");
  const [sessionId, setSessionId] = useState(0);
  const [classId, setClassId] = useState(0);
  const [subjectId, setSubjectId] = useState(0);
  const [method, setMethod] = useState<Method>("equal");
  const [lines, setLines] = useState<LineDraft[]>([emptyLine("Note de classe"), emptyLine("Devoir"), emptyLine("Composition")]);
  const [groups, setGroups] = useState<GroupDraft[]>([{ name: "Contrôle continu", weight: 40, lines: [{ ...emptyLine("Note de classe"), weight: 50 }, { ...emptyLine("Devoir"), weight: 50 }] }, { name: "Examen", weight: 60, lines: [{ ...emptyLine("Composition"), weight: 100 }] }]);
  const [sheet, setSheet] = useState<GradeSheet | null>(null);
  const [scores, setScores] = useState<Record<number, Record<number, string>>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => { void getGradeContexts(schoolId).then((data) => { setContext(data); setSessionId((data.sessions ?? [])[0]?.id ?? 0); }).catch((e) => setError(e instanceof Error ? e.message : "Chargement impossible.")); }, [schoolId]);
  const selectedSession = (context?.sessions ?? []).find((row) => row.id === sessionId) ?? null;
  const selectedClass = (selectedSession?.classes ?? []).find((row) => row.id === classId) ?? selectedSession?.classes?.[0] ?? null;
  const selectedSubject = (selectedClass?.subjects ?? []).find((row) => row.id === subjectId) ?? selectedClass?.subjects?.[0] ?? null;
  useEffect(() => { setClassId(selectedSession?.classes[0]?.id ?? 0); }, [sessionId]);
  useEffect(() => { setSubjectId(selectedClass?.subjects[0]?.id ?? 0); }, [selectedClass?.id]);
  useEffect(() => {
    if (!sessionId || tab !== "config") return;
    void getGradeScheme(schoolId, sessionId).then((scheme) => {
      if (!scheme) {
        setMethod("equal");
        setLines([emptyLine("Note de classe"), emptyLine("Devoir"), emptyLine("Composition")]);
        setGroups([{ name: "Contrôle continu", weight: 40, lines: [{ ...emptyLine("Note de classe"), weight: 50 }, { ...emptyLine("Devoir"), weight: 50 }] }, { name: "Examen", weight: 60, lines: [{ ...emptyLine("Composition"), weight: 100 }] }]);
        return;
      }
      setMethod(scheme.calculation_method);
      if (scheme.calculation_method === "groups") {
        const savedGroups = scheme.groups ?? [];
        setGroups(savedGroups.length ? savedGroups.map((group, groupIndex) => ({ name: group.name, weight: Number(group.weight ?? equalPercentage(groupIndex, savedGroups.length)), lines: (group.lines ?? []).map((line, lineIndex, groupLines) => ({ name: line.name, weight: Number(line.weight ?? equalPercentage(lineIndex, groupLines.length)), max_score: Number(line.max_score) })) })) : [{ name: "Groupe 1", weight: 50, lines: [{ ...emptyLine(), weight: 100 }] }, { name: "Groupe 2", weight: 50, lines: [{ ...emptyLine(), weight: 100 }] }]);
      } else {
        const savedLines = scheme.lines ?? [];
        setLines(savedLines.length ? savedLines.map((line) => ({ name: line.name, weight: Number(line.weight ?? 0), max_score: Number(line.max_score) })) : [emptyLine()]);
      }
    }).catch((e) => setError(e instanceof Error ? e.message : "Configuration introuvable."));
  }, [schoolId, sessionId, tab]);
  useEffect(() => {
    if (!sessionId || !selectedSubject || tab !== "entry") { setSheet(null); return; }
    void getGradeSheet(schoolId, sessionId, selectedSubject.id).then((data) => {
      setSheet(data); setScores(Object.fromEntries((data.students ?? []).map((student) => [student.enrollment, Object.fromEntries(Object.entries(student.scores ?? {}).map(([line, score]) => [Number(line), String(score)]))])));
    }).catch((e) => { setSheet(null); setError(e instanceof Error ? e.message : "Feuille de notes indisponible."); });
  }, [schoolId, sessionId, selectedSubject?.id, tab]);

  const saveConfiguration = async (event: FormEvent) => {
    event.preventDefault(); setError(""); setMessage("");
    try {
      const payload: GradeSchemePayload = { calculation_method: method,
        lines: method === "groups" ? [] : lines.map((line, index) => ({ ...line, weight: method === "weighted" ? Number(line.weight) : null, order: index + 1 })),
        groups: method === "groups" ? groups.map((group, groupIndex) => ({ name: group.name, weight: Number(group.weight), order: groupIndex + 1, lines: group.lines.map((line, index) => ({ name: line.name, weight: Number(line.weight), max_score: Number(line.max_score), order: index + 1 })) })) : [] };
      await saveGradeScheme(schoolId, sessionId, payload); setMessage("Configuration des notes enregistrée.");
    } catch (e) { setError(e instanceof Error ? e.message : "Enregistrement impossible."); }
  };
  const submitGrades = async () => {
    if (!sheet || !selectedSubject) return; setError("");
    const grades = Object.entries(scores).flatMap(([enrollment, row]) => Object.entries(row).filter(([, score]) => score !== "").map(([line, score]) => ({ enrollment: Number(enrollment), line: Number(line), score: Number(score) })));
    try { const updated = await saveGrades(schoolId, sessionId, selectedSubject.id, grades); setSheet(updated); setMessage("Notes enregistrées."); }
    catch (e) { setError(e instanceof Error ? e.message : "Enregistrement impossible."); }
  };
  const totalWeight = lines.reduce((sum, line) => sum + Number(line.weight), 0);

  return <div className="content-inner grades-page"><div className="page-header"><div><h1 className="page-title">Notes</h1><p>Configuration des évaluations et saisie des notes.</p></div></div>{error && <div className="form-error">{error}</div>}{message && <div className="form-success">{message}</div>}<div className="grades-tabs"><button className={tab === "entry" ? "active" : ""} onClick={() => { setTab("entry"); setError(""); }}>Saisie des notes</button>{context?.can_configure && <button className={tab === "config" ? "active" : ""} onClick={() => { setTab("config"); setError(""); }}>Configuration</button>}</div><div className="grades-context"><label>Session<select className="form-select" value={sessionId} onChange={(e) => setSessionId(Number(e.target.value))}>{(context?.sessions ?? []).map((row) => <option value={row.id} key={row.id}>{row.label} — {row.name}</option>)}</select></label>{tab === "entry" && <><label>Classe<select className="form-select" value={selectedClass?.id ?? ""} onChange={(e) => setClassId(Number(e.target.value))}>{(selectedSession?.classes ?? []).map((row) => <option value={row.id} key={row.id}>{row.name}</option>)}</select></label><label>Matière<select className="form-select" value={selectedSubject?.id ?? ""} onChange={(e) => setSubjectId(Number(e.target.value))}>{(selectedClass?.subjects ?? []).map((row) => <option value={row.id} key={row.id}>{row.name}</option>)}</select></label></>}</div>
    {tab === "config" && <form className="grade-config-card" onSubmit={saveConfiguration}><h2>Lignes de notes</h2><label>Mode de calcul<select className="form-select" value={method} onChange={(e) => setMethod(e.target.value as Method)}><option value="equal">Même poids pour chaque ligne</option><option value="weighted">Pourcentage par ligne</option><option value="groups">Moyenne pondérée des groupes</option></select></label>{method !== "groups" ? <div className="grade-lines">{lines.map((line, index) => <div key={index}><input className="form-input" value={line.name} onChange={(e) => setLines(lines.map((row, i) => i === index ? { ...row, name: e.target.value } : row))} placeholder="Nom de la ligne" required /><input className="form-input" type="number" min="1" value={line.max_score} onChange={(e) => setLines(lines.map((row, i) => i === index ? { ...row, max_score: Number(e.target.value) } : row))} title="Note maximale" required />{method === "weighted" && <input className="form-input" type="number" min="0.01" max="100" step="0.01" value={line.weight} onChange={(e) => setLines(lines.map((row, i) => i === index ? { ...row, weight: Number(e.target.value) } : row))} title="Pourcentage" required />}<button type="button" onClick={() => setLines(lines.filter((_, i) => i !== index))}>×</button></div>)}<button type="button" onClick={() => setLines([...lines, emptyLine()])}>+ Ligne de note</button>{method === "weighted" && <p className={totalWeight === 100 ? "valid" : "invalid"}>Total : {totalWeight} %</p>}</div> : <div className="grade-groups">{groups.map((group, groupIndex) => { const lineTotal = group.lines.reduce((sum, line) => sum + Number(line.weight), 0); return <section key={groupIndex}><div><input className="form-input" value={group.name} onChange={(e) => setGroups(groups.map((row, i) => i === groupIndex ? { ...row, name: e.target.value } : row))} placeholder="Nom du groupe" required /><input className="form-input" type="number" min="0.01" max="100" step="0.01" value={group.weight} onChange={(e) => setGroups(groups.map((row, i) => i === groupIndex ? { ...row, weight: Number(e.target.value) } : row))} title="Pourcentage du groupe" required /><span>% de la moyenne générale</span><button type="button" onClick={() => setGroups(groups.filter((_, i) => i !== groupIndex))}>Supprimer le groupe</button></div>{group.lines.map((line, lineIndex) => <div className="group-line" key={lineIndex}><input className="form-input" value={line.name} onChange={(e) => setGroups(groups.map((row, i) => i === groupIndex ? { ...row, lines: row.lines.map((item, j) => j === lineIndex ? { ...item, name: e.target.value } : item) } : row))} placeholder="Ligne de note" required /><input className="form-input" type="number" min="1" value={line.max_score} onChange={(e) => setGroups(groups.map((row, i) => i === groupIndex ? { ...row, lines: row.lines.map((item, j) => j === lineIndex ? { ...item, max_score: Number(e.target.value) } : item) } : row))} title="Note maximale" required /><input className="form-input" type="number" min="0.01" max="100" step="0.01" value={line.weight} onChange={(e) => setGroups(groups.map((row, i) => i === groupIndex ? { ...row, lines: row.lines.map((item, j) => j === lineIndex ? { ...item, weight: Number(e.target.value) } : item) } : row))} title="Pourcentage dans le groupe" required /><span>% du groupe</span><button type="button" onClick={() => setGroups(groups.map((row, i) => i === groupIndex ? { ...row, lines: row.lines.filter((_, j) => j !== lineIndex) } : row))}>×</button></div>)}<p className={lineTotal === 100 ? "valid" : "invalid"}>Total des notes du groupe : {lineTotal} %</p><button type="button" onClick={() => setGroups(groups.map((row, i) => i === groupIndex ? { ...row, lines: [...row.lines, emptyLine()] } : row))}>+ Ligne dans ce groupe</button></section>})}<p className={groups.reduce((sum, group) => sum + Number(group.weight), 0) === 100 ? "valid" : "invalid"}>Total des groupes : {groups.reduce((sum, group) => sum + Number(group.weight), 0)} %</p><button type="button" onClick={() => setGroups([...groups, { name: `Groupe ${groups.length + 1}`, weight: 0, lines: [{ ...emptyLine(), weight: 100 }] }])}>+ Groupe</button></div>}<button className="btn-primary" disabled={!sessionId}>Enregistrer la configuration</button></form>}
    {tab === "entry" && sheet && <div className="grade-sheet-card"><div className="grade-sheet-head"><h2>{selectedClass?.name} — {sheet.class_subject.subject}</h2><button className="btn-primary" onClick={() => void submitGrades()}>Enregistrer les notes</button></div><div className="grade-sheet-wrap"><table><thead><tr><th>Matricule</th><th>Élève</th>{(sheet.scheme.lines ?? []).map((line) => <th key={line.id}>{line.name}<small>/{line.max_score}</small></th>)}<th>Moyenne /20</th></tr></thead><tbody>{(sheet.students ?? []).map((student) => <tr key={student.enrollment}><td>{student.matricule}</td><td><b>{student.student_name}</b></td>{(sheet.scheme.lines ?? []).map((line) => <td key={line.id}><input type="number" min="0" max={line.max_score} step="0.01" value={scores[student.enrollment]?.[line.id] ?? ""} onChange={(e) => setScores((current) => ({ ...current, [student.enrollment]: { ...current[student.enrollment], [line.id]: e.target.value } }))} /></td>)}<td><strong>{student.average ?? "—"}</strong></td></tr>)}</tbody></table></div></div>}{tab === "entry" && !sheet && <div className="empty-state"><p className="empty-title">Sélectionnez une session, une classe et une matière configurées.</p></div>}</div>;
}
