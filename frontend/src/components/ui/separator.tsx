"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SeparatorProps extends React.HTMLAttributes<HTMLHRElement> {}
function Separator({ className, ...props }: SeparatorProps) {
  return (
    <hr
      className={cn(
        "my-4 h-px bg-border",
        className
      )}
      {...props}
    />
  );
}

export { Separator };
