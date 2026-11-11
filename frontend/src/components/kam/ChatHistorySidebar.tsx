"use client";

import { MessageSquare, Plus } from "lucide-react";
import type { ChatSessionSummary } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ChatHistorySidebarProps {
  sessions: ChatSessionSummary[];
  activeSessionId: string | null;
  loading?: boolean;
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
  onNewChat,
  onSelectSession,
}: ChatHistorySidebarProps) {
  return (
    <aside
      className="w-[260px] shrink-0 border-r border-border bg-card/50 hidden md:flex flex-col h-full"
      aria-label="Previous chats"
    >
      <div className="p-3 border-b border-border">
        <Button
          type="button"
          variant="outline"
          className="w-full justify-start gap-2 font-medium"
          onClick={onNewChat}
        >
          <Plus className="w-4 h-4" />
          New chat
        </Button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {loading && sessions.length === 0 ? (
          <p className="px-3 py-4 text-xs text-muted-foreground">Loading previous chats...</p>
        ) : sessions.length === 0 ? (
          <p className="px-3 py-4 text-xs text-muted-foreground">
            No previous chats yet. Send a message to start.
          </p>
        ) : (
          sessions.map((session) => {
            const isActive = session.session_id === activeSessionId;
            return (
              <button
                key={session.session_id}
                type="button"
                onClick={() => onSelectSession(session.session_id)}
                className={cn(
                  "w-full text-left px-3 py-2.5 rounded-lg transition-colors flex items-start gap-2.5 border",
                  isActive
                    ? "bg-primary/10 border-primary/30 text-foreground"
                    : "border-transparent hover:bg-accent/70 text-muted-foreground hover:text-foreground"
                )}
              >
                <MessageSquare className="w-3.5 h-3.5 mt-1 shrink-0 opacity-70" />
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
    </aside>
  );
}

