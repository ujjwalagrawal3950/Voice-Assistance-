"use client";

import { useState, useEffect } from "react";
import { Save, AlertCircle, CheckCircle } from "lucide-react";
import { api } from "@/api/client";
import type { Seller } from "@/types";
import { formatINR } from "@/lib/utils";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function toPctDisplay(fraction: number | undefined | null): string | number {
  if (fraction == null) return "";
  return Math.round(fraction * 1000) / 10;
}

export function SettingsPage() {
  const [seller, setSeller] = useState<Seller | null>(null);
  const [draft, setDraft] = useState<Partial<Seller>>({});
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [sellerLoading, setSellerLoading] = useState(true);

  useEffect(() => {
    api
      .getSellerProfile()
      .then((s) => setSeller(s))
      .catch(() => {})
      .finally(() => setSellerLoading(false));
  }, []);

  const handleChange = (key: keyof Partial<Seller>, value: string | number | undefined) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setStatus("idle");
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!seller) return;
    setSaving(true);
    setStatus("saving");
    try {
      const updated = await api.updateSellerProfile({ ...draft });
      setSeller(updated);
      setDraft({});
      setStatus("saved");
      setTimeout(() => setStatus("idle"), 3000);
    } catch {
      setStatus("error");
    } finally {
      setSaving(false);
    }
  };

  const effectiveBudgetPaise =
    draft.available_replenishment_budget ?? seller?.available_replenishment_budget ?? 0;
  const effectiveBudgetRupees = Math.round(effectiveBudgetPaise / 100);
  const effectiveRisk = draft.risk_tolerance ?? seller?.risk_tolerance ?? "medium";
  const effectivePriority =
    draft.growth_vs_margin_priority ?? seller?.growth_vs_margin_priority ?? "balanced";
  const effectiveMargin = draft.target_margin ?? seller?.target_margin ?? 0.25;
  const effectiveGrowth = draft.target_growth ?? seller?.target_growth;
  const effectiveStretch = draft.max_credit_stretch_pct ?? seller?.max_credit_stretch_pct ?? 0.15;
  const hasUnsaved = Object.keys(draft).length > 0;

  return (
    <div className="container-responsive py-6 sm:py-8 space-y-6 max-w-4xl fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">Store Settings</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Set your restock budget and margin targets used by your AI manager.
          </p>
        </div>
        {hasUnsaved && (
          <span className="text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full w-fit">
            Unsaved changes
          </span>
        )}
      </div>

      {!seller && sellerLoading ? (
        <div className="space-y-4">
          <div className="h-24 rounded-xl bg-white border border-border animate-pulse" />
          <div className="h-72 rounded-xl bg-white border border-border animate-pulse" />
        </div>
      ) : (
        <>
          {/* Clear Current Guardrail Summary */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="kpi-card">
              <p className="text-xs font-medium text-muted-foreground">Restock Budget Cap</p>
              <p className="text-2xl font-semibold text-foreground tabular-nums mt-1">
                {formatINR(effectiveBudgetPaise)}
              </p>
            </div>
            <div className="kpi-card">
              <p className="text-xs font-medium text-muted-foreground">Minimum Margin Goal</p>
              <p className="text-2xl font-semibold text-foreground tabular-nums mt-1">
                {toPctDisplay(effectiveMargin)}%
              </p>
            </div>
            <div className="kpi-card">
              <p className="text-xs font-medium text-muted-foreground">Buying Strategy</p>
              <p className="text-base font-semibold text-foreground capitalize mt-2">
                {effectiveRisk} risk · {effectivePriority} focus
              </p>
            </div>
          </div>

          <form onSubmit={handleSave} className="space-y-5">
            <Card>
              <CardHeader className="pb-3 border-b border-border/60">
                <CardTitle className="text-base">Store Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 pt-4">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div className="space-y-1.5">
                    <Label>Store name</Label>
                    <Input
                      value={draft.display_name ?? seller?.display_name ?? ""}
                      onChange={(e) => handleChange("display_name", e.target.value)}
                      placeholder="e.g., Rajesh Kirana Store"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>Main category</Label>
                    <Input
                      value={draft.business_category ?? seller?.business_category ?? ""}
                      onChange={(e) => handleChange("business_category", e.target.value)}
                      placeholder="e.g., Women's Ethnic & Footwear"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>State / Region</Label>
                    <Input
                      value={draft.state ?? seller?.state ?? ""}
                      onChange={(e) => handleChange("state", e.target.value)}
                      placeholder="e.g., Maharashtra"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label>City</Label>
                    <Input
                      value={draft.city ?? seller?.city ?? ""}
                      onChange={(e) => handleChange("city", e.target.value)}
                      placeholder="e.g., Pune"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label>Main business goal</Label>
                  <Input
                    value={draft.business_goals ?? seller?.business_goals ?? ""}
                    onChange={(e) => handleChange("business_goals", e.target.value)}
                    placeholder="e.g., Grow revenue 20% before Diwali while keeping margin above 25%"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3 border-b border-border/60">
                <CardTitle className="text-base">Budget &amp; Risk Rules</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-4">
                <div className="space-y-1.5">
                  <Label>Available restock budget (₹)</Label>
                  <Input
                    type="number"
                    min={0}
                    step={500}
                    value={effectiveBudgetRupees || ""}
                    onChange={(e) =>
                      handleChange(
                        "available_replenishment_budget",
                        e.target.value === "" ? 0 : Math.max(0, Math.round(Number(e.target.value) * 100))
                      )
                    }
                    placeholder="40000"
                    className="tabular-nums"
                  />
                  <span className="text-xs text-muted-foreground">Total cash available in Rupees</span>
                </div>

                <div className="space-y-1.5">
                  <Label>Minimum target margin (%)</Label>
                  <Input
                    type="number"
                    step="0.5"
                    min={0}
                    max={100}
                    value={toPctDisplay(effectiveMargin)}
                    onChange={(e) =>
                      handleChange(
                        "target_margin",
                        e.target.value === ""
                          ? undefined
                          : Math.max(0, Math.min(1, Number((Number(e.target.value) / 100).toFixed(4))))
                      )
                    }
                    placeholder="25"
                    className="tabular-nums"
                  />
                  <span className="text-xs text-muted-foreground">Example: 25 means 25% profit</span>
                </div>

                <div className="space-y-1.5">
                  <Label>Sales growth goal (%)</Label>
                  <Input
                    type="number"
                    step="1"
                    min={0}
                    max={200}
                    value={toPctDisplay(effectiveGrowth)}
                    onChange={(e) =>
                      handleChange(
                        "target_growth",
                        e.target.value === ""
                          ? undefined
                          : Math.max(0, Number((Number(e.target.value) / 100).toFixed(4)))
                      )
                    }
                    placeholder="20"
                    className="tabular-nums"
                  />
                  <span className="text-xs text-muted-foreground">Example: 20 means +20% growth</span>
                </div>

                <div className="space-y-1.5">
                  <Label>Risk comfort level</Label>
                  <select
                    value={effectiveRisk}
                    onChange={(e) => handleChange("risk_tolerance", e.target.value)}
                    className="input"
                  >
                    <option value="low">Low (Conservative cash spending)</option>
                    <option value="medium">Medium (Balanced restocking)</option>
                    <option value="high">High (Aggressive festival buying)</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label>Priority balance</Label>
                  <select
                    value={effectivePriority}
                    onChange={(e) => handleChange("growth_vs_margin_priority", e.target.value)}
                    className="input"
                  >
                    <option value="margin">Protect Margin First</option>
                    <option value="balanced">Balanced (Sales &amp; Margin)</option>
                    <option value="growth">Grow Sales Volume First</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label>Supplier relationship</Label>
                  <select
                    value={draft.supplier_relationship_strength ?? seller?.supplier_relationship_strength ?? "standard"}
                    onChange={(e) => handleChange("supplier_relationship_strength", e.target.value)}
                    className="input"
                  >
                    <option value="strong">Strong (Short credit possible)</option>
                    <option value="standard">Standard (Normal terms)</option>
                    <option value="new">New Supplier (Advance payment)</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <Label>Festival credit buffer (%)</Label>
                  <Input
                    type="number"
                    step="5"
                    min={0}
                    max={100}
                    value={toPctDisplay(effectiveStretch)}
                    onChange={(e) =>
                      handleChange(
                        "max_credit_stretch_pct",
                        e.target.value === ""
                          ? 0
                          : Math.max(0, Math.min(1, Number((Number(e.target.value) / 100).toFixed(4))))
                      )
                    }
                    placeholder="15"
                    className="tabular-nums"
                  />
                  <span className="text-xs text-muted-foreground">Extra budget buffer allowed (%)</span>
                </div>

                <div className="space-y-1.5">
                  <Label>Target stock cover (days)</Label>
                  <Input
                    type="number"
                    min={1}
                    value={draft.preferred_stock_cover_days ?? seller?.preferred_stock_cover_days ?? ""}
                    onChange={(e) => handleChange("preferred_stock_cover_days", Number(e.target.value) || 14)}
                    placeholder="14"
                    className="tabular-nums"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label>Warehouse storage limit (units)</Label>
                  <Input
                    type="number"
                    min={0}
                    value={draft.storage_capacity ?? seller?.storage_capacity ?? ""}
                    onChange={(e) =>
                      handleChange(
                        "storage_capacity",
                        e.target.value === "" ? undefined : Number(e.target.value)
                      )
                    }
                    placeholder="5000"
                    className="tabular-nums"
                  />
                </div>
              </CardContent>
            </Card>

            <CardFooter className="flex items-center gap-3 px-0 pt-1">
              <Button type="submit" disabled={saving || !hasUnsaved}>
                <Save className="w-4 h-4 mr-2" />
                {saving ? "Saving..." : "Save Settings"}
              </Button>
              {status === "saved" && (
                <div className="flex items-center gap-1.5 text-sm text-emerald-600 font-medium">
                  <CheckCircle className="w-4 h-4" /> Saved
                </div>
              )}
              {status === "error" && (
                <div className="flex items-center gap-1.5 text-sm text-red-600 font-medium">
                  <AlertCircle className="w-4 h-4" /> Could not save changes
                </div>
              )}
            </CardFooter>
          </form>
        </>
      )}
    </div>
  );
}
