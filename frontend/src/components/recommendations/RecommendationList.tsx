"use client";

import { useEffect, useState } from "react";
import { Check, X, AlertCircle, ClipboardList, TrendingUp } from "lucide-react";
import { api } from "@/api/client";
import type { OutcomeTrackRecord, Recommendation } from "@/types";
import { formatINR } from "@/lib/utils";
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [trackRecord, setTrackRecord] = useState<OutcomeTrackRecord | null>(null);
  const [outcomeFormId, setOutcomeFormId] = useState<string | null>(null);
  const [outcomeStatusInput, setOutcomeStatusInput] = useState<"positive" | "neutral" | "negative">("positive");
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
      <div className="container-responsive py-8">
        <div className="flex flex-col items-center justify-center min-h-[360px]">
          <div className="animate-pulse rounded-full bg-primary/10 p-4 mb-4">
            <ClipboardList className="w-10 h-10 text-primary" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-1">Loading recommendations...</h2>
          <p className="text-sm text-muted-foreground">Fetching prioritized actions for your store</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container-responsive py-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Recommendations</h1>
          <p className="text-sm text-muted-foreground">
            Prioritised business actions with evidence, impact, assumptions, and explicit seller approval.
          </p>
        </div>
        {trackRecord && trackRecord.measured_count > 0 && (
          <div className="flex items-center gap-2 bg-muted/50 border border-border rounded-lg px-3 py-2 text-xs">
            <TrendingUp className="w-4 h-4 text-primary shrink-0" />
            <span>
              <strong>Outcome Memory:</strong> {trackRecord.positive_count}/{trackRecord.measured_count} positive
              {trackRecord.overall_win_rate_pct !== null ? ` (${trackRecord.overall_win_rate_pct}% win-rate)` : ""}
            </span>
          </div>
        )}
      </div>

      {error && (
        <div className="alert alert-destructive mb-6">
          <AlertCircle className="w-4 h-4 mr-2 shrink-0 mt-0.5" />
          <span className="text-sm">{error}</span>
        </div>
      )}

      {recommendations.length === 0 ? (
        <Card className="p-8 text-center">
          <ClipboardList className="w-10 h-10 mx-auto mb-3 text-muted-foreground" />
          <h3 className="text-base font-semibold text-foreground mb-1">No recommendations yet</h3>
          <p className="text-sm text-muted-foreground">
            Ask your Virtual KAM in the voice workspace to diagnose your store and propose actions.
          </p>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 fade-in">
          {recommendations.map((rec) => {
            const isPending = rec.approval_status === "pending" || rec.approval_status === "new";
            const isUpdating = updatingId === rec.id;

            return (
              <Card key={rec.id} className="card-hover flex flex-col justify-between">
                <div>
                  <CardHeader className="flex flex-row items-center justify-between gap-2 pb-3 flex-wrap">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <Badge
                        variant={
                          rec.urgency === "high"
                            ? "destructive"
                            : rec.urgency === "medium"
                            ? "warning"
                            : "default"
                        }
                      >
                        {rec.urgency} urgency
                      </Badge>
                      <Badge
                        variant={
                          rec.confidence === "high"
                            ? "success"
                            : rec.confidence === "medium"
                            ? "warning"
                            : "destructive"
                        }
                      >
                        {rec.confidence} confidence
                      </Badge>
                    </div>
                    <Badge
                      variant={
                        rec.approval_status === "approved"
                          ? "success"
                          : rec.approval_status === "rejected"
                          ? "destructive"
                          : "info"
                      }
                    >
                      {rec.approval_status}
                    </Badge>
                  </CardHeader>

                  <CardContent className="pt-0 space-y-4">
                    <div>
                      <h3 className="font-semibold text-foreground mb-1.5">{rec.title}</h3>
                      <p className="text-sm text-muted-foreground">{rec.problem_or_opportunity}</p>
                    </div>

                    <div className="grid grid-cols-1 gap-2.5">
                      <div className="bg-muted/50 p-3 rounded-lg">
                        <div className="text-xs text-muted-foreground uppercase tracking-wider">
                          Suggested action
                        </div>
                        <div className="text-sm font-medium text-foreground mt-1">
                          {rec.suggested_action}
                        </div>
                      </div>
                      {rec.expected_impact && (
                        <div className="bg-muted/50 p-3 rounded-lg">
                          <div className="text-xs text-muted-foreground uppercase tracking-wider">
                            Expected impact
                          </div>
                          <div className="text-sm font-medium text-foreground mt-1">
                            {rec.expected_impact}
                          </div>
                        </div>
                      )}
                      <div className="grid grid-cols-2 gap-2.5">
                        <div className="bg-muted/50 p-3 rounded-lg">
                          <div className="text-xs text-muted-foreground uppercase tracking-wider">
                            Est. cost
                          </div>
                          <div className="text-sm font-medium text-foreground mt-1">
                            {rec.cost_or_budget != null && rec.cost_or_budget > 0
                              ? formatINR(rec.cost_or_budget)
                              : "₹0 (process fix)"}
                          </div>
                        </div>
                        <div className="bg-muted/50 p-3 rounded-lg">
                          <div className="text-xs text-muted-foreground uppercase tracking-wider">
                            Risk
                          </div>
                          <div className="text-sm font-medium text-foreground mt-1 capitalize">
                            {rec.risk}
                          </div>
                        </div>
                      </div>
                      {rec.assumptions && (
                        <p className="text-xs text-muted-foreground italic">
                          Assumption: {rec.assumptions}
                        </p>
                      )}
                      {rec.outcome_status && rec.outcome_status !== "pending" && (
                        <div className="bg-primary/5 border border-primary/20 p-2.5 rounded-lg text-xs space-y-1">
                          <div className="font-semibold text-foreground flex items-center gap-2">
                            <span>Measured Outcome:</span>
                            <Badge variant={rec.outcome_status === "positive" ? "success" : rec.outcome_status === "negative" ? "destructive" : "secondary"}>
                              {rec.outcome_status}
                            </Badge>
                          </div>
                          {(rec.actual_units_ordered != null || rec.actual_revenue_delta_pct != null || rec.actual_margin_pct != null) && (
                            <div className="text-muted-foreground">
                              {rec.actual_units_ordered != null ? `${rec.actual_units_ordered} units · ` : ""}
                              {rec.actual_revenue_delta_pct != null ? `${rec.actual_revenue_delta_pct > 0 ? "+" : ""}${rec.actual_revenue_delta_pct}% revenue · ` : ""}
                              {rec.actual_margin_pct != null ? `${rec.actual_margin_pct}% margin` : ""}
                            </div>
                          )}
                          {rec.outcome_notes && <div className="text-muted-foreground">{rec.outcome_notes}</div>}
                        </div>
                      )}
                      {outcomeFormId === rec.id && (
                        <div className="bg-muted/60 p-3 rounded-lg space-y-2 text-xs border border-border">
                          <div className="font-medium text-foreground">Record Realized Outcome</div>
                          <select
                            value={outcomeStatusInput}
                            onChange={(e) => setOutcomeStatusInput(e.target.value as "positive" | "neutral" | "negative")}
                            className="w-full h-8 rounded border border-input bg-background px-2"
                          >
                            <option value="positive">Positive (Lifted sales / met margin)</option>
                            <option value="neutral">Neutral</option>
                            <option value="negative">Negative</option>
                          </select>
                          <div className="grid grid-cols-3 gap-1.5">
                            <input
                              type="number"
                              placeholder="Units"
                              value={outcomeUnitsInput}
                              onChange={(e) => setOutcomeUnitsInput(e.target.value)}
                              className="h-8 rounded border border-input bg-background px-2"
                            />
                            <input
                              type="number"
                              step="0.1"
                              placeholder="Rev %"
                              value={outcomeRevDeltaInput}
                              onChange={(e) => setOutcomeRevDeltaInput(e.target.value)}
                              className="h-8 rounded border border-input bg-background px-2"
                            />
                            <input
                              type="number"
                              step="0.1"
                              placeholder="Margin %"
                              value={outcomeMarginInput}
                              onChange={(e) => setOutcomeMarginInput(e.target.value)}
                              className="h-8 rounded border border-input bg-background px-2"
                            />
                          </div>
                          <input
                            type="text"
                            placeholder="Brief outcome notes..."
                            value={outcomeNotesInput}
                            onChange={(e) => setOutcomeNotesInput(e.target.value)}
                            className="w-full h-8 rounded border border-input bg-background px-2"
                          />
                          <div className="flex gap-1.5">
                            <Button size="sm" className="flex-1 h-7 text-xs" disabled={isUpdating} onClick={() => handleSaveOutcome(rec.id)}>
                              Save
                            </Button>
                            <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setOutcomeFormId(null)}>
                              Cancel
                            </Button>
                          </div>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </div>

                <CardFooter className="pt-2 flex items-center gap-2">
                  {isPending ? (
                    <>
                      <Button
                        size="sm"
                        className="flex-1"
                        disabled={isUpdating}
                        onClick={() => handleDecision(rec.id, "approve")}
                      >
                        <Check className="w-4 h-4 mr-1" /> Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="flex-1"
                        disabled={isUpdating}
                        onClick={() => handleDecision(rec.id, "reject")}
                      >
                        <X className="w-4 h-4 mr-1" /> Reject
                      </Button>
                    </>
                  ) : (
                    <div className="w-full flex items-center justify-between text-xs font-medium text-muted-foreground py-1">
                      <span>Decision: <span className="uppercase">{rec.approval_status}</span></span>
                      {rec.approval_status === "approved" && (!rec.outcome_status || rec.outcome_status === "pending") && (
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-7 text-xs"
                          onClick={() => setOutcomeFormId(rec.id)}
                        >
                          Record Outcome
                        </Button>
                      )}
                    </div>
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
