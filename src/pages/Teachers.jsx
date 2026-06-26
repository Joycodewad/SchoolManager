import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Visibility, Edit, Delete } from "@mui/icons-material";

const TEACHERS = [
  {
    id: 1,
    name: "Kristin Watson",
    subject: "Chemistry",
    class: "JSS 2",
    email: "michelle.rivera@example.com",
    gender: "Female",
    avatar: "KW",
    phone: "123-456-7890",
    address: "123 Main St",
    city: "Anytown",
    state: "Anystate",
    country: "USA",
  },
  {
    id: 2,
    name: "Marvin McKinney",
    subject: "French",
    class: "JSS 3",
    email: "debbie.baker@example.com",
    gender: "Female",
    avatar: "MM",
    phone: "987-654-3210",
    address: "456 Elm St",
    city: "Othertown",
    state: "Otherstate",
    country: "USA",
  },
  {
    id: 3,
    name: "Jane Cooper",
    subject: "Maths",
    class: "JSS 3",
    email: "kenzi.lawson@example.com",
    gender: "Female",
    avatar: "JC",
    phone: "555-123-4567",
    address: "789 Oak St",
    city: "Sometown",
    state: "Somestate",
    country: "USA",
  },
  {
    id: 4,
    name: "Cody Fisher",
    subject: "English",
    class: "SS 3",
    email: "nathan.roberts@example.com",
    gender: "Female",
    avatar: "CF",
    phone: "555-987-6543",
    address: "321 Pine St",
    city: "Anycity",
    state: "Anystate",
    country: "USA",
  },
  {
    id: 5,
    name: "Bessie Cooper",
    subject: "Social studies",
    class: "SS 3",
    email: "felicia.reid@example.com",
    gender: "Male",
    avatar: "BC",
    phone: "555-555-5555",
    address: "654 Cedar St",
    city: "Othercity",
    state: "Otherstate",
    country: "USA",
  },
  {
    id: 6,
    name: "Leslie Alexander",
    subject: "Home economics",
    class: "SS 3",
    email: "tim.jennings@example.com",
    gender: "Male",
    avatar: "LA",
    phone: "555-111-2222",
    address: "987 Spruce St",
    city: "Sometown",
    state: "Somestate",
    country: "USA",
  },
  {
    id: 7,
    name: "Guy Hawkins",
    subject: "Geography",
    class: "JSS 1",
    email: "alma.lawson@example.com",
    gender: "Male",
    avatar: "GH",
    phone: "555-333-4444",
    address: "123 Maple St",
    city: "Anyville",
    state: "Anystate",
    country: "USA",
  },
  {
    id: 8,
    name: "Theresa Webb",
    subject: "Psychology",
    class: "JSS 3",
    email: "debra.holt@example.com",
    gender: "Female",
    avatar: "TW",
    phone: "555-444-3333",
    address: "456 Birch St",
    city: "Otherville",
    state: "Otherstate",
    country: "USA",
  },
  {
    id: 9,
    name: "Jerome Bell",
    subject: "Physic",
    class: "JSS 4",
    email: "deanna.curtis@example.com",
    gender: "Male",
    avatar: "JB",
    phone: "555-666-7777",
    address: "789 Walnut St",
    city: "Someville",
    state: "Somestate",
    country: "USA",
  },
  {
    id: 10,
    name: "Savannah Nguyen",
    subject: "Accounting",
    class: "JSS 4",
    email: "georgia.young@example.com",
    gender: "Female",
    avatar: "SN",
    phone: "555-777-8888",
    address: "321 Chestnut St",
    city: "Anyburg",
    state: "Anystate",
    country: "USA",
  },
  {
    id: 11,
    name: "Wade Warren",
    subject: "C.R.s",
    class: "JSS 5",
    email: "jackson.graham@example.com",
    gender: "Male",
    avatar: "WW",
    phone: "555-888-9999",
    address: "654 Aspen St",
    city: "Otherburg",
    state: "Otherstate",
    country: "USA",
  },
  {
    id: 12,
    name: "Annette Black",
    subject: "Politics",
    class: "JSS 1",
    email: "dolores.chambers@example.com",
    gender: "Female",
    avatar: "AB",
    phone: "555-999-0000",
    address: "987 Poplar St",
    city: "Someburg",
    state: "Somestate",
    country: "USA",
  },
];

