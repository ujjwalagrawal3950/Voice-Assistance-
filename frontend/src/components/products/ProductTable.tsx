"use client";

import { useEffect, useState } from "react";
import { Search, Plus, AlertCircle } from "lucide-react";
import { api } from "@/api/client";
import type { Product } from "@/types";
import { formatINR } from "@/lib/utils";

export function ProductsPage() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<{ q: string; category: string }>({ q: "", category: "" });

  useEffect(() => {
    api.listProducts()
      .then((ps) => { setProducts(ps); setLoading(false) })
      .catch((err) => { setError(err.message); setLoading(false) });
  }, []);

  const categories = [...new Set(products.map((p) => p.category))];

  const filtered = products.filter(
    (p) =>
      p.title.toLowerCase().includes(filter.q.toLowerCase()) ||
      p.sku_code.toLowerCase().includes(filter.q.toLowerCase())
  ).filter((p) => (!filter.category || p.category === filter.category));

  if (loading) {
    return (
      <div className="container-responsive py-8">
        <div className="flex flex-col items-center justify-center min-h-[400px]">
          <div className="animate-pulse rounded-full bg-primary/10 p-4 mb-4">
            <Plus className="w-12 h-12 text-primary" />
          </div>
          <h2 className="text-xl font-semibold text-foreground mb-2">Loading products...</h2>
          <p className="text-sm text-muted-foreground">Fetching your catalogue</p>
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
          <h2 className="text-xl font-semibold text-foreground mb-2">Unable to load products</h2>
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

  return (
    <div className="container-responsive py-6">
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Products</h1>
          <p className="text-sm text-muted-foreground">
            {filtered.length} of {products.length} SKUs in your catalogue
          </p>
        </div>
        <button
          className="btn-outline"
          onClick={() => {
            // Placeholder for add product
            alert("Add product feature coming soon");
          }}
        >
          <Plus className="w-4 h-4 mr-2" /> Add product
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground w-4 h-4" />
          <input
            className="input pl-10"
            placeholder="Search SKU or title…"
            value={filter.q}
            onChange={(e) => setFilter({ ...filter, q: e.target.value })}
          />
        </div>
        <select
          className="input"
          value={filter.category}
          onChange={(e) => setFilter({ ...filter, category: e.target.value })}
        >
          <option value="">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <div className="table fade-in">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="table-header">
              <th className="px-4 py-3 font-medium">SKU</th>
              <th className="px-4 py-3 font-medium">Title</th>
              <th className="px-4 py-3 font-medium">Category</th>
              <th className="px-4 py-3 font-medium">Segment &amp; Season</th>
              <th className="px-4 py-3 font-medium text-right">Lead Time</th>
              <th className="px-4 py-3 font-medium text-right">Price</th>
              <th className="px-4 py-3 font-medium text-right">Stock</th>
              <th className="px-4 py-3 font-medium text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {filtered.map((p) => (
              <tr key={p.id} className="hover:bg-accent/50 transition-colors">
                <td className="px-4 py-3 font-mono text-xs font-medium text-muted-foreground">
                  {p.sku_code}
                </td>
                <td className="px-4 py-3 font-medium text-foreground">{p.title}</td>
                <td className="px-4 py-3 text-muted-foreground">{p.category}</td>
                <td className="px-4 py-3 text-xs text-muted-foreground">
                  <span className="capitalize">{p.demand_segment || "discretionary"}</span>
                  {p.seasonality_tag && p.seasonality_tag !== "evergreen" && (
                    <span className="ml-1.5 inline-flex items-center px-1.5 py-0.5 rounded bg-primary/10 text-primary font-medium capitalize">
                      {p.seasonality_tag}
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-right text-xs text-muted-foreground">
                  {p.supplier_lead_time_days}d
                </td>
                <td className="px-4 py-3 text-right text-foreground font-medium">
                  {formatINR(p.selling_price)}
                </td>
                <td className="px-4 py-3 text-right text-foreground">
                  {p.current_stock.toLocaleString("en-IN")}
                </td>
                <td className="px-4 py-3 text-center">
                  {p.current_stock <= 0 ? (
                    <span className="badge badge-destructive">Out of stock</span>
                  ) : p.current_stock < 20 ? (
                    <span className="badge badge-warning">Low stock</span>
                  ) : (
                    <span className="badge badge-success">In stock</span>
                  )}
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">
                  <AlertCircle className="w-6 h-6 mx-auto mb-2 opacity-50" />
                  <p>No products match your filters.</p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-6 pt-4 border-t border-border text-xs text-muted-foreground fade-in">
        Prices and stock in INR paise. Cover days and per-SKU KPIs come from the KAM agent.
      </div>
    </div>
  );
}
