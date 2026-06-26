import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Visibility, Edit, Delete } from "@mui/icons-material";

const ALL_STUDENTS = [
  {
    id: "2016-01-001",
    name: "Sarah Miller",
    email: "smiller@eduprohigh.edu",
    class: "10A",
    dob: "04/18/2008",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "101 High St, Springfield, IL",
  },
  {
    id: "2014-02-002",
    name: "Ethan Brown",
    email: "ebrown@eduprohigh.edu",
    class: "12",
    dob: "07/22/2006",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "202 Lake Ave, Springfield, IL",
  },
  {
    id: "2017-03-003",
    name: "Olivia",
    email: "osmith@eduprohigh.edu",
    class: "9B",
    dob: "09/29/2010",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "303 River Rd, Springfield, IL",
  },
  {
    id: "2015-01-004",
    name: "Lucas Johnson",
    email: "ljohnson@eduprohigh.edu",
    class: "11A",
    dob: "11/03/2009",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "404 Pine Dr, Springfield, IL",
  },
  {
    id: "2018-02-005",
    name: "Mia Williams",
    email: "mwilliams@eduprohigh.edu",
    class: "8B",
    dob: "01/19/2007",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "505 Maple Ln, Springfield, IL",
  },
  {
    id: "2015-03-006",
    name: "Noah Davis",
    email: "ndavis@eduprohigh.edu",
    class: "9C",
    dob: "05/05/2010",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "606 Birch Blvd, Springfield, IL",
  },
  {
    id: "2019-01-007",
    name: "Emma Wilson",
    email: "ewilson@eduprohigh.edu",
    class: "7C",
    dob: "02/20/2007",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "707 Cedar Ct, Springfield, IL",
  },
  {
    id: "2017-02-008",
    name: "Liam Thompson",
    email: "lthomps@eduprohigh.edu",
    class: "10B",
    dob: "08/28/2011",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "808 Walnut St, Springfield, IL",
  },
  {
    id: "2016-03-009",
    name: "Ava Garcia",
    email: "agarcia@eduprohigh.edu",
    class: "11A",
    dob: "03/15/2009",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "909 Spruce St, Springfield, IL",
  },
  {
    id: "2018-01-010",
    name: "James Martinez",
    email: "jmartinez@eduprohigh.edu",
    class: "7B",
    dob: "12/12/2008",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "1010 Fir St, Springfield, IL",
  },
  {
    id: "2016-02-011",
    name: "Isabella Lee",
    email: "ilee@eduprohigh.edu",
    class: "10A",
    dob: "06/01/2008",
    phone: "(555) 101-0101",
    gender: "   Female",
    address: "1111 Elm Ave, Springfield, IL",
  },
  {
    id: "2015-01-012",
    name: "Mason Clark",
    email: "mclark@eduprohigh.edu",
    class: "11B",
    dob: "09/14/2007",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "1212 Oak St, Springfield, IL",
  },
  {
    id: "2017-03-013",
    name: "Sophia White",
    email: "swhite@eduprohigh.edu",
    class: "9A",
    dob: "02/28/2010",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "1313 Willow Dr, Springfield, IL",
  },
  {
    id: "2019-02-014",
    name: "Oliver Harris",
    email: "oharris@eduprohigh.edu",
    class: "8C",
    dob: "11/11/2009",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "1414 Ash Blvd, Springfield, IL",
  },
  {
    id: "2014-01-015",
    name: "Charlotte Young",
    email: "cyoung@eduprohigh.edu",
    class: "12",
    dob: "04/04/2006",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "1515 Maple Ct, Springfield, IL",
  },
  {
    id: "2016-03-016",
    name: "Elijah King",
    email: "eking@eduprohigh.edu",
    class: "10C",
    dob: "07/07/2008",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "1616 Cedar Ln, Springfield, IL",
  },
  {
    id: "2018-02-017",
    name: "Amelia Scott",
    email: "ascott@eduprohigh.edu",
    class: "8A",
    dob: "03/22/2007",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "1717 Pine Ave, Springfield, IL",
  },
  {
    id: "2015-03-018",
    name: "Benjamin Adams",
    email: "badams@eduprohigh.edu",
    class: "11C",
    dob: "10/10/2009",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "1818 Birch Rd, Springfield, IL",
  },
  {
    id: "2017-01-019",
    name: "Harper Nelson",
    email: "hnelson@eduprohigh.edu",
    class: "9B",
    dob: "01/01/2010",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "1919 Elm Dr, Springfield, IL",
  },
  {
    id: "2019-03-020",
    name: "Henry Carter",
    email: "hcarter@eduprohigh.edu",
    class: "7A",
    dob: "08/08/2011",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "2020 Oak Ave, Springfield, IL",
  },
  {
    id: "2016-01-021",
    name: "Evelyn Mitchell",
    email: "emitchell@eduprohigh.edu",
    class: "10B",
    dob: "05/05/2008",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "2121 Walnut Blvd, Springfield, IL",
  },
  {
    id: "2014-02-022",
    name: "Alexander Perez",
    email: "aperez@eduprohigh.edu",
    class: "12",
    dob: "06/06/2006",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "2222 Spruce St, Springfield, IL",
  },
  {
    id: "2018-03-023",
    name: "Scarlett Roberts",
    email: "sroberts@eduprohigh.edu",
    class: "8B",
    dob: "02/02/2007",
    phone: "(555) 101-0101",
    gender: "Female",
    address: "2323 Fir Ct, Springfield, IL",
  },
  {
    id: "2015-02-024",
    name: "Daniel Turner",
    email: "dturner@eduprohigh.edu",
    class: "11A",
    dob: "12/12/2009",
    phone: "(555) 101-0101",
    gender: "Male",
    address: "2424 Cedar Blvd, Springfield, IL",
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

  const filtered = ALL_STUDENTS.filter(
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
        <h1 className="page-title">Tous les élèves</h1>
        <div className="page-header-actions">
          <button
            className="btn-primary"
            onClick={() => navigate("/teachers/add")}
          >
            Ajouter des élèves
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
            placeholder="Rechercher un élève par nom ou courriel"
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
          <p className="empty-title">Aucun élève pour le moment</p>
          <p className="empty-sub">
            Students will appear here after they enroll in your school.
          </p>
        </div>
      ) : (
        <div className="teachers-table-wrap">
          <table className="teachers-table">
            <thead>
              <tr>
                <th>Nom</th>
                <th>Courriel</th>
                <th>Classe</th>
                <th>Date de naissance</th>
                <th>Téléphone</th>
                <th>Genre</th>
                <th>Adresse</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedData.map((t, i) => {
                const bg = AVATAR_COLORS[i % AVATAR_COLORS.length];
                const color = TEXT_COLORS[i % TEXT_COLORS.length];
                return (
                  <tr
                    key={t.id}
                    className={i % 2 === 1 ? "row-alt" : ""}
                    onClick={() => navigate(`/teachers/${t.id}`)}
                    style={{ cursor: "pointer" }}
                  >
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
                    <td>{t.email}</td>
                    <td>{t.class}</td>
                    <td>{t.dob}</td>
                    <td>{t.phone}</td>
                    <td>{t.gender}</td>
                    <td>{t.address}</td>
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
                          title="Modifier l’élève"
                        >
                          <Edit fontSize="small" />
                        </button>
                        <button
                          className="action-btn delete-btn"
                          title="Supprimer l’élève"
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
