import { Outlet } from "react-router-dom";
import Sidebar from "../components/SideBar";
import TopBanner from "../components/TopBanner";

export default function DashboardLayout() {
  return (
    <div className="dashboard-root">
      <Sidebar />
      <div className="main">
        <TopBanner />
        <main className="content">
          <Outlet /> {/* ← la page active s'injecte ici */}
        </main>
      </div>
    </div>
  );
}