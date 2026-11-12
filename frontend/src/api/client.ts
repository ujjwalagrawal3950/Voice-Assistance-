/**
 * Typed API client for the Virtual KAM backend.
 * All calls go through relative /api paths. In development Vite proxies
 * /api -> http://127.0.0.1:8000. In production the frontend is served
 * from the same origin as the backend.
 *
 * Seller identity is sent via the X-Seller-Id header, matching the
 * backend's get_current_seller_id dependency.
 */

import type {
  DashboardSummary,
  Seller,
  Product,
  Recommendation,
  ChatRequest,
  ChatResponse,
  VoiceSessionResponse,
  ProactiveAlert,
  StockoutImpact,
  RevenueDecomposition,
  WhatIfResult,
  OutcomeTrackRecord,
  InventoryHealth,
  FestivalCalendarResponse,
} from '@/types'

const BASE = '/api'

function headers(): HeadersInit {
  const h: HeadersInit = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'X-Seller-Id': 'demo-seller-001',
  }
  return h
}

async function request<T>(input: RequestInfo | URL, init: RequestInit = {}): Promise<T> {
  const res = await fetch(input.toString(), {
    ...init,
    headers: { ...headers(), ...(init.headers || {}) },
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body?.detail ?? body?.message ?? detail
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(`API error (${res.status}): ${detail}`)
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  /** GET /health */
  health: () =>
    request<{ status: string; app_env: string }>(`${BASE.replace('/api', '')}/health`),

  /** GET /api/dashboard/summary */
  getDashboard: (params?: { period_days?: number }) => {
    const qs = params ? `?period_days=${params.period_days}` : ''
    return request<DashboardSummary>(`${BASE}/dashboard/summary${qs}`)
  },

  /** GET /api/seller/profile */
  getSellerProfile: () => request<Seller>(`${BASE}/seller/profile`),

  /** PATCH /api/seller/profile */
  updateSellerProfile: (payload: Partial<Seller>) =>
    request<Seller>(`${BASE}/seller/profile`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),

  /** GET /api/products */
  listProducts: (params?: { category?: string }) => {
    const qs = params?.category ? `?category=${encodeURIComponent(params.category)}` : ''
    return request<Product[]>(`${BASE}/products${qs}`)
  },

  /** GET /api/products/:skuId */
  getProduct: (skuId: string) => request<Product>(`${BASE}/products/${skuId}`),

  /** POST /api/products */
  createProduct: (
    payload: Omit<Product, 'id' | 'seller_id' | 'created_at' | 'updated_at'> & {
      seller_id: string
    }
  ) =>
    request<Product>(`${BASE}/products`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /** POST /api/assistant/chat */
  chat: (payload: ChatRequest) =>
    request<ChatResponse>(`${BASE}/assistant/chat`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /** POST /api/voice/session */
  getVoiceSession: () =>
    request<VoiceSessionResponse>(`${BASE}/voice/session`, {
      method: 'POST',
    }),

  /** GET /api/recommendations */
  listRecommendations: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : ''
    return request<Recommendation[]>(`${BASE}/recommendations${qs}`)
  },

  /** POST /api/recommendations/:id/approve */
  approveRecommendation: (recId: string, action: 'approve' | 'reject') =>
    request<Recommendation>(`${BASE}/recommendations/${recId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  /** POST /api/recommendations/:id/outcome */
  recordOutcome: (
    recId: string,
    payload: {
      outcome_status: 'positive' | 'neutral' | 'negative'
      actual_units_ordered?: number
      actual_revenue_delta_pct?: number
      actual_margin_pct?: number
      outcome_notes?: string
    }
  ) =>
    request<Recommendation>(`${BASE}/recommendations/${recId}/outcome`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  /** GET /api/recommendations/track-record */
  getOutcomeTrackRecord: () =>
    request<OutcomeTrackRecord>(`${BASE}/recommendations/track-record`),

  /** GET /api/alerts */
  listAlerts: () => request<ProactiveAlert[]>(`${BASE}/alerts`),

  /** POST /api/alerts/run-digest */
  runAlertsDigest: () =>
    request<ProactiveAlert[]>(`${BASE}/alerts/run-digest`, { method: 'POST' }),

  /** POST /api/alerts/:id/dismiss */
  dismissAlert: (alertId: string) =>
    request<ProactiveAlert>(`${BASE}/alerts/${alertId}/dismiss`, { method: 'POST' }),

  /** GET /api/analytics/stockout-impact */
  getStockoutImpact: (periodDays = 30) =>
    request<StockoutImpact>(`${BASE}/analytics/stockout-impact?period_days=${periodDays}`),

  /** GET /api/analytics/decomposition */
  getDecomposition: (periodDays = 30) =>
    request<RevenueDecomposition>(`${BASE}/analytics/decomposition?period_days=${periodDays}`),

  /** GET /api/inventory/health */
  getInventoryHealth: () =>
    request<InventoryHealth>(`${BASE}/inventory/health`),

  /** GET /api/calendar/festival */
  getFestivalCalendar: () =>
    request<FestivalCalendarResponse>(`${BASE}/calendar/festival`),

  /** POST /api/analytics/what-if */
  runWhatIf: (payload: {
    budget_inr: number
    sku_id?: string
    delay_days?: number
    festival_uplift_pct?: number
  }) =>
    request<WhatIfResult>(`${BASE}/analytics/what-if`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
}
