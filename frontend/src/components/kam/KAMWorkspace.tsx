"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api } from "@/api/client";
import {
  createChatSession,
  getChatSessionMessages,
  listChatSessions,
  type ChatSessionSummary,
} from "@/lib/api";
import type { ProactiveAlert } from "@/types";
import { ChatHistorySidebar } from "@/components/kam/ChatHistorySidebar";
import { MarkdownMessage } from "@/components/kam/MarkdownMessage";
import {
  Mic,
  MicOff,
  Send as SendIcon,
  Loader2,
  User,
  Bot,
  Clock,
  AlertCircle,
  Bell,
  Volume2,
  VolumeX,
  Square,
  Check,
  CheckCircle2,
  FileText,
  SlidersHorizontal,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useVoice, type VoiceState } from "@/hooks/useVoice";

const STATE_LABELS: Record<VoiceState, string> = {
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

export function KAMWorkspace() {
  const {
    state: voiceState,
    mode,
    transcript,
    interimTranscript,
    audioLevel,
    isVoiceSupported,
    permissionDenied,
    isMuted,
    error,
    start,
    stop,
    interrupt,
    finishTurn,
    toggleMute,
    sendText,
    summarizeCall,
    voiceSettings,
    availableVoices,
    activeEngineLabel,
    activeSessionId,
    hydrateSessionMessages,
    resetChatPane,
    updateVoiceSettings,
    clearError,
  } = useVoice();

  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>();
  const navigate = useNavigate();

  const [input, setInput] = useState("");
  const [showVoiceSettings, setShowVoiceSettings] = useState(false);
  const [topAlert, setTopAlert] = useState<ProactiveAlert | null>(null);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const justCreatedSessionRef = useRef<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const refreshSessions = useCallback(async () => {
    try {
      const rows = await listChatSessions();
      setSessions(rows);
    } catch {
      // ignore transient list failure
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    if (!urlSessionId) return;
    if (justCreatedSessionRef.current === urlSessionId) {
      justCreatedSessionRef.current = null;
      return;
    }
    if (urlSessionId === activeSessionId && transcript.length > 0) {
      return;
    }

    let cancelled = false;
    setSessionError(null);
    getChatSessionMessages(urlSessionId)
      .then((rows) => {
        if (!cancelled) {
          hydrateSessionMessages(urlSessionId, rows);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          resetChatPane();
          setSessionError(
            err instanceof Error && err.message.includes("404")
              ? "Chat session not found (404)."
              : err instanceof Error
              ? err.message
              : "Failed to load chat session."
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, [urlSessionId, activeSessionId, transcript.length, hydrateSessionMessages, resetChatPane]);

  useEffect(() => {
    api
      .listAlerts()
      .then((rows) => {
        const high = rows.find((r) => r.severity === "high") || rows[0] || null;
        setTopAlert(high);
      })
      .catch(() => {});
  }, []);

  const isVoiceActive =
    voiceState !== "idle" && voiceState !== "error" && voiceState !== "stopping";
  const isProcessing = voiceState === "processing" || isCreatingSession;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [transcript.length, isProcessing]);

  useEffect(() => {
    if (interimTranscript) {
      messagesEndRef.current?.scrollIntoView({ behavior: "auto", block: "end" });
    }
  }, [interimTranscript]);

  const handleNewChat = () => {
    setSessionError(null);
    resetChatPane();
    navigate("/chat");
  };

  const handleSelectSession = (targetSessionId: string) => {
    setSessionError(null);
    navigate(`/chat/${targetSessionId}`);
  };

  const handleSendMessage = async (rawText: string) => {
    const text = rawText.trim();
    if (!text || isProcessing) return;
    setSessionError(null);

    let targetSessionId = urlSessionId || activeSessionId;
    if (!targetSessionId) {
      setIsCreatingSession(true);
      try {
        const created = await createChatSession(text);
        targetSessionId = created.session_id;
        justCreatedSessionRef.current = targetSessionId;
        setSessions((prev) => [
          {
            session_id: created.session_id,
            title: created.title,
            updated_at: new Date().toISOString(),
          },
          ...prev,
        ]);
        navigate(`/chat/${targetSessionId}`, { replace: true });
      } catch (err) {
        setSessionError(err instanceof Error ? err.message : "Failed to create chat session");
        return;
      } finally {
        setIsCreatingSession(false);
      }
    }

    await sendText(text, targetSessionId);
    await refreshSessions();
  };

  const handleTextSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isProcessing) return;
    setInput("");
    await handleSendMessage(text);
  };

  const handleVoiceToggle = async () => {
    if (isVoiceActive) {
      stop();
    } else {
      clearError();
      await start();
    }
  };

  return (
    <div className="flex h-full bg-background rounded-2xl border border-border overflow-hidden">
      <ChatHistorySidebar
        sessions={sessions}
        activeSessionId={urlSessionId || activeSessionId}
        loading={sessionsLoading}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
      />
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-card/80 backdrop-blur-md p-4 sm:px-6 sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Bot className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-bold text-foreground text-lg">Virtual KAM</h2>
            <p className="text-xs text-muted-foreground">
              Two-way voice &amp; text business partner
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {mode !== "none" && (
            <Badge variant="outline" className="text-xs">
              {mode === "local-ws" ? activeEngineLabel : "Browser Voice"}
            </Badge>
          )}

          <Badge
            variant={
              voiceState === "error"
                ? "destructive"
                : voiceState === "idle"
                ? "secondary"
                : voiceState === "assistant_speaking" || voiceState === "user_speaking"
                ? "default"
                : "info"
            }
            className={cn(
              (voiceState === "assistant_speaking" || voiceState === "user_speaking") &&
                "animate-pulse"
            )}
          >
            {STATE_LABELS[voiceState]}
          </Badge>

          {(voiceState === "user_speaking" || voiceState === "listening") && mode === "local-ws" && (
            <Button
              variant="outline"
              size="sm"
              onClick={finishTurn}
              title="Finish speaking and send now"
            >
              <Check className="w-4 h-4 mr-1" /> Send voice
            </Button>
          )}

          {voiceState === "assistant_speaking" && (
            <Button
              variant="outline"
              size="sm"
              onClick={interrupt}
              title="Interrupt assistant and speak"
            >
              <Square className="w-3.5 h-3.5 mr-1 fill-current" /> Interrupt
            </Button>
          )}

          <Button
            variant={isVoiceActive ? "destructive" : "default"}
            size="sm"
            onClick={handleVoiceToggle}
            disabled={!isVoiceSupported && !isVoiceActive}
            title={
              !isVoiceSupported
                ? "Microphone not supported in this browser"
                : isVoiceActive
                ? "Stop voice session"
                : "Start voice conversation"
            }
          >
            {isVoiceActive ? (
              <>
                <MicOff className="w-4 h-4 mr-1.5 animate-pulse" /> Stop Voice
              </>
            ) : (
              <>
                <Mic className="w-4 h-4 mr-1.5" /> Start Voice
              </>
            )}
          </Button>

          {transcript.length > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={summarizeCall}
              disabled={isProcessing}
              title="Summarise key issues, recommendations, and next steps"
            >
              <FileText className="w-4 h-4 mr-1.5" /> Summarize
            </Button>
          )}

          <Button
            variant={showVoiceSettings ? "secondary" : "outline"}
            size="icon"
            onClick={() => setShowVoiceSettings((v) => !v)}
            title="Voice model, speed, and hands-free settings"
            aria-label="Voice settings"
          >
            <SlidersHorizontal className="w-4 h-4" />
          </Button>

          <Button
            variant="outline"
            size="icon"
            onClick={toggleMute}
            title={isMuted ? "Unmute assistant audio" : "Mute assistant audio"}
            aria-label={isMuted ? "Unmute" : "Mute"}
          >
            {isMuted ? (
              <VolumeX className="w-4 h-4 text-destructive" />
            ) : (
              <Volume2 className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Voice Model & Advanced Controls Bar */}
      {showVoiceSettings && (
        <div className="border-b border-border bg-muted/40 px-4 sm:px-6 py-3 grid grid-cols-1 md:grid-cols-4 gap-3 text-xs">
          <label className="flex flex-col gap-1">
            <span className="font-medium text-muted-foreground">Assistant Voice</span>
            <select
              value={voiceSettings.voiceId}
              onChange={(e) => updateVoiceSettings({ voiceId: e.target.value })}
              className="h-8 rounded-md border border-input bg-background px-2 text-xs text-foreground"
            >
              {availableVoices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
          </label>

          <div className="flex flex-col gap-1">
            <span className="font-medium text-muted-foreground">Speaking Speed</span>
            <div className="flex items-center gap-1">
              {[0.9, 1.0, 1.1, 1.2].map((rate) => (
                <Button
                  key={rate}
                  type="button"
                  size="sm"
                  variant={Math.abs(voiceSettings.speechRate - rate) < 0.02 ? "default" : "outline"}
                  className="h-8 px-2 text-xs flex-1"
                  onClick={() => updateVoiceSettings({ speechRate: rate })}
                >
                  {rate.toFixed(1)}x
                </Button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-1">
            <span className="font-medium text-muted-foreground">Speech Recognition</span>
            <div className="flex items-center gap-1">
              <Button
                type="button"
                size="sm"
                variant={voiceSettings.sttModel === "base" ? "default" : "outline"}
                className="h-8 px-2 text-xs flex-1"
                onClick={() => updateVoiceSettings({ sttModel: "base" })}
              >
                Fast (1.7s)
              </Button>
              <Button
                type="button"
                size="sm"
                variant={voiceSettings.sttModel === "small.en" ? "default" : "outline"}
                className="h-8 px-2 text-xs flex-1"
                onClick={() => updateVoiceSettings({ sttModel: "small.en" })}
              >
                Accurate (small)
              </Button>
            </div>
          </div>

          <div className="flex flex-col justify-between gap-1">
            <span className="font-medium text-muted-foreground">Hands-Free Interrupt</span>
            <label className="flex items-center gap-2 h-8 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={voiceSettings.autoBargeIn}
                onChange={(e) => updateVoiceSettings({ autoBargeIn: e.target.checked })}
                className="rounded border-input accent-primary"
              />
              <span className="text-foreground">Barge-in while speaking (use headphones)</span>
            </label>
          </div>
        </div>
      )}

      {/* Proactive KAM Alert Banner */}
      {topAlert && (
        <div className="border-b border-border bg-amber-500/10 px-4 sm:px-6 py-2 flex items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 min-w-0">
            <Bell className="w-3.5 h-3.5 text-amber-600 shrink-0" />
            <span className="truncate text-foreground">
              <strong>Proactive KAM Alert:</strong> {topAlert.title}
            </span>
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
            <Button
              size="sm"
              variant="outline"
              className="h-6 px-2 text-[11px]"
              disabled={isProcessing}
              onClick={() => handleSendMessage(`Tell me more about this alert and what to do: ${topAlert.message}`)}
            >
              Ask KAM
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="h-6 px-2 text-[11px]"
              onClick={() => setTopAlert(null)}
            >
              Hide
            </Button>
          </div>
        </div>
      )}

      {/* Live Voice Status & Interim Transcript Bar */}
      {isVoiceActive && (
        <div className="border-b border-border bg-primary/5 px-4 sm:px-6 py-2.5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <div className="flex items-center gap-1 h-4 shrink-0" aria-hidden="true">
              {[0.3, 0.6, 1, 0.7, 0.4].map((scale, idx) => {
                const activeHeight = Math.max(
                  20,
                  Math.min(100, audioLevel * scale + (voiceState === "listening" ? 15 : 0))
                );
                return (
                  <span
                    key={idx}
                    className={cn(
                      "w-1 rounded-full transition-all duration-100",
                      voiceState === "user_speaking"
                        ? "bg-primary"
                        : voiceState === "assistant_speaking"
                        ? "bg-green-600"
                        : "bg-primary/40"
                    )}
                    style={{ height: `${activeHeight}%` }}
                  />
                );
              })}
            </div>
            <p className="text-xs sm:text-sm text-foreground truncate">
              {interimTranscript ? (
                <span className="italic text-primary">“{interimTranscript}”</span>
              ) : voiceState === "listening" ? (
                "Listening — speak naturally and pause when done."
              ) : voiceState === "user_speaking" ? (
                "Hearing you..."
              ) : voiceState === "processing" ? (
                "Checking store data and preparing response..."
              ) : voiceState === "assistant_speaking" ? (
                isMuted
                  ? "Assistant audio muted — reading response in transcript."
                  : "Speaking response... click Interrupt to speak."
              ) : (
                "Connecting voice..."
              )}
            </p>
          </div>
        </div>
      )}

      {/* Transcript / Messages */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4 scrollbar-thin">
        {sessionError && (
          <Card className="border-destructive/40 bg-destructive/5">
            <CardContent className="p-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 text-sm text-destructive">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{sessionError}</span>
              </div>
              <Button variant="outline" size="sm" onClick={handleNewChat}>
                New chat
              </Button>
            </CardContent>
          </Card>
        )}

        {error && (
          <Card className="border-destructive/40 bg-destructive/5">
            <CardContent className="p-3 flex items-start justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <AlertCircle className="w-4 h-4 text-destructive shrink-0 mt-0.5" />
                <div className="text-sm text-destructive">
                  <p>{error}</p>
                  {permissionDenied && (
                    <p className="text-xs mt-1 text-muted-foreground">
                      Allow microphone access in your browser address bar, then click Start Voice again.
                    </p>
                  )}
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={clearError}>
                Dismiss
              </Button>
            </CardContent>
          </Card>
        )}

        {transcript.length === 0 &&
          !isProcessing &&
          voiceState !== "user_speaking" &&
          !interimTranscript && (
          <div className="flex flex-col items-center justify-center text-center py-12 px-4">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-4">
              <Mic className="w-6 h-6" />
            </div>
            <h3 className="text-base font-semibold text-foreground mb-1">
              Talk or type to your Virtual KAM
            </h3>
            <p className="text-sm text-muted-foreground max-w-md">
              Click <strong>Start Voice</strong> to ask questions hands-free, or pick a prompt below to test with text.
            </p>
          </div>
        )}

        {transcript.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex gap-3 max-w-[85%]",
              msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
            )}
          >
            <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0">
              {msg.role === "user" ? (
                <div className="bg-primary text-primary-foreground text-xs font-medium flex items-center justify-center w-full h-full rounded-full">
                  <User className="w-4 h-4" />
                </div>
              ) : (
                <div className="bg-secondary text-secondary-foreground text-xs font-medium flex items-center justify-center w-full h-full rounded-full">
                  <Bot className="w-4 h-4" />
                </div>
              )}
            </div>
            <Card
              className={cn(
                "flex-1",
                msg.role === "user" && "bg-primary/5 border-primary/20"
              )}
            >
              <CardContent className="p-3.5 pt-3">
                {msg.role === "assistant" ? (
                  <MarkdownMessage content={msg.content} />
                ) : (
                  <p className="text-sm text-foreground whitespace-pre-wrap">{msg.content}</p>
                )}
                {msg.actionPerformed?.recommendations && msg.actionPerformed.recommendations.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-border/50 flex flex-wrap gap-1.5">
                    {msg.actionPerformed.recommendations.map((rec) => (
                      <Badge
                        key={rec.id}
                        variant="secondary"
                        className="text-[11px] gap-1 bg-green-100 text-green-800 border-green-300"
                      >
                        <CheckCircle2 className="w-3 h-3" />
                        {msg.actionPerformed?.action}: {rec.title}
                      </Badge>
                    ))}
                  </div>
                )}
                <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    {msg.timestamp.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                  {msg.channel && (
                    <Badge variant="outline" className="text-[10px] px-1.5 py-0">
                      {msg.channel}
                    </Badge>
                  )}
                  {msg.specialistsConsulted && msg.specialistsConsulted.length > 0 && (
                    msg.specialistsConsulted.map((sp) => (
                      <Badge
                        key={sp}
                        variant="secondary"
                        className="text-[10px] px-1.5 py-0 bg-primary/10 text-primary border-primary/20"
                      >
                        {sp}
                      </Badge>
                    ))
                  )}
                  {msg.toolActivity && msg.toolActivity.length > 0 && (
                    <span className="text-[11px] text-muted-foreground">
                      Tools: {msg.toolActivity.join(", ")}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        ))}

        {(voiceState === "user_speaking" || interimTranscript) && (
          <div className="flex gap-3 max-w-[85%] ml-auto flex-row-reverse">
            <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0">
              <div className="bg-primary text-primary-foreground text-xs font-medium flex items-center justify-center w-full h-full rounded-full animate-pulse">
                <Mic className="w-4 h-4" />
              </div>
            </div>
            <Card className="flex-1 border-primary/40 bg-primary/5">
              <CardContent className="p-3 pt-2.5">
                <p className="text-sm text-foreground whitespace-pre-wrap">
                  {interimTranscript ? (
                    <>
                      {interimTranscript}
                      <span className="inline-block w-1.5 h-4 ml-1 align-middle bg-primary animate-pulse rounded-sm" />
                    </>
                  ) : (
                    <span className="italic text-muted-foreground">Listening to you speak...</span>
                  )}
                </p>
                <div className="flex items-center gap-2 mt-1.5">
                  <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-primary/40 text-primary">
                    live voice
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {isProcessing && (
          <div className="flex gap-3 max-w-[85%] mr-auto fade-in" role="status" aria-live="polite">
            <div className="w-9 h-9 rounded-full flex items-center justify-center shrink-0 relative">
              <span className="absolute inset-0 rounded-full bg-primary/25 animate-ping" />
              <div className="relative bg-primary/15 text-primary border border-primary/30 flex items-center justify-center w-full h-full rounded-full">
                <Bot className="w-4 h-4 animate-pulse" />
              </div>
            </div>
            <Card className="flex-1 border-primary/30 bg-primary/[0.03] min-w-[240px]">
              <CardContent className="p-3.5 space-y-2.5">
                <div className="flex items-center gap-2.5">
                  <div className="flex items-center gap-1" aria-hidden="true">
                    <span className="w-2 h-2 rounded-full bg-primary kam-typing-dot" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 rounded-full bg-primary kam-typing-dot" style={{ animationDelay: "160ms" }} />
                    <span className="w-2 h-2 rounded-full bg-primary kam-typing-dot" style={{ animationDelay: "320ms" }} />
                  </div>
                  <span className="text-sm font-medium text-foreground">
                    Virtual KAM is analyzing store metrics &amp; formulating strategy...
                  </span>
                </div>
                <div className="h-1.5 w-full rounded-full kam-thinking-bar" />
              </CardContent>
            </Card>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-border bg-card p-4 sm:px-6">
        <form onSubmit={handleTextSubmit} className="flex gap-2">
          <Input
            className="flex-1 h-auto py-2.5"
            placeholder='Ask about your business (e.g., "Why are my sales down?")'
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isProcessing}
          />
          <Button type="submit" disabled={isProcessing || !input.trim()} aria-label={isProcessing ? "Waiting for AI response" : "Send message"}>
            {isProcessing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <SendIcon className="w-4 h-4" />
            )}
          </Button>
        </form>

        {/* Suggested prompts */}
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            "Why are my sales down? Break down stockout vs cancellation drivers.",
            "What if I spend ₹15,000 on restocking today vs delaying 1 week?",
            "Which festival-sensitive SKUs have long supplier lead times?",
            "What actions worked best before and what should I approve next?",
          ].map((prompt) => (
            <Button
              key={prompt}
              variant="outline"
              size="sm"
              disabled={isProcessing}
              onClick={() => handleSendMessage(prompt)}
            >
              {prompt}
            </Button>
          ))}
        </div>
      </div>
      </div>
    </div>
  );
}

export const KamWorkspace = KAMWorkspace;
