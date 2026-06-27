import { Navigate, Outlet, useParams } from "react-router-dom";
import { useEffect } from "react";
import { useAuth } from "../hooks/AuthContext";
import Sidebar from "../components/SideBar";
import TopBanner from "../components/TopBanner";

export default function DashboardLayout() {
  const { schoolId } = useParams();
  const { activeSchool, schools, selectSchool } = useAuth();

  useEffect(() => {
    if (!schoolId) return;
    const id = Number(schoolId);
    if (activeSchool?.id !== id && schools.some((school) => school.id === id)) {
      selectSchool(id);
    }
  }, [schoolId, activeSchool?.id, schools]);

  if (schoolId && !schools.some((school) => school.id === Number(schoolId))) {
    return <Navigate to="/schools" replace />;
  }

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
