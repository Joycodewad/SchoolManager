import { useState } from "react";
import { useNavigate } from "react-router-dom";

const SUBJECTS = [
  "Mathématiques",
  "Sciences",
  "Anglais",
  "Histoire",
  "Géographie",
  "Art",
  "Musique",
  "Éducation physique",
];
const CLASSES = [
  "Classe 1",
  "Classe 2",
  "Classe 3",
  "Classe 4",
  "Classe 5",
  "Classe 6",
];
const GENDERS = ["Homme", "Femme", "Autre"];

const emptyTeacher = () => ({
  fullName: "",
  email: "",
  password: "",
  phone: "",
  class: "",
  gender: "",
  subject: "",
});

export default function AddTeacher() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("manual"); // "manual" | "csv"
  const [designation, setDesignation] = useState("");
  const [teachers, setTeachers] = useState([emptyTeacher()]);

  const update = (i, field, val) =>
    setTeachers((prev) =>
      prev.map((t, idx) => (idx === i ? { ...t, [field]: val } : t)),
    );

  const addAnother = () => setTeachers((prev) => [...prev, emptyTeacher()]);

  const handleSubmit = () => {
    // logique de soumission ici
    navigate("/teachers");
  };

  return (
    <div className="content-inner">
      {/* Header row */}
      <div className="add-teacher-header">
        <h1 className="page-title">Ajouter des enseignants</h1>
        <div className="add-teacher-designation">
          <label className="form-label">Fonction</label>
          <input
            className="form-input"
            type="text"
            value={designation}
            onChange={(e) => setDesignation(e.target.value)}
          />
        </div>
      </div>

      {/* Tabs */}
      <div className="add-teacher-tabs">
        <button
          className={`tab-btn${tab === "manual" ? " tab-active" : ""}`}
          onClick={() => setTab("manual")}
        >
          Manuellement
        </button>
        <button
          className={`tab-btn${tab === "csv" ? " tab-active" : ""}`}
          onClick={() => setTab("csv")}
        >
          Importer un CSV
        </button>
      </div>

      {tab === "manual" && (
        <div className="teacher-forms">
          {teachers.map((t, i) => (
            <div key={i} className="teacher-form-row">
              {/* Full Name */}
              <div className="form-group full-width">
                <label className="form-label">Nom complet</label>
                <input
                  className="form-input"
                  type="text"
                  value={t.fullName}
                  onChange={(e) => update(i, "fullName", e.target.value)}
                />
              </div>

              {/* Email + Class + Gender */}
              <div className="form-row-3">
                <div className="form-group">
                  <label className="form-label">Adresse courriel</label>
                  <input
                    className="form-input"
                    type="email"
                    value={t.email}
                    onChange={(e) => update(i, "email", e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <select
                    className="form-select"
                    value={t.class}
                    onChange={(e) => update(i, "class", e.target.value)}
                  >
                    <option value="">Classe</option>
                    {CLASSES.map((c) => (
                      <option key={c} value={c}>
                        {c}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="form-group">
                  <select
                    className="form-select"
                    value={t.gender}
                    onChange={(e) => update(i, "gender", e.target.value)}
                  >
                    <option value="">Genre</option>
                    {GENDERS.map((g) => (
                      <option key={g} value={g}>
                        {g}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Password + Phone */}
              <div className="form-row-2">
                <div className="form-group">
                  <label className="form-label">Mot de passe</label>
                  <input
                    className="form-input"
                    type="password"
                    value={t.password}
                    onChange={(e) => update(i, "password", e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Numéro de téléphone</label>
                  <input
                    className="form-input"
                    type="tel"
                    value={t.phone}
                    onChange={(e) => update(i, "phone", e.target.value)}
                  />
                </div>
              </div>

              {/* Subject */}
              <div className="form-group" style={{ maxWidth: 260 }}>
                <select
                  className="form-select"
                  value={t.subject}
                  onChange={(e) => update(i, "subject", e.target.value)}
                >
                  <option value="">Matière</option>
                  {SUBJECTS.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ))}

          {/* Actions */}
          <div className="form-actions">
            <button className="btn-add-another" onClick={addAnother}>
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
            </button>
            <button className="btn-primary" onClick={handleSubmit}>
              Ajouter l’enseignant
            </button>
          </div>
        </div>
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
