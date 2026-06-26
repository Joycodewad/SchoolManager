import { useState } from "react";

const BOOKS = [
  {
    id: "2024-LIT-001-01",
    title: "Great Expectations",
    author: "Charles Dickens",
    subject: "English Literature",
    classes: "Class 12",
    year: 1861,
    status: "Available",
    spine: "#ef4444",
  },
  {
    id: "2024-SCI-002-01",
    title: "Brief History of Time",
    author: "Stephen Hawking",
    subject: "Science",
    classes: "Class 10–12",
    year: 1988,
    status: "Checked Out",
    spine: "#64748b",
  },
  {
    id: "2024-HIS-003-01",
    title: "A People's History of the United States",
    author: "Howard Zinn",
    subject: "History",
    classes: "Class 11–12",
    year: 1980,
    status: "Available",
    spine: "#f97316",
  },
  {
    id: "2024-MATH-004-01",
    title: "Calculus Made Easy",
    author: "Silvanus P. Thompson",
    subject: "Mathematics",
    classes: "Class 12",
    year: 1910,
    status: "Available",
    spine: "#94a3b8",
  },
  {
    id: "2024-BIO-005-01",
    title: "The Selfish Gene",
    author: "Richard Dawkins",
    subject: "Biology",
    classes: "Class 11",
    year: 1976,
    status: "Checked Out",
    spine: "#1e293b",
  },
  {
    id: "2024-ART-006-01",
    title: "The Story of Art",
    author: "E.H. Gombrich",
    subject: "Art History",
    classes: "Class 9–12",
    year: 1950,
    status: "Available",
    spine: "#22c55e",
  },
  {
    id: "2024-PHY-007-01",
    title: "Feynman Lectures on Physics",
    author: "Richard Feynman",
    subject: "Physics",
    classes: "Class 11–12",
    year: 1964,
    status: "Available",
    spine: "#3b82f6",
  },
  {
    id: "2024-CHE-008-01",
    title: "Chemistry: The Central Science",
    author: "Brown & LeMay",
    subject: "Chemistry",
    classes: "Class 10–12",
    year: 2018,
    status: "Checked Out",
    spine: "#a855f7",
  },
  {
    id: "2024-ENG-009-01",
    title: "Of Mice and Men",
    author: "John Steinbeck",
    subject: "English Literature",
    classes: "Class 10",
    year: 1937,
    status: "Available",
    spine: "#f59e0b",
  },
  {
    id: "2024-GEO-010-01",
    title: "Guns, Germs, and Steel",
    author: "Jared Diamond",
    subject: "Geography",
    classes: "Class 11–12",
    year: 1997,
    status: "Available",
    spine: "#10b981",
  },
  {
    id: "2024-MAT-011-01",
    title: "Introduction to Algorithms",
    author: "Cormen et al.",
    subject: "Computer Science",
    classes: "Class 12",
    year: 2009,
    status: "Checked Out",
    spine: "#6366f1",
  },
  {
    id: "2024-MUS-012-01",
    title: "Music Theory for Dummies",
    author: "Michael Pilhofer",
    subject: "Music",
    classes: "Class 9–12",
    year: 2007,
    status: "Available",
    spine: "#ec4899",
  },
];

const PAGE_SIZE = 8;

function BookSpine({ color }) {
  return (
    <div className="book-spine" style={{ background: color }}>
      <div className="book-spine-line" />
      <div className="book-spine-line short" />
    </div>
  );
}

function StatusBadge({ status }) {
  const isAvailable = status === "Available";
  return (
    <span className={`lib-status ${isAvailable ? "available" : "checked-out"}`}>
      {status}
    </span>
  );
}

export default function Library() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(new Set());
  const [page, setPage] = useState(1);

  const filtered = BOOKS.filter(
    (b) =>
      b.id.toLowerCase().includes(search.toLowerCase()) ||
      b.title.toLowerCase().includes(search.toLowerCase()) ||
      b.subject.toLowerCase().includes(search.toLowerCase()),
  );

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const toggleAll = () => {
    if (selected.size === paginated.length) setSelected(new Set());
    else setSelected(new Set(paginated.map((b) => b.id)));
  };

  const toggleOne = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleSearch = (val) => {
    setSearch(val);
    setPage(1);
  };

  return (
    <div className="content-inner full-width">
      {/* Header */}
      <div className="page-header" style={{ marginBottom: 20 }}>
        <h1 className="page-title">All Books</h1>
        <div className="lib-header-actions">
          <div className="lib-search-box">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#9ca3af"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              className="lib-search-input"
              placeholder="Search by ID, Name or Subject"
              value={search}
              onChange={(e) => handleSearch(e.target.value)}
            />
          </div>
          <button className="lib-icon-btn lib-filter-btn">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.2"
            >
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="8" y1="12" x2="20" y2="12" />
              <line x1="12" y1="18" x2="20" y2="18" />
            </svg>
          </button>
          <button className="lib-icon-btn lib-add-btn">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2.5"
            >
              <line x1="12" y1="5" x2="12" y2="19" />
              <line x1="5" y1="12" x2="19" y2="12" />
            </svg>
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="lib-table-wrap">
        <table className="lib-table">
          <thead>
            <tr>
              <th style={{ width: 40 }}>
                <input
                  type="checkbox"
                  className="st-checkbox"
                  checked={
                    selected.size === paginated.length && paginated.length > 0
                  }
                  onChange={toggleAll}
                />
              </th>
              <th>Book ID</th>
              <th>Book Name</th>
              <th>Writer</th>
              <th>Subject</th>
              <th>Class(es)</th>
              <th>Publish Date</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {paginated.map((b, i) => {
              const isChecked = selected.has(b.id);
              return (
                <tr
                  key={b.id}
                  className={
                    isChecked ? "row-selected" : i % 2 === 1 ? "row-alt" : ""
                  }
                >
                  <td>
                    <input
                      type="checkbox"
                      className="st-checkbox"
                      checked={isChecked}
                      onChange={() => toggleOne(b.id)}
                    />
                  </td>
                  <td className="lib-td-id">{b.id}</td>
                  <td>
                    <div className="lib-book-name-cell">
                      <BookSpine color={b.spine} />
                      <span className="lib-book-title">{b.title}</span>
                    </div>
                  </td>
                  <td className="lib-td">{b.author}</td>
                  <td className="lib-td">{b.subject}</td>
                  <td className="lib-td">{b.classes}</td>
                  <td className="lib-td">{b.year}</td>
                  <td>
                    <StatusBadge status={b.status} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination" style={{ marginTop: 16 }}>
          <button
            className="pag-btn"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            ← Previous
          </button>
          <span className="pag-info">
            Page {page} of {totalPages}
          </span>
          <button
            className="pag-btn"
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Next →
          </button>
        </div>
      )}
    </div>
  );
}
