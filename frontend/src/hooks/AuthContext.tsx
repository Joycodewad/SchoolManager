import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { AuthUser, fetchSchools, LoginResponse, logoutUser, School } from "../api/auth";
import { AcademicYear, listAcademicYears } from "../api/academicYears";

interface AuthContextValue {
  user: AuthUser | null;
  schools: School[];
  activeSchool: School | null;
  academicYears: AcademicYear[];
  activeAcademicYear: AcademicYear | null;
  login: (data: LoginResponse) => void;
  logout: () => Promise<void>;
  selectSchool: (schoolId: number) => void;
  addSchool: (school: School) => void;
  updateSchoolInContext: (school: School) => void;
  selectAcademicYear: (yearId: number) => void;
  refreshAcademicYears: () => Promise<void>;
  getAccessToken: () => string | null;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(() => JSON.parse(localStorage.getItem("auth_user") || "null"));
  const [schools, setSchools] = useState<School[]>(() => JSON.parse(localStorage.getItem("auth_schools") || "[]"));
  const [activeSchool, setActiveSchool] = useState<School | null>(() => JSON.parse(localStorage.getItem("active_school") || "null"));
  const [academicYears, setAcademicYears] = useState<AcademicYear[]>([]);
  const [activeAcademicYear, setActiveAcademicYear] = useState<AcademicYear | null>(() => JSON.parse(localStorage.getItem("active_academic_year") || "null"));

  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (!token) return;
    fetchSchools(token).then((freshSchools) => {
      localStorage.setItem("auth_schools", JSON.stringify(freshSchools));
      setSchools(freshSchools);
      setActiveSchool((current) => {
        const next = freshSchools.find((school) => school.id === current?.id) ?? freshSchools[0] ?? null;
        localStorage.setItem("active_school", JSON.stringify(next));
        return next;
      });
    }).catch(() => undefined);
  }, []);

  const refreshAcademicYears = async () => {
    if (!activeSchool) { setAcademicYears([]); setActiveAcademicYear(null); return; }
    const years = await listAcademicYears(activeSchool.id);
    setAcademicYears(years);
    setActiveAcademicYear((current) => {
      const next = years.find((year) => year.id === current?.id) ?? years.find((year) => year.is_active) ?? years[0] ?? null;
      localStorage.setItem("active_academic_year", JSON.stringify(next));
      return next;
    });
  };

  useEffect(() => { void refreshAcademicYears().catch(() => undefined); }, [activeSchool?.id]);

  const login = (data: LoginResponse) => {
    const school = data.schools[0] ?? null;
    localStorage.setItem("auth_token", data.token);
    localStorage.setItem("auth_user", JSON.stringify(data.user));
    localStorage.setItem("auth_schools", JSON.stringify(data.schools));
    localStorage.setItem("active_school", JSON.stringify(school));
    setUser(data.user);
    setSchools(data.schools);
    setActiveSchool(school);
  };

  const selectSchool = (schoolId: number) => {
    const school = schools.find((item) => item.id === schoolId) ?? null;
    localStorage.setItem("active_school", JSON.stringify(school));
    setActiveSchool(school);
    window.dispatchEvent(new Event("school-changed"));
  };

  const selectAcademicYear = (yearId: number) => {
    const year = academicYears.find((item) => item.id === yearId) ?? null;
    localStorage.setItem("active_academic_year", JSON.stringify(year));
    setActiveAcademicYear(year);
    window.dispatchEvent(new Event("academic-year-changed"));
  };

  const addSchool = (school: School) => {
    const next = [...schools.filter((item) => item.id !== school.id), school];
    localStorage.setItem("auth_schools", JSON.stringify(next));
    setSchools(next);
    if (!activeSchool) {
      localStorage.setItem("active_school", JSON.stringify(school));
      setActiveSchool(school);
      window.dispatchEvent(new Event("school-changed"));
    }
  };

  const updateSchoolInContext = (school: School) => {
    const next = schools.map((item) => item.id === school.id ? school : item);
    localStorage.setItem("auth_schools", JSON.stringify(next));
    setSchools(next);
    if (activeSchool?.id === school.id) {
      localStorage.setItem("active_school", JSON.stringify(school));
      setActiveSchool(school);
    }
  };

  const logout = async () => {
    const token = localStorage.getItem("auth_token");
    if (token) await logoutUser(token).catch(() => undefined);
    ["auth_token", "auth_user", "auth_schools", "active_school"].forEach((key) => localStorage.removeItem(key));
    setUser(null); setSchools([]); setActiveSchool(null);
  };

  return <AuthContext.Provider value={{ user, schools, activeSchool, academicYears, activeAcademicYear, login, logout, selectSchool, addSchool, updateSchoolInContext, selectAcademicYear, refreshAcademicYears,
    getAccessToken: () => localStorage.getItem("auth_token"), isAuthenticated: Boolean(user) }}>
    {children}
  </AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth doit être utilisé dans AuthProvider");
  return context;
}
