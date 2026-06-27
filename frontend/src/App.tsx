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
import PrivateRoute from "./hooks/PrivateRoute";
import Schools from "./pages/Schools";
import Subjects from "./pages/Subjects";
import AcademicYears from "./pages/AcademicYears";
import Enrollments from "./pages/Enrollments";
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Login />} />
        {/* Toutes les routes partagent DashboardLayout */}
        <Route element={<PrivateRoute><DashboardLayout /></PrivateRoute>}>
          <Route path="/schools" element={<Schools />} />
          <Route path="/schools/:schoolId/dashboard" element={<Dashboard />} />
          <Route path="/schools/:schoolId/teachers" element={<Teachers />} />
          <Route path="/schools/:schoolId/subjects" element={<Subjects />} />
          <Route path="/schools/:schoolId/academic-years" element={<AcademicYears />} />
          <Route path="/schools/:schoolId/enrollments" element={<Enrollments />} />
          <Route path="/schools/:schoolId/teachers/add" element={<AddTeacher />} />
          <Route path="/schools/:schoolId/teachers/:id" element={<TeacherDetail />} />
          <Route path="/schools/:schoolId/students" element={<Students />} />
          <Route path="/schools/:schoolId/attendance" element={<Attendance />} />
          <Route path="/schools/:schoolId/message" element={<Message />} />
          <Route path="/schools/:schoolId/calendar" element={<Calendar />} />
          <Route path="/schools/:schoolId/notice" element={<Notice />} />
          <Route path="/schools/:schoolId/library" element={<Library/>} />
          <Route path="/schools/:schoolId/finance/fees" element={<FeesCollection/>} />
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
