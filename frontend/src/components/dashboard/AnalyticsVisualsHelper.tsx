"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";

export function AnalyticsVisualPlaceholder() {
  const [pulse] = useState(true);
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <Card className={pulse ? "h-64 animate-pulse" : "h-64"} />
      <Card className={pulse ? "h-64 animate-pulse" : "h-64"} />
    </div>
  );
}

