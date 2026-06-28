import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createTeacher, getTeacher, listRoles, RoleOption, suggestUsername, TeacherApiError, updateTeacher } from "../api/teachers";
import { listSubjects, Subject } from "../api/subjects";
import { useAuth } from "../hooks/AuthContext";

const GENDERS = [
  { value: "M", label: "Masculin" },
  { value: "F", label: "Féminin" },
];

const emptyTeacher = (schoolIds: number[] = []) => ({
  username: "",
  usernameTouched: false,
  role: "enseignant",
  lastName: "",
  firstNames: "",
  email: "",
  phone: "+228",
  gender: "",
  primarySubject: "",
  secondarySubject: "",
  tertiarySubject: "",
  schoolIds,
});

const formatPhone = (value: string) => {
  let digits = value.replace(/\D/g, "");
  if (digits.startsWith("228")) digits = digits.slice(3);
  return `+228${digits}`;
};

const formatPhoneInput = (value: string) => {
  const digits = value.replace(/\D/g, "");
  const localNumber = digits.startsWith("228")
    ? digits.slice(3)
    : "228".startsWith(digits)
      ? ""
      : digits;
  return `+228${localNumber.slice(0, 8)}`;
};

export default function AddTeacher() {
  const navigate = useNavigate();
  const { schoolId, id } = useParams();
  const editingId = id ? Number(id) : null;
  const { schools, activeSchool } = useAuth();
  const [tab, setTab] = useState("manual"); // "manual" | "csv"
  const [teachers, setTeachers] = useState([
    emptyTeacher(activeSchool ? [activeSchool.id] : []),
  ]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<Record<number, Record<string, string>>>({});
  const [roles, setRoles] = useState<RoleOption[]>([]);
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [subjectsLoading, setSubjectsLoading] = useState(false);

  const update = (i, field, val) =>
    setTeachers((prev) =>
      prev.map((t, idx) => (idx === i ? { ...t, [field]: val } : t)),
    );

  const namesSignature = teachers
    .map((teacher) => `${teacher.lastName}|${teacher.firstNames}|${teacher.usernameTouched}`)
    .join(";");

  useEffect(() => {
    const timer = window.setTimeout(() => {
      teachers.forEach((teacher, index) => {
        if (teacher.usernameTouched || !teacher.lastName.trim() || !teacher.firstNames.trim()) return;
        const expectedLastName = teacher.lastName;
        const expectedFirstNames = teacher.firstNames;
        void suggestUsername(expectedLastName, expectedFirstNames).then((username) => {
          setTeachers((current) => current.map((item, itemIndex) =>
            itemIndex === index && !item.usernameTouched && item.lastName === expectedLastName && item.firstNames === expectedFirstNames
              ? { ...item, username }
              : item,
          ));
        }).catch(() => undefined);
      });
    }, 350);
    return () => window.clearTimeout(timer);
  }, [namesSignature]);

  useEffect(() => {
    void listRoles().then(setRoles).catch((requestError) =>
      setError(requestError instanceof Error ? requestError.message : "Impossible de charger les rôles."),
    );
  }, []);

  useEffect(() => {
    if (!schoolId) {
      setSubjects([]);
      return;
    }
    setSubjectsLoading(true);
    void listSubjects(schoolId)
      .then(setSubjects)
      .catch((requestError) => setError(
        requestError instanceof Error ? requestError.message : "Impossible de charger les matières.",
      ))
      .finally(() => setSubjectsLoading(false));
  }, [schoolId]);

  useEffect(() => {
    if (!editingId) return;
    setIsSubmitting(true);
    void getTeacher(editingId).then((teacher) => {
      setTeachers([{
        username: teacher.username,
        usernameTouched: true,
        role: teacher.role,
        lastName: teacher.last_name,
        firstNames: teacher.first_names,
        email: teacher.email ?? "",
        phone: teacher.phone ?? "+228",
        gender: teacher.gender,
        primarySubject: teacher.primary_subject ? String(teacher.primary_subject) : "",
        secondarySubject: teacher.secondary_subject ? String(teacher.secondary_subject) : "",
        tertiarySubject: teacher.tertiary_subject ? String(teacher.tertiary_subject) : "",
        schoolIds: teacher.assigned_school_ids,
      }]);
    }).catch((requestError) => setError(
      requestError instanceof Error ? requestError.message : "Impossible de charger le personnel.",
    )).finally(() => setIsSubmitting(false));
  }, [editingId]);

  const addAnother = () => setTeachers((prev) => [
    ...prev,
    emptyTeacher(activeSchool ? [activeSchool.id] : []),
  ]);

  const toggleSchool = (teacherIndex: number, schoolId: number) => {
    setTeachers((current) => current.map((teacher, index) => {
      if (index !== teacherIndex) return teacher;
      const schoolIds = teacher.schoolIds.includes(schoolId)
        ? teacher.schoolIds.filter((id) => id !== schoolId)
        : [...teacher.schoolIds, schoolId];
      return { ...teacher, schoolIds };
    }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError("");
    setFieldErrors({});
    setIsSubmitting(true);
    let currentTeacherIndex = 0;

    try {
      const phones = teachers.map((teacher) => formatPhone(teacher.phone));
      const emails = teachers.map((teacher) => teacher.email.trim().toLowerCase()).filter(Boolean);
      if (new Set(phones).size !== phones.length) {
        throw new Error("Le même numéro de téléphone est saisi plusieurs fois.");
      }
      if (new Set(emails).size !== emails.length) {
        throw new Error("La même adresse courriel est saisie plusieurs fois.");
      }
      if (teachers.some((teacher) => teacher.schoolIds.length === 0)) {
        throw new Error("Sélectionnez au moins une école pour chaque enseignant.");
      }

      for (const [index, teacher] of teachers.entries()) {
        currentTeacherIndex = index;
        const payload = {
          username: teacher.username.trim(),
          last_name: teacher.lastName.trim(),
          first_names: teacher.firstNames.trim(),
          email: teacher.email.trim(),
          phone: formatPhone(teacher.phone),
          gender: teacher.gender as "M" | "F",
          primary_subject: teacher.primarySubject ? Number(teacher.primarySubject) : null,
          secondary_subject: teacher.secondarySubject ? Number(teacher.secondarySubject) : null,
          tertiary_subject: teacher.tertiarySubject ? Number(teacher.tertiarySubject) : null,
          school_ids: teacher.schoolIds,
          role: teacher.role,
        };
        if (editingId) await updateTeacher(editingId, payload);
        else await createTeacher(payload);
      }
      navigate(`/schools/${schoolId}/teachers`);
    } catch (submitError) {
      if (submitError instanceof TeacherApiError) {
        setFieldErrors({ [currentTeacherIndex]: submitError.fieldErrors });
      }
      setError(submitError instanceof Error ? submitError.message : "Une erreur est survenue.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="content-inner">
      {/* Header row */}
      <div className="add-teacher-header">
        <h1 className="page-title">{editingId ? "Modifier le personnel" : "Ajouter du personnel"}</h1>
      </div>

      {/* Tabs */}
      {!editingId && <div className="add-teacher-tabs">
        <button
          className={`tab-btn${tab === "manual" ? " tab-active" : ""}`}
          type="button"
          onClick={() => setTab("manual")}
        >
          Manuellement
        </button>
        <button
          className={`tab-btn${tab === "csv" ? " tab-active" : ""}`}
          type="button"
          onClick={() => setTab("csv")}
        >
          Importer un CSV
        </button>
      </div>}

      {tab === "manual" && (
        <form className="teacher-forms" onSubmit={handleSubmit}>
          {error && <div className="form-error" role="alert">{error}</div>}
          {teachers.map((t, i) => (
            <div key={i} className="teacher-form-row">
              
              <div className="form-row-2">
                <div className="form-group">
                  <label className="form-label">Nom *</label>
                  <input
                    className="form-input"
                    type="text"
                    value={t.lastName}
                    onChange={(e) => update(i, "lastName", e.target.value)}
                    required
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Prénoms *</label>
                  <input
                    className="form-input"
                    type="text"
                    value={t.firstNames}
                    onChange={(e) => update(i, "firstNames", e.target.value)}
                    required
                  />
                </div>
              </div>
              <div className="form-group full-width">
                <label className="form-label">Nom d’utilisateur *</label>
                <input className="form-input" type="text" value={t.username}
                  onChange={(e) => setTeachers((current) => current.map((teacher, index) =>
                    index === i ? { ...teacher, username: e.target.value.replace(/\s/g, ""), usernameTouched: true } : teacher,
                  ))} minLength={3} pattern="\S+" title="Aucun espace n’est autorisé" required />
                <span className="form-hint">Généré automatiquement, mais modifiable. Mot de passe initial : identique au nom d’utilisateur.</span>
              </div>
              <div className="form-group full-width">
                <label className="form-label">Rôle *</label>
                <select className="form-select" value={t.role} onChange={(event) => update(i, "role", event.target.value)} required>
                  {roles.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
                </select>
              </div>

              <div className="form-group teacher-schools-group">
                <label className="form-label">Écoles accessibles *</label>
                <div className="teacher-school-options">
                  {schools.map((school) => (
                    <label className="teacher-school-option" key={school.id}>
                      <input type="checkbox" checked={t.schoolIds.includes(school.id)}
                        onChange={() => toggleSchool(i, school.id)} />
                      <span>{school.name} ({school.code})</span>
                    </label>
                  ))}
                </div>
                {schools.length === 0 && <span className="field-error">Aucune école disponible.</span>}
              </div>

              <div className="form-row-2">
                <div className="form-group">
                  <label className="form-label">Adresse courriel (optionnel)</label>
                  <input
                    className="form-input"
                    type="email"
                    value={t.email}
                    onChange={(e) => update(i, "email", e.target.value)}
                    aria-invalid={Boolean(fieldErrors[i]?.email)}
                  />
                  {fieldErrors[i]?.email && <span className="field-error">{fieldErrors[i].email}</span>}
                </div>
                <div className="form-group">
                  <label className="form-label">Numéro de téléphone *</label>
                  <input
                    className="form-input"
                    type="tel"
                    value={t.phone}
                    onChange={(e) => update(i, "phone", formatPhoneInput(e.target.value))}
                    pattern="\+228[0-9]{8}"
                    title="Le numéro doit contenir +228 suivi de 8 chiffres."
                    maxLength={12}
                    aria-invalid={Boolean(fieldErrors[i]?.phone)}
                    required
                  />
                  {fieldErrors[i]?.phone && <span className="field-error">{fieldErrors[i].phone}</span>}
                </div>
              </div>

              <div className="form-row-2">
                <div className="form-group">
                  <label className="form-label">Genre *</label>
                  <select
                    className="form-select"
                    value={t.gender}
                    onChange={(e) => update(i, "gender", e.target.value)}
                    required
                  >
                    <option value="">Choisir le genre</option>
                    {GENDERS.map((g) => (
                      <option key={g.value} value={g.value}>
                        {g.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Matière principale (optionnel)</label>
                  <select className="form-select" value={t.primarySubject} disabled={subjectsLoading} onChange={(e) => update(i, "primarySubject", e.target.value)}>
                    <option value="">{subjectsLoading ? "Chargement…" : "Aucune"}</option>
                    {subjects.map((subject) => <option key={subject.id} value={subject.id}
                      disabled={String(subject.id) === t.secondarySubject || String(subject.id) === t.tertiarySubject}>{subject.name}</option>)}
                  </select>
                </div>
              </div>

              <div className="form-row-2">
                <div className="form-group">
                  <label className="form-label">Matière secondaire (optionnel)</label>
                  <select className="form-select" value={t.secondarySubject} disabled={subjectsLoading} onChange={(e) => update(i, "secondarySubject", e.target.value)}>
                    <option value="">{subjectsLoading ? "Chargement…" : "Aucune"}</option>
                    {subjects.map((subject) => <option key={subject.id} value={subject.id}
                      disabled={String(subject.id) === t.primarySubject || String(subject.id) === t.tertiarySubject}>{subject.name}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Matière tertiaire (optionnel)</label>
                  <select className="form-select" value={t.tertiarySubject} disabled={subjectsLoading} onChange={(e) => update(i, "tertiarySubject", e.target.value)}>
                    <option value="">{subjectsLoading ? "Chargement…" : "Aucune"}</option>
                    {subjects.map((subject) => <option key={subject.id} value={subject.id}
                      disabled={String(subject.id) === t.primarySubject || String(subject.id) === t.secondarySubject}>{subject.name}</option>)}
                  </select>
                </div>
              </div>
            </div>
          ))}

          {/* Actions */}
          <div className="form-actions">
            {!editingId && <button className="btn-add-another" type="button" onClick={addAnother} disabled={isSubmitting}>
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M12 8v8M8 12h8" />
              </svg>
              En ajouter un autre
            </button>}
            <button className="btn-primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Enregistrement…" : editingId ? "Mettre à jour le personnel" : "Enregistrer le personnel"}
            </button>
          </div>
        </form>
      )}

      {tab === "csv" && (
        <div className="csv-drop">
          <svg
            width="40"
            height="40"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#9ca3af"
            strokeWidth="1.5"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <p className="csv-label">Glisse ton fichier CSV ici</p>
          <button className="btn-export">Parcourir</button>
        </div>
      )}
    </div>
  );
}
