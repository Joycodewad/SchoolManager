import { useAuth } from "../hooks/AuthContext";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { useState } from "react";

const MENU = [
  {
    path: "/dashboard",
    label: "Tableau de bord",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M3 9.5L12 3l9 6.5V20a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V9.5z"/>
        <path d="M9 21V12h6v9"/>
      </svg>
    ),
  },
  {
    path: "/teachers",
    label: "Personnels",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 3L2 8l10 5 10-5-10-5z"/>
        <path d="M2 8v6c0 3 4.5 5 10 5s10-2 10-5V8"/>
      </svg>
    ),
  },
  {
    path: "/subjects",
    label: "Matières",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5v-16Z" />
        <path d="M4 21.5A2.5 2.5 0 0 1 6.5 19H20M8 7h8M8 11h6" />
      </svg>
    ),
  },
  {
    path: "/academic-years",
    label: "Années académiques",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="4" width="18" height="17" rx="2" /><path d="M8 2v4M16 2v4M3 9h18M8 13h3M13 13h3M8 17h3" />
      </svg>
    ),
  },
  {
    path: "/students",
    label: "Élèves",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="9" cy="7" r="4"/>
        <path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        <path d="M21 21v-2a4 4 0 0 0-3-3.87"/>
      </svg>
    ),
  },
  {
    path: "/enrollments",
    label: "Inscriptions",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M12 3 3 8l9 5 9-5-9-5Z" /><path d="M5 11v5c0 2 3 4 7 4s7-2 7-4v-5M21 9v6" /><path d="M18 3v4M16 5h4" />
      </svg>
    ),
  },
  {
    path: "/attendance",
    label: "Présences",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
        <circle cx="9" cy="7" r="4"/>
        <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
        <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
      </svg>
    ),
  },
  {
    label: "Finance",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="2" y="5" width="20" height="14" rx="2"/>
        <path d="M2 10h20"/>
        <circle cx="12" cy="15" r="1.5" fill="currentColor"/>
      </svg>
    ),
    children: [
      { path: "/finance/fees",     label: "Collecte des frais" },
      { path: "/finance/expenses", label: "Dépenses scolaires" },
    ],
  },
  {
    path: "/notice",
    label: "Annonces",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
        <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
      </svg>
    ),
  },
  {
    path: "/calendar",
    label: "Calendrier",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <rect x="3" y="4" width="18" height="18" rx="2"/>
        <path d="M16 2v4M8 2v4M3 10h18"/>
      </svg>
    ),
  },
  {
    path: "/library",
    label: "Bibliothèque",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
      </svg>
    ),
  },
  {
    path: "/message",
    label: "Message",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
    ),
  },
];

const OTHER = [
  {
    path: "/profile",
    label: "Profil",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="8" r="4"/>
        <path d="M4 20v-1a8 8 0 0 1 16 0v1"/>
      </svg>
    ),
  },
  {
    path: "/settings",
    label: "Paramètres",
    icon: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
        <circle cx="12" cy="12" r="3"/>
        <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
      </svg>
    ),
  },
];

export default function Sidebar() {
  const { logout, user, schools, activeSchool, selectSchool, academicYears, activeAcademicYear, selectAcademicYear } = useAuth();
  const navigate   = useNavigate();
  const location = useLocation();
  const [financeOpen, setFinanceOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const scopedPath = (path: string, schoolId = activeSchool?.id) =>
    schoolId ? `/schools/${schoolId}${path}` : "/schools";

  const handleSchoolChange = (schoolId: number) => {
    selectSchool(schoolId);
    const scopedRoute = location.pathname.match(/^\/schools\/\d+(\/.*)$/);
    navigate(scopedRoute ? `/schools/${schoolId}${scopedRoute[1]}` : scopedPath("/dashboard", schoolId));
  };

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon" aria-hidden="true">
          <svg viewBox="0 0 48 48" role="img">
            <path className="logo-cap" d="M5 18.5 24 9l19 9.5L24 28 5 18.5Z" />
            <path className="logo-book" d="M12 24v10.5c7-1.2 10.2 1.1 12 3.5 1.8-2.4 5-4.7 12-3.5V24l-12 6-12-6Z" />
            <path className="logo-tassel" d="M42 19v10" />
            <circle className="logo-tassel-dot" cx="42" cy="31.5" r="2" />
          </svg>
        </div>
        <span className="sidebar-school-name">
          <strong>EKD</strong>
          <small>SCHOOL MANAGER</small>
        </span>
      </div>

      <div className="sidebar-school-switcher">
        <label htmlFor="sidebar-school">École active</label>
        {schools.length ? <select id="sidebar-school" value={activeSchool?.id ?? ""}
          onChange={(event) => handleSchoolChange(Number(event.target.value))}>
          {schools.map((school) => <option key={school.id} value={school.id}>{school.name} ({school.code})</option>)}
        </select> : <span>Aucune école</span>}
        <label className="academic-year-label" htmlFor="sidebar-academic-year">Année académique</label>
        {academicYears.length ? <select id="sidebar-academic-year" value={activeAcademicYear?.id ?? ""}
          onChange={(event) => selectAcademicYear(Number(event.target.value))}>
          {academicYears.map((year) => <option key={year.id} value={year.id}>{year.name}</option>)}
        </select> : <span>Aucune année configurée</span>}
      </div>

      <div className="sidebar-scroll">
        {/* MENU */}
        <p className="sidebar-section-label">MENU</p>
        <nav className="sidebar-nav">
          {(user?.role === "proprietaire" || user?.is_superuser) && (
            <NavLink to="/schools" className={({ isActive }) => `nav-btn${isActive ? " active" : ""}`}>
              <span className="nav-icon">▦</span><span className="nav-label">Mes écoles</span>
            </NavLink>
          )}
          {MENU.map((item) => {
            if (item.children) {
              return (
                <div key={item.label}>
                  <button
                    className={`nav-btn${financeOpen ? " active" : ""}`}
                    onClick={() => setFinanceOpen(o => !o)}
                  >
                    <span className="nav-icon">{item.icon}</span>
                    <span className="nav-label">{item.label}</span>
                    <svg
                      className={`nav-chevron${financeOpen ? " open" : ""}`}
                      width="14" height="14" viewBox="0 0 24 24"
                      fill="none" stroke="currentColor" strokeWidth="2.5"
                    >
                      <path d="M6 9l6 6 6-6"/>
                    </svg>
                  </button>
                  {financeOpen && (
                    <div className="nav-submenu">
                      {item.children.map(child => (
                        <NavLink
                          key={child.path}
                          to={scopedPath(child.path)}
                          className={({ isActive }) =>
                            `nav-sub-item${isActive ? " active" : ""}`
                          }
                        >
                          {child.label}
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              );
            }
            return (
              <NavLink
                key={item.path}
                to={scopedPath(item.path)}
                end={item.path === "/"}
                className={({ isActive }) =>
                  `nav-btn${isActive ? " active" : ""}`
                }
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </NavLink>
            );
          })}
        </nav>

        {/* OTHER */}
        <p className="sidebar-section-label" style={{ marginTop: 24 }}>AUTRES</p>
        <nav className="sidebar-nav">
          {OTHER.map((item) => (
            <NavLink
              key={item.path}
              to={scopedPath(item.path)}
              className={({ isActive }) =>
                `nav-btn${isActive ? " active" : ""}`
              }
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          ))}

          {/* Log out */}
          <button className="nav-btn nav-logout" onClick={handleLogout}>
            <span className="nav-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
            </span>
            <span className="nav-label">Se déconnecter</span>
          </button>
        </nav>
      </div>
    </aside>
  );
}
