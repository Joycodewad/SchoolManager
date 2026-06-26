// import { Logout } from "@mui/icons-material";
import { useAuth } from "../hooks/AuthContext";
import { useNavigate } from "react-router-dom";
import { useState } from "react";

export default function TopBanner() {
  const { logout, user } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const initials = user
    ? `${user.first_name?.[0] ?? ""}${user.last_name?.[0] ?? ""}`.toUpperCase()
    : "U";

  const fullName = user
    ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
    : "Admin";

  return (
    <>
      <header className="topbar">
        {/* Search */}
        <div className="topbar-search">
          <svg
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#9ca3af"
            strokeWidth="2"
          >
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
          <input
            className="topbar-search-input"
            type="text"
            placeholder="Rechercher"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Right side */}
        <div className="topbar-right">
          {/* Chat icon */}
          <button className="topbar-icon-btn">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#6b7280"
              strokeWidth="1.8"
            >
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
          </button>

          {/* Bell icon */}
          <button className="topbar-icon-btn">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#6b7280"
              strokeWidth="1.8"
            >
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
              <path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <span className="topbar-bell-dot" />
          </button>

          {/* Divider */}
          <div className="topbar-divider" />

          {/* User */}
          <div className="topbar-user">
            <div className="topbar-user-info">
              <span className="topbar-user-name">{fullName}</span>
              <span className="topbar-user-role">Administrateur</span>
            </div>
            <div
              className="topbar-avatar"
              onClick={handleLogout}
              title="Se déconnecter"
            >
              {initials}
            </div>
          </div>
        </div>
      </header>
    </>
  );
}
