import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { getMyTimetable, MyTimetable } from "../api/timetable";

const DAYS_LABEL = ["DIM", "LUN", "MAR", "MER", "JEU", "VEN", "SAM"];
const MONTHS = [
  "Janvier",
  "Février",
  "Mars",
  "Avril",
  "Mai",
  "Juin",
  "Juillet",
  "Août",
  "Septembre",
  "Octobre",
  "Novembre",
  "Décembre",
];

const EVENT_COLORS = {
  blue: { bg: "#e8f1fd", border: "#2563eb", text: "#1d4ed8" },
  purple: { bg: "#ede9fe", border: "#7c3aed", text: "#5b21b6" },
  pink: { bg: "#fce7f3", border: "#db2777", text: "#be185d" },
  green: { bg: "#d1fae5", border: "#059669", text: "#065f46" },
  yellow: { bg: "#fef9c3", border: "#ca8a04", text: "#92400e" },
  teal: { bg: "#ccfbf1", border: "#0d9488", text: "#115e59" },
};

const AGENDA_CATEGORIES = [
  { label: "Journée spéciale et célébration", color: "purple" },
  { label: "Présentation de matière et examen", color: "pink" },
  { label: "Foire, exposition et spectacle", color: "blue" },
  { label: "Réunion officielle", color: "yellow" },
];

// All events keyed by "YYYY-M-D"
const RAW_EVENTS = [
  {
    date: [2030, 5, 1],
    title: "Teacher Professional Dev.",
    color: "blue",
    time: "09:00 am",
    group: "Faculty",
  },
  {
    date: [2030, 5, 2],
    title: "Students Day",
    color: "purple",
    time: "08:00 am",
    group: "All Students",
  },
  {
    date: [2030, 5, 2],
    title: "AP Calculus Exam",
    color: "pink",
    time: "10:00 am",
    group: "Grade 12",
  },
  {
    date: [2030, 5, 3],
    title: "Spring Concert",
    color: "green",
    time: "06:00 pm",
    group: "Music Club",
  },
  {
    date: [2030, 5, 5],
    title: "Cinco de Mayo Celebration",
    color: "yellow",
    time: "12:00 pm",
    group: "All School",
  },
  {
    date: [2030, 5, 8],
    title: "Science Fair Setup",
    color: "blue",
    time: "08:00 am",
    group: "Science Club",
  },
  {
    date: [2030, 5, 8],
    title: "Teacher Meeting",
    color: "yellow",
    time: "11:00 am",
    group: "All Teacher",
  },
  {
    date: [2030, 5, 8],
    title: "Varsity Track Meet",
    color: "teal",
    time: "01:00 pm",
    group: "Track Team",
  },
  {
    date: [2030, 5, 8],
    title: "Parents Meeting",
    color: "yellow",
    time: "03:00 pm",
    group: "All Teacher and Parents",
  },
  {
    date: [2030, 5, 9],
    title: "Science Fair",
    color: "blue",
    time: "09:00 am",
    group: "Science Club",
  },
  {
    date: [2030, 5, 10],
    title: "PTA Meeting",
    color: "yellow",
    time: "07:00 pm",
    group: "Parents & Teachers",
  },
  {
    date: [2030, 5, 13],
    title: "English Literature Review",
    color: "pink",
    time: "10:00 am",
    group: "Grade 11",
  },
  {
    date: [2030, 5, 15],
    title: "Varsity Track Meet",
    color: "teal",
    time: "03:00 pm",
    group: "Track Team",
  },
  {
    date: [2030, 5, 16],
    title: "Junior Prom",
    color: "purple",
    time: "07:00 pm",
    group: "Grade 11–12",
  },
  {
    date: [2030, 5, 19],
    title: "Senior Project Fair",
    color: "blue",
    time: "09:00 am",
    group: "Grade 12",
  },
  {
    date: [2030, 5, 19],
    title: "Teacher Meeting",
    color: "yellow",
    time: "11:00 am",
    group: "All Teacher",
  },
  {
    date: [2030, 5, 21],
    title: "Board of Education Meeting",
    color: "yellow",
    time: "06:00 pm",
    group: "Admin",
  },
  {
    date: [2030, 5, 22],
    title: "Art Exhibition Opening",
    color: "green",
    time: "04:00 pm",
    group: "Art Club",
  },
  {
    date: [2030, 5, 23],
    title: "Drama Club Performance",
    color: "purple",
    time: "07:00 pm",
    group: "Drama Club",
  },
  {
    date: [2030, 5, 23],
    title: "PTA Meeting",
    color: "yellow",
    time: "06:00 pm",
    group: "Parents & Teachers",
  },
  {
    date: [2030, 5, 26],
    title: "Memorial Day",
    color: "blue",
    time: "All Day",
    group: "All School",
  },
  {
    date: [2030, 5, 28],
    title: "Sophomore Career Day",
    color: "green",
    time: "09:00 am",
    group: "Grade 10",
  },
  {
    date: [2030, 5, 28],
    title: "Art Fair & Exhibition",
    color: "pink",
    time: "11:00 am",
    group: "Art Dept.",
  },
  {
    date: [2030, 5, 30],
    title: "Last Day of School",
    color: "purple",
    time: "All Day",
    group: "All School",
  },
];

