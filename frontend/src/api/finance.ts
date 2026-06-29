const API_URL = import.meta.env.VITE_API_URL ?? "/api";

export interface Installment { id: number; name: string; percentage: string; due_date: string | null; order: number; }
export interface FeeItem { id: number; module_name: string; male_amount: string; female_amount: string; payable_in_installments: boolean; installments: Installment[]; }
export interface FeePlan {
  id: number; school_class: number; class_name: string; level_name: string; series: string;
  items: FeeItem[];
}
export interface FeePlanPayload {
  school_class: number;
  items: Array<{ module_name: string; male_amount: number; female_amount: number; payable_in_installments: boolean; installments: Array<{ name: string; percentage: number; due_date: string | null; order: number }> }>;
}
export interface FeePayment {
  id: number; enrollment: number; student_name: string; enrollment_number: string; class_name: string;
  class_fee: number; module_name: string; installment: number | null; installment_name: string | null;
  amount: string; paid_on: string; method: string; method_label: string; reference: string; notes: string; received_by_name: string;
}
export interface ComplianceStudent { enrollment: number; enrollment_number: string; student_name: string; gender: string; student_status: string; expected: string; paid: string; balance: string; is_compliant: boolean; }
export interface ComplianceReport { plan: FeePlan; target: string; compliant_count: number; non_compliant_count: number; students: ComplianceStudent[]; }
export interface ExpenseCategory { id: number; name: string; is_active: boolean; }
export interface SchoolExpense { id: number; category: number; category_name: string; label: string; description: string; beneficiary: string; amount: string; expense_date: string; method: string; method_label: string; reference: string; recorded_by_name: string; created_at: string; updated_at: string; }
export interface SchoolExpensePayload { category: number; label: string; description?: string; beneficiary?: string; amount: number; expense_date: string; method: string; reference?: string; }

const headers = () => {
  const year = JSON.parse(localStorage.getItem("active_academic_year") || "null");
  return { "Content-Type": "application/json", Authorization: `Token ${localStorage.getItem("auth_token") ?? ""}`, ...(year?.id ? { "X-Academic-Year-ID": String(year.id) } : {}) };
};
const parse = async (response: Response) => {
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) {
    const message = Object.entries(data ?? {}).map(([field, value]) => `${field}: ${Array.isArray(value) ? value.join(" ") : value}`).join(" — ");
    throw new Error(message || "Une erreur est survenue.");
  }
  return data;
};
const base = (schoolId: string) => `${API_URL}/schools/${schoolId}/finance`;
export const listFeePlans = (schoolId: string): Promise<FeePlan[]> => fetch(`${base(schoolId)}/tuition-plans/`, { headers: headers() }).then(parse);
export const saveFeePlan = (schoolId: string, payload: FeePlanPayload, id?: number): Promise<FeePlan> => fetch(`${base(schoolId)}/tuition-plans/${id ? `${id}/` : ""}`, { method: id ? "PATCH" : "POST", headers: headers(), body: JSON.stringify(payload) }).then(parse);
export const copyFeePlan = (schoolId: string, sourcePlanId: number, targetClasses: number[]): Promise<FeePlan[]> => fetch(`${base(schoolId)}/tuition-plans/${sourcePlanId}/copy/`, { method: "POST", headers: headers(), body: JSON.stringify({ target_classes: targetClasses }) }).then(parse);
export const listPayments = (schoolId: string, classId?: number): Promise<FeePayment[]> => fetch(`${base(schoolId)}/payments/${classId ? `?class_id=${classId}` : ""}`, { headers: headers() }).then(parse);
export const createPayment = (schoolId: string, payload: Record<string, unknown>): Promise<FeePayment> => fetch(`${base(schoolId)}/payments/`, { method: "POST", headers: headers(), body: JSON.stringify(payload) }).then(parse);
export const getCompliance = (schoolId: string, classId: number, target: string): Promise<ComplianceReport> => fetch(`${base(schoolId)}/compliance/?class_id=${classId}&target=${encodeURIComponent(target)}`, { headers: headers() }).then(parse);
export const listExpenseCategories = (schoolId: string): Promise<ExpenseCategory[]> => fetch(`${base(schoolId)}/expense-categories/`, { headers: headers() }).then(parse);
export const createExpenseCategory = (schoolId: string, name: string): Promise<ExpenseCategory> => fetch(`${base(schoolId)}/expense-categories/`, { method: "POST", headers: headers(), body: JSON.stringify({ name }) }).then(parse);
export const listExpenses = (schoolId: string): Promise<SchoolExpense[]> => fetch(`${base(schoolId)}/expenses/`, { headers: headers() }).then(parse);
export const createExpense = (schoolId: string, payload: SchoolExpensePayload): Promise<SchoolExpense> => fetch(`${base(schoolId)}/expenses/`, { method: "POST", headers: headers(), body: JSON.stringify(payload) }).then(parse);
export const updateExpense = (schoolId: string, id: number, payload: Partial<SchoolExpensePayload>): Promise<SchoolExpense> => fetch(`${base(schoolId)}/expenses/${id}/`, { method: "PATCH", headers: headers(), body: JSON.stringify(payload) }).then(parse);
export const deleteExpense = (schoolId: string, id: number): Promise<void> => fetch(`${base(schoolId)}/expenses/${id}/`, { method: "DELETE", headers: headers() }).then(parse);
