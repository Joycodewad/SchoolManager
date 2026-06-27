import { useState } from "react";

const STUDENTS = [
  "Lucas Johnson","Emily Peterson","Michael Brown","Hannah White",
  "Oliver Martinez","Isabella Garcia","Ethan Lee","Sophia Wilson",
  "Aiden Taylor","Ava Smith","Noah Clark","Mia Lewis",
  "James Walker","Charlotte Hall","Benjamin Allen","Amelia Young",
  "Logan Hernandez","Harper King","Elijah Wright","Abigail Scott",
];

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const CLASSES = ["Class 11A","Class 11B","Class 10A","Class 10B","Class 9A","Class 9B"];
const WEEKS   = ["Week 1","Week 2–3","Week 3–4","Week 4"];

// Génère des jours pour une semaine donnée
function getWeekDays(weekIndex) {
  const starts = [1, 8, 15, 22];
  const start  = starts[weekIndex] ?? 1;
  return Array.from({ length: 7 }, (_, i) => start + i);
}

// Génère une présence aléatoire stable par étudiant+jour
function seedRandom(seed) {
  let x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
}

function getStatus(studentIdx, day) {
  const r = seedRandom(studentIdx * 100 + day);
  if (r < 0.12) return "absent";
  if (r < 0.20) return "weekend";
  return "present";
}

const PAGE_SIZE = 10;

function PresentIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="11" fill="#38bdf8" />
      <path d="M7 12.5l3.5 3.5 6-7" stroke="white" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
  );
}

function AbsentIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="11" fill="#f87171" />
      <path d="M8 8l8 8M16 8l-8 8" stroke="white" strokeWidth="2.2" strokeLinecap="round"/>
    </svg>
  );
}

export default function Attendance() {
  const today = new Date();
  const [monthIdx, setMonthIdx]   = useState(3); // April
  const [weekIdx,  setWeekIdx]    = useState(1); // Week 2-3
  const [classVal, setClassVal]   = useState("Class 11A");
  const [page,     setPage]       = useState(1);

  const days       = getWeekDays(weekIdx);
  const totalPages = Math.ceil(STUDENTS.length / PAGE_SIZE);
  const paginated  = STUDENTS.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  // Pages à afficher dans la pagination
  const pageNumbers = () => {
    const pages = [];
    if (totalPages <= 5) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1, 2, 3, "...", totalPages);
    }
    return pages;
  };

  return (
    <div className="content-inner full-width">

      {/* Header */}
      <div className="page-header" style={{ marginBottom: 24 }}>
        <h1 className="page-title">Présences</h1>
        <div className="att-filters">
          {/* Month */}
          <div className="att-select-wrap">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>
            </svg>
            <select className="att-select" value={monthIdx} onChange={e => setMonthIdx(+e.target.value)}>
              {MONTHS.map((m, i) => <option key={m} value={i}>{m} 2024</option>)}
            </select>
          </div>
          {/* Week */}
          <select className="att-select" value={weekIdx} onChange={e => setWeekIdx(+e.target.value)}>
            {WEEKS.map((w, i) => <option key={w} value={i}>{w}</option>)}
          </select>
          {/* Class */}
          <select className="att-select" value={classVal} onChange={e => setClassVal(e.target.value)}>
            {CLASSES.map(c => <option key={c}>{c}</option>)}
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="att-table-wrap">
        <table className="att-table">
          <thead>
            <tr>
              <th className="att-th-name">Nom de l’élève</th>
              {days.map(d => (
                <th key={d} className="att-th-day">{String(d).padStart(2,"0")}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {paginated.map((name, rowIdx) => {
              const si = STUDENTS.indexOf(name);
              return (
                <tr key={name} className={rowIdx % 2 === 0 ? "" : "row-alt"}>
                  <td className="att-td-name">{name}</td>
                  {days.map(d => {
                    const status = getStatus(si, d);
                    return (
                      <td key={d} className="att-td-day">
                        {status === "present"  && <PresentIcon />}
                        {status === "absent"   && <AbsentIcon />}
                        {status === "weekend"  && <span className="att-dash">–</span>}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="att-pagination">
        <button className="pag-btn" onClick={() => setPage(p => Math.max(1, p-1))} disabled={page === 1}>
          Previous
        </button>
        <div className="att-pages">
          {pageNumbers().map((p, i) =>
            p === "..." ? (
              <span key={"dots"+i} className="att-dots">...</span>
            ) : (
              <button
                key={p}
                className={`att-page-btn${page === p ? " active" : ""}`}
                onClick={() => setPage(p)}
              >
                {p}
              </button>
            )
          )}
        </div>
        <button className="pag-btn" onClick={() => setPage(p => Math.min(totalPages, p+1))} disabled={page === totalPages}>
          Next
        </button>
      </div>

    </div>
  );
}
