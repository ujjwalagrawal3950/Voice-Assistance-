"use client";

import { MessageSquare, Plus, X } from "lucide-react";
import type { ChatSessionSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatHistorySidebarProps {
  sessions: ChatSessionSummary[];
  activeSessionId: string | null;
  loading?: boolean;
  mobileOpen?: boolean;
  onCloseMobile?: () => void;
  onNewChat: () => void;
  onSelectSession: (sessionId: string) => void;
}

function truncateTitle(raw: string | null, maxLen = 30): string {
  const clean = (raw || "New chat").trim() || "New chat";
  if (clean.length <= maxLen) return clean;
  return clean.slice(0, maxLen).trimEnd() + "…";
}

function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  if (Number.isNaN(date.getTime())) return "";
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;

  const todayMidnight = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const dateMidnight = new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
  const dayDiff = Math.round((todayMidnight - dateMidnight) / 86400000);
  if (dayDiff === 1) return "Yesterday";

  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function ChatHistorySidebar({
  sessions,
  activeSessionId,
  loading = false,
  mobileOpen = false,
  onCloseMobile,
  onNewChat,
  onSelectSession,
}: ChatHistorySidebarProps) {
  const content = (
    <div className="flex flex-col h-full">
      <div className="p-3 border-b border-border flex items-center gap-2">
        <Button
          type="button"
          variant="outline"
          className="flex-1 justify-start gap-2 font-semibold rounded-xl"
          onClick={() => {
            onNewChat();
            onCloseMobile?.();
          }}
        >
          <Plus className="w-4 h-4 text-primary" />
          New chat
        </Button>
        {onCloseMobile && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="md:hidden h-9 w-9"
            onClick={onCloseMobile}
            aria-label="Close chat history"
          >
            <X className="w-4 h-4" />
          </Button>
        )}
      </div>

      <div className="px-3 pt-3 pb-1.5 text-xs font-medium text-muted-foreground">
        Recent Chats
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1 scrollbar-thin">
        {loading && sessions.length === 0 ? (
          <div className="space-y-2 p-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-11 rounded-xl bg-muted/70 animate-pulse" />
            ))}
          </div>
        ) : sessions.length === 0 ? (
          <p className="px-3 py-4 text-xs text-muted-foreground">
            No previous chats yet. Ask a question or start voice to begin.
          </p>
        ) : (
          sessions.map((session) => {
            const isActive = session.session_id === activeSessionId;
            return (
              <button
                key={session.session_id}
                type="button"
                onClick={() => {
                  onSelectSession(session.session_id);
                  onCloseMobile?.();
                }}
                className={cn(
                  "w-full text-left px-3 py-2 rounded-lg transition-colors flex items-start gap-2.5 cursor-pointer",
                  isActive
                    ? "bg-muted text-foreground"
                    : "hover:bg-muted/50 text-muted-foreground hover:text-foreground"
                )}
              >
                <MessageSquare
                  className={cn(
                    "w-3.5 h-3.5 mt-0.5 shrink-0",
                    isActive ? "text-primary" : "opacity-65"
                  )}
                />
                <div className="min-w-0 flex-1">
                  <div
                    className={cn(
                      "text-xs truncate",
                      isActive ? "font-semibold text-foreground" : "font-medium"
                    )}
                    title={session.title || "New chat"}
                  >
                    {truncateTitle(session.title)}
                  </div>
                  <div className="text-[11px] text-muted-foreground mt-0.5">
                    {formatRelativeTime(session.updated_at)}
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );

  return (
    <>
      <aside
        className="w-[260px] shrink-0 border-r border-border bg-card/60 hidden md:flex flex-col h-full"
        aria-label="Previous chats"
      >
        {content}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-slate-950/45 backdrop-blur-sm"
            onClick={onCloseMobile}
          />
          <aside
            className="relative w-[275px] max-w-[85vw] bg-card border-r border-border h-full shadow-2xl flex flex-col"
            aria-label="Previous chats mobile drawer"
          >
            {content}
          </aside>
        </div>
      )}
    </>
  );
}
