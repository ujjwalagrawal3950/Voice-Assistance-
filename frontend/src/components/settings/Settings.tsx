"use client";

import { useState, useEffect } from "react";
import { Save, AlertCircle, CheckCircle } from "lucide-react";
import { api } from "@/api/client";
import type { Seller } from "@/types";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function SettingsPage() {
  const [seller, setSeller] = useState<Seller | null>(null);
  const [draft, setDraft] = useState<Partial<Seller>>({});
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [sellerLoading, setSellerLoading] = useState(true);

  useEffect(() => {
    api.getSellerProfile()
      .then((s) => setSeller(s))
      .catch(() => {})
      .finally(() => setSellerLoading(false));
  }, []);

  const handleChange = (key: keyof Partial<Seller>, value: string | number | undefined) => {
    setDraft((d) => ({ ...d, [key]: value }));
    setStatus('idle');
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!seller) return;
    setSaving(true);
    setStatus('saving');
    try {
      const updated = await api.updateSellerProfile({
        ...draft,
      });
      setSeller(updated);
      setDraft({});
      setStatus('saved');
      setTimeout(() => setStatus('idle'), 3000);
    } catch {
      setStatus('error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="container-responsive py-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Seller Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure your business constraints. These shape every recommendation
            the Virtual KAM makes.
          </p>
        </div>
      </div>

      {!seller && sellerLoading ? (
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="animate-pulse rounded-full bg-primary/10 p-4 mb-4">
            <Save className="w-12 h-12 text-primary" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2">Loading seller profile…</h2>
        </div>
      ) : (
        <form onSubmit={handleSave} className="space-y-6 fade-in">
          <Card>
            <CardHeader>
              <CardTitle>Business Profile</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Display name</Label>
                  <Input
                    className="h-auto p-2"
                    value={draft.display_name ?? seller?.display_name ?? ""}
                    onChange={(e) => handleChange('display_name', e.target.value)}
                    placeholder="e.g., Rajesh Kirana Store"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Business category</Label>
                  <Input
                    className="h-auto p-2"
                    value={draft.business_category ?? seller?.business_category ?? ""}
                    onChange={(e) => handleChange('business_category', e.target.value)}
                    placeholder="e.g., General Store"
                  />
                </div>
                <div className="space-y-2">
                  <Label>State / region</Label>
                  <Input
                    className="h-auto p-2"
                    value={draft.state ?? seller?.state ?? ""}
                    onChange={(e) => handleChange('state', e.target.value)}
                    placeholder="e.g., Maharashtra"
                  />
                </div>
                <div className="space-y-2">
                  <Label>City</Label>
                  <Input
                    className="h-auto p-2"
                    value={draft.city ?? seller?.city ?? ""}
                    onChange={(e) => handleChange('city', e.target.value)}
                    placeholder="e.g., Pune"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Business goals</Label>
                <Input
                  className="h-auto p-2"
                  value={draft.business_goals ?? seller?.business_goals ?? ""}
                  onChange={(e) => handleChange('business_goals', e.target.value)}
                  placeholder="e.g., Grow revenue 20% before Diwali while keeping margin above 25%"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Constraints & Goals</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Target margin</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={draft.target_margin ?? seller?.target_margin ?? ""}
                  onChange={(e) => handleChange('target_margin', e.target.value)}
                  placeholder="0.25"
                />
                <span className="text-xs text-muted-foreground">as fraction (0.25 = 25%)</span>
              </div>
              <div className="space-y-2">
                <Label>Target growth</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={draft.target_growth ?? seller?.target_growth ?? ""}
                  onChange={(e) => handleChange('target_growth', e.target.value)}
                  placeholder="0.20"
                />
                <span className="text-xs text-muted-foreground">as fraction (0.20 = 20%)</span>
              </div>
              <div className="space-y-2">
                <Label>Risk tolerance</Label>
                <select
                  value={draft.risk_tolerance ?? seller?.risk_tolerance ?? "medium"}
                  onChange={(e) => handleChange("risk_tolerance", e.target.value)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm text-foreground"
                >
                  <option value="low">Low (Upfront cash only · conservative cover)</option>
                  <option value="medium">Medium (Balanced cash & restock speed)</option>
                  <option value="high">High (Aggressive festival / growth capture)</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Growth vs Margin Priority</Label>
                <select
                  value={draft.growth_vs_margin_priority ?? seller?.growth_vs_margin_priority ?? "balanced"}
                  onChange={(e) => handleChange("growth_vs_margin_priority", e.target.value)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm text-foreground"
                >
                  <option value="margin">Margin First (Protect ≥25% margin floor)</option>
                  <option value="balanced">Balanced (Steady sales & healthy margin)</option>
                  <option value="growth">Growth First (Capture festival volume & rank)</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Supplier Relationship</Label>
                <select
                  value={draft.supplier_relationship_strength ?? seller?.supplier_relationship_strength ?? "standard"}
                  onChange={(e) => handleChange("supplier_relationship_strength", e.target.value)}
                  className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm text-foreground"
                >
                  <option value="strong">Strong (Short credit / priority dispatch)</option>
                  <option value="standard">Standard (Net-0 / normal lead times)</option>
                  <option value="new">New Supplier (Strict advance terms)</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>Max Credit Stretch (fraction)</Label>
                <Input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  value={draft.max_credit_stretch_pct ?? seller?.max_credit_stretch_pct ?? 0.15}
                  onChange={(e) => handleChange("max_credit_stretch_pct", Number(e.target.value) || 0)}
                  placeholder="0.15"
                />
                <span className="text-xs text-muted-foreground">0.25 = up to +25% festival credit buffer</span>
              </div>
              <div className="space-y-2">
                <Label>Preferred stock cover (days)</Label>
                <Input
                  type="number"
                  value={draft.preferred_stock_cover_days ?? seller?.preferred_stock_cover_days ?? ""}
                  onChange={(e) => handleChange('preferred_stock_cover_days', Number(e.target.value) || 14)}
                  placeholder="14"
                />
              </div>
              <div className="space-y-2">
                <Label>Replenishment budget (₹)</Label>
                <Input
                  type="number"
                  value={draft.available_replenishment_budget ?? seller?.available_replenishment_budget ?? ""}
                  onChange={(e) => handleChange('available_replenishment_budget', Number(e.target.value) || 0)}
                  placeholder="4000000"
                />
                <span className="text-xs text-muted-foreground">in paise</span>
              </div>
              <div className="space-y-2">
                <Label>Storage capacity (units)</Label>
                <Input
                  type="number"
                  value={draft.storage_capacity ?? seller?.storage_capacity ?? ""}
                  onChange={(e) => handleChange('storage_capacity', e.target.value === "" ? undefined : Number(e.target.value))}
                  placeholder="5000"
                />
              </div>
            </CardContent>
          </Card>

          <CardFooter className="flex items-center gap-3 pt-6 px-0">
            <Button type="submit" disabled={saving || Object.keys(draft).length === 0}>
              {saving ? <Save size={16} strokeWidth={2} className="mr-2 animate-spin" /> : <Save size={16} strokeWidth={2} className="mr-2" />}
              Save changes
            </Button>
            {status === "saved" && (
              <div className="flex items-center gap-1 text-success font-medium">
                <CheckCircle size={14} strokeWidth={2} /> Saved
              </div>
            )}
            {status === "error" && (
              <div className="flex items-center gap-1 text-destructive font-medium">
                <AlertCircle size={14} strokeWidth={2} /> Save failed
              </div>
            )}
          </CardFooter>
        </form>
      )}
    </div>
  );
}

export const Settings = SettingsPage;
