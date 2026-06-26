import { useState } from "react";

const NOTICES = [
  {
    id: 1,
    title: "Welcome Back to School!",
    author: "Principal Linda Carter",
    date: "August 1, 2024",
    views: "1.2K",
    preview:
      "As we embark on another exciting academic year, let's embrace the opportunities that lie ahead. We're thrilled to welcome new faces and reunite with returning students. Don't miss our opening assembly on August 5th!",
    full: "As we embark on another exciting academic year, let's embrace the opportunities that lie ahead. We're thrilled to welcome new faces and reunite with returning students. Don't miss our opening assembly on August 5th!\n\nAttention students! To support your exam preparation, the library will offer extended hours starting September 15th. Join us for additional study sessions and access thousands of resources. Please bring and collect over 2,000 pounds of food for local food banks.",
    tags: ["School", "Academic", "Student"],
    avatar: "WB",
    color: "#dbeafe",
    tc: "#1d4ed8",
    image:
      "https://images.unsplash.com/photo-1529156069898-49953e39b3ac?w=400&h=200&fit=crop",
  },
  {
    id: 2,
    title: "Fall Sports Tryouts Schedule",
    author: "Coach Michael Jordan",
    date: "August 15, 2024",
    views: "850",
    preview:
      "Get ready to show your spirit and skills! Tryouts for soccer, volleyball, and football start next week. Check the gym bulletin board for exact dates and required gear. Go Eagles!",
    full: "Get ready to show your spirit and skills! Tryouts for soccer, volleyball, and football start next week. Check the gym bulletin board for exact dates and required gear. Go Eagles!\n\nAll students must have a current physical on file with the nurse's office before participating.",
    tags: ["Sports", "Student"],
    avatar: "FS",
    color: "#d1fae5",
    tc: "#065f46",
    image: null,
  },
  {
    id: 3,
    title: "Library Hours Extension",
    author: "Librarian Sarah Knox",
    date: "September 5, 2024",
    views: "600",
    preview:
      "Attention students! To support your exam preparation, the library will offer extended hours starting September 15th. Join us for additional study sessions and access thousands of resources!",
    full: "Attention students! To support your exam preparation, the library will offer extended hours starting September 15th. Join us for additional study sessions and access thousands of resources!\n\nNew hours: Monday–Friday 7 AM to 9 PM, Saturday 9 AM to 5 PM.",
    tags: ["Academic", "Student"],
    avatar: "LH",
    color: "#ede9fe",
    tc: "#5b21b6",
    image: null,
  },
  {
    id: 4,
    title: "Flu Vaccination Clinic",
    author: "Nurse Emily White",
    date: "October 10, 2024",
    views: "300",
    preview:
      "Protect yourself this flu season! The school nurse's office will host a vaccination clinic on October 20th. Sign up in the main office. Vaccines are free and available to all students and staff.",
    full: "Protect yourself this flu season! The school nurse's office will host a vaccination clinic on October 20th. Sign up in the main office. Vaccines are free and available to all students and staff.\n\nParent consent forms are required for students under 18.",
    tags: ["Health", "Student", "Staff"],
    avatar: "FV",
    color: "#fce7f3",
    tc: "#be185d",
    image: null,
  },
  {
    id: 5,
    title: "Annual Food Drive Kickoff",
    author: "Head of Student Council, Tom Briggs",
    date: "November 1, 2024",
    views: "400",
    preview:
      "Let's make a difference together! Our annual food drive starts November 5th. Please bring non-perishable food items to Room 108. Help us reach our goal to collect over 2,000 pounds of food for local food banks.",
    full: "Let's make a difference together! Our annual food drive starts November 5th. Please bring non-perishable food items to Room 108. Help us reach our goal to collect over 2,000 pounds of food for local food banks.\n\nTop contributing homeroom wins a pizza party!",
    tags: ["Community", "Student"],
    avatar: "AF",
    color: "#fef3c7",
    tc: "#92400e",
    image: null,
  },
];

