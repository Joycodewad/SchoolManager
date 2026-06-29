import { useState } from "react";
import { useAuth } from "../hooks/AuthContext";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer
} from "recharts";

// ── Données ──────────────────────────────────────────────────────────
const STATS = [
  { label: "Élèves", value: "124,684", trend: "+15%", up: true,  color: "#e8e4ff", accent: "#6c5ce7" },
  { label: "Enseignants",  value: "12,379",  trend: "-3%",  up: false, color: "#fff8dc", accent: "#f0b429" },
  { label: "Personnel",    value: "29,300",  trend: "-3%",  up: false, color: "#e8e4ff", accent: "#6c5ce7" },
  { label: "Récompenses",    value: "95,800",  trend: "+5%",  up: true,  color: "#fff8dc", accent: "#f0b429" },
];

const ATTENDANCE = [
  { day: "Mon", present: 65, absent: 55 },
  { day: "Tue", present: 75, absent: 65 },
  { day: "Wed", present: 95, absent: 72 },
  { day: "Thu", present: 70, absent: 80 },
  { day: "Fri", present: 68, absent: 60 },
];

// const AGENDA = [
//   { time: "08:00 am", grade: "All Grade",   title: "Homeroom & Announcement",      color: "#e8e4ff" },
//   { time: "10:00 am", grade: "Grade 3–5",   title: "Math Review & Practice",        color: "#fff8dc" },
//   { time: "10:30 am", grade: "Grade 6–8",   title: "Science Experiment & Discussion", color: "#e8f0fe" },
// ];

const MESSAGES = [
  { name: "Dr. Lila Ramirez",  time: "9:00 AM",  text: "The science lab session has been rescheduled.", avatar: "LR", color: "#e8e4ff", tc: "#6c5ce7" },
  { name: "Mr. James Okafor",  time: "8:30 AM",  text: "Please review the updated curriculum changes.",  avatar: "JO", color: "#fff8dc", tc: "#b7791f" },
  { name: "Ms. Tina Bright",   time: "7:45 AM",  text: "Parent meeting confirmed for Friday 3 PM.",       avatar: "TB", color: "#d1fae5", tc: "#065f46" },
];

// Calendrier simple
const DAYS_LABEL = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
function getCalendarDays(year, month) {
  const first = new Date(year, month, 1).getDay();
  const total = new Date(year, month + 1, 0).getDate();
  return { first, total };
}

// Donut SVG maison
function DonutChart({ boys, girls }) {
  const total = boys + girls;
  const boysPct  = boys  / total;
  const r = 70, cx = 90, cy = 90, stroke = 22;
  const circ = 2 * Math.PI * r;
  const boysArc  = circ * boysPct;
  const girlsArc = circ * (1 - boysPct);
  return (
    <svg width="180" height="180" viewBox="0 0 180 180">
      {/* Girls arc (background) */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#bde0fe" strokeWidth={stroke}
        strokeDasharray={`${girlsArc} ${circ}`}
        strokeDashoffset={0}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dasharray 0.6s" }}
      />
      {/* Boys arc */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#f0b429" strokeWidth={stroke}
        strokeDasharray={`${boysArc} ${circ}`}
        strokeDashoffset={-girlsArc}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: "stroke-dasharray 0.6s" }}
      />
      {/* Center icon */}
      <text x={cx} y={cy - 6} textAnchor="middle" fontSize="26" fill="#9ca3af">👫</text>
    </svg>
  );
}

