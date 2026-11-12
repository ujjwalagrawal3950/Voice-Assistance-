"use client";

import { useEffect, useMemo, useState } from "react";
import { Check, X, AlertCircle, ClipboardList, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { api } from "@/api/client";
import type { OutcomeTrackRecord, Recommendation } from "@/types";
import { cn, formatINR, formatNumber } from "@/lib/utils";
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type StatusTab = "all" | "pending" | "approved" | "rejected";

export function RecommendationsPage() {
  const navigate = useNavigate();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [trackRecord, setTrackRecord] = useState<OutcomeTrackRecord | null>(null);
  const [activeTab, setActiveTab] = useState<StatusTab>("all");
  const [outcomeFormId, setOutcomeFormId] = useState<string | null>(null);
  const [outcomeStatusInput, setOutcomeStatusInput] = useState<"positive" | "neutral" | "negative">(
    "positive"
  );
  const [outcomeUnitsInput, setOutcomeUnitsInput] = useState<string>("");
  const [outcomeRevDeltaInput, setOutcomeRevDeltaInput] = useState<string>("");
  const [outcomeMarginInput, setOutcomeMarginInput] = useState<string>("");
  const [outcomeNotesInput, setOutcomeNotesInput] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);

  const loadRecommendations = () => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.listRecommendations(),
      api.getOutcomeTrackRecord().catch(() => null),
    ])
      .then(([rows, tr]) => {
        setRecommendations(rows);
        setTrackRecord(tr);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load recommendations"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRecommendations();
    const onUpdated = () => loadRecommendations();
    window.addEventListener("kam:recommendations-updated", onUpdated);
    return () => window.removeEventListener("kam:recommendations-updated", onUpdated);
  }, []);

  const counts = useMemo(() => {
    let pending = 0;
    let approved = 0;
    let rejected = 0;
    for (const r of recommendations) {
      if (r.approval_status === "approved") approved += 1;
      else if (r.approval_status === "rejected") rejected += 1;
      else pending += 1;
    }
    return { all: recommendations.length, pending, approved, rejected };
  }, [recommendations]);

  const visibleRecs = useMemo(() => {
    return recommendations.filter((r) => {
      if (activeTab === "pending") {
        return (
          r.approval_status === "pending" ||
          r.approval_status === "new" ||
          r.approval_status === "viewed"
        );
      }
      if (activeTab === "approved") return r.approval_status === "approved";
      if (activeTab === "rejected") return r.approval_status === "rejected";
      return true;
    });
  }, [recommendations, activeTab]);

  const handleDecision = async (recId: string, action: "approve" | "reject") => {
    setUpdatingId(recId);
    try {
      const updated = await api.approveRecommendation(recId, action);
      setRecommendations((prev) => prev.map((r) => (r.id === recId ? updated : r)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update recommendation");
    } finally {
      setUpdatingId(null);
    }
  };

  const handleSaveOutcome = async (recId: string) => {
    setUpdatingId(recId);
    try {
      const updated = await api.recordOutcome(recId, {
        outcome_status: outcomeStatusInput,
        actual_units_ordered: outcomeUnitsInput ? Number(outcomeUnitsInput) : undefined,
        actual_revenue_delta_pct: outcomeRevDeltaInput ? Number(outcomeRevDeltaInput) : undefined,
        actual_margin_pct: outcomeMarginInput ? Number(outcomeMarginInput) : undefined,
        outcome_notes: outcomeNotesInput || undefined,
      });
      setRecommendations((prev) => prev.map((r) => (r.id === recId ? updated : r)));
      const freshTrack = await api.getOutcomeTrackRecord().catch(() => null);
      if (freshTrack) setTrackRecord(freshTrack);
      setOutcomeFormId(null);
      setOutcomeUnitsInput("");
      setOutcomeRevDeltaInput("");
      setOutcomeMarginInput("");
      setOutcomeNotesInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save outcome");
    } finally {
      setUpdatingId(null);
    }
  };

  if (loading) {
    return (
      <div className="container-responsive py-8 space-y-5">
        <div className="h-14 rounded-xl bg-white border border-border animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-64 rounded-xl bg-white border border-border animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="container-responsive py-6 sm:py-8 space-y-6 fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Action Recommendations
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Review AI proposals with exact estimated costs before taking action.
          </p>
        </div>

        {trackRecord && trackRecord.measured_count > 0 && (
          <div className="rounded-lg border border-border bg-white px-4 py-2 text-xs tabular-nums">
            <span className="text-muted-foreground">Past outcome track record: </span>
            <strong className="font-semibold text-foreground">
              {trackRecord.positive_count} of {trackRecord.measured_count} positive
            </strong>
            {trackRecord.overall_win_rate_pct !== null && (
              <span className="text-emerald-600 font-semibold ml-1.5">
                ({trackRecord.overall_win_rate_pct}% win rate)
              </span>
            )}
          </div>
        )}
      </div>

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="inline-flex rounded-lg border border-border bg-white p-0.5">
          {(
            [
              { id: "all", label: "All", count: counts.all },
              { id: "pending", label: "Pending Review", count: counts.pending },
              { id: "approved", label: "Approved", count: counts.approved },
              { id: "rejected", label: "Rejected", count: counts.rejected },
            ] as const
          ).map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                "px-3 py-1.5 rounded-md text-xs font-medium transition-colors cursor-pointer tabular-nums",
                activeTab === tab.id
                  ? "bg-slate-900 text-white"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {tab.label} ({tab.count})
            </button>
          ))}
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={() =>
            navigate(
              "/chat?prompt=" +
                encodeURIComponent(
                  "What are my pending recommendations and which one should I approve first?"
                )
            )
          }
        >
          <Sparkles className="w-3.5 h-3.5 mr-1.5 text-primary" />
          Discuss with AI
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {visibleRecs.length === 0 ? (
        <Card className="p-12 text-center space-y-2">
          <ClipboardList className="w-7 h-7 mx-auto text-muted-foreground" />
          <p className="text-base font-medium text-foreground">
            {activeTab === "all" ? "No recommendations yet" : `No ${activeTab} recommendations`}
          </p>
          <p className="text-sm text-muted-foreground">
            Ask your AI KAM about low stock or high cancellations to generate new plans.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {visibleRecs.map((rec) => {
            const isApproved = rec.approval_status === "approved";
            const isRejected = rec.approval_status === "rejected";
            const isPending = !isApproved && !isRejected;
            const busy = updatingId === rec.id;

            return (
              <Card key={rec.id} className="flex flex-col">
                <CardHeader className="pb-3 border-b border-border/60 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={isApproved ? "success" : isRejected ? "destructive" : "secondary"}
                      >
                        {isApproved ? "Approved" : isRejected ? "Rejected" : "Pending"}
                      </Badge>
                      <span className="text-xs text-muted-foreground capitalize">
                        {rec.urgency} priority · {rec.risk} risk
                      </span>
                    </div>

                    <span className="text-sm font-semibold text-foreground tabular-nums">
                      {rec.cost_or_budget != null && rec.cost_or_budget > 0
                        ? formatINR(rec.cost_or_budget)
                        : "₹0 cost"}
                    </span>
                  </div>

                  <h3 className="text-base font-semibold text-foreground leading-snug">
                    {rec.title}
                  </h3>
                </CardHeader>

                <CardContent className="space-y-3.5 pt-4 flex-1 text-sm">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Why it matters</p>
                    <p className="text-foreground mt-0.5 leading-relaxed">
                      {rec.problem_or_opportunity}
                    </p>
                  </div>

                  <div>
                    <p className="text-xs font-medium text-muted-foreground">Suggested action</p>
                    <p className="text-foreground font-medium mt-0.5 leading-relaxed">
                      {rec.suggested_action}
                    </p>
                  </div>

                  {rec.expected_impact && (
                    <div className="rounded-lg bg-emerald-50/70 border border-emerald-200/70 px-3.5 py-2.5">
                      <p className="text-xs font-medium text-emerald-800">Expected impact</p>
                      <p className="text-sm font-medium text-emerald-950 mt-0.5">
                        {rec.expected_impact}
                      </p>
                    </div>
                  )}

                  {rec.assumptions && (
                    <p className="text-xs text-muted-foreground">
                      Note: {rec.assumptions}
                    </p>
                  )}

                  {rec.outcome_status && rec.outcome_status !== "pending" && (
                    <div className="rounded-lg bg-muted/40 border border-border px-3.5 py-2.5 text-xs space-y-1">
                      <div className="flex items-center gap-2 font-medium text-foreground">
                        <span>Recorded outcome:</span>
                        <Badge
                          variant={
                            rec.outcome_status === "positive"
                              ? "success"
                              : rec.outcome_status === "negative"
                              ? "destructive"
                              : "secondary"
                          }
                        >
                          {rec.outcome_status}
                        </Badge>
                      </div>
                      {(rec.actual_units_ordered != null ||
                        rec.actual_revenue_delta_pct != null ||
                        rec.actual_margin_pct != null) && (
                        <p className="text-muted-foreground tabular-nums">
                          {rec.actual_units_ordered != null
                            ? `${formatNumber(rec.actual_units_ordered)} units`
                            : ""}
                          {rec.actual_revenue_delta_pct != null
                            ? ` · ${rec.actual_revenue_delta_pct > 0 ? "+" : ""}${
                                rec.actual_revenue_delta_pct
                              }% revenue`
                            : ""}
                          {rec.actual_margin_pct != null
                            ? ` · ${rec.actual_margin_pct}% margin`
                            : ""}
                        </p>
                      )}
                      {rec.outcome_notes && (
                        <p className="text-muted-foreground">{rec.outcome_notes}</p>
                      )}
                    </div>
                  )}

                  {outcomeFormId === rec.id && (
                    <div className="rounded-lg bg-muted/40 border border-border p-3.5 space-y-2.5 text-xs">
                      <p className="font-semibold text-foreground">Record Actual Outcome</p>
                      <select
                        value={outcomeStatusInput}
                        onChange={(e) =>
                          setOutcomeStatusInput(e.target.value as "positive" | "neutral" | "negative")
                        }
                        className="input h-8 text-xs"
                      >
                        <option value="positive">Positive (Helped sales or margin)</option>
                        <option value="neutral">Neutral</option>
                        <option value="negative">Negative</option>
                      </select>
                      <div className="grid grid-cols-3 gap-2">
                        <input
                          type="number"
                          placeholder="Units ordered"
                          value={outcomeUnitsInput}
                          onChange={(e) => setOutcomeUnitsInput(e.target.value)}
                          className="input h-8 text-xs"
                        />
                        <input
                          type="number"
                          placeholder="Sales change %"
                          value={outcomeRevDeltaInput}
                          onChange={(e) => setOutcomeRevDeltaInput(e.target.value)}
                          className="input h-8 text-xs"
                        />
                        <input
                          type="number"
                          placeholder="Margin %"
                          value={outcomeMarginInput}
                          onChange={(e) => setOutcomeMarginInput(e.target.value)}
                          className="input h-8 text-xs"
                        />
                      </div>
                      <input
                        type="text"
                        placeholder="Optional notes"
                        value={outcomeNotesInput}
                        onChange={(e) => setOutcomeNotesInput(e.target.value)}
                        className="input h-8 text-xs"
                      />
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          disabled={busy}
                          onClick={() => handleSaveOutcome(rec.id)}
                          className="h-8 text-xs"
                        >
                          Save Result
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setOutcomeFormId(null)}
                          className="h-8 text-xs"
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>

                <CardFooter className="border-t border-border/60 pt-3.5 flex items-center justify-between gap-2">
                  {isPending ? (
                    <div className="flex items-center gap-2 w-full">
                      <Button
                        size="sm"
                        disabled={busy}
                        onClick={() => handleDecision(rec.id, "approve")}
                        className="flex-1 h-9"
                      >
                        <Check className="w-4 h-4 mr-1.5" />
                        {busy ? "Saving..." : "Approve Plan"}
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={busy}
                        onClick={() => handleDecision(rec.id, "reject")}
                        className="h-9 px-3.5 text-muted-foreground hover:text-red-600"
                      >
                        <X className="w-4 h-4 mr-1" />
                        Reject
                      </Button>
                    </div>
                  ) : isApproved && outcomeFormId !== rec.id ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setOutcomeFormId(rec.id)}
                      className="h-8 text-xs"
                    >
                      {rec.outcome_status && rec.outcome_status !== "pending"
                        ? "Update Outcome"
                        : "Record Outcome"}
                    </Button>
                  ) : (
                    <span className="text-xs text-muted-foreground">
                      {isRejected ? "Marked as rejected" : ""}
                    </span>
                  )}
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
