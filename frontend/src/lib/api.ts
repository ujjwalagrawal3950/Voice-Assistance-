/**
 * Typed API client for the Virtual KAM backend.
 * All requests include the X-Seller-Id header for seller scoping.
 */

const API_BASE = import.meta.env.VITE_API_BASE || "";

async function request(
  path: string,
  options: RequestInit = {}
): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Seller-Id": "demo-seller-001",
      ...options.headers,
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${text}`);
  }
  return res;
}

// ── Seller ──────────────────────────────────────────────────────────

export interface Seller {
  id: string;
  display_name: string;
  marketplace: string;
  business_category: string | null;
  state: string | null;
  city: string | null;
  serviceable_regions: string | null;
  timezone: string;
  business_goals: string | null;
  target_growth: number | null;
  target_margin: number | null;
  available_replenishment_budget: number;
  risk_tolerance: string;
  preferred_stock_cover_days: number;
  storage_capacity: number | null;
  created_at: string;
  updated_at: string;
}

export async function getSellerProfile(): Promise<Seller> {
  const res = await request("/api/seller/profile");
  return res.json();
}

export interface UpdateSellerProfile {
  display_name?: string;
  business_category?: string;
  state?: string;
  city?: string;
  serviceable_regions?: string;
  timezone?: string;
  business_goals?: string;
  target_growth?: number;
  target_margin?: number;
  available_replenishment_budget?: number;
  risk_tolerance?: string;
  preferred_stock_cover_days?: number;
  storage_capacity?: number;
}

export async function updateSellerProfile(
  payload: UpdateSellerProfile
): Promise<Seller> {
  const res = await request("/api/seller/profile", {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  return res.json();
}

// ── Dashboard ───────────────────────────────────────────────────────

export interface DashboardSummary {
  seller_id: string;
  period_start: string;
  period_end: string;
  comparison_start: string;
  comparison_end: string;
  revenue: number;
  orders: number;
  units: number;
  average_selling_price: number | null;
  cancellation_rate: number | null;
  return_rate: number | null;
  conversion_rate: number | null;
  stockout_sku_count: number;
  inventory_value_cost: number;
  inventory_value_selling: number;
  days_of_stock_cover: number | null;
  revenue_change_pct: number | null;
  orders_change_pct: number | null;
  top_alerts: string[];
  data_status: string;
  calculated_at: string;
}

export async function getDashboardSummary(
  periodDays = 30
): Promise<DashboardSummary> {
  const res = await request(
    `/api/dashboard/summary?period_days=${periodDays}`
  );
  return res.json();
}

// ── Products ────────────────────────────────────────────────────────
export interface Product {
  id: string;
  seller_id: string;
  sku_code: string;
  title: string;
  category: string;
  subcategory: string | null;
  selling_price: number;
  unit_cost: number;
  minimum_margin: number | null;
  current_stock: number;
  reserved_stock: number;
  incoming_stock: number;
  supplier_lead_time_days: number;
  minimum_order_quantity: number;
  seasonality_tags: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export async function getProducts(): Promise<Product[]> {
  const res = await request("/api/products");
  return res.json();
}

// ── Chat / Agent ────────────────────────────────────────────────────
export interface ChatRequest {
  message: string;
  channel: "text" | "voice";
  conversation_id?: string;
  locale?: string;
}

export interface ChatResponse {
  response_text: string;
  spoken_text: string | null;
  conversation_id: string;
  findings: string[];
  recommendation_ids: string[];
  follow_up_question: string | null;
  tool_activity: string[];
  specialists_consulted?: string[] | null;
  channel?: string;
}

export async function chat(payload: ChatRequest): Promise<ChatResponse> {
  const res = await request("/api/assistant/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  return res.json();
}

// ── Chat Sessions Sidebar ───────────────────────────────────────────

export interface ChatSessionSummary {
  session_id: string;
  title: string | null;
  updated_at: string;
}

export interface ChatSessionMessage {
  role: "user" | "assistant";
  content: string;
  sequence_no: number;
}

export async function createChatSession(
  firstMessage: string
): Promise<{ session_id: string; title: string }> {
  const res = await request("/sessions", {
    method: "POST",
    body: JSON.stringify({ first_message: firstMessage }),
  });
  return res.json();
}

export async function listChatSessions(): Promise<ChatSessionSummary[]> {
  const res = await request("/sessions");
  return res.json();
}

export async function getChatSessionMessages(
  sessionId: string
): Promise<ChatSessionMessage[]> {
  const res = await request(`/sessions/${encodeURIComponent(sessionId)}/messages`);
  return res.json();
}

// ── Voice session ────────────────────────────────────────────────────
export interface VoiceSessionResponse {
  session_id: string;
  pipecat_ws_url: string;
  seller_id: string;
}

export async function getVoiceSession(): Promise<VoiceSessionResponse> {
  const res = await request("/api/voice/session", {
    method: "POST",
  });
  return res.json();
}
