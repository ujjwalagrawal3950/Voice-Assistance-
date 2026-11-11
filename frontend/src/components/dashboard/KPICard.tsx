"use client";

import { TrendingUp, TrendingDown, AlertCircle } from "lucide-react";

interface KPICardProps {
  title: string;
  value: React.ReactNode;
  subtitle?: string;
  change?: number | null;
  icon: React.ElementType;
  changeLabel?: string;
  variant?: "default" | "destructive" | "success" | "warning" | "info";
}

export function KPICard({
  title,
  value,
  subtitle,
  change,
  icon: Icon,
  changeLabel,
  variant = "default",
}: KPICardProps) {
  const hasChange = change != null;
  const isPositive = hasChange && change > 0;
  const isNegative = hasChange && change < 0;

  const variantConfig = {
    default: { bg: "bg-primary/10", text: "text-primary", icon: "text-primary" },
    destructive: { bg: "bg-destructive/10", text: "text-destructive", icon: "text-destructive" },
    success: { bg: "bg-success/10", text: "text-success", icon: "text-success" },
    warning: { bg: "bg-warning/10", text: "text-warning-foreground", icon: "text-warning-foreground" },
    info: { bg: "bg-info/10", text: "text-info-foreground", icon: "text-info-foreground" },
  };

  const config = variantConfig[variant];

  return (
    <div className="rounded-2xl border border-border bg-card p-5 shadow-sm group transition-all duration-300 hover:shadow-md hover:border-border/60">
      <div className="flex flex-row items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{title}</p>
          <div className="flex items-baseline gap-1 pt-1">
            <span className="text-3xl font-bold text-foreground">{value}</span>
            {subtitle && <span className="text-sm text-muted-foreground">{subtitle}</span>}
          </div>
          {hasChange && (
            <p className={`mt-2 text-sm font-medium ${isPositive ? "text-success" : isNegative ? "text-destructive" : "text-muted-foreground"}`}>
              {isPositive ? <TrendingUp className="w-3 h-3 mr-1" /> : null}
              {isNegative ? <TrendingDown className="w-3 h-3 mr-1" /> : null}
              {changeLabel || ""}{Math.abs(change || 0)}% vs previous period
            </p>
          )}
        </div>
        <div className={`h-10 w-10 rounded-xl flex items-center justify-center text-sm ${config.bg} ${config.icon}`}>
          <Icon size={18} strokeWidth={2} />
        </div>
      </div>
    </div>
  );
}

interface AlertItemProps {
  title: string;
  onDismiss?: () => void;
}

export function AlertItem({ title, onDismiss }: AlertItemProps) {
  return (
    <div className="flex items-start gap-3 rounded-xl border border-border bg-card p-3 shadow-sm">
      <AlertCircle size={18} strokeWidth={2} className="text-destructive mt-0.5 flex-shrink-0" />
      <div>
        <p className="text-sm text-destructive font-medium">{title}</p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="ml-auto p-1 text-muted-foreground hover:bg-accent rounded-xl transition-colors"
          aria-label="Dismiss alert"
        >
          <span className="sr-only">Dismiss</span>
          <span aria-hidden="true">✕</span>
        </button>
      )}
    </div>
  );
}