const TAG_COLORS = {
  School: { bg: "#e8f1fd", color: "#1d4ed8" },
  Academic: { bg: "#d1fae5", color: "#065f46" },
  Student: { bg: "#fef3c7", color: "#92400e" },
  Sports: { bg: "#ede9fe", color: "#5b21b6" },
  Health: { bg: "#fce7f3", color: "#be185d" },
  Staff: { bg: "#e0f2fe", color: "#0369a1" },
  Community: { bg: "#f0fdf4", color: "#14532d" },
};

export default function Notice() {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(NOTICES[0]);

  const filtered = NOTICES.filter(
    (n) =>
      n.title.toLowerCase().includes(search.toLowerCase()) ||
      n.author.toLowerCase().includes(search.toLowerCase()),
  );

  return (
    <div className="notice-root">
      {/* ── Left panel ── */}
      <div className="notice-left">
        {/* Header */}
        <div className="notice-header">
          <h1 className="page-title">Notice Board</h1>
          <div className="notice-header-actions">
            <div className="notice-search-box">
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
                className="notice-search-input"
                placeholder="Search by Title or Author"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <button className="notice-icon-btn">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#6b7280"
                strokeWidth="2"
              >
                <line x1="4" y1="6" x2="20" y2="6" />
                <line x1="8" y1="12" x2="20" y2="12" />
                <line x1="12" y1="18" x2="20" y2="18" />
              </svg>
            </button>
            <button className="notice-icon-btn notice-add-btn">
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

        {/* Notice list */}
        <div className="notice-list">
          {filtered.map((n) => (
            <div
              key={n.id}
              className={`notice-card${selected?.id === n.id ? " active" : ""}`}
              onClick={() => setSelected(n)}
            >
              <div className="notice-card-header">
                <div className="notice-card-left">
                  <div
                    className="notice-avatar"
                    style={{ background: n.color, color: n.tc }}
                  >
                    {n.avatar}
                  </div>
                  <div>
                    <div className="notice-title">{n.title}</div>
                    <div className="notice-author">By {n.author}</div>
                  </div>
                </div>
                <div className="notice-meta">
                  <span className="notice-date">{n.date}</span>
                  <span className="notice-views">
                    <svg
                      width="13"
                      height="13"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                    >
                      <circle cx="12" cy="12" r="3" />
                      <path d="M2 12s3.636-7 10-7 10 7 10 7-3.636 7-10 7S2 12 2 12z" />
                    </svg>
                    {n.views}
                  </span>
                </div>
              </div>
              <p className="notice-preview">{n.preview}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ── Right panel — detail ── */}
      {selected && (
        <div className="notice-detail">
          {selected.image && (
            <img
              src={selected.image}
              alt={selected.title}
              className="notice-detail-img"
            />
          )}
          <h2 className="notice-detail-title">{selected.title}</h2>
          <p className="notice-detail-author">By {selected.author}</p>

          <div className="notice-detail-meta">
            <span className="notice-date">{selected.date}</span>
            <span className="notice-views">
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="3" />
                <path d="M2 12s3.636-7 10-7 10 7 10 7-3.636 7-10 7S2 12 2 12z" />
              </svg>
              {selected.views}
            </span>
          </div>

          <div className="notice-detail-body">
            {selected.full.split("\n\n").map((para, i) => (
              <p key={i}>{para}</p>
            ))}
          </div>

          <div className="notice-detail-tags-section">
            <p className="notice-tags-label">Tag</p>
            <div className="notice-tags">
              {selected.tags.map((tag) => {
                const c = TAG_COLORS[tag] || {
                  bg: "#f3f4f6",
                  color: "#374151",
                };
                return (
                  <span
                    key={tag}
                    className="notice-tag"
                    style={{ background: c.bg, color: c.color }}
                  >
                    {tag}
                  </span>
                );
              })}
            </div>
          </div>

          <button className="notice-read-btn">
            Read Full Page
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <line x1="5" y1="12" x2="19" y2="12" />
              <path d="M12 5l7 7-7 7" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