// Tooltip attendance
function AttTooltip({ active, payload, label }: { active?: boolean; payload?: any[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#1e3a5f", color: "white", borderRadius: 10, padding: "10px 16px", fontSize: 13, boxShadow: "0 4px 16px rgba(0,0,0,0.2)" }}>
      <div style={{ fontWeight: 700, marginBottom: 4 }}>{payload[0]?.value}%</div>
      <div style={{ opacity: 0.8 }}>Présents</div>
    </div>
  );
}

export default function Dashboard() {
  const { academicYears } = useAuth();
  const currentAcademicYear = academicYears.find((year) => year.is_active) ?? null;
  const today = new Date();
  const [calDate, setCalDate] = useState({ year: today.getFullYear(), month: today.getMonth() });
  const { first, total } = getCalendarDays(calDate.year, calDate.month);
  const monthName = new Date(calDate.year, calDate.month).toLocaleString("en-US", { month: "long" });

  const prevMonth = () => setCalDate(d => {
    const m = d.month === 0 ? 11 : d.month - 1;
    const y = d.month === 0 ? d.year - 1 : d.year;
    return { year: y, month: m };
  });
  const nextMonth = () => setCalDate(d => {
    const m = d.month === 11 ? 0 : d.month + 1;
    const y = d.month === 11 ? d.year + 1 : d.year;
    return { year: y, month: m };
  });

  return (
    <div className="db-root">

      <div className="dashboard-academic-banner">
        <div><span>Année académique en cours</span><strong>{currentAcademicYear?.name ?? "Aucune année active"}</strong></div>
        {currentAcademicYear && <small>{currentAcademicYear.start_date} → {currentAcademicYear.end_date}</small>}
      </div>

      {/* ── Stat cards ── */}
      <div className="db-stats">
        {STATS.map((s, i) => (
          <div key={i} className="db-stat-card" style={{ background: s.color }}>
            <div className="db-stat-top">
              <span className={`db-trend ${s.up ? "up" : "down"}`}>
                {s.up ? "↑" : "↓"} {s.trend}
              </span>
              <span className="db-dots">···</span>
            </div>
            <div className="db-stat-value">{s.value}</div>
            <div className="db-stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* ── Middle row ── */}
      <div className="db-middle">

        {/* Students donut */}
        <div className="db-card db-students">
          <div className="db-card-header">
            <span className="db-card-title">Élèves</span>
            <span className="db-dots">···</span>
          </div>
          <div className="db-donut-wrap">
            <DonutChart boys={45414} girls={40270} />
          </div>
          <div className="db-donut-legend">
            <div className="db-legend-item">
              <span className="db-legend-dot" style={{ background: "#f0b429" }} />
              <div>
                <div className="db-legend-val">45.414</div>
                <div className="db-legend-sub">Garçons (47 %)</div>
              </div>
            </div>
            <div className="db-legend-item">
              <span className="db-legend-dot" style={{ background: "#bde0fe" }} />
              <div>
                <div className="db-legend-val">40.270</div>
                <div className="db-legend-sub">Filles (53 %)</div>
              </div>
            </div>
          </div>
        </div>

        {/* Attendance chart */}
        <div className="db-card db-attendance">
          <div className="db-card-header">
            <span className="db-card-title">Présences</span>
            <div style={{ display: "flex", gap: 8 }}>
              <select className="db-select">
                <option>Hebdomadaire</option><option>Mensuel</option>
              </select>
              <select className="db-select">
                <option>Classe 3</option><option>Classe 4</option><option>Classe 5</option>
              </select>
            </div>
          </div>
          <div className="db-legend-row">
            <span className="db-legend-dot" style={{ background: "#f0b429" }} />
            <span className="db-legend-text">Total des présents</span>
            <span className="db-legend-dot" style={{ background: "#bde0fe" }} />
            <span className="db-legend-text">Total des absents</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={ATTENDANCE} barGap={4} barCategoryGap="30%">
              <XAxis dataKey="day" axisLine={false} tickLine={false} tick={{ fill: "#9ca3af", fontSize: 13 }} />
              <YAxis domain={[0, 100]} ticks={[0,25,50,75,100]} axisLine={false} tickLine={false} tick={{ fill: "#9ca3af", fontSize: 12 }} />
              <Tooltip content={<AttTooltip />} cursor={false} />
              <Bar dataKey="present" fill="#f0b429" radius={[6,6,0,0]} />
              <Bar dataKey="absent"  fill="#bde0fe" radius={[6,6,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Right column */}
        <div className="db-right-col">

          {/* Calendar */}
          <div className="db-card db-calendar">
            <div className="db-cal-header">
              <button className="db-cal-nav" onClick={prevMonth}>‹</button>
              <span className="db-cal-title">{monthName} {calDate.year}</span>
              <button className="db-cal-nav" onClick={nextMonth}>›</button>
            </div>
            <div className="db-cal-days-label">
              {DAYS_LABEL.map(d => <span key={d}>{d}</span>)}
            </div>
            <div className="db-cal-grid">
              {Array.from({ length: first }).map((_, i) => <span key={"e"+i} />)}
              {Array.from({ length: total }).map((_, i) => {
                const day = i + 1;
                const isToday = day === today.getDate() && calDate.month === today.getMonth() && calDate.year === today.getFullYear();
                return (
                  <span key={day} className={`db-cal-day${isToday ? " today" : ""}`}>{day}</span>
                );
              })}
            </div>
          </div>

          {/* Agenda */}
          {/* <div className="db-card db-agenda">
            <div className="db-card-header">
              <span className="db-card-title">Agenda</span>
              <span className="db-dots">···</span>
            </div>
            <div className="db-agenda-list">
              {AGENDA.map((a, i) => (
                <div key={i} className="db-agenda-item" style={{ background: a.color }}>
                  <span className="db-agenda-time">{a.time}</span>
                  <div>
                    <div className="db-agenda-grade">{a.grade}</div>
                    <div className="db-agenda-title">{a.title}</div>
                  </div>
                </div>
              ))}
            </div>
          </div> */}

        </div>
      </div>

      {/* ── Messages ── */}
      <div className="db-card db-messages">
        <div className="db-card-header">
          <span className="db-card-title">Messages</span>
          <button className="db-view-all">Tout voir</button>
        </div>
        <div className="db-msg-list">
          {MESSAGES.map((m, i) => (
            <div key={i} className="db-msg-item">
              <div className="db-msg-avatar" style={{ background: m.color, color: m.tc }}>
                {m.avatar}
              </div>
              <div className="db-msg-body">
                <div className="db-msg-top">
                  <span className="db-msg-name">{m.name}</span>
                  <span className="db-msg-time">{m.time}</span>
                </div>
                <p className="db-msg-text">{m.text}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