function getKey(y, m, d) {
  return `${y}-${m}-${d}`;
}

function buildEventMap() {
  const map = {};
  RAW_EVENTS.forEach((e) => {
    const k = getKey(e.date[0], e.date[1], e.date[2]);
    if (!map[k]) map[k] = [];
    map[k].push(e);
  });
  return map;
}
const EVENT_MAP = buildEventMap();

function getCalendar(year, month) {
  const firstDay = new Date(year, month - 1, 1).getDay();
  const daysInMonth = new Date(year, month, 0).getDate();
  const prevDays = new Date(year, month - 1, 0).getDate();
  const cells = [];
  for (let i = firstDay - 1; i >= 0; i--)
    cells.push({ day: prevDays - i, cur: false });
  for (let d = 1; d <= daysInMonth; d++) cells.push({ day: d, cur: true });
  while (cells.length % 7 !== 0)
    cells.push({ day: cells.length - daysInMonth - firstDay + 1, cur: false });
  return cells;
}

/**
 * Convertit un jour JavaScript (0 = dimanche) en jour d'emploi du temps
 * (0 = lundi). Le dimanche vaut 6 et ne porte jamais de cours.
 */
function toTimetableDay(jsDay) {
  return (jsDay + 6) % 7;
}

const shortTime = (value) => String(value).slice(0, 5);

function EventChip({ event, small }) {
  const c = EVENT_COLORS[event.color];
  return (
    <div
      className="cal-event-chip"
      style={{
        background: c.bg,
        borderLeft: `3px solid ${c.border}`,
        color: c.text,
      }}
    >
      {event.title.length > 13 && small
        ? event.title.slice(0, 13) + "…"
        : event.title}
    </div>
  );
}

