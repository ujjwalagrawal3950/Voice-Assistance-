"use client";

import { useEffect, useState } from "react";
import { CreditCard, Package, AlertCircle, RefreshCw, TrendingUp, TrendingDown, Calculator, Bell, Check, Sparkles } from "lucide-react";
import { api } from "@/api/client";
import type { DashboardSummary, ProactiveAlert, RevenueDecomposition, StockoutImpact, WhatIfResult } from "@/types";
import { formatINR } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function Dashboard() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<ProactiveAlert[]>([]);
  const [decomposition, setDecomposition] = useState<RevenueDecomposition | null>(null);
  const [stockoutImpact, setStockoutImpact] = useState<StockoutImpact | null>(null);
  const [whatIfBudget, setWhatIfBudget] = useState<number>(15000);
  const [whatIfDelay, setWhatIfDelay] = useState<number>(7);
  const [whatIfResult, setWhatIfResult] = useState<WhatIfResult | null>(null);
  const [simulating, setSimulating] = useState(false);
  const [digestRunning, setDigestRunning] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getDashboard({ period_days: 30 }),
      api.listAlerts().catch(() => [] as ProactiveAlert[]),
      api.getDecomposition(30).catch(() => null),
      api.getStockoutImpact(30).catch(() => null),
      api.runWhatIf({ budget_inr: 15000, delay_days: 7 }).catch(() => null),
    ])
      .then(([d, al, decomp, oos, wif]) => {
        setData(d);
        setAlerts(al);
        setDecomposition(decomp);
        setStockoutImpact(oos);
        setWhatIfResult(wif);
        setLoading(false);
      })
      .catch((err) => { setError(err.message); setLoading(false) });
  }, []);

  const handleRunWhatIf = async (e: React.FormEvent) => {
    e.preventDefault();
    setSimulating(true);
    try {
      const res = await api.runWhatIf({
        budget_inr: Math.max(500, whatIfBudget || 10000),
        delay_days: Math.max(0, whatIfDelay || 0),
      });
      setWhatIfResult(res);
    } finally {
      setSimulating(false);
    }
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
      <div className="container-responsive py-8">
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="animate-pulse rounded-full bg-primary/10 p-4 mb-4">
            <CreditCard className="w-12 h-12 text-primary" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2">Loading dashboard...</h2>
          <p className="text-sm text-muted-foreground">Preparing your business insights</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container-responsive py-8">
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="animate-pulse rounded-full bg-destructive/10 p-4 mb-4">
            <AlertCircle className="w-12 h-12 text-destructive" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2">Unable to load dashboard</h2>
          <p className="text-sm text-muted-foreground">{error}</p>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 btn-primary"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="container-responsive py-6">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Seller Overview</h1>
          <p className="text-sm text-muted-foreground">
            Last 30 days · {new Date(data.period_start).toLocaleDateString("en-IN")} to {new Date(data.period_end).toLocaleDateString("en-IN")}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="default" className="px-3 py-1.5">
            Data: {data.data_status}
          </Badge>
          <span className="text-xs text-muted-foreground">
            Updated: {new Date(data.calculated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        </div>
      </div>

      {/* Alerts */}
      {data.top_alerts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8 fade-in">
          {data.top_alerts.map((alert, i) => (
            <div key={i} className="alert alert-destructive fade-in">
              <AlertCircle className="w-4 h-4 mr-2 mt-0.5 text-destructive" />
              <span className="text-sm font-medium">{alert}</span>
            </div>
          ))}
        </div>
      )}

      {/* KPI Grid */}
      <div className="grid-responsive mb-8 fade-in">
        <Card className="kpi-card">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium">Revenue</CardTitle>
            <CreditCard className="w-5 h-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-3xl font-bold text-foreground">{formatINR(data.revenue)}</div>
            {data.revenue_change_pct !== null && (
              <div className={`mt-2 flex items-center text-sm font-medium ${data.revenue_change_pct < 0 ? "text-destructive" : "text-success"}`}>
                {data.revenue_change_pct < 0 ? <TrendingDown className="w-3.5 h-3.5 mr-1 shrink-0" /> : <TrendingUp className="w-3.5 h-3.5 mr-1 shrink-0" />}
                {Math.abs(data.revenue_change_pct).toFixed(1)}% vs previous period
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="kpi-card">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium">Orders</CardTitle>
            <Package className="w-5 h-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-3xl font-bold text-foreground">{data.orders.toLocaleString("en-IN")}</div>
            {data.orders_change_pct !== null && (
              <div className={`mt-2 flex items-center text-sm font-medium ${data.orders_change_pct < 0 ? "text-destructive" : "text-success"}`}>
                {data.orders_change_pct < 0 ? <TrendingDown className="w-3.5 h-3.5 mr-1 shrink-0" /> : <TrendingUp className="w-3.5 h-3.5 mr-1 shrink-0" />}
                {Math.abs(data.orders_change_pct).toFixed(1)}% vs previous period
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="kpi-card">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium">Avg. Selling Price</CardTitle>
            <CreditCard className="w-5 h-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-3xl font-bold text-foreground">{formatINR(data.average_selling_price ?? 0)}</div>
          </CardContent>
        </Card>

        <Card className="kpi-card">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium">Units Sold</CardTitle>
            <Package className="w-5 h-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-3xl font-bold text-foreground">{data.units.toLocaleString("en-IN")}</div>
          </CardContent>
        </Card>

        <Card className="kpi-card">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium">Cancellation Rate</CardTitle>
            <AlertCircle className="w-5 h-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-3xl font-bold text-foreground">
              {data.cancellation_rate !== null ? (data.cancellation_rate * 100).toFixed(1) + "%" : "—"}
            </div>
          </CardContent>
        </Card>

        <Card className="kpi-card">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium">Return Rate</CardTitle>
            <AlertCircle className="w-5 h-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-3xl font-bold text-foreground">
              {data.return_rate !== null ? (data.return_rate * 100).toFixed(1) + "%" : "—"}
            </div>
          </CardContent>
        </Card>

        <Card className="kpi-card">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium">Stockouts</CardTitle>
            <AlertCircle className="w-5 h-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-3xl font-bold text-foreground">{data.stockout_sku_count}</div>
            <div className="mt-1 text-xs text-muted-foreground">products out of stock</div>
          </CardContent>
        </Card>

        <Card className="kpi-card">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium">Stock Cover</CardTitle>
            <RefreshCw className="w-5 h-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-3xl font-bold text-foreground">
              {data.days_of_stock_cover !== null ? data.days_of_stock_cover.toFixed(1) : "—"} days
            </div>
          </CardContent>
        </Card>

        <Card className="kpi-card">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-medium">Conversion Rate</CardTitle>
            <CreditCard className="w-5 h-5 text-muted-foreground" />
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-3xl font-bold text-foreground">
              {data.conversion_rate !== null ? (data.conversion_rate * 100).toFixed(1) + "%" : "—"}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stock Cover & Inventory Value */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8 fade-in">
        <Card>
          <CardHeader>
            <CardTitle>Inventory Value</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-border/50">
                <span className="text-sm text-muted-foreground">Value at cost</span>
                <span className="text-sm font-medium text-foreground">{formatINR(data.inventory_value_cost)}</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-muted-foreground">Value at selling price</span>
                <span className="text-sm font-medium text-foreground">{formatINR(data.inventory_value_selling)}</span>
              </div>
              <div className="mt-4 h-1 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-1000"
                  style={{
                    width: `${Math.min(
                      ((data.inventory_value_cost || 0) / Math.max(data.inventory_value_selling || 1, 1)) * 100,
                      100
                    )}%`,
                    ...((data.inventory_value_cost || 0) > Math.max(data.inventory_value_selling || 1, 1)
                      ? { backgroundColor: "oklch(0.58 0.23 20)" }
                      : {}),
                  }}
                ></div>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Stock Cover Days</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="text-4xl font-bold text-primary mb-2">
              {data.days_of_stock_cover !== null ? data.days_of_stock_cover.toFixed(1) : "—"}
            </div>
            <div className="text-sm text-muted-foreground">
              Average days of inventory cover across all active SKUs.
              {data.days_of_stock_cover !== null && data.days_of_stock_cover < 7 && (
                <span className="text-destructive font-medium ml-2">⚠ Low stock cover</span>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Phase 2 Proactive Alerts + Phase 3 Root-Cause & Stockout Impact */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8 fade-in">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 pb-3">
            <div className="flex items-center gap-2">
              <Bell className="w-4 h-4 text-primary" />
              <CardTitle className="text-base">Proactive KAM Alerts</CardTitle>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleRefreshDigest}
              disabled={digestRunning}
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1 ${digestRunning ? "animate-spin" : ""}`} />
              Run Digest
            </Button>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            {alerts.length === 0 ? (
              <p className="text-sm text-muted-foreground">No active risks flagged right now.</p>
            ) : (
              alerts.slice(0, 4).map((al) => (
                <div key={al.id} className="p-3 rounded-lg border border-border bg-muted/40 space-y-1">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant={al.severity === "high" ? "destructive" : "warning"}>
                        {al.severity}
                      </Badge>
                      <span className="text-sm font-semibold text-foreground">{al.title}</span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2 text-xs shrink-0"
                      onClick={() => handleDismissAlert(al.id)}
                    >
                      <Check className="w-3 h-3 mr-1" /> Dismiss
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground leading-relaxed">{al.message}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-primary" />
              <CardTitle className="text-base">Root-Cause Revenue Decomposition</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            {decomposition ? (
              <>
                <p className="text-xs text-muted-foreground leading-relaxed">{decomposition.summary_text}</p>
                <div className="grid grid-cols-3 gap-2 pt-1">
                  <div className="bg-muted/50 rounded-lg p-2.5">
                    <div className="text-[11px] text-muted-foreground">Stockout Loss</div>
                    <div className="text-sm font-bold text-destructive">
                      {decomposition.drivers.availability_share_pct}%
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      ₹{decomposition.drivers.availability_stockout_loss_inr.toLocaleString("en-IN")}
                    </div>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-2.5">
                    <div className="text-[11px] text-muted-foreground">Cancellations</div>
                    <div className="text-sm font-bold text-foreground">
                      {decomposition.drivers.cancellation_share_pct}%
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      ₹{decomposition.drivers.cancellation_drag_inr.toLocaleString("en-IN")}
                    </div>
                  </div>
                  <div className="bg-muted/50 rounded-lg p-2.5">
                    <div className="text-[11px] text-muted-foreground">Price Effect (ASP)</div>
                    <div className="text-sm font-bold text-foreground">
                      {decomposition.components.price_share_pct}%
                    </div>
                    <div className="text-[11px] text-muted-foreground">
                      ₹{decomposition.previous_asp_inr} → ₹{decomposition.current_asp_inr}
                    </div>
                  </div>
                </div>
                {stockoutImpact && stockoutImpact.top_impacted_skus.length > 0 && (
                  <div className="pt-2 border-t border-border/50 space-y-1.5">
                    <div className="text-xs font-medium text-foreground">
                      Top Stockout Lost Revenue ({stockoutImpact.total_lost_units} est. lost units · ₹{stockoutImpact.total_lost_revenue_inr.toLocaleString("en-IN")}):
                    </div>
                    {stockoutImpact.top_impacted_skus.slice(0, 3).map((s) => (
                      <div key={s.sku_id} className="flex items-center justify-between text-xs text-muted-foreground">
                        <span className="truncate pr-2">
                          {s.sku_code} · {s.title} ({s.supplier_lead_time_days}d lead)
                        </span>
                        <span className="font-semibold text-destructive shrink-0">
                          ~{s.lost_units}u · ₹{s.lost_revenue_inr.toLocaleString("en-IN")}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-muted-foreground">Decomposition unavailable.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Interactive "What-If" Scenario Planner */}
      <Card className="mb-8 fade-in">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Calculator className="w-4 h-4 text-primary" />
            <CardTitle className="text-base">&ldquo;What-If&rdquo; Restocking Scenario Planner</CardTitle>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 pt-0">
          <form onSubmit={handleRunWhatIf} className="flex flex-wrap items-end gap-3">
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground font-medium">Restock Budget (₹)</span>
              <Input
                type="number"
                min={500}
                step={500}
                value={whatIfBudget}
                onChange={(e) => setWhatIfBudget(Number(e.target.value))}
                className="w-40 h-9"
              />
            </label>
            <label className="flex flex-col gap-1 text-xs">
              <span className="text-muted-foreground font-medium">If Delayed By (days)</span>
              <Input
                type="number"
                min={0}
                max={30}
                value={whatIfDelay}
                onChange={(e) => setWhatIfDelay(Number(e.target.value))}
                className="w-36 h-9"
              />
            </label>
            <Button type="submit" size="sm" disabled={simulating}>
              {simulating ? "Simulating..." : "Simulate What-If"}
            </Button>
          </form>

          {whatIfResult && (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">{whatIfResult.profile_guidance}</p>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs text-muted-foreground">Expected Revenue Uplift</div>
                  <div className="text-lg font-bold text-primary">
                    ₹{whatIfResult.expected_revenue_uplift_inr.toLocaleString("en-IN")}
                  </div>
                  <div className="text-[11px] text-muted-foreground">{whatIfResult.units_procured} units · {whatIfResult.roi_multiple}x ROI</div>
                </div>
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs text-muted-foreground">Gross Profit &amp; Margin</div>
                  <div className="text-lg font-bold text-foreground">
                    ₹{whatIfResult.expected_gross_profit_inr.toLocaleString("en-IN")}
                  </div>
                  <div className="text-[11px] text-muted-foreground">{whatIfResult.projected_margin_pct}% margin</div>
                </div>
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs text-muted-foreground">Cash Payback</div>
                  <div className="text-lg font-bold text-foreground">
                    ~{whatIfResult.estimated_payback_days} days
                  </div>
                  <div className="text-[11px] text-muted-foreground">Spend ₹{whatIfResult.actual_allocated_spend_inr.toLocaleString("en-IN")}</div>
                </div>
                <div className="bg-muted/50 rounded-lg p-3">
                  <div className="text-xs text-muted-foreground">Cost of {whatIfDelay}-Day Delay</div>
                  <div className="text-lg font-bold text-destructive">
                    ~₹{whatIfResult.delay_opportunity_cost_inr.toLocaleString("en-IN")}
                  </div>
                  <div className="text-[11px] text-muted-foreground">lost sales opportunity</div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Data provenance */}
      <div className="mt-8 pt-6 border-t border-border text-sm text-muted-foreground fade-in">
        <p>
          All metrics are <strong>calculated</strong> from seller records via deterministic KPI
          functions (never generated by the LLM). Last calculated:{" "}
          {new Date(data.calculated_at).toLocaleString("en-IN")}
        </p>
        <p className="mt-1">
          Currency: INR (integer paise). Timezone: Asia/Kolkata.{" "}
          <span className="text-muted-foreground">Data status: {data.data_status}</span>
        </p>
      </div>
    </div>
  );
}