const AVATAR_COLORS = [
  "#dbeafe",
  "#fce7f3",
  "#d1fae5",
  "#fef3c7",
  "#ede9fe",
  "#fee2e2",
  "#e0f2fe",
  "#f0fdf4",
];
const TEXT_COLORS = [
  "#1d4ed8",
  "#be185d",
  "#065f46",
  "#92400e",
  "#5b21b6",
  "#991b1b",
  "#0369a1",
  "#14532d",
];

export default function Teachers() {
  const [search, setSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const navigate = useNavigate();
  const itemsPerPage = 5;

  const filtered = TEACHERS.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.email.toLowerCase().includes(search.toLowerCase()),
  );

  const totalPages = Math.ceil(filtered.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedData = filtered.slice(startIndex, startIndex + itemsPerPage);

  return (
    <div className="content-inner">
      {/* Header */}
      <div className="page-header">
        <h1 className="page-title">Enseignants</h1>
        <div className="page-header-actions">
          <button className="btn-export">Exporter en CSV</button>
          <button
            className="btn-primary"
            onClick={() => navigate("/teachers/add")}
          >
            Ajouter des enseignants
          </button>
        </div>
      </div>

      {/* Toolbar */}
      <div className="toolbar">
        <button className="btn-filter">
          Ajouter un filtre
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
          >
            <path d="M6 9l6 6 6-6" />
          </svg>
        </button>
        <div className="search-box">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#9ca3af"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            className="search-input"
            type="text"
            placeholder="Rechercher un enseignant par nom ou courriel"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setCurrentPage(1);
            }}
          />
        </div>
      </div>

      {/* Table */}
      {filtered.length === 0 ? (
        <div className="empty-state">
          <p className="empty-title">Aucun enseignant pour le moment</p>
          <p className="empty-sub">
            Les enseignants apparaîtront ici après leur inscription à votre école.
          </p>
        </div>
      ) : (
        <div className="teachers-table-wrap">
          <table className="teachers-table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Matière</th>
                <th>Classe</th>
                <th>Adresse courriel</th>
                <th>Genre</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((t, i) => {
                const bg = AVATAR_COLORS[i % AVATAR_COLORS.length];
                const color = TEXT_COLORS[i % TEXT_COLORS.length];
                return (
                  <tr key={t.id} className={i % 2 === 1 ? "row-alt" : ""} onClick={() => navigate(`/teachers/${t.id}`)} style={{ cursor: "pointer" }}>
                    <td>
                      <div className="teacher-name-cell">
                        <div
                          className="teacher-avatar"
                          style={{ background: bg, color }}
                        >
                          {t.avatar}
                        </div>
                        {t.name}
                      </div>
                    </td>
                    <td>{t.subject}</td>
                    <td>{t.class}</td>
                    <td>{t.email}</td>
                    <td>{t.gender}</td>
                    <td>
                      <div className="actions-cell">
                        <button
                          className="action-btn view-btn"
                          title="Voir les détails"
                          onClick={() => navigate(`/teachers/${t.id}`)}
                        >
                          <Visibility fontSize="small" />
                        </button>
                        <button
                          className="action-btn edit-btn"
                          title="Modifier l’enseignant"
                        >
                          <Edit fontSize="small" />
                        </button>
                        <button
                          className="action-btn delete-btn"
                          title="Supprimer l’enseignant"
                        >
                          <Delete fontSize="small" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {filtered.length > 0 && totalPages > 1 && (
        <div className="pagination">
          <button
            className="pagination-btn"
            disabled={currentPage === 1}
            onClick={() => setCurrentPage(currentPage - 1)}
          >
            ← Previous
          </button>

          <div className="pagination-pages">
            {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
              <button
                key={page}
                className={`pagination-page ${page === currentPage ? "active" : ""}`}
                onClick={() => setCurrentPage(page)}
              >
                {page}
              </button>
            ))}
          </div>

          <button
            className="pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => setCurrentPage(currentPage + 1)}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
