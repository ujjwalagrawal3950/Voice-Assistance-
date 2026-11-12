"use client";

import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import {
  Mic,
  MessageSquareText,
  BarChart3,
  ArrowRight,
  AlertCircle,
  Package,
  ClipboardCheck,
} from "lucide-react";
import { api } from "@/api/client";
import { useVoice } from "@/hooks/useVoice";
import type { DashboardSummary, ProactiveAlert, Recommendation } from "@/types";
import { Button } from "@/components/ui/button";
import { cn, formatINR, formatRupees, formatNumber, formatPctPrecise, formatDeltaPct } from "@/lib/utils";

interface QuickQuestion {
  title: string;
  description: string;
  prompt: string;
}

const QUICK_QUESTIONS: QuickQuestion[] = [
  {
    title: "Why did sales drop?",
    description: "Break down the exact revenue loss from stockouts vs cancellations.",
    prompt: "Why did my revenue drop over the last 30 days? Break it down in simple numbers.",
  },
  {
    title: "What should I restock first?",
    description: "Get a prioritized restock list fitted to my current budget.",
    prompt: "Which out-of-stock products should I restock first within my available budget?",
  },
  {
    title: "Upcoming festival demand",
    description: "See upcoming shopping events and how early to place supplier orders.",
    prompt: "Which festivals are coming up in my category and when should I order stock?",
  },
  {
    title: "Pending action plans",
    description: "Review recommended actions with estimated cost and profit impact.",
    prompt: "Summarize my pending recommendations with cost, expected profit, and risk.",
  },
];

