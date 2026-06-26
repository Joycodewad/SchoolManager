import { useState } from "react";

const CONVERSATIONS = [
  {
    id: 1,
    name: "Dr. Lila Ramirez",
    role: "Principal",
    time: "9:00 AM",
    unread: 0,
    preview:
      "Please ensure the monthly attendance report is accurate before the April 30th deadline.",
    avatar: "LR",
    color: "#dbeafe",
    tc: "#1d4ed8",
  },
  {
    id: 2,
    name: "Ms. Heather Morris",
    role: "IT Coordinator",
    time: "10:15 AM",
    unread: 4,
    preview:
      "Don't forget the staff training on digital tools scheduled for May 15th at 3 PM in the...",
    avatar: "HM",
    color: "#fce7f3",
    tc: "#be185d",
  },
  {
    id: 3,
    name: "Staff Coordination",
    role: "Group • 12 members",
    time: "2:00 PM",
    unread: 0,
    preview:
      "Ms. Patel: All staff performance reviews are due by the end of this month. Please submit your report...",
    avatar: "SC",
    color: "#e8e4ff",
    tc: "#6c5ce7",
    isGroup: true,
  },
  {
    id: 4,
    name: "Officer Dan Brooks",
    role: "Security",
    time: "3:10 PM",
    unread: 2,
    preview:
      "Review the updated security protocols effective May 1st. Familiarize yourself with...",
    avatar: "DB",
    color: "#d1fae5",
    tc: "#065f46",
  },
  {
    id: 5,
    name: "Ms. Tina Goldberg",
    role: "Admin",
    time: "5:00 PM",
    unread: 0,
    preview: "Reminder: Major IT system upgrade on May 8th from 1 PM to 4 PM.",
    avatar: "TG",
    color: "#fef3c7",
    tc: "#92400e",
  },
  {
    id: 6,
    name: "Mr. Roberto Gracias",
    role: "Teacher",
    time: "7:00 PM",
    unread: 0,
    preview: "Reminder: Major IT system upgrade on May 8th from 1 PM to 4 PM.",
    avatar: "RG",
    color: "#fee2e2",
    tc: "#991b1b",
  },
  {
    id: 7,
    name: "Mr. Reed",
    role: "Science Teacher",
    time: "9:00 PM",
    unread: 0,
    preview:
      "Science Club meeting today at lunch in lab room 204. We'll be planning for the Science Fair.",
    avatar: "MR",
    color: "#e0f2fe",
    tc: "#0369a1",
  },
  {
    id: 8,
    name: "Nurse Emily",
    role: "School Nurse",
    time: "7:00 PM",
    unread: 0,
    preview: "Flu vaccinations are available next week.",
    avatar: "NE",
    color: "#f0fdf4",
    tc: "#14532d",
  },
];

const MESSAGES = [
  {
    id: 1,
    sender: "Mr. Franklin",
    role: "School Secretary",
    time: "8:00 AM",
    text: "Good morning, everyone! Please remember to update your calendars. The school board meeting has been rescheduled to April 27th at 10 AM.",
    avatar: "MF",
    color: "#dbeafe",
    tc: "#1d4ed8",
    mine: false,
  },
  {
    id: 2,
    sender: "Mrs. Thompson",
    role: "Vice Principal",
    time: "8:05 AM",
    text: "Thanks for the heads-up, Ms. Franklin. I'll make sure the agenda items from each department are ready by next Monday. Can someone confirm it next Monday with Mr. Reed?",
    avatar: "MT",
    color: "#fce7f3",
    tc: "#be185d",
    mine: false,
  },
  {
    id: 3,
    sender: "Mr. Harris",
    role: "Health Services Coordinator",
    time: "8:10 AM",
    text: "Can someone confirm if the nurse's office will receive additional flu vaccines before the health fair next week?",
    avatar: "MH",
    color: "#d1fae5",
    tc: "#065f46",
    mine: false,
  },
  {
    id: 4,
    sender: "Linda Adora",
    role: "Admin",
    time: "8:15 AM",
    text: "Maintenance update: The gym's air conditioning system will be repaired this Wednesday. Gym classes need to be relocated for the day.",
    avatar: "LA",
    color: "#e8e4ff",
    tc: "#6c5ce7",
    mine: true,
  },
  {
    id: 5,
    sender: "Ms. Patel",
    role: "HR Manager",
    time: "8:20 AM",
    text: "All staff performance reviews are due by the end of this month. Please submit your reports to HR as soon as possible. Thank you.",
    avatar: "MP",
    color: "#fef3c7",
    tc: "#92400e",
    mine: false,
  },
];