export default function Calendar() {
  const today = new Date();
  const { schoolId = "" } = useParams();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);
  const [view, setView] = useState("Month");
  const [selectedDay, setSelectedDay] = useState(today.getDate());

  const [schedule, setSchedule] = useState<MyTimetable | null>(null);
  // Les gestionnaires basculent entre leur emploi du temps et celui de
  // l'établissement ; les enseignants n'ont que le leur.
  const [scope, setScope] = useState<"mine" | "all">("mine");

  useEffect(() => {
    if (!schoolId) return;
    getMyTimetable(schoolId, scope).then(setSchedule).catch(() => setSchedule(null));
  }, [schoolId, scope]);

  // Cours indexés par jour de la semaine, dans l'ordre des créneaux.
  type Lesson = MyTimetable["slots"][number];
  const lessonsByDay = useMemo(() => {
    const map: Record<number, Lesson[]> = {};
    (schedule?.slots ?? []).forEach((slot) => {
      (map[slot.day] ??= []).push(slot);
    });
    Object.values(map).forEach((rows) =>
      rows.sort((a, b) => a.start_time.localeCompare(b.start_time)));
    return map;
  }, [schedule]);

  const lessonsOn = (day) => {
    const weekday = toTimetableDay(new Date(year, month - 1, day).getDay());
    return lessonsByDay[weekday] ?? [];
  };

  /**
   * En vue établissement, toutes les classes occupent les mêmes heures :
   * on regroupe par créneau pour obtenir une liste lisible plutôt que
   * vingt lignes au même horaire.
   */
  const groupByStart = (lessons: Lesson[]) => {
    const rows = new Map<string, { start: string; end: string; items: Lesson[] }>();
    lessons.forEach((lesson) => {
      const key = lesson.start_time;
      if (!rows.has(key)) rows.set(key, { start: lesson.start_time, end: lesson.end_time, items: [] });
      rows.get(key).items.push(lesson);
    });
    return [...rows.values()];
  };

  const cells = getCalendar(year, month);
  const selectedKey = getKey(year, month, selectedDay);
  const selectedEvents = EVENT_MAP[selectedKey] || [];
  const selectedLessons = lessonsOn(selectedDay);

  const prevMonth = () => {
    if (month === 1) {
      setMonth(12);
      setYear((y) => y - 1);
    } else setMonth((m) => m - 1);
  };
  const nextMonth = () => {
    if (month === 12) {
      setMonth(1);
      setYear((y) => y + 1);
    } else setMonth((m) => m + 1);
  };
  const goToday = () => {
    setYear(today.getFullYear());
    setMonth(today.getMonth() + 1);
    setSelectedDay(today.getDate());
  };

  return (
    <div className="cal-root">
      {/* ── Main calendar ── */}
      <div className="cal-main">
        {/* Header */}
        <div className="cal-header">
          <div className="cal-view-tabs">
            {["Month", "Week", "Day"].map((v) => (
              <button
                key={v}
                className={`cal-view-btn${view === v ? " active" : ""}`}
                onClick={() => setView(v)}
              >
                {v}
              </button>
            ))}
          </div>
          <h2 className="cal-month-title">
            {MONTHS[month - 1]} {year}
          </h2>
          <div className="cal-nav">
            <span className="cal-today-btn" onClick={goToday}>
              Aujourd’hui
            </span>
            <button className="cal-nav-btn" onClick={prevMonth}>
              ‹
            </button>
            <button className="cal-nav-btn" onClick={nextMonth}>
              ›
            </button>
          </div>
        </div>

        {/* Grid */}
        <div className="cal-grid-wrap">
          {/* Day labels */}
          <div className="cal-day-labels">
            {DAYS_LABEL.map((d) => (
              <div key={d} className="cal-day-label">
                {d}
              </div>
            ))}
          </div>

          {/* Cells */}
          <div className="cal-cells">
            {cells.map((cell, idx) => {
              const key = cell.cur ? getKey(year, month, cell.day) : null;
              const events = key ? EVENT_MAP[key] || [] : [];
              const isToday =
                cell.cur &&
                cell.day === today.getDate() &&
                month === today.getMonth() + 1 &&
                year === today.getFullYear();
              const isSelected = cell.cur && cell.day === selectedDay;
              const extra = events.length > 2 ? events.length - 2 : 0;

              return (
                <div
                  key={idx}
                  className={`cal-cell${!cell.cur ? " other" : ""}${isSelected ? " selected" : ""}`}
                  onClick={() => cell.cur && setSelectedDay(cell.day)}
                >
                  <div className={`cal-cell-day${isToday ? " today" : ""}`}>
                    {cell.day}
                  </div>
                  {extra > 0 && <div className="cal-more">{extra} de plus</div>}
                  <div className="cal-cell-events">
                    {events.slice(0, 2).map((e, i) => (
                      <EventChip key={i} event={e} small />
                    ))}
                    {/* Le détail des cours tiendrait mal dans une case de mois :
                        on annonce le volume, le panneau du jour donne le reste. */}
                    {cell.cur && lessonsOn(cell.day).length > 0 && (
                      <div className="cal-lesson-count">
                        {scope === "all"
                          ? `${groupByStart(lessonsOn(cell.day)).length} créneaux`
                          : `${lessonsOn(cell.day).length} cours`}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ── Right sidebar ── */}
      <div className="cal-sidebar">
        {/* Agenda legend */}
        <div className="cal-sidebar-card">
          <div className="cal-sidebar-header">
            <span className="cal-sidebar-title">Ordre du jour</span>
            <span className="cal-dots">···</span>
          </div>
          <div className="cal-agenda-list">
            {AGENDA_CATEGORIES.map((a, i) => {
              const c = EVENT_COLORS[a.color];
              return (
                <div
                  key={i}
                  className="cal-agenda-item"
                  style={{
                    borderLeft: `3px solid ${c.border}`,
                    background: c.bg,
                  }}
                >
                  <span
                    style={{ color: c.text, fontSize: 13, fontWeight: 500 }}
                  >
                    {a.label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Selected day events */}
        <div className="cal-sidebar-card">
          <div className="cal-sidebar-header">
            <span className="cal-sidebar-title">
              {selectedDay} {MONTHS[month - 1].toLowerCase()} {year}
            </span>
            <span className="cal-dots">···</span>
          </div>
          <div className="cal-day-events">
            {/* Emploi du temps du jour sélectionné */}
            {schedule?.timetable && (
              <div className="cal-lessons">
                <div className="cal-lessons-head">
                  <span className="cal-lessons-title">
                    {selectedLessons.length > 0
                      ? `Cours du jour (${selectedLessons.length})`
                      : "Cours du jour"}
                  </span>
                  {schedule.can_manage && (
                    <button
                      type="button"
                      className="cal-scope-btn"
                      onClick={() => setScope((s) => (s === "mine" ? "all" : "mine"))}
                    >
                      {scope === "mine" ? "Voir tout l’établissement" : "Voir mes cours"}
                    </button>
                  )}
                </div>

                {selectedLessons.length === 0 ? (
                  <p className="cal-no-events">
                    {scope === "mine"
                      ? "Aucun cours ce jour."
                      : "Aucun cours programmé ce jour."}
                  </p>
                ) : (
                  groupByStart(selectedLessons).map((row) => (
                    <div key={row.start} className="cal-lesson-row">
                      <span className="cal-lesson-time">
                        {shortTime(row.start)}
                        <small>{shortTime(row.end)}</small>
                      </span>
                      <span className="cal-lesson-body">
                        {row.items.map((lesson) => (
                          <span key={lesson.id} className="cal-lesson-item">
                            <strong>{lesson.subject}</strong>
                            <small>
                              {scope === "all"
                                ? `${lesson.class_name}${lesson.teacher ? ` · ${lesson.teacher}` : ""}`
                                : lesson.class_name}
                            </small>
                          </span>
                        ))}
                      </span>
                    </div>
                  ))
                )}
              </div>
            )}

            {selectedEvents.length === 0 && (
              <p className="cal-no-events">Aucun événement ce jour.</p>
            )}
            {selectedEvents.map((e, i) => {
              const c = EVENT_COLORS[e.color];
              return (
                <div
                  key={i}
                  className="cal-day-event-card"
                  style={{ background: c.bg }}
                >
                  <div className="cal-day-event-top">
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke={c.border}
                      strokeWidth="2"
                    >
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    <span
                      className="cal-day-event-time"
                      style={{ color: c.border }}
                    >
                      {e.time}
                    </span>
                  </div>
                  <div
                    className="cal-day-event-title"
                    style={{ color: "#111827" }}
                  >
                    {e.title}
                  </div>
                  <div
                    className="cal-day-event-group"
                    style={{ color: "#9ca3af" }}
                  >
                    {e.group}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
