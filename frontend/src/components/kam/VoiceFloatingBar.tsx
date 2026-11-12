"use client";

import { useLocation, useNavigate } from "react-router-dom";
import { Check, Mic, PhoneOff, Square, Volume2, VolumeX, ArrowUpRight } from "lucide-react";
import { useVoice, type VoiceState } from "@/hooks/useVoice";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

const STATUS_LABELS: Record<VoiceState, string> = {
  idle: "Ready",
  connecting: "Connecting...",
  listening: "Listening",
  user_speaking: "Listening (Speaking)",
  processing: "Thinking...",
  assistant_speaking: "KAM Speaking",
  interrupted: "Interrupted",
  reconnecting: "Reconnecting...",
  error: "Voice Error",
  stopping: "Stopping...",
};

export function VoiceFloatingBar() {
  const location = useLocation();
  const navigate = useNavigate();
  const {
    state,
    mode,
    messages,
    interimTranscript,
    audioLevel,
    isMuted,
    error,
    activeSessionId,
    stop,
    interrupt,
    finishTurn,
    toggleMute,
  } = useVoice();

  const isOnKamPage =
    location.pathname === "/kam" ||
    location.pathname === "/chat" ||
    location.pathname.startsWith("/chat/");
  const isVoiceActive = state !== "idle" && state !== "stopping";

  if (isOnKamPage || !isVoiceActive) {
    return null;
  }

  const lastMessage = messages.length > 0 ? messages[messages.length - 1] : null;
  const previewText =
    error ||
    interimTranscript ||
    (lastMessage ? `${lastMessage.role === "assistant" ? "KAM" : "You"}: ${lastMessage.content}` : "Voice session active...");

  return (
    <div
      className="fixed bottom-4 right-4 z-50 w-[320px] sm:w-[360px] rounded-xl border border-border bg-white shadow-lg p-3.5 space-y-2.5 fade-in"
      role="region"
      aria-label="Active voice session controller"
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={cn(
              "w-2.5 h-2.5 rounded-full shrink-0",
              state === "error"
                ? "bg-destructive"
                : state === "assistant_speaking"
                ? "bg-green-500 animate-pulse"
                : "bg-primary animate-pulse"
            )}
          />
          <span className="text-xs font-semibold text-foreground truncate">
            {STATUS_LABELS[state]}
          </span>
          {mode !== "none" && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
              {mode === "local-ws" ? "live" : "browser"}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0">
          <div className="flex items-center gap-0.5 h-3.5 mr-1" aria-hidden="true">
            {[0.4, 0.8, 0.5].map((scale, idx) => (
              <span
                key={idx}
                className="w-0.5 rounded-full bg-primary transition-all duration-100"
                style={{
                  height: `${Math.max(25, Math.min(100, audioLevel * scale + (state === "listening" ? 20 : 0)))}%`,
                }}
              />
            ))}
          </div>

          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-xs"
            onClick={() => navigate(activeSessionId ? `/chat/${activeSessionId}` : "/chat")}
            title="Return to full KAM chat"
          >
            <Mic className="w-3.5 h-3.5 mr-1 text-primary" />
            Chat
            <ArrowUpRight className="w-3 h-3 ml-0.5" />
          </Button>
        </div>
      </div>

      <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
        {previewText}
      </p>

      <div className="flex items-center justify-end gap-1.5 pt-0.5">
        {(state === "user_speaking" || state === "listening") && mode === "local-ws" && (
          <Button size="sm" variant="secondary" className="h-7 px-2.5 text-xs" onClick={finishTurn}>
            <Check className="w-3.5 h-3.5 mr-1" /> Send voice
          </Button>
        )}
        {state === "assistant_speaking" && (
          <Button size="sm" variant="outline" className="h-7 px-2.5 text-xs" onClick={interrupt}>
            <Square className="w-3 h-3 mr-1" /> Interrupt
          </Button>
        )}
        <Button
          size="icon"
          variant="outline"
          className="h-7 w-7"
          onClick={toggleMute}
          title={isMuted ? "Unmute" : "Mute"}
        >
          {isMuted ? <VolumeX className="w-3.5 h-3.5 text-destructive" /> : <Volume2 className="w-3.5 h-3.5" />}
        </Button>
        <Button
          size="sm"
          variant="destructive"
          className="h-7 px-2.5 text-xs"
          onClick={stop}
          title="End voice conversation"
        >
          <PhoneOff className="w-3.5 h-3.5 mr-1" /> End
        </Button>
      </div>
    </div>
  );
}

