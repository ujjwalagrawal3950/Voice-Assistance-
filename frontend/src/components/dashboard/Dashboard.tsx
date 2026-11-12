"use client";

import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  ArrowRight,
  Calendar,
  Check,
  Mic,
  RefreshCw,
} from "lucide-react";
import { api } from "@/api/client";
import { AnalyticsVisualPlaceholder } from "@/components/dashboard/AnalyticsVisualsHelper";
import { RevenueWaterfallVisual, StockCoverGauge } from "@/components/dashboard/AnalyticsVisuals";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  cn,
  formatDeltaPct,
  formatINR,
  formatNumber,
  formatPctPrecise,
  formatRupees,
} from "@/lib/utils";
import type {
  CalendarEvent,
  DashboardSummary,
  ProactiveAlert,
  RevenueDecomposition,
  StockoutImpact,
  WhatIfResult,
} from "@/types";

const PERIOD_OPTIONS = [
  { days: 7, label: "7 Days" },
  { days: 30, label: "30 Days" },
  { days: 90, label: "90 Days" },
];

const BUDGET_PRESETS = [10000, 18000, 40000];

export function Dashboard() {
  const navigate = useNavigate();
  const [periodDays, setPeriodDays] = useState<number>(30);
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<ProactiveAlert[]>([]);
  const [decomposition, setDecomposition] = useState<RevenueDecomposition | null>(null);
  const [stockoutImpact, setStockoutImpact] = useState<StockoutImpact | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [whatIfBudget, setWhatIfBudget] = useState<number>(18000);
  const [whatIfDelay, setWhatIfDelay] = useState<number>(7);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResult | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [digestRunning, setDigestRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPeriodData = async (days: number, initial = false) => {
    if (initial) setLoading(true);
    else setRefreshing(true);

    try {
      const [dash, al, decomp, oos, cal, wif] = await Promise.all([
        api.getDashboard({ period_days: days }),
        api.listAlerts().catch(() => [] as ProactiveAlert[]),
        api.getDecomposition(days).catch(() => null),
        api.getStockoutImpact(days).catch(() => null),
        api.getFestivalCalendar().catch(() => null),
        initial
          ? api.runWhatIf({ budget_inr: 18000, delay_days: 7 }).catch(() => null)
          : Promise.resolve(null),
      ]);
      setData(dash);
      setAlerts(al);
      setDecomposition(decomp);
      setStockoutImpact(oos);
      if (cal?.upcoming_events) setEvents(cal.upcoming_events);
      if (wif) setWhatIfResult(wif);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadPeriodData(periodDays, data === null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodDays]);

  const simulateWithValues = async (budget: number, delay: number) => {
    setSimulating(true);
    try {
      const res = await api.runWhatIf({
        budget_inr: Math.max(500, budget || 10000),
        delay_days: Math.max(0, delay || 0),
      });
      setWhatIfResult(res);
    } finally {
      setSimulating(false);
    }
  };

  const handleRunWhatIf = async (e: React.FormEvent) => {
    e.preventDefault();
    await simulateWithValues(whatIfBudget, whatIfDelay);
  };

  const handleRefreshDigest = async () => {
    setDigestRunning(true);
    try {
      const fresh = await api.runAlertsDigest();
      setAlerts(fresh);
    } finally {
      setDigestRunning(false);
    }
  };

  const handleDismissAlert = async (alertId: string) => {
    await api.dismissAlert(alertId).catch(() => {});
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
  };

  if (loading) {
    return (
      <div className="container-responsive py-8 space-y-6">
        <div className="h-16 rounded-xl bg-white border border-border animate-pulse" />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-28 rounded-xl bg-white border border-border animate-pulse" />
          ))}
        </div>
        <AnalyticsVisualPlaceholder />
      </div>
    );
  }

  if (error) {
    return (
      <div className="container-responsive py-12">
        <Card className="max-w-md mx-auto p-8 text-center space-y-4">
          <div className="mx-auto w-12 h-12 rounded-xl bg-red-50 flex items-center justify-center">
            <AlertCircle className="w-6 h-6 text-red-600" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-foreground">Unable to load dashboard</h2>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <Button onClick={() => loadPeriodData(periodDays, true)}>
            <RefreshCw className="w-4 h-4 mr-2" /> Retry
          </Button>
        </Card>
      </div>
    );
  }

  if (!data) return null;

  const invCost = data.inventory_value_cost || 0;
  const invSell = data.inventory_value_selling || 0;
  const potentialProfit = Math.max(0, invSell - invCost);
  const nextFestival = events[0] || null;
  const revDelta = data.revenue_change_pct;
  const ordersDelta = data.orders_change_pct;

  return (
    <div className="container-responsive py-6 sm:py-8 space-y-7 fade-in">
      {/* Clean Page Header & Period Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-semibold tracking-tight text-foreground">
              Store Dashboard
            </h1>
            {refreshing && (
              <span className="inline-flex items-center text-xs text-muted-foreground">
                <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> Updating…
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground">
            {new Date(data.period_start).toLocaleDateString("en-IN", {
              day: "numeric",
              month: "short",
            })}
            {" – "}
            {new Date(data.period_end).toLocaleDateString("en-IN", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
            {" · "}Compared against previous {periodDays} days
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="inline-flex rounded-lg border border-border bg-white p-0.5">
            {PERIOD_OPTIONS.map((opt) => (
              <button
                key={opt.days}
                type="button"
                onClick={() => setPeriodDays(opt.days)}
                className={cn(
                  "px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer",
                  periodDays === opt.days
                    ? "bg-slate-900 text-white"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>

          <Button
            size="sm"
            onClick={() =>
              navigate(
                "/chat?prompt=" +
                  encodeURIComponent(
                    "Explain my store performance for this period in clear numbers and tell me the top 3 priorities."
                  )
              )
            }
          >
            <Mic className="w-3.5 h-3.5 mr-1.5" />
            Ask AI KAM
          </Button>
        </div>
      </div>

      {/* Single Calm Summary Strip for Upcoming Event / Key Alerts */}
      {(nextFestival || data.top_alerts.length > 0) && (
        <div className="rounded-xl border border-border bg-white px-5 py-3.5 flex flex-col lg:flex-row lg:items-center justify-between gap-3">
          {data.top_alerts.length > 0 && (
            <div className="flex items-start gap-2.5 text-sm text-foreground">
              <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
              <span>{data.top_alerts[0]}</span>
            </div>
          )}

          {nextFestival && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground shrink-0">
              <Calendar className="w-3.5 h-3.5 text-primary shrink-0" />
              <span>
                Upcoming: <strong className="font-medium text-foreground">{nextFestival.event_name}</strong>{" "}
                ({new Date(nextFestival.start_date).toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
                {" · "}
                {nextFestival.shopping_lead_in_days}d preparation window)
              </span>
            </div>
          )}
        </div>
      )}

      {/* 6 Single-Focus KPI Cards — 1 Clear Metric Per Card */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="kpi-card">
          <p className="text-[13px] font-medium text-muted-foreground">Total Revenue</p>
          <p className="text-3xl font-semibold text-foreground tabular-nums mt-1.5">
            {formatINR(data.revenue)}
          </p>
          <p
            className={cn(
              "text-xs font-medium mt-1.5 tabular-nums",
              revDelta == null
                ? "text-muted-foreground"
                : revDelta >= 0
                ? "text-emerald-600"
                : "text-red-600"
            )}
          >
            {revDelta != null
              ? `${formatDeltaPct(revDelta)} vs previous ${periodDays} days`
              : `Net completed revenue`}
          </p>
        </div>

        <div className="kpi-card">
          <p className="text-[13px] font-medium text-muted-foreground">Completed Orders</p>
          <p className="text-3xl font-semibold text-foreground tabular-nums mt-1.5">
            {formatNumber(data.orders)}
          </p>
          <p className="text-xs text-muted-foreground mt-1.5 tabular-nums">
            {formatNumber(data.units)} units sold
            {ordersDelta != null && (
              <span
                className={cn(
                  "ml-1.5 font-medium",
                  ordersDelta >= 0 ? "text-emerald-600" : "text-red-600"
                )}
              >
                ({formatDeltaPct(ordersDelta)})
              </span>
            )}
          </p>
        </div>

        <div className="kpi-card">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[13px] font-medium text-muted-foreground">Products Out of Stock</p>
            <button
              type="button"
              onClick={() => navigate("/products")}
              className="text-xs font-medium text-primary hover:underline cursor-pointer"
            >
              View list
            </button>
          </div>
          <p
            className={cn(
              "text-3xl font-semibold tabular-nums mt-1.5",
              data.stockout_sku_count > 0 ? "text-red-600" : "text-foreground"
            )}
          >
            {formatNumber(data.stockout_sku_count)}
          </p>
          <p className="text-xs text-muted-foreground mt-1.5">
            Products with zero available inventory
          </p>
        </div>

        <div className="kpi-card">
          <p className="text-[13px] font-medium text-muted-foreground">Order Cancellation Rate</p>
          <p
            className={cn(
              "text-3xl font-semibold tabular-nums mt-1.5",
              (data.cancellation_rate ?? 0) > 0.08 ? "text-amber-600" : "text-foreground"
            )}
          >
            {formatPctPrecise(data.cancellation_rate)}
          </p>
          <p className="text-xs text-muted-foreground mt-1.5 tabular-nums">
            Return rate: {formatPctPrecise(data.return_rate)} · Target below 8.0%
          </p>
        </div>

        <div className="kpi-card">
          <p className="text-[13px] font-medium text-muted-foreground">Avg. Selling Price</p>
          <p className="text-3xl font-semibold text-foreground tabular-nums mt-1.5">
            {formatINR(data.average_selling_price)}
          </p>
          <p className="text-xs text-muted-foreground mt-1.5 tabular-nums">
            {data.conversion_rate !== null
              ? `Store conversion: ${formatPctPrecise(data.conversion_rate)}`
              : "Average revenue per unit sold"}
          </p>
        </div>

        <div className="kpi-card">
          <p className="text-[13px] font-medium text-muted-foreground">Stock Cover Remaining</p>
          <p className="text-3xl font-semibold text-foreground tabular-nums mt-1.5">
            {data.days_of_stock_cover != null ? `${data.days_of_stock_cover} days` : "—"}
          </p>
          <p className="text-xs text-muted-foreground mt-1.5 tabular-nums">
            Stock value at cost: {formatINR(invCost)}
          </p>
        </div>
      </div>

      {/* Why Sales Changed + Inventory Health */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-7">
          {decomposition ? (
            <RevenueWaterfallVisual decomposition={decomposition} />
          ) : (
            <Card className="p-6">
              <p className="text-sm text-muted-foreground">Sales breakdown is not available yet.</p>
            </Card>
          )}
        </div>

        <div className="lg:col-span-5 space-y-5">
          <Card>
            <CardHeader className="pb-3 border-b border-border/60">
              <CardTitle className="text-base">Inventory Value &amp; Cover</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 pt-4">
              <StockCoverGauge daysCover={data.days_of_stock_cover} />

              <div className="divide-y divide-border/70 text-sm border-t border-border/60 pt-2">
                <div className="flex items-center justify-between py-2">
                  <span className="text-muted-foreground text-xs">Inventory cost value</span>
                  <span className="font-semibold text-foreground tabular-nums">
                    {formatINR(invCost)}
                  </span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-muted-foreground text-xs">Expected selling value</span>
                  <span className="font-semibold text-foreground tabular-nums">
                    {formatINR(invSell)}
                  </span>
                </div>
                <div className="flex items-center justify-between py-2">
                  <span className="text-muted-foreground text-xs">Potential gross profit</span>
                  <span className="font-semibold text-emerald-600 tabular-nums">
                    {formatINR(potentialProfit)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {stockoutImpact && stockoutImpact.top_impacted_skus.length > 0 && (
            <Card>
              <CardHeader className="pb-3 border-b border-border/60">
                <div className="flex items-baseline justify-between gap-2">
                  <CardTitle className="text-base">Biggest Losses from Stockouts</CardTitle>
                  <span className="text-sm font-semibold text-red-600 tabular-nums">
                    -{formatRupees(stockoutImpact.total_lost_revenue_inr)} total
                  </span>
                </div>
              </CardHeader>
              <CardContent className="pt-2 divide-y divide-border/70">
                {stockoutImpact.top_impacted_skus.slice(0, 4).map((sku) => (
                  <div
                    key={sku.sku_id}
                    className="py-3 flex items-center justify-between gap-3 text-sm"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-foreground truncate">{sku.title}</p>
                      <p className="text-xs text-muted-foreground tabular-nums">
                        Out of stock {sku.stockout_days} days · {sku.supplier_lead_time_days}d supplier lead time
                      </p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="font-semibold text-red-600 tabular-nums">
                        -{formatRupees(sku.lost_revenue_inr)}
                      </p>
                      <p className="text-xs text-muted-foreground tabular-nums">
                        {formatNumber(sku.lost_units)} units missed
                      </p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Proactive Alerts + Restock Simulator */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <Card className="lg:col-span-5">
          <CardHeader className="flex flex-row items-center justify-between gap-2 pb-3 border-b border-border/60">
            <div>
              <CardTitle className="text-base">Action Alerts</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                Issues spotted automatically in your store
              </p>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleRefreshDigest}
              disabled={digestRunning}
              className="h-8 text-xs"
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${digestRunning ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </CardHeader>

          <CardContent className="space-y-3 pt-4">
            {alerts.length === 0 ? (
              <div className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                No urgent alerts right now. Click Refresh to check again.
              </div>
            ) : (
              alerts.slice(0, 4).map((al) => (
                <div
                  key={al.id}
                  className="p-3.5 rounded-lg border border-border bg-muted/20 space-y-2"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant={al.severity === "high" ? "destructive" : "warning"}>
                        {al.severity === "high" ? "Urgent" : "Notice"}
                      </Badge>
                      <span className="text-sm font-medium text-foreground">{al.title}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleDismissAlert(al.id)}
                      className="text-xs text-muted-foreground hover:text-foreground inline-flex items-center gap-1 shrink-0 cursor-pointer"
                    >
                      <Check className="w-3 h-3" /> Dismiss
                    </button>
                  </div>

                  <p className="text-xs text-muted-foreground leading-relaxed">{al.message}</p>

                  <div className="flex items-center justify-between pt-1">
                    {al.estimated_impact_inr ? (
                      <span className="text-xs font-medium text-foreground tabular-nums">
                        Estimated impact: {formatRupees(al.estimated_impact_inr)}
                      </span>
                    ) : (
                      <span />
                    )}
                    <button
                      type="button"
                      onClick={() =>
                        navigate(
                          `/chat?prompt=${encodeURIComponent(
                            `Explain this alert and recommend next steps: ${al.title}`
                          )}`
                        )
                      }
                      className="text-xs font-medium text-primary hover:underline inline-flex items-center gap-1 cursor-pointer"
                    >
                      Ask AI <ArrowRight className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Restock Simulator */}
        <Card className="lg:col-span-7">
          <CardHeader className="pb-3 border-b border-border/60">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <CardTitle className="text-base">Restock Budget Simulator</CardTitle>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Preview expected sales and profit before spending
                </p>
              </div>
              <div className="flex items-center gap-1.5">
                {BUDGET_PRESETS.map((preset) => (
                  <button
                    key={preset}
                    type="button"
                    onClick={() => {
                      setWhatIfBudget(preset);
                      simulateWithValues(preset, whatIfDelay);
                    }}
                    className={cn(
                      "px-2.5 py-1 rounded-md text-xs font-medium border transition-colors cursor-pointer tabular-nums",
                      whatIfBudget === preset
                        ? "bg-slate-900 text-white border-slate-900"
                        : "bg-white text-muted-foreground border-border hover:text-foreground"
                    )}
                  >
                    {formatRupees(preset)}
                  </button>
                ))}
              </div>
            </div>
          </CardHeader>

          <CardContent className="space-y-5 pt-4">
            <form onSubmit={handleRunWhatIf} className="flex flex-wrap items-end gap-3">
              <label className="flex flex-col gap-1.5 text-xs">
                <span className="text-muted-foreground font-medium">Budget (₹)</span>
                <Input
                  type="number"
                  min={500}
                  step={500}
                  value={whatIfBudget}
                  onChange={(e) => setWhatIfBudget(Number(e.target.value))}
                  className="w-36 h-9 tabular-nums"
                />
              </label>

              <label className="flex flex-col gap-1.5 text-xs">
                <span className="text-muted-foreground font-medium">If delayed by (days)</span>
                <Input
                  type="number"
                  min={0}
                  max={60}
                  value={whatIfDelay}
                  onChange={(e) => setWhatIfDelay(Number(e.target.value))}
                  className="w-36 h-9 tabular-nums"
                />
              </label>

              <Button type="submit" size="sm" disabled={simulating} className="h-9">
                {simulating ? "Calculating..." : "Calculate"}
              </Button>
            </form>

            {whatIfResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  <div className="rounded-lg border border-border bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground">Expected Sales</p>
                    <p className="text-lg font-semibold text-foreground tabular-nums mt-0.5">
                      {formatRupees(whatIfResult.expected_revenue_uplift_inr)}
                    </p>
                    <p className="text-[11px] text-muted-foreground tabular-nums mt-0.5">
                      {formatNumber(whatIfResult.units_procured)} units
                    </p>
                  </div>

                  <div className="rounded-lg border border-border bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground">Expected Profit</p>
                    <p className="text-lg font-semibold text-emerald-600 tabular-nums mt-0.5">
                      {formatRupees(whatIfResult.expected_gross_profit_inr)}
                    </p>
                    <p className="text-[11px] text-muted-foreground tabular-nums mt-0.5">
                      {whatIfResult.projected_margin_pct}% margin
                    </p>
                  </div>

                  <div className="rounded-lg border border-border bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground">Payback Time</p>
                    <p className="text-lg font-semibold text-foreground tabular-nums mt-0.5">
                      {whatIfResult.estimated_payback_days} days
                    </p>
                    <p className="text-[11px] text-muted-foreground tabular-nums mt-0.5">
                      Spend: {formatRupees(whatIfResult.actual_allocated_spend_inr)}
                    </p>
                  </div>

                  <div className="rounded-lg border border-border bg-muted/20 p-3">
                    <p className="text-xs text-muted-foreground">Delay Loss ({whatIfDelay}d)</p>
                    <p className="text-lg font-semibold text-red-600 tabular-nums mt-0.5">
                      -{formatRupees(whatIfResult.delay_opportunity_cost_inr)}
                    </p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      Missed sales if late
                    </p>
                  </div>
                </div>

                {whatIfResult.profile_guidance && (
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    {whatIfResult.profile_guidance}
                  </p>
                )}

                {whatIfResult.sku_allocations && whatIfResult.sku_allocations.length > 0 && (
                  <div className="rounded-lg border border-border overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="table-header">
                          <th className="px-3.5 py-2.5">Product to Restock</th>
                          <th className="px-3.5 py-2.5 text-right">Lead Time</th>
                          <th className="px-3.5 py-2.5 text-right">Order Qty</th>
                          <th className="px-3.5 py-2.5 text-right">Cost</th>
                          <th className="px-3.5 py-2.5 text-right">Margin</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-border">
                        {whatIfResult.sku_allocations.slice(0, 5).map((item) => (
                          <tr key={item.sku_id} className="hover:bg-muted/30">
                            <td className="px-3.5 py-2.5 font-medium text-foreground">
                              {item.title}
                            </td>
                            <td className="px-3.5 py-2.5 text-right text-muted-foreground tabular-nums">
                              {item.lead_time_days} days
                            </td>
                            <td className="px-3.5 py-2.5 text-right font-semibold text-foreground tabular-nums">
                              {formatNumber(item.units_to_order)}
                            </td>
                            <td className="px-3.5 py-2.5 text-right text-foreground tabular-nums">
                              {formatRupees(item.cost_inr)}
                            </td>
                            <td className="px-3.5 py-2.5 text-right font-medium text-emerald-600 tabular-nums">
                              {item.margin_pct}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Minimal Footer */}
      <div className="pt-4 border-t border-border/70 text-xs text-muted-foreground flex flex-wrap items-center justify-between gap-2">
        <span>Numbers calculated directly from store order records · Currency: INR</span>
        <span>Updated {new Date(data.calculated_at).toLocaleString("en-IN")}</span>
      </div>
    </div>
  );
}
