import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" | string;
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
        variant === "default" &&
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        variant === "secondary" &&
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        variant === "destructive" &&
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/90",
        variant === "outline" &&
          "text-foreground border-input",
        variant === "success" &&
          "border-transparent bg-green-100 text-green-800",
        variant === "warning" &&
          "border-transparent bg-amber-100 text-amber-800",
        variant === "info" &&
          "border-transparent bg-blue-100 text-blue-800",
        className
      )}
      {...props}
    />
  );
}

export { Badge };
