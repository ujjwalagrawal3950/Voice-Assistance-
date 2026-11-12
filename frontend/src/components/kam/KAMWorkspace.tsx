"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
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
  Copy,
  FileText,
  History,
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
    activeSessionId,
    hydrateSessionMessages,
    resetChatPane,
    updateVoiceSettings,
    clearError,
  } = useVoice();

  const { sessionId: urlSessionId } = useParams<{ sessionId?: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [input, setInput] = useState("");
  const [showVoiceSettings, setShowVoiceSettings] = useState(false);
  const [mobileHistoryOpen, setMobileHistoryOpen] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [topAlert, setTopAlert] = useState<ProactiveAlert | null>(null);
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const justCreatedSessionRef = useRef<string | null>(null);
  const consumedPromptRef = useRef<string | null>(null);
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

  const handleSendMessage = useCallback(async (rawText: string) => {
    const text = rawText.trim();
    if (!text || isCreatingSession || voiceState === "processing") return;
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
  }, [activeSessionId, isCreatingSession, navigate, refreshSessions, sendText, urlSessionId, voiceState]);

  useEffect(() => {
    const queuedPrompt = searchParams.get("prompt");
    if (!queuedPrompt || consumedPromptRef.current === queuedPrompt) return;
    consumedPromptRef.current = queuedPrompt;
    resetChatPane();
    setSearchParams({}, { replace: true });
    handleSendMessage(queuedPrompt);
  }, [handleSendMessage, resetChatPane, searchParams, setSearchParams]);

  const handleCopyMessage = async (msgId: string, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedId(msgId);
      setTimeout(() => setCopiedId((prev) => (prev === msgId ? null : prev)), 1800);
    } catch {
      // ignore clipboard denial
    }
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
    <div className="flex h-full bg-white rounded-xl border border-border overflow-hidden">
      <ChatHistorySidebar
        sessions={sessions}
        activeSessionId={urlSessionId || activeSessionId}
        loading={sessionsLoading}
        mobileOpen={mobileHistoryOpen}
        onCloseMobile={() => setMobileHistoryOpen(false)}
        onNewChat={handleNewChat}
        onSelectSession={handleSelectSession}
      />
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-[#fafafa]">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-white px-4 sm:px-6 py-3 sticky top-0 z-10">
        <div className="flex items-center gap-2.5 sm:gap-3">
          <Button
            type="button"
            variant="outline"
            size="icon"
            className="md:hidden h-9 w-9 shrink-0"
            onClick={() => setMobileHistoryOpen(true)}
            aria-label="Open previous chats"
            title="Previous chats"
          >
            <History className="w-4 h-4" />
          </Button>
          <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white">
            <Bot className="w-4 h-4" />
            {isVoiceActive && (
              <span className="absolute -top-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-500 ring-2 ring-white" />
            )}
          </div>
          <div>
            <h2 className="font-semibold text-foreground text-sm sm:text-base leading-tight">Virtual KAM Assistant</h2>
            <p className="text-xs text-muted-foreground">
              Ask about sales, stockouts, or restock budgets
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {voiceState !== "idle" && (
            <Badge
              variant={
                voiceState === "error"
                  ? "destructive"
                  : voiceState === "assistant_speaking" || voiceState === "user_speaking"
                  ? "default"
                  : "secondary"
              }
            >
              {STATE_LABELS[voiceState]}
            </Badge>
          )}

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
          <div className="flex flex-col items-center justify-center text-center py-10 sm:py-16 px-4">
            <div className="max-w-md w-full rounded-2xl border border-border bg-white p-7 space-y-4">
              <div className="mx-auto w-12 h-12 rounded-xl bg-slate-100 text-slate-900 flex items-center justify-center">
                <Mic className="w-5 h-5" />
              </div>
              <div className="space-y-1.5">
                <h3 className="text-base font-semibold text-foreground">
                  Ask your Virtual KAM anything
                </h3>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  Start a live voice call or type a question below to check store numbers and restock options.
                </p>
              </div>
              {isVoiceSupported && !isVoiceActive && (
                <Button type="button" onClick={handleVoiceToggle} className="w-full sm:w-auto">
                  <Mic className="w-4 h-4 mr-2" /> Start Voice Call
                </Button>
              )}
            </div>
          </div>
        )}

        {transcript.map((msg) => (
          <div
            key={msg.id}
            className={cn(
              "flex gap-3 max-w-3xl",
              msg.role === "user" ? "ml-auto flex-row-reverse" : "mr-auto"
            )}
          >
            <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5">
              {msg.role === "user" ? (
                <div className="bg-slate-900 text-white flex items-center justify-center w-full h-full rounded-full">
                  <User className="w-4 h-4" />
                </div>
              ) : (
                <div className="bg-white border border-border text-slate-700 flex items-center justify-center w-full h-full rounded-full">
                  <Bot className="w-4 h-4" />
                </div>
              )}
            </div>
            <div
              className={cn(
                "rounded-2xl border px-4 py-3 text-sm",
                msg.role === "user"
                  ? "bg-slate-900 text-white border-slate-900"
                  : "bg-white text-foreground border-border flex-1"
              )}
            >
              {msg.role === "assistant" ? (
                <MarkdownMessage content={msg.content} />
              ) : (
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
              )}

              {msg.actionPerformed?.recommendations && msg.actionPerformed.recommendations.length > 0 && (
                <div className="mt-2.5 pt-2.5 border-t border-border/60 flex flex-wrap gap-1.5">
                  {msg.actionPerformed.recommendations.map((rec) => (
                    <Badge
                      key={rec.id}
                      variant="secondary"
                      className="text-[11px] gap-1 bg-emerald-50 text-emerald-700 border-emerald-200"
                    >
                      <CheckCircle2 className="w-3 h-3" />
                      {msg.actionPerformed?.action}: {rec.title}
                    </Badge>
                  ))}
                </div>
              )}

              <div
                className={cn(
                  "flex items-center gap-2 mt-2 flex-wrap text-[11px]",
                  msg.role === "user" ? "text-slate-300" : "text-muted-foreground"
                )}
              >
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {msg.timestamp.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </span>
                {msg.toolActivity && msg.toolActivity.length > 0 && (
                  <span>· Checked: {msg.toolActivity.join(", ")}</span>
                )}
                {msg.role === "assistant" && (
                  <button
                    type="button"
                    onClick={() => handleCopyMessage(msg.id, msg.content)}
                    className="ml-auto inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors cursor-pointer"
                    title="Copy response"
                  >
                    {copiedId === msg.id ? (
                      <>
                        <Check className="w-3 h-3 text-emerald-600" /> Copied
                      </>
                    ) : (
                      <>
                        <Copy className="w-3 h-3" /> Copy
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
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
          <div className="flex gap-3 max-w-3xl mr-auto fade-in" role="status" aria-live="polite">
            <div className="w-8 h-8 rounded-full bg-white border border-border text-primary flex items-center justify-center shrink-0 mt-0.5">
              <Bot className="w-4 h-4 animate-pulse" />
            </div>
            <div className="flex-1 rounded-2xl border border-border bg-white px-4 py-3.5 min-w-[240px] space-y-2.5">
              <div className="flex items-center gap-2.5">
                <div className="flex items-center gap-1" aria-hidden="true">
                  <span className="w-1.5 h-1.5 rounded-full bg-primary kam-typing-dot" style={{ animationDelay: "0ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary kam-typing-dot" style={{ animationDelay: "160ms" }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-primary kam-typing-dot" style={{ animationDelay: "320ms" }} />
                </div>
                <span className="text-sm text-muted-foreground">
                  Checking store numbers &amp; preparing reply...
                </span>
              </div>
              <div className="h-1 w-full rounded-full kam-thinking-bar" />
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-border bg-white p-4 sm:px-6">
        <div className="max-w-3xl mx-auto space-y-2.5">
          <form onSubmit={handleTextSubmit} className="flex gap-2">
            <Input
              className="flex-1 h-10"
              placeholder='Ask about your sales, stockouts, or restocking...'
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={isProcessing}
            />
            <Button
              type="submit"
              className="h-10 px-4"
              disabled={isProcessing || !input.trim()}
              aria-label={isProcessing ? "Waiting for AI response" : "Send message"}
            >
              {isProcessing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <SendIcon className="w-4 h-4" />
              )}
            </Button>
          </form>

          {/* Suggested prompts */}
          <div className="flex flex-wrap gap-1.5">
            {[
              "Why are my sales down?",
              "What should I restock with ₹15,000?",
              "Which products have long lead times?",
              "What actions should I approve next?",
            ].map((prompt) => (
              <button
                key={prompt}
                type="button"
                disabled={isProcessing}
                onClick={() => handleSendMessage(prompt)}
                className="px-2.5 py-1 rounded-lg border border-border bg-[#fafafa] hover:bg-muted text-xs text-muted-foreground hover:text-foreground transition-colors cursor-pointer disabled:opacity-50"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}

export const KamWorkspace = KAMWorkspace;
