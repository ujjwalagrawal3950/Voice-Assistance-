/** Shared TypeScript types mirroring the backend API schemas. */

export type DataStatus = 'observed' | 'calculated' | 'estimated' | 'forecast' | 'simulated'

export interface Seller {
  id: string
  display_name: string
  marketplace: string
  business_category?: string
  state?: string
  city?: string
  serviceable_regions?: string
  timezone: string
  business_goals?: string
  target_growth?: number
  target_margin?: number
  available_replenishment_budget: number
  risk_tolerance: string
  growth_vs_margin_priority?: string
  supplier_relationship_strength?: string
  max_credit_stretch_pct?: number
  preferred_stock_cover_days: number
  storage_capacity?: number
  created_at: string
  updated_at: string
}

export interface Product {
  id: string
  seller_id: string
  sku_code: string
  title: string
  category: string
  subcategory?: string
  selling_price: number
  unit_cost: number
  minimum_margin?: number
  current_stock: number
  reserved_stock: number
  incoming_stock: number
  supplier_lead_time_days: number
  minimum_order_quantity: number
  seasonality_tags?: string
  seasonality_tag?: string
  demand_segment?: string
  is_festival_sensitive?: boolean
  is_payday_sensitive?: boolean
  is_wedding_sensitive?: boolean
  product_attributes?: string
  active: boolean
  created_at: string
  updated_at: string
}

export interface DashboardSummary {
  seller_id: string
  period_start: string
  period_end: string
  comparison_start: string
  comparison_end: string
  revenue: number
  orders: number
  units: number
  average_selling_price: number
  cancellation_rate: number
  return_rate: number
  conversion_rate: number | null
  stockout_sku_count: number
  inventory_value_cost: number
  inventory_value_selling: number
  days_of_stock_cover: number | null
  revenue_change_pct: number | null
  orders_change_pct: number | null
  top_alerts: string[]
  data_status: DataStatus
  calculated_at: string
}

export interface SKUPerformance {
  sku_id: string
  sku_code: string
  title: string
  category: string
  selling_price: number
  unit_cost: number
  current_stock: number
  reserved_stock: number
  incoming_stock: number
  supplier_lead_time_days: number
  minimum_order_quantity: number
  days_of_stock_cover: number | null
  recent_7d_units: number
  recent_7d_net_sales: number
  recent_7d_cancellations: number
  is_stockout: boolean
  data_status: DataStatus
}

export interface InventoryHealth {
  seller_id: string
  stockouts: Array<{ sku_id: string; sku_code: string; title: string; category: string }>
  low_cover: Array<{ sku_id: string; sku_code: string; title: string; cover_days: number }>
  dead_stock: Array<{ sku_id: string; sku_code: string; title: string; current_stock: number; cover_days: number }>
  data_status: DataStatus
}

export interface Recommendation {
  id: string
  seller_id: string
  title: string
  problem_or_opportunity: string
  suggested_action: string
  expected_impact?: string
  cost_or_budget?: number
  risk: string
  confidence: string
  urgency: string
  priority: number
  assumptions?: string
  what_to_measure_next?: string
  requires_approval: boolean
  approval_status: string
  execution_status: string
  action_type?: string
  outcome_status?: string
  outcome_notes?: string
  actual_units_ordered?: number
  actual_revenue_delta_pct?: number
  actual_margin_pct?: number
  outcome_recorded_at?: string
  expiry?: string
  related_sku_ids?: string
  created_at: string
  updated_at: string
}

export interface ChatResponse {
  response_text: string
  spoken_text: string | null
  conversation_id: string
  findings: string[] | null
  recommendation_ids: string[]
  follow_up_question: string | null
  tool_activity: string[] | null
  specialists_consulted?: string[] | null
  channel: string
}

export interface ChatRequest {
  message: string
  channel?: 'text' | 'voice'
  conversation_id?: string
  locale?: string
}

export interface CalendarEvent {
  event_name: string
  event_type: string
  start_date: string
  end_date: string
  geography?: string
  shopping_lead_in_days: number
  category_relevance?: string
  confidence: string
  source_url?: string
  data_status: DataStatus
}

export interface VoiceSessionResponse {
  session_id: string
  pipecat_ws_url: string
  seller_id: string
}

export interface ProactiveAlert {
  id: string
  seller_id: string
  alert_type: string
  severity: 'high' | 'medium' | 'low' | string
  title: string
  message: string
  spoken_message?: string
  related_sku_id?: string
  estimated_impact_inr?: number
  is_read: boolean
  dismissed: boolean
  delivered_channel: string
  created_at: string
}

export interface StockoutImpact {
  seller_id: string
  period_days: number
  affected_sku_count: number
  total_lost_units: number
  total_lost_revenue_inr: number
  total_lost_margin_inr: number
  top_impacted_skus: Array<{
    sku_id: string
    sku_code: string
    title: string
    category: string
    demand_segment: string
    seasonality_tag: string
    supplier_lead_time_days: number
    stockout_days: number
    avg_daily_velocity: number
    lost_units: number
    lost_revenue_inr: number
  }>
  summary_text: string
  data_status: DataStatus
}

export interface RevenueDecomposition {
  seller_id: string
  period_days: number
  previous_revenue_inr: number
  current_revenue_inr: number
  revenue_change_inr: number
  previous_asp_inr: number
  current_asp_inr: number
  components: {
    volume_effect_inr: number
    price_effect_inr: number
    interaction_effect_inr: number
    volume_share_pct: number
    price_share_pct: number
  }
  drivers: {
    availability_stockout_loss_inr: number
    availability_share_pct: number
    cancellation_drag_inr: number
    cancellation_share_pct: number
    mix_and_visibility_inr: number
    mix_and_visibility_share_pct: number
  }
  segment_performance: Record<string, { previous_inr: number; current_inr: number; change_inr: number }>
  summary_text: string
  data_status: DataStatus
}

export interface WhatIfResult {
  actual_allocated_spend_inr: number
  unspent_budget_inr: number
  units_procured: number
  expected_revenue_uplift_inr: number
  expected_gross_profit_inr: number
  projected_margin_pct: number
  roi_multiple: number
  estimated_payback_days: number
  delay_opportunity_cost_inr: number
  within_upfront_budget: boolean
  within_profile_cap: boolean
  profile_guidance: string
  upcoming_event?: string
  days_to_event?: number
  sku_allocations: Array<{
    sku_id: string
    sku_code: string
    title: string
    seasonality_tag: string
    lead_time_days: number
    units_to_order: number
    cost_inr: number
    expected_revenue_inr: number
    expected_profit_inr: number
    margin_pct: number
    delay_risk_inr: number
  }>
  summary_text: string
  data_status: DataStatus
}

export interface OutcomeTrackRecord {
  seller_id: string
  measured_count: number
  positive_count: number
  overall_win_rate_pct: number | null
  by_action_type: Record<string, {
    total: number
    positive: number
    win_rate_pct: number
    avg_revenue_delta_pct: number | null
    avg_margin_pct: number | null
    confidence_signal: string
  }>
  recent_outcomes: Array<{
    id: string
    title: string
    action_type: string
    outcome_status: string
    actual_units_ordered?: number
    actual_revenue_delta_pct?: number
    actual_margin_pct?: number
    outcome_notes?: string
  }>
}

// Runtime object exports for backwards compatibility with non-type imports
export const Seller = {};
export const Product = {};
export const DashboardSummary = {};
export const SKUPerformance = {};
export const InventoryHealth = {};
export const Recommendation = {};
export const ChatResponse = {};
export const ChatRequest = {};
export const CalendarEvent = {};
export const VoiceSessionResponse = {};