export function LandingPage() {
  const navigate = useNavigate();
  const { state: voiceState, start } = useVoice();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [alerts, setAlerts] = useState<ProactiveAlert[]>([]);
  const [pendingRecs, setPendingRecs] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.allSettled([
      api.getDashboard({ period_days: 30 }),
      api.listAlerts(),
      api.listRecommendations("pending"),
    ])
      .then(([dashRes, alertsRes, recsRes]) => {
        if (!active) return;
        if (dashRes.status === "fulfilled") setSummary(dashRes.value);
        if (alertsRes.status === "fulfilled") setAlerts(alertsRes.value);
        if (recsRes.status === "fulfilled") setPendingRecs(recsRes.value);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const isVoiceLive =
    voiceState !== "idle" && voiceState !== "error" && voiceState !== "stopping";

  const handleStartVoice = async () => {
    navigate("/chat");
    if (!isVoiceLive) {
      await start();
    }
  };

  const askPrompt = (prompt: string) => {
    navigate(`/kam?prompt=${encodeURIComponent(prompt)}`);
  };

  const revDelta = summary?.revenue_change_pct;
  const topAlert = alerts[0];

  return (
    <div className="container-responsive py-8 space-y-8 fade-in">
      {/* Clean Minimal Hero */}
      <section className="rounded-2xl border border-border bg-white p-6 sm:p-8">
        <div className="max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 text-xs font-medium text-muted-foreground">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            Virtual Key Account Manager · Ready
          </div>

          <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-foreground leading-snug">
            Clear answers on your sales, stockouts, and restock plan.
          </h1>

          <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
            Talk hands-free with your AI manager or open a text conversation to check store numbers and approve actions.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-1">
            <Button onClick={handleStartVoice} className="h-10 px-5 text-sm font-medium">
              <Mic className={cn("w-4 h-4 mr-2", isVoiceLive && "animate-pulse")} />
              {isVoiceLive ? "Return to Active Call" : "Start Voice Call"}
            </Button>

            <Button
              variant="outline"
              onClick={() => navigate("/kam")}
              className="h-10 px-4 text-sm font-medium"
            >
              <MessageSquareText className="w-4 h-4 mr-2 text-muted-foreground" />
              Open AI Chat
            </Button>

            <Link
              to="/dashboard"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-muted-foreground hover:text-foreground px-2 py-2 transition-colors"
            >
              <BarChart3 className="w-4 h-4" />
              Full Dashboard
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Top Store Numbers — 1 Number, 1 Label, 1 Clear Explanation */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Store at a glance (Last 30 days)</h2>
          <Link to="/dashboard" className="text-xs font-medium text-primary hover:underline">
            View detailed analytics
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="kpi-card">
            <p className="text-[13px] font-medium text-muted-foreground">Total Sales</p>
            {loading ? (
              <div className="h-8 w-28 bg-muted rounded animate-pulse mt-2" />
            ) : (
              <p className="text-2xl sm:text-3xl font-semibold text-foreground tabular-nums mt-1.5">
                {formatINR(summary?.revenue)}
              </p>
            )}
            <p
              className={cn(
                "text-xs mt-1.5 font-medium tabular-nums",
                revDelta == null
                  ? "text-muted-foreground"
                  : revDelta >= 0
                  ? "text-emerald-600"
                  : "text-red-600"
              )}
            >
              {revDelta == null
                ? `${formatNumber(summary?.orders)} orders completed`
                : `${formatDeltaPct(revDelta)} compared to previous 30 days`}
            </p>
          </div>

          <div className="kpi-card">
            <p className="text-[13px] font-medium text-muted-foreground">Out-of-Stock Products</p>
            {loading ? (
              <div className="h-8 w-16 bg-muted rounded animate-pulse mt-2" />
            ) : (
              <p
                className={cn(
                  "text-2xl sm:text-3xl font-semibold tabular-nums mt-1.5",
                  (summary?.stockout_sku_count ?? 0) > 0 ? "text-red-600" : "text-foreground"
                )}
              >
                {formatNumber(summary?.stockout_sku_count)}
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1.5">
              Products with zero units available
            </p>
          </div>

          <div className="kpi-card">
            <p className="text-[13px] font-medium text-muted-foreground">Order Cancellation Rate</p>
            {loading ? (
              <div className="h-8 w-20 bg-muted rounded animate-pulse mt-2" />
            ) : (
              <p
                className={cn(
                  "text-2xl sm:text-3xl font-semibold tabular-nums mt-1.5",
                  (summary?.cancellation_rate ?? 0) > 0.08 ? "text-amber-600" : "text-foreground"
                )}
              >
                {formatPctPrecise(summary?.cancellation_rate)}
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1.5">
              Target is below 8.0% of orders
            </p>
          </div>

          <div className="kpi-card">
            <p className="text-[13px] font-medium text-muted-foreground">Stock Cover Left</p>
            {loading ? (
              <div className="h-8 w-20 bg-muted rounded animate-pulse mt-2" />
            ) : (
              <p className="text-2xl sm:text-3xl font-semibold text-foreground tabular-nums mt-1.5">
                {summary?.days_of_stock_cover != null ? `${summary.days_of_stock_cover} days` : "—"}
              </p>
            )}
            <p className="text-xs text-muted-foreground mt-1.5">
              Total orders: {formatNumber(summary?.orders)}
            </p>
          </div>
        </div>
      </section>

      {/* Single Priority Alert (Only shown when present) */}
      {topAlert && (
        <section className="rounded-xl border border-amber-200 bg-amber-50/60 px-5 py-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3 min-w-0">
            <AlertCircle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <p className="text-sm font-medium text-foreground">{topAlert.title}</p>
              <p className="text-xs text-muted-foreground">
                {topAlert.message}
                {topAlert.estimated_impact_inr ? (
                  <span className="font-medium text-foreground tabular-nums">
                    {" "}
                    (Estimated impact: {formatRupees(topAlert.estimated_impact_inr)})
                  </span>
                ) : null}
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => askPrompt(`Tell me more about this alert and what to do: ${topAlert.title}`)}
            className="shrink-0 bg-white"
          >
            Ask AI
          </Button>
        </section>
      )}

      {/* Ask a Question */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-foreground">Quick questions to ask your AI KAM</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {QUICK_QUESTIONS.map((item) => (
            <button
              key={item.title}
              type="button"
              onClick={() => askPrompt(item.prompt)}
              className="group text-left rounded-xl border border-border bg-white p-4 hover:border-slate-300 hover:bg-slate-50/50 transition-colors flex items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <p className="text-sm font-medium text-foreground group-hover:text-primary transition-colors">
                  {item.title}
                </p>
                <p className="text-xs text-muted-foreground">{item.description}</p>
              </div>
              <ArrowRight className="w-4 h-4 text-muted-foreground group-hover:text-primary shrink-0 transition-transform group-hover:translate-x-0.5" />
            </button>
          ))}
        </div>
      </section>

      {/* Clean Quick Links */}
      <section className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
        <Link
          to="/products"
          className="rounded-xl border border-border bg-white p-4 flex items-center justify-between hover:border-slate-300 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center text-slate-700">
              <Package className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">Product Inventory</p>
              <p className="text-xs text-muted-foreground">Check prices, margins, and stock levels</p>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground" />
        </Link>

        <Link
          to="/recommendations"
          className="rounded-xl border border-border bg-white p-4 flex items-center justify-between hover:border-slate-300 transition-colors"
        >
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-slate-100 flex items-center justify-center text-slate-700">
              <ClipboardCheck className="w-4 h-4" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">
                Recommendations {pendingRecs.length > 0 ? `(${pendingRecs.length} pending)` : ""}
              </p>
              <p className="text-xs text-muted-foreground">Approve or reject AI restock proposals</p>
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-muted-foreground" />
        </Link>
      </section>
    </div>
  );
}