const MEMBERS = [
  {
    name: "Mr. Franklin",
    role: "School Secretary",
    avatar: "MF",
    color: "#dbeafe",
    tc: "#1d4ed8",
  },
  {
    name: "Mrs. Thompson",
    role: "Vice Principal",
    avatar: "MT",
    color: "#fce7f3",
    tc: "#be185d",
  },
  {
    name: "Mr. Harris",
    role: "Health Services Coordinator",
    avatar: "MH",
    color: "#d1fae5",
    tc: "#065f46",
  },
  {
    name: "Linda Adora",
    role: "Admin",
    avatar: "LA",
    color: "#e8e4ff",
    tc: "#6c5ce7",
  },
  {
    name: "Ms. Patel",
    role: "HR Manager",
    avatar: "MP",
    color: "#fef3c7",
    tc: "#92400e",
  },
];

function Avatar({ initials, color, tc, size = 38 }) {
  return (
    <div
      className="msg-avatar"
      style={{
        width: size,
        height: size,
        minWidth: size,
        background: color,
        color: tc,
        fontSize: size < 32 ? 11 : 13,
      }}
    >
      {initials}
    </div>
  );
}

export default function Messages() {
  const [activeId, setActiveId] = useState(3);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState(MESSAGES);
  const [search, setSearch] = useState("");

  const activeConv = CONVERSATIONS.find((c) => c.id === activeId);

  const filtered = CONVERSATIONS.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase()),
  );

  const sendMessage = () => {
    if (!input.trim()) return;
    setMessages((prev) => [
      ...prev,
      {
        id: prev.length + 1,
        sender: "Linda Adora",
        role: "Admin",
        time: new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
        }),
        text: input.trim(),
        avatar: "LA",
        color: "#e8e4ff",
        tc: "#6c5ce7",
        mine: true,
      },
    ]);
    setInput("");
  };

  return (
    <div className="msg-root">
      {/* ── Left panel — conversation list ── */}
      <div className="msg-left">
        <div className="msg-left-header">
          <div className="msg-search-box">
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
              className="msg-search-input"
              placeholder="Search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button className="msg-icon-btn">
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#6b7280"
              strokeWidth="2"
            >
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="4" y1="12" x2="14" y2="12" />
              <line x1="4" y1="18" x2="18" y2="18" />
            </svg>
          </button>
          <button className="msg-icon-btn msg-icon-add">
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

        <div className="msg-conv-list">
          {filtered.map((c) => (
            <div
              key={c.id}
              className={`msg-conv-item${activeId === c.id ? " active" : ""}`}
              onClick={() => setActiveId(c.id)}
            >
              <Avatar initials={c.avatar} color={c.color} tc={c.tc} size={42} />
              <div className="msg-conv-body">
                <div className="msg-conv-top">
                  <span className="msg-conv-name">{c.name}</span>
                  <span className="msg-conv-time">{c.time}</span>
                </div>
                <div className="msg-conv-preview">{c.preview}</div>
              </div>
              {c.unread > 0 && <span className="msg-unread">{c.unread}</span>}
            </div>
          ))}
        </div>
      </div>

      {/* ── Center panel — chat ── */}
      <div className="msg-center">
        {/* Chat header */}
        <div className="msg-chat-header">
          <div className="msg-chat-info">
            <Avatar
              initials={activeConv?.avatar}
              color={activeConv?.color}
              tc={activeConv?.tc}
              size={40}
            />
            <div>
              <div className="msg-chat-name">{activeConv?.name}</div>
              <div className="msg-chat-sub">
                Click here to see group members
              </div>
            </div>
          </div>
          <div className="msg-chat-actions">
            <button className="msg-icon-btn">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#6b7280"
                strokeWidth="1.8"
              >
                <rect x="2" y="7" width="20" height="14" rx="2" />
                <path d="M16 3l-4 4-4-4" />
              </svg>
            </button>
            <button className="msg-icon-btn">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#6b7280"
                strokeWidth="1.8"
              >
                <path d="M22 16.92v3a2 2 0 0 1-2.18 2A19.79 19.79 0 0 1 11.69 19 19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.36 2 2 0 0 1 3.6 1.18h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 8.75a16 16 0 0 0 5.34 5.34l.95-.95a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 21 16.92z" />
              </svg>
            </button>
            <button className="msg-icon-btn">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#6b7280"
                strokeWidth="1.8"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
            </button>
          </div>
        </div>

        {/* Messages */}
        <div className="msg-chat-body">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`msg-bubble-row${m.mine ? " mine" : ""}`}
            >
              {!m.mine && (
                <Avatar
                  initials={m.avatar}
                  color={m.color}
                  tc={m.tc}
                  size={34}
                />
              )}
              <div className="msg-bubble-wrap">
                {!m.mine && (
                  <div className="msg-bubble-meta">
                    <span className="msg-bubble-sender">{m.sender}</span>
                    <span className="msg-bubble-role">{m.role}</span>
                  </div>
                )}
                <div className={`msg-bubble${m.mine ? " mine" : ""}`}>
                  {m.text}
                </div>
                <div className="msg-bubble-time">{m.time}</div>
              </div>
              {m.mine && (
                <Avatar
                  initials={m.avatar}
                  color={m.color}
                  tc={m.tc}
                  size={34}
                />
              )}
            </div>
          ))}
        </div>

        {/* Input */}
        <div className="msg-input-bar">
          <input
            className="msg-input"
            placeholder="Type a message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          />
          <button className="msg-icon-btn">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#6b7280"
              strokeWidth="1.8"
            >
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.41 17.41a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
          </button>
          <button className="msg-send-btn" onClick={sendMessage}>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </div>

      {/* ── Right panel — group info ── */}
      <div className="msg-right">
        <div className="msg-right-header">
          <span className="msg-right-title">Group info</span>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="msg-icon-btn">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#6b7280"
                strokeWidth="2"
              >
                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
              </svg>
            </button>
            <button className="msg-icon-btn">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#6b7280"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="15" y1="9" x2="9" y2="15" />
                <line x1="9" y1="9" x2="15" y2="15" />
              </svg>
            </button>
          </div>
        </div>

        {/* Group avatar */}
        <div className="msg-group-avatar-wrap">
          <div className="msg-group-avatar">SC</div>
          <div className="msg-group-name">{activeConv?.name}</div>
          <div className="msg-group-sub">{activeConv?.role}</div>
        </div>

        {/* Description */}
        <div className="msg-info-section">
          <div className="msg-info-label">
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#6b7280"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            Description
          </div>
          <p className="msg-info-text">
            This is your go-to hub for seamless communication, collaboration,
            and coordination among our team members. Whether you're working on a
            project, seeking assistance, or just want to connect with your
            colleagues, this chat room has got you covered.
          </p>
        </div>

        {/* Members */}
        <div className="msg-info-section">
          <div className="msg-info-row-header">
            <div className="msg-info-label">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#6b7280"
                strokeWidth="2"
              >
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
              Members
            </div>
            <button className="msg-view-all">View All</button>
          </div>
          <div className="msg-members-list">
            {MEMBERS.map((m, i) => (
              <div key={i} className="msg-member-item">
                <Avatar
                  initials={m.avatar}
                  color={m.color}
                  tc={m.tc}
                  size={32}
                />
                <div>
                  <div className="msg-member-name">{m.name}</div>
                  <div className="msg-member-role">{m.role}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Attachments */}
        <div className="msg-info-section">
          <div className="msg-info-row-header">
            <div className="msg-info-label">
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#6b7280"
                strokeWidth="2"
              >
                <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66L9.41 17.41a2 2 0 0 1-2.83-2.83l8.49-8.48" />
              </svg>
              Attachment
            </div>
            <button className="msg-view-all">View All</button>
          </div>
          <div className="msg-attach-tabs">
            <button className="msg-attach-tab active">Media • 34</button>
            <button className="msg-attach-tab">Files • 12</button>
          </div>
          <div className="msg-attach-grid">
            {[
              "#dbeafe",
              "#fce7f3",
              "#d1fae5",
              "#fef3c7",
              "#ede9fe",
              "#e0f2fe",
            ].map((c, i) => (
              <div
                key={i}
                className="msg-attach-thumb"
                style={{ background: c }}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
