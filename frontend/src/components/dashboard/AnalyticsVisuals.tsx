"use client";

import type { RevenueDecomposition } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn, formatRupees, formatDeltaPct } from "@/lib/utils";

interface RevenueWaterfallVisualProps {
  decomposition: RevenueDecomposition;
}

export function RevenueWaterfallVisual({ decomposition }: RevenueWaterfallVisualProps) {
  const prevRev = decomposition.previous_revenue_inr || 0;
  const currRev = decomposition.current_revenue_inr || 0;
  const diffRev = decomposition.revenue_change_inr || currRev - prevRev;
  const maxRev = Math.max(prevRev, currRev, 1);

  const drivers = [
    {
      label: "Out-of-stock losses",
      hint: "Sales missed because popular items hit zero inventory",
      amount: Math.abs(decomposition.drivers.availability_stockout_loss_inr || 0),
      pct: Math.max(0, Math.min(100, decomposition.drivers.availability_share_pct || 0)),
      barColor: "bg-red-500",
    },
    {
      label: "Order cancellations",
      hint: "Orders placed but cancelled before fulfilment",
      amount: Math.abs(decomposition.drivers.cancellation_drag_inr || 0),
      pct: Math.max(0, Math.min(100, decomposition.drivers.cancellation_share_pct || 0)),
      barColor: "bg-amber-500",
    },
    {
      label: "Pricing & demand shift",
      hint: "Changes in average selling price or category demand",
      amount: Math.abs(decomposition.drivers.mix_and_visibility_inr || 0),
      pct: Math.max(0, Math.min(100, decomposition.drivers.mix_and_visibility_share_pct || 0)),
      barColor: "bg-slate-400",
    },
  ];

  const segments = decomposition.segment_performance
    ? Object.entries(decomposition.segment_performance)
    : [];

  return (
    <Card className="h-full">
      <CardHeader className="pb-4 border-b border-border/60">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <CardTitle className="text-base">Why Sales Changed</CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">
              Comparing this period with the previous {decomposition.period_days} days
            </p>
          </div>
          <div className="text-right tabular-nums">
            <span
              className={cn(
                "text-sm font-semibold",
                diffRev >= 0 ? "text-emerald-600" : "text-red-600"
              )}
            >
              {diffRev >= 0 ? "+" : "-"}
              {formatRupees(Math.abs(diffRev))}
            </span>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6 pt-5">
        {/* Simple Two-Bar Period Comparison */}
        <div className="space-y-3">
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Previous Period</span>
              <span className="font-semibold text-foreground tabular-nums">
                {formatRupees(prevRev)}
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-slate-400 transition-all duration-500"
                style={{ width: `${(prevRev / maxRev) * 100}%` }}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Current Period</span>
              <span className="font-semibold text-foreground tabular-nums">
                {formatRupees(currRev)}
              </span>
            </div>
            <div className="h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${(currRev / maxRev) * 100}%` }}
              />
            </div>
          </div>
        </div>

        {/* Clear Driver Breakdown */}
        <div className="space-y-3 pt-4 border-t border-border/60">
          <p className="text-xs font-semibold text-foreground">Main Reasons for Change</p>

          <div className="space-y-3.5">
            {drivers.map((d) => (
              <div key={d.label} className="space-y-1.5">
                <div className="flex items-baseline justify-between gap-2 text-xs">
                  <div>
                    <span className="font-medium text-foreground">{d.label}</span>
                    <span className="text-muted-foreground ml-1.5 hidden sm:inline">
                      — {d.hint}
                    </span>
                  </div>
                  <span className="font-semibold text-foreground tabular-nums shrink-0">
                    {formatRupees(d.amount)}{" "}
                    <span className="font-normal text-muted-foreground">({d.pct.toFixed(0)}%)</span>
                  </span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all duration-500", d.barColor)}
                    style={{ width: `${d.pct}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Segment Summary Table (Clean & Minimal) */}
        {segments.length > 0 && (
          <div className="pt-4 border-t border-border/60 space-y-2.5">
            <p className="text-xs font-semibold text-foreground">Sales by Demand Segment</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {segments.map(([seg, vals]) => {
                const pct =
                  vals.previous_inr > 0
                    ? ((vals.current_inr - vals.previous_inr) / vals.previous_inr) * 100
                    : 0;
                return (
                  <div
                    key={seg}
                    className="rounded-lg border border-border bg-muted/25 px-3.5 py-2.5 flex items-center justify-between gap-2"
                  >
                    <div className="min-w-0">
                      <p className="text-xs font-medium capitalize text-foreground truncate">
                        {seg.replace(/_/g, " ")}
                      </p>
                      <p className="text-[11px] text-muted-foreground tabular-nums">
                        {formatRupees(vals.previous_inr)} → {formatRupees(vals.current_inr)}
                      </p>
                    </div>
                    <span
                      className={cn(
                        "text-xs font-semibold tabular-nums shrink-0",
                        pct >= 0 ? "text-emerald-600" : "text-red-600"
                      )}
                    >
                      {formatDeltaPct(pct)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface StockCoverGaugeProps {
  daysCover: number | null;
  targetDays?: number;
}

export function StockCoverGauge({ daysCover, targetDays = 14 }: StockCoverGaugeProps) {
  const safeDays = daysCover ?? 0;
  const maxScale = Math.max(targetDays * 2, 28);
  const pct = Math.max(0, Math.min(100, (safeDays / maxScale) * 100));

  const status =
    daysCover == null
      ? { label: "Not enough sales history", color: "text-muted-foreground", bar: "bg-slate-400" }
      : safeDays < 7
      ? { label: "Critical — under 7 days left", color: "text-red-600", bar: "bg-red-500" }
      : safeDays < targetDays
      ? { label: `Low — below ${targetDays}-day target`, color: "text-amber-600", bar: "bg-amber-500" }
      : { label: "Healthy stock buffer", color: "text-emerald-600", bar: "bg-emerald-500" };

  return (
    <div className="space-y-2.5">
      <div className="flex items-baseline justify-between">
        <div>
          <span className="text-2xl font-semibold text-foreground tabular-nums">
            {daysCover != null ? `${daysCover} days` : "—"}
          </span>
          <p className={cn("text-xs font-medium mt-0.5", status.color)}>{status.label}</p>
        </div>
        <span className="text-xs text-muted-foreground tabular-nums">Target: {targetDays} days</span>
      </div>

      <div className="relative h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={cn("h-full rounded-full transition-all duration-500", status.bar)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
