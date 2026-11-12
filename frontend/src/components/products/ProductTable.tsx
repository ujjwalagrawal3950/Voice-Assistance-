"use client";

import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertCircle, Package, Search } from "lucide-react";
import { api } from "@/api/client";
import type { Product } from "@/types";
import { cn, formatINR, formatNumber } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

type StockFilter = "all" | "oos" | "low" | "healthy";

export function ProductsPage() {
  const navigate = useNavigate();
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<{ q: string; category: string; stock: StockFilter }>({
    q: "",
    category: "",
    stock: "all",
  });

  useEffect(() => {
    api
      .listProducts()
      .then((ps) => {
        setProducts(ps);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const categories = useMemo(
    () => [...new Set(products.map((p) => p.category))].sort(),
    [products]
  );

  const counts = useMemo(() => {
    let oos = 0;
    let low = 0;
    let healthy = 0;
    for (const p of products) {
      if (p.current_stock <= 0) oos += 1;
      else if (p.current_stock < 20) low += 1;
      else healthy += 1;
    }
    return { total: products.length, oos, low, healthy };
  }, [products]);

  const filtered = useMemo(() => {
    const query = filter.q.trim().toLowerCase();
    return products.filter((p) => {
      if (
        query &&
        !p.title.toLowerCase().includes(query) &&
        !p.sku_code.toLowerCase().includes(query) &&
        !p.category.toLowerCase().includes(query)
      ) {
        return false;
      }
      if (filter.category && p.category !== filter.category) return false;
      if (filter.stock === "oos" && p.current_stock > 0) return false;
      if (filter.stock === "low" && (p.current_stock <= 0 || p.current_stock >= 20)) return false;
      if (filter.stock === "healthy" && p.current_stock < 20) return false;
      return true;
    });
  }, [products, filter]);

  if (loading) {
    return (
      <div className="container-responsive py-8 space-y-4">
        <div className="h-14 rounded-xl bg-white border border-border animate-pulse" />
        <div className="h-96 rounded-xl bg-white border border-border animate-pulse" />
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
            <h2 className="text-lg font-semibold text-foreground">Unable to load products</h2>
            <p className="text-sm text-muted-foreground mt-1">{error}</p>
          </div>
          <Button onClick={() => window.location.reload()}>Retry</Button>
        </Card>
      </div>
    );
  }

  const filterTabs: Array<{ key: StockFilter; label: string; count: number }> = [
    { key: "all", label: "All Products", count: counts.total },
    { key: "oos", label: "Out of Stock", count: counts.oos },
    { key: "low", label: "Low Stock (<20)", count: counts.low },
    { key: "healthy", label: "Healthy Stock", count: counts.healthy },
  ];

  return (
    <div className="container-responsive py-6 sm:py-8 space-y-6 fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Product Inventory
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5 tabular-nums">
            {counts.total} products tracked · {counts.oos} out of stock · {counts.low} running low
          </p>
        </div>

        <Button
          size="sm"
          onClick={() =>
            navigate(
              `/chat?prompt=${encodeURIComponent(
                "Which out-of-stock products should I restock first within my available budget?"
              )}`
            )
          }
        >
          Plan Restocking with AI
        </Button>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-1.5">
          {filterTabs.map((t) => (
            <button
              key={t.key}
              type="button"
              onClick={() => setFilter((f) => ({ ...f, stock: t.key }))}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors cursor-pointer tabular-nums",
                filter.stock === t.key
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white text-muted-foreground border-border hover:text-foreground"
              )}
            >
              {t.label} ({t.count})
            </button>
          ))}
        </div>

        <div className="flex flex-col sm:flex-row gap-2.5 sm:items-center">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={filter.q}
              onChange={(e) => setFilter((f) => ({ ...f, q: e.target.value }))}
              placeholder="Search name or SKU..."
              className="input pl-9 h-9 text-xs sm:w-56"
            />
          </div>

          <select
            value={filter.category}
            onChange={(e) => setFilter((f) => ({ ...f, category: e.target.value }))}
            className="input h-9 text-xs sm:w-44"
            aria-label="Filter by category"
          >
            <option value="">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Clean Readable Product Table */}
      <div className="table">
        {filtered.length === 0 ? (
          <div className="py-14 px-6 text-center space-y-2">
            <Package className="w-6 h-6 mx-auto text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">No matching products</p>
            <p className="text-xs text-muted-foreground">Try clearing your search or filter tabs.</p>
          </div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="table-header">
                <th className="py-3 px-4">Product</th>
                <th className="py-3 px-4">Category</th>
                <th className="py-3 px-4 text-right">Selling Price</th>
                <th className="py-3 px-4 text-right">Margin</th>
                <th className="py-3 px-4 text-right">In Stock</th>
                <th className="py-3 px-4 text-right">Lead Time</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border text-sm">
              {filtered.map((p) => {
                const marginPct =
                  p.selling_price > 0
                    ? Math.round(((p.selling_price - p.unit_cost) / p.selling_price) * 100)
                    : 0;
                const isOos = p.current_stock <= 0;
                const isLow = p.current_stock > 0 && p.current_stock < 20;

                return (
                  <tr key={p.id} className="hover:bg-muted/25 transition-colors">
                    <td className="py-3.5 px-4">
                      <p className="font-medium text-foreground">{p.title}</p>
                      <p className="text-xs text-muted-foreground font-mono mt-0.5">{p.sku_code}</p>
                    </td>

                    <td className="py-3.5 px-4 text-xs text-muted-foreground">
                      {p.category}
                    </td>

                    <td className="py-3.5 px-4 text-right font-medium text-foreground tabular-nums">
                      {formatINR(p.selling_price)}
                    </td>

                    <td className="py-3.5 px-4 text-right tabular-nums">
                      <span
                        className={cn(
                          "text-xs font-medium",
                          marginPct >= 30 ? "text-emerald-600" : "text-foreground"
                        )}
                      >
                        {marginPct}%
                      </span>
                    </td>

                    <td className="py-3.5 px-4 text-right tabular-nums">
                      <p
                        className={cn(
                          "font-semibold",
                          isOos
                            ? "text-red-600"
                            : isLow
                            ? "text-amber-600"
                            : "text-foreground"
                        )}
                      >
                        {formatNumber(p.current_stock)} units
                      </p>
                      {p.incoming_stock > 0 && (
                        <p className="text-[11px] text-primary mt-0.5">
                          +{formatNumber(p.incoming_stock)} incoming
                        </p>
                      )}
                    </td>

                    <td className="py-3.5 px-4 text-right text-xs text-muted-foreground tabular-nums">
                      {p.supplier_lead_time_days} days
                    </td>

                    <td className="py-3.5 px-4">
                      <Badge
                        variant={isOos ? "destructive" : isLow ? "warning" : "success"}
                      >
                        {isOos ? "Out of stock" : isLow ? "Low stock" : "In stock"}
                      </Badge>
                    </td>

                    <td className="py-3.5 px-4 text-right">
                      <button
                        type="button"
                        onClick={() =>
                          navigate(
                            `/chat?prompt=${encodeURIComponent(
                              `Should I restock ${p.title} (${p.sku_code}) right now? Check stock cover, margin, and supplier lead time.`
                            )}`
                          )
                        }
                        className="text-xs font-medium text-primary hover:underline cursor-pointer"
                      >
                        Ask AI
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
