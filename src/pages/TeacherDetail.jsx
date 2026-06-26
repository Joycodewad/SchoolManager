import { useParams, useNavigate } from "react-router-dom";

const TEACHERS = [
  { id: 1,  name: "Kristin Watson",   subject: "Chemistry",       class: "JSS 2", email: "michelle.rivera@example.com",  gender: "Female", age: 34, designation: "Geology teacher",     avatar: "KW", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum. Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 2,  name: "Marvin McKinney",  subject: "French",          class: "JSS 3", email: "debbie.baker@example.com",     gender: "Female", age: 28, designation: "French teacher",       avatar: "MM", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 3,  name: "Jane Cooper",      subject: "Maths",           class: "JSS 3", email: "kenzi.lawson@example.com",     gender: "Female", age: 31, designation: "Mathematics teacher",  avatar: "JC", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 4,  name: "Cody Fisher",      subject: "English",         class: "SS 3",  email: "nathan.roberts@example.com",   gender: "Female", age: 26, designation: "English teacher",      avatar: "CF", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 5,  name: "Bessie Cooper",    subject: "Social studies",  class: "SS 3",  email: "felicia.reid@example.com",     gender: "Male",   age: 39, designation: "Social studies teacher",avatar: "BC", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 6,  name: "Leslie Alexander", subject: "Home economics",  class: "SS 3",  email: "tim.jennings@example.com",     gender: "Male",   age: 44, designation: "Home economics teacher",avatar: "LA", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 7,  name: "Guy Hawkins",      subject: "Geography",       class: "JSS 1", email: "alma.lawson@example.com",      gender: "Male",   age: 37, designation: "Geography teacher",    avatar: "GH", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 8,  name: "Theresa Webb",     subject: "Psychology",      class: "JSS 3", email: "debra.holt@example.com",       gender: "Female", age: 29, designation: "Psychology teacher",   avatar: "TW", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 9,  name: "Jerome Bell",      subject: "Physic",          class: "JSS 4", email: "deanna.curtis@example.com",    gender: "Male",   age: 33, designation: "Physics teacher",      avatar: "JB", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 10, name: "Savannah Nguyen",  subject: "Accounting",      class: "JSS 4", email: "georgia.young@example.com",    gender: "Female", age: 41, designation: "Accounting teacher",   avatar: "SN", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 11, name: "Wade Warren",      subject: "C.R.s",           class: "JSS 5", email: "jackson.graham@example.com",   gender: "Male",   age: 35, designation: "C.R.s teacher",        avatar: "WW", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
  { id: 12, name: "Annette Black",    subject: "Politics",        class: "JSS 1", email: "dolores.chambers@example.com", gender: "Female", age: 45, designation: "Politics teacher",     avatar: "AB", about: "Nulla Lorem mollit cupidatat irure. Laborum magna nulla duis ullamco cillum dolor. Voluptate exercitation incididunt aliquip deserunt reprehenderit elit laborum." },
];

const AVATAR_COLORS = ["#dbeafe","#fce7f3","#d1fae5","#fef3c7","#ede9fe","#fee2e2","#e0f2fe","#f0fdf4"];
const TEXT_COLORS   = ["#1d4ed8","#be185d","#065f46","#92400e","#5b21b6","#991b1b","#0369a1","#14532d"];

export default function TeacherDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const teacher = TEACHERS.find(t => t.id === Number(id));

  // Collègues de la même classe
  const sameClass = TEACHERS.filter(t => t.class === teacher?.class && t.id !== teacher?.id);

  if (!teacher) return (
    <div className="content-inner">
      <p>Enseignant introuvable.</p>
      <button className="btn-primary" onClick={() => navigate("/teachers")}>Retour</button>
    </div>
  );

  const idx   = TEACHERS.findIndex(t => t.id === teacher.id);
  const bg    = AVATAR_COLORS[idx % AVATAR_COLORS.length];
  const color = TEXT_COLORS[idx % TEXT_COLORS.length];

  return (
    <div className="content-inner">

      {/* Back + toolbar */}
      <div className="page-header">
        <button className="btn-back" onClick={() => navigate("/teachers")}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M19 12H5M12 5l-7 7 7 7" />
          </svg>
          Enseignants
        </button>
        <div className="page-header-actions">
          <button className="btn-export">Exporter en CSV</button>
          <button className="btn-primary" onClick={() => navigate("/teachers/add")}>Ajouter des enseignants</button>
        </div>
      </div>

      {/* Detail card */}
      <div className="detail-card">

        {/* Left — profile */}
        <div className="detail-left">
          <div className="detail-avatar-wrap">
            <div className="detail-avatar" style={{ background: bg, color }}>
              {teacher.avatar}
            </div>
          </div>
          <h2 className="detail-name">{teacher.name}</h2>
          <p className="detail-designation">{teacher.designation}</p>

          <div className="detail-actions">
            <button className="detail-icon-btn" title="Cours">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#374151" strokeWidth="1.8">
                <path d="M12 3L2 8l10 5 10-5-10-5z" />
                <path d="M2 8v6c0 3 4.5 5 10 5s10-2 10-5V8" />
              </svg>
            </button>
            <button className="detail-icon-btn" title="Appeler">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#374151" strokeWidth="1.8">
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.37 2 2 0 0 1 3.6 1.18h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.75a16 16 0 0 0 5.34 5.34l.95-.95a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21 16.92z" />
              </svg>
            </button>
            <button className="detail-icon-btn" title="Courriel">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#374151" strokeWidth="1.8">
                <rect x="2" y="4" width="20" height="16" rx="2" />
                <path d="M2 7l10 7 10-7" />
              </svg>
            </button>
          </div>
        </div>

        {/* Right — info */}
        <div className="detail-right">
          <h3 className="detail-section-title">À propos</h3>
          <p className="detail-about">{teacher.about}</p>

          <div className="detail-meta">
            <div>
              <p className="detail-meta-label">Âge</p>
              <p className="detail-meta-value">{teacher.age}</p>
            </div>
            <div>
              <p className="detail-meta-label">Genre</p>
              <p className="detail-meta-value">{teacher.gender}</p>
            </div>
          </div>

          <div className="detail-same-class">
            <p className="detail-section-title">Enseignants de la même classe</p>
            <div className="same-class-avatars">
              {sameClass.slice(0, 4).map((t, i) => {
                const ti  = TEACHERS.findIndex(x => x.id === t.id);
                const tbg = AVATAR_COLORS[ti % AVATAR_COLORS.length];
                const tc  = TEXT_COLORS[ti % TEXT_COLORS.length];
                return (
                  <div
                    key={t.id}
                    className="same-class-avatar"
                    style={{ background: tbg, color: tc, marginLeft: i === 0 ? 0 : -10, zIndex: 4 - i }}
                    title={t.name}
                  >
                    {t.avatar}
                  </div>
                );
              })}
              {sameClass.length > 4 && (
                <span className="same-class-more">+{sameClass.length - 4} autres</span>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
