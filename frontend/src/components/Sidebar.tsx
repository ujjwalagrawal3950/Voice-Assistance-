"use client";

import { useState } from "react";
import {
  LayoutDashboard,
  ShoppingCart,
  Settings as SettingsIcon,
  Activity,
  Mail,
  Menu,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useVoice } from "@/hooks/useVoice";
import { cn } from "@/lib/utils";

const navItems = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "KAM Workspace", href: "/kam", icon: Activity },
  { name: "Products", href: "/products", icon: ShoppingCart },
  { name: "Recommendations", href: "/recommendations", icon: Mail },
  { name: "Settings", href: "/settings", icon: SettingsIcon },
];

export function Sidebar({ mobileOpen, setMobileOpen }: { mobileOpen?: boolean; setMobileOpen?: (open: boolean) => void }) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const { state: voiceState, activeSessionId } = useVoice();
  const isVoiceLive = voiceState !== "idle" && voiceState !== "error" && voiceState !== "stopping";

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 backdrop-blur-sm sm:hidden"
          onClick={() => setMobileOpen?.(false)}
        />
      )}

      <aside
        className={cn(
          "flex flex-col border-r border-border bg-card transition-all duration-300 flex-shrink-0 z-50",
          collapsed ? "w-16" : "w-60",
          "fixed sm:static inset-y-0 left-0 h-full",
          mobileOpen ? "translate-x-0" : "-translate-x-full sm:translate-x-0"
        )}
      >
        <div className="flex items-center justify-between h-14 px-4 border-b border-border">
          {!collapsed && (
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shadow-sm">
                VK
              </div>
              <h1 className="text-base font-semibold tracking-tight text-foreground">
                Virtual KAM
              </h1>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden sm:inline-flex items-center justify-center p-1.5 rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors ml-auto"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto space-y-1 p-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const targetHref =
              item.href === "/kam"
                ? activeSessionId
                  ? `/chat/${activeSessionId}`
                  : "/chat"
                : item.href;
            const isActive =
              item.href === "/kam"
                ? location.pathname === "/kam" ||
                  location.pathname === "/chat" ||
                  location.pathname.startsWith("/chat/")
                : location.pathname === item.href;
            return (
              <Link
                key={item.name}
                to={targetHref}
                className={cn(
                  "nav-link",
                  isActive ? "nav-link-active" : "text-muted-foreground hover:text-foreground"
                )}
                onClick={() => setMobileOpen?.(false)}
              >
                <Icon className={cn("w-5 h-5 shrink-0", collapsed && "mx-auto")} />
                {!collapsed && (
                  <span className="flex items-center gap-2 flex-1">
                    {item.name}
                    {item.href === "/kam" && isVoiceLive && (
                      <span className="ml-auto w-2 h-2 rounded-full bg-green-500 animate-pulse" title="Voice session active" />
                    )}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>
      </aside>
    </>
  );
}

export function Navbar({ onMenuClick }: { onMenuClick?: () => void }) {
  return (
    <header className="h-14 border-b border-border bg-card/80 backdrop-blur-md sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="sm:hidden inline-flex items-center justify-center p-2 rounded-lg text-muted-foreground hover:bg-accent hover:text-accent-foreground"
          aria-label="Toggle sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
        <div className="sm:hidden flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold">
            VK
          </div>
          <span className="text-sm font-semibold">Virtual KAM</span>
        </div>
      </div>
      <div className="flex items-center gap-3 ml-auto">
        <div className="hidden sm:flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
          <span className="text-xs text-muted-foreground font-medium">System online</span>
        </div>
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground text-xs font-bold shadow-sm">
          RK
        </div>
      </div>
    </header>
  );
}
