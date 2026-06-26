import { BrowserRouter, Routes, Route } from "react-router-dom";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Teachers from "./pages/Teachers";
import AddTeacher from "./pages/AddTeachers";
import TeacherDetail from "./pages/TeacherDetail";
import Students from "./pages/Students";
import Attendance from "./pages/Attendance";
import Message from "./pages/Messages";
import Calendar from "./pages/Calendar";
import Notice from "./pages/Notice";
import Library from "./pages/Library";
import FeesCollection from "./pages/FeesCollection";
import "./assets/login.css";
import "./assets/dashboard.css";
import "./assets/sidebar.css";
import "./assets/topbar.css";
import "./assets/attendance.css";
import "./assets/message.css";
import "./assets/calendar.css";
import "./assets/notice.css";
import "./assets/library.css";
import "./assets/feescollection.css";
import DashboardLayout from "./layouts/DashboardLayout";
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        {/* Toutes les routes partagent DashboardLayout */}
        <Route element={<DashboardLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/teachers" element={<Teachers />} />
          <Route path="/teachers/add" element={<AddTeacher />} />
          <Route path="/teachers/:id" element={<TeacherDetail />} />
          <Route path="/students" element={<Students />} />
          <Route path="/attendance" element={<Attendance />} />
          <Route path="/message" element={<Message />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/notice" element={<Notice />} />
          <Route path="/library" element={<Library/>} />
          <Route path="/finance/fees" element={<FeesCollection/>} />
          {/* 
          <Route
            path="/finance/expenses"
            element={<Placeholder name="School Expenses" />}
          />
         
          <Route path="/profile" element={<Placeholder name="Profile" />} />
          <Route path="/settings" element={<Placeholder name="Settings" />} /> */}
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
