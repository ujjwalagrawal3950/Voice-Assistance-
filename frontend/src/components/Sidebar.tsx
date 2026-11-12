"use client";

import { useState } from "react";
import {
  LayoutDashboard,
  ShoppingCart,
  Settings as SettingsIcon,
  MessageSquareText,
  ClipboardCheck,
  Menu,
  ChevronLeft,
  ChevronRight,
  Home,
  Mic,
} from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useVoice } from "@/hooks/useVoice";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

const navItems = [
  { name: "Overview", href: "/", icon: Home },
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "AI KAM Chat", href: "/kam", icon: MessageSquareText },
  { name: "Products", href: "/products", icon: ShoppingCart },
  { name: "Recommendations", href: "/recommendations", icon: ClipboardCheck },
  { name: "Settings", href: "/settings", icon: SettingsIcon },
];

export function Sidebar({
  mobileOpen,
  setMobileOpen,
}: {
  mobileOpen?: boolean;
  setMobileOpen?: (open: boolean) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const { state: voiceState, activeSessionId } = useVoice();
  const isVoiceLive = voiceState !== "idle" && voiceState !== "error" && voiceState !== "stopping";

  return (
    <>
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-slate-900/20 backdrop-blur-[1px] sm:hidden"
          onClick={() => setMobileOpen?.(false)}
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex flex-col border-r border-border bg-white transition-all duration-200 sm:static sm:translate-x-0 shrink-0",
          collapsed ? "w-16" : "w-60",
          mobileOpen ? "translate-x-0" : "-translate-x-full sm:translate-x-0"
        )}
      >
        {/* Minimal Brand Header */}
        <div className="flex h-14 items-center justify-between border-b border-border px-4 shrink-0">
          {!collapsed && (
            <Link to="/" className="flex items-center gap-2.5 group" onClick={() => setMobileOpen?.(false)}>
              <div className="w-7 h-7 rounded-lg bg-slate-900 flex items-center justify-center text-white text-xs font-semibold tracking-tight">
                VK
              </div>
              <div className="flex flex-col leading-tight">
                <span className="text-sm font-semibold text-foreground">Virtual KAM</span>
                <span className="text-[11px] text-muted-foreground">Seller Workspace</span>
              </div>
            </Link>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden sm:inline-flex items-center justify-center w-7 h-7 rounded-md text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* Navigation Links */}
        <nav className="flex-1 overflow-y-auto px-2.5 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive =
              item.href === "/"
                ? location.pathname === "/"
                : item.href === "/kam"
                ? location.pathname === "/kam" ||
                  location.pathname === "/chat" ||
                  location.pathname.startsWith("/chat/")
                : location.pathname.startsWith(item.href);

            const resolvedHref =
              item.href === "/kam" && activeSessionId ? `/chat/${activeSessionId}` : item.href;

            return (
              <Link
                key={item.name}
                to={resolvedHref}
                onClick={() => setMobileOpen?.(false)}
                className={cn(
                  "nav-link",
                  isActive ? "nav-link-active" : "",
                  collapsed && "justify-center px-2"
                )}
                title={collapsed ? item.name : undefined}
              >
                <Icon
                  className={cn(
                    "w-[17px] h-[17px] shrink-0",
                    isActive ? "text-primary" : "text-muted-foreground"
                  )}
                />
                {!collapsed && <span className="flex-1 truncate">{item.name}</span>}
                {!collapsed && item.href === "/kam" && isVoiceLive && (
                  <span className="inline-flex h-2 w-2 rounded-full bg-emerald-500" title="Voice session active" />
                )}
              </Link>
            );
          })}
        </nav>

        {!collapsed && (
          <div className="p-3 border-t border-border">
            <div className="rounded-lg bg-muted/60 px-3 py-2.5 flex items-center justify-between">
              <div className="min-w-0">
                <p className="text-xs font-medium text-foreground truncate">Demo Seller Store</p>
                <p className="text-[11px] text-muted-foreground truncate">Account connected</p>
              </div>
              <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
            </div>
          </div>
        )}
      </aside>
    </>
  );
}

function getPageLabel(pathname: string): string {
  if (pathname === "/") return "Overview";
  if (pathname.startsWith("/dashboard")) return "Dashboard";
  if (pathname.startsWith("/kam") || pathname.startsWith("/chat")) return "AI KAM Chat";
  if (pathname.startsWith("/products")) return "Products";
  if (pathname.startsWith("/recommendations")) return "Recommendations";
  if (pathname.startsWith("/settings")) return "Settings";
  return "Virtual KAM";
}

export function Navbar({ onMenuClick }: { onMenuClick?: () => void }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { state: voiceState, start } = useVoice();
  const isVoiceLive = voiceState !== "idle" && voiceState !== "error" && voiceState !== "stopping";
  const onChat =
    location.pathname === "/kam" ||
    location.pathname === "/chat" ||
    location.pathname.startsWith("/chat/");

  const handleQuickVoice = async () => {
    navigate("/chat");
    if (!isVoiceLive) {
      await start();
    }
  };

  return (
    <header className="h-14 border-b border-border bg-white/95 backdrop-blur-sm sticky top-0 z-30 flex items-center justify-between px-4 sm:px-6 shrink-0">
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuClick}
          className="sm:hidden inline-flex items-center justify-center p-2 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Toggle sidebar"
        >
          <Menu className="w-5 h-5" />
        </button>
        <span className="text-sm font-medium text-muted-foreground hidden sm:inline">
          {getPageLabel(location.pathname)}
        </span>
        <Link to="/" className="sm:hidden flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-slate-900 flex items-center justify-center text-white text-[10px] font-semibold">
            VK
          </div>
          <span className="text-sm font-semibold text-foreground">Virtual KAM</span>
        </Link>
      </div>

      <div className="flex items-center gap-2.5 ml-auto">
        {!onChat && (
          <Button
            size="sm"
            variant={isVoiceLive ? "destructive" : "outline"}
            onClick={handleQuickVoice}
            className="h-8 rounded-lg px-3 text-xs font-medium"
          >
            <Mic className={cn("w-3.5 h-3.5 mr-1.5", isVoiceLive ? "animate-pulse" : "text-primary")} />
            {isVoiceLive ? "Voice Live" : "Voice Call"}
          </Button>
        )}

        <Link
          to="/settings"
          className="flex items-center gap-2 pl-2 border-l border-border hover:opacity-80 transition-opacity"
          title="Seller Settings"
        >
          <div className="w-7 h-7 rounded-full bg-slate-100 border border-border flex items-center justify-center text-[11px] font-semibold text-slate-700">
            DS
          </div>
          <span className="hidden md:inline text-xs font-medium text-foreground">Demo Seller</span>
        </Link>
      </div>
    </header>
  );
}
