/**
 * Dual-mode real-time voice conversation hook for the Virtual KAM workspace.
 *
 * Mode 1 ("local-ws"): Connects to local Python voice-service (ws://localhost:8765)
 *   running faster-whisper STT → Backend KAM Agent (Ollama + tools) → Piper TTS.
 *   Provides real-time live captions via browser SpeechRecognition preview (when available)
 *   and streaming faster-whisper partial_transcript fallback.
 * Mode 2 ("browser"): Automatically falls back to browser Web Speech API
 *   (SpeechRecognition + speechSynthesis) wired to Backend POST /api/assistant/chat
 *   when the local WebSocket voice service is unavailable.
 *
 * States: idle → connecting → listening → user_speaking → processing → assistant_speaking
 */

import { createContext, createElement, useContext, useState, useEffect, useRef, useCallback, type ReactNode } from "react";
import { chat, getVoiceSession } from "@/lib/api";

export type VoiceState =
  | "idle"
  | "connecting"
  | "listening"
  | "user_speaking"
  | "processing"
  | "assistant_speaking"
  | "interrupted"
  | "reconnecting"
  | "error"
  | "stopping";

export type VoiceMode = "none" | "local-ws" | "browser";

export interface VoiceOption {
  id: string;
  label: string;
  engine: string;
}

export interface VoiceSettings {
  voiceId: string;
  speechRate: number;
  sttModel: "base" | "small.en";
  autoBargeIn: boolean;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  channel?: "voice" | "text";
  toolActivity?: string[];
  specialistsConsulted?: string[];
  recommendationIds?: string[];
  actionPerformed?: {
    action: string;
    recommendations?: Array<{ id: string; title: string; approval_status: string }>;
  };
}

export interface UseVoiceReturn {
  state: VoiceState;
  mode: VoiceMode;
  transcript: ChatMessage[];
  messages: ChatMessage[];
  interimTranscript: string;
  audioLevel: number;
  isVoiceSupported: boolean;
  permissionDenied: boolean;
  isMuted: boolean;
  error: string | null;
  voiceSettings: VoiceSettings;
  availableVoices: VoiceOption[];
  activeEngineLabel: string;
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  hydrateSessionMessages: (
    sessionId: string,
    rows: Array<{ role: "user" | "assistant"; content: string; sequence_no: number }>
  ) => void;
  resetChatPane: () => void;
  start: () => Promise<void>;
  stop: () => void;
  interrupt: () => void;
  finishTurn: () => void;
  toggleMute: () => void;
  sendText: (message: string, sessionIdOverride?: string) => Promise<void>;
  summarizeCall: () => Promise<void>;
  updateVoiceSettings: (patch: Partial<VoiceSettings>) => void;
  clearError: () => void;
}

const DEFAULT_VOICE_OPTIONS: VoiceOption[] = [
  { id: "en-IN-NeerjaExpressiveNeural", label: "Neerja (Indian English • Expressive)", engine: "edge-tts" },
  { id: "en-IN-PrabhatNeural", label: "Prabhat (Indian English Male • Neural)", engine: "edge-tts" },
  { id: "en-US-AvaMultilingualNeural", label: "Ava (Conversational • Expressive)", engine: "edge-tts" },
  { id: "en-GB-SoniaNeural", label: "Sonia (British English • Neural)", engine: "edge-tts" },
  { id: "offline-cori", label: "Cori HD (Offline Local)", engine: "piper" },
  { id: "offline-jenny", label: "Jenny (Offline Local)", engine: "piper" },
];

const DEFAULT_VOICE_SETTINGS: VoiceSettings = {
  voiceId: "en-IN-NeerjaExpressiveNeural",
  speechRate: 1.0,
  sttModel: "base",
  autoBargeIn: false,
};

function loadSavedVoiceSettings(): VoiceSettings {
  try {
    const raw = window.localStorage.getItem("kam_voice_settings");
    if (!raw) return DEFAULT_VOICE_SETTINGS;
    const parsed = JSON.parse(raw);
    return {
      voiceId: typeof parsed.voiceId === "string" ? parsed.voiceId : DEFAULT_VOICE_SETTINGS.voiceId,
      speechRate: typeof parsed.speechRate === "number" ? Math.max(0.8, Math.min(1.3, parsed.speechRate)) : 1.0,
      sttModel: parsed.sttModel === "small.en" ? "small.en" : "base",
      autoBargeIn: Boolean(parsed.autoBargeIn),
    };
  } catch {
    return DEFAULT_VOICE_SETTINGS;
  }
}

const GREETING_TEXT =
  "Namaste! I'm your Virtual Key Account Manager for your Snapdeal store. How is business going today, and how can I help you?";

const SUMMARY_PROMPT =
  "Please summarise the key issues we discussed, your top 2-3 practical recommendations, and our concrete next steps.";

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}
interface SpeechRecognitionResult {
  isFinal: boolean;
  length: number;
  [index: number]: SpeechRecognitionAlternative;
}
interface SpeechRecognitionResultList {
  length: number;
  [index: number]: SpeechRecognitionResult;
}
interface SpeechRecognitionEvent extends Event {
  resultIndex: number;
  results: SpeechRecognitionResultList;
}
interface SpeechRecognitionErrorEvent extends Event {
  error: string;
}
interface BrowserSpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onstart: (() => void) | null;
  onspeechstart: (() => void) | null;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
}

function getSpeechRecognitionCtor(): (new () => BrowserSpeechRecognition) | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: new () => BrowserSpeechRecognition;
    webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

function getSupportedMimeType(): string {
  if (typeof MediaRecorder === "undefined") return "";
  const candidates = [
    "audio/webm;codecs=opus",
    "audio/webm",
    "audio/ogg;codecs=opus",
    "audio/mp4",
  ];
  for (const mime of candidates) {
    if (MediaRecorder.isTypeSupported(mime)) return mime;
  }
  return "";
}

async function blobToBase64(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

export function useVoiceSession(): UseVoiceReturn {
  const [state, setState] = useState<VoiceState>("idle");
  const [mode, setMode] = useState<VoiceMode>("none");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activeSessionId, setActiveSessionIdState] = useState<string | null>(null);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [audioLevel, setAudioLevel] = useState(0);
  const [isVoiceSupported, setIsVoiceSupported] = useState(false);
  const [permissionDenied, setPermissionDenied] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [voiceSettings, setVoiceSettings] = useState<VoiceSettings>(() => loadSavedVoiceSettings());
  const [availableVoices, setAvailableVoices] = useState<VoiceOption[]>(DEFAULT_VOICE_OPTIONS);
  const [activeEngineLabel, setActiveEngineLabel] = useState<string>("Indian Neural Voice");

  const stateRef = useRef<VoiceState>("idle");
  const activeRef = useRef(false);
  const isMutedRef = useRef(false);
  const modeRef = useRef<VoiceMode>("none");
  const conversationIdRef = useRef<string | undefined>(undefined);
  const voiceSettingsRef = useRef<VoiceSettings>(voiceSettings);
  const greetedRef = useRef(false);

  // Local WebSocket voice refs
  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const vadTimerRef = useRef<number | null>(null);
  const bargeInFramesRef = useRef<number>(0);
  const bargeInRafRef = useRef<number | null>(null);
  const bargeInCleanupRef = useRef<(() => void) | null>(null);
  const stopPlaybackRef = useRef<() => void>(() => {});
  const beginWsUtteranceCaptureRef = useRef<() => void>(() => {});
  const chunksRef = useRef<Blob[]>([]);
  const forceSendRef = useRef(false);
  const hasSpokenRef = useRef(false);
  const audioPlayerRef = useRef<HTMLAudioElement | null>(null);
  const audioObjectUrlRef = useRef<string | null>(null);
  const pendingChunkMetaRef = useRef<{ mimeType: string; isFinal: boolean; voiceId?: string } | null>(null);
  const audioQueueRef = useRef<Array<{ blob: Blob; isFinal: boolean; voiceId?: string }>>([]);
  const awaitingMoreChunksRef = useRef(false);

  // SpeechRecognition refs (both fallback mode and live caption preview in local-ws)
  const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const previewRecognitionRef = useRef<BrowserSpeechRecognition | null>(null);
  const hasBrowserPreviewRef = useRef(false);
  const previewCursorRef = useRef(0);
  const latestPreviewLenRef = useRef(0);
  const lastBrowserPreviewAtRef = useRef(0);

  const updateState = useCallback((next: VoiceState) => {
    stateRef.current = next;
    setState(next);
  }, []);

  const addMessage = useCallback(
    (
      role: "user" | "assistant",
      content: string,
      channel: "voice" | "text",
      toolActivity?: string[],
      extra?: {
        specialistsConsulted?: string[];
        recommendationIds?: string[];
        actionPerformed?: ChatMessage["actionPerformed"];
      }
    ) => {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
          role,
          content,
          timestamp: new Date(),
          channel,
          toolActivity,
          specialistsConsulted: extra?.specialistsConsulted,
          recommendationIds: extra?.recommendationIds,
          actionPerformed: extra?.actionPerformed,
        },
      ]);
    },
    []
  );

  useEffect(() => {
    const hasMic =
      typeof navigator !== "undefined" &&
      !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    const hasSpeechRec = getSpeechRecognitionCtor() !== null;
    setIsVoiceSupported(hasMic || hasSpeechRec);
  }, []);

  const updateVoiceSettings = useCallback((patch: Partial<VoiceSettings>) => {
    const next: VoiceSettings = {
      ...voiceSettingsRef.current,
      ...patch,
    };
    voiceSettingsRef.current = next;
    setVoiceSettings(next);
    try {
      window.localStorage.setItem("kam_voice_settings", JSON.stringify(next));
    } catch {
      // ignore storage quota errors
    }
    const matched = availableVoices.find((v) => v.id === next.voiceId);
    if (matched) {
      setActiveEngineLabel(matched.engine === "piper" ? "Offline Local Voice" : "Indian Neural Voice");
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "config",
          voice_id: next.voiceId,
          speech_rate: next.speechRate,
          stt_model: next.sttModel,
        })
      );
    }
  }, [availableVoices]);

  const stopPreviewRecognition = useCallback(() => {
    hasBrowserPreviewRef.current = false;
    previewCursorRef.current = 0;
    latestPreviewLenRef.current = 0;
    lastBrowserPreviewAtRef.current = 0;
    if (previewRecognitionRef.current) {
      try {
        previewRecognitionRef.current.onresult = null;
        previewRecognitionRef.current.onerror = null;
        previewRecognitionRef.current.onend = null;
        previewRecognitionRef.current.abort();
      } catch {
        // ignore
      }
      previewRecognitionRef.current = null;
    }
  }, []);

  const stopBargeInMonitor = useCallback(() => {
    if (bargeInRafRef.current !== null) {
      cancelAnimationFrame(bargeInRafRef.current);
      bargeInRafRef.current = null;
    }
    if (bargeInCleanupRef.current) {
      bargeInCleanupRef.current();
      bargeInCleanupRef.current = null;
    }
    bargeInFramesRef.current = 0;
  }, []);

  const startBargeInMonitor = useCallback(() => {
    stopBargeInMonitor();
    if (!voiceSettingsRef.current.autoBargeIn || !mediaStreamRef.current) return;
    try {
      if (!audioCtxRef.current || audioCtxRef.current.state === "closed") {
        const AudioCtx =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        audioCtxRef.current = new AudioCtx();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === "suspended") void ctx.resume();
      const source = ctx.createMediaStreamSource(mediaStreamRef.current);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      const data = new Uint8Array(analyser.frequencyBinCount);
      bargeInCleanupRef.current = () => {
        try {
          source.disconnect();
          analyser.disconnect();
        } catch {
          // ignore
        }
      };

      const tick = () => {
        if (!activeRef.current || stateRef.current !== "assistant_speaking" || isMutedRef.current) {
          stopBargeInMonitor();
          return;
        }
        analyser.getByteTimeDomainData(data);
        let sum = 0;
        for (let i = 0; i < data.length; i += 1) {
          const v = (data[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.round(Math.sqrt(sum / data.length) * 200);
        if (rms > 38) {
          bargeInFramesRef.current += 1;
          if (bargeInFramesRef.current >= 14) {
            stopBargeInMonitor();
            if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
              wsRef.current.send(JSON.stringify({ type: "interrupt" }));
            }
            stopPlaybackRef.current();
            updateState("interrupted");
            beginWsUtteranceCaptureRef.current();
            return;
          }
        } else {
          bargeInFramesRef.current = Math.max(0, bargeInFramesRef.current - 1);
        }
        bargeInRafRef.current = requestAnimationFrame(tick);
      };
      bargeInRafRef.current = requestAnimationFrame(tick);
    } catch {
      // ignore if AudioContext unavailable
    }
  }, [stopBargeInMonitor, updateState]);

  const stopPlayback = useCallback(() => {
    stopBargeInMonitor();
    audioQueueRef.current = [];
    pendingChunkMetaRef.current = null;
    awaitingMoreChunksRef.current = false;
    if (audioPlayerRef.current) {
      try {
        audioPlayerRef.current.onended = null;
        audioPlayerRef.current.onerror = null;
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
      } catch {
        // ignore
      }
      audioPlayerRef.current = null;
    }
    if (audioObjectUrlRef.current) {
      URL.revokeObjectURL(audioObjectUrlRef.current);
      audioObjectUrlRef.current = null;
    }
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      try {
        window.speechSynthesis.cancel();
      } catch {
        // ignore
      }
    }
  }, [stopBargeInMonitor]);

  stopPlaybackRef.current = stopPlayback;

  const stopAllResources = useCallback(() => {
    activeRef.current = false;
    forceSendRef.current = false;
    hasSpokenRef.current = false;

    if (vadTimerRef.current !== null) {
      window.clearInterval(vadTimerRef.current);
      vadTimerRef.current = null;
    }

    if (mediaRecorderRef.current) {
      try {
        mediaRecorderRef.current.onstop = null;
        if (mediaRecorderRef.current.state !== "inactive") {
          mediaRecorderRef.current.stop();
        }
      } catch {
        // ignore
      }
      mediaRecorderRef.current = null;
    }
    chunksRef.current = [];

    if (audioCtxRef.current) {
      try {
        audioCtxRef.current.close();
      } catch {
        // ignore
      }
      audioCtxRef.current = null;
    }

    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }

    if (wsRef.current) {
      try {
        wsRef.current.onclose = null;
        wsRef.current.onerror = null;
        wsRef.current.close();
      } catch {
        // ignore
      }
      wsRef.current = null;
    }

    if (recognitionRef.current) {
      try {
        recognitionRef.current.onend = null;
        recognitionRef.current.onerror = null;
        recognitionRef.current.abort();
      } catch {
        // ignore
      }
      recognitionRef.current = null;
    }

    stopPreviewRecognition();
    stopPlayback();
    setAudioLevel(0);
    setInterimTranscript("");
  }, [stopPlayback, stopPreviewRecognition]);

  useEffect(() => {
    return () => {
      stopAllResources();
    };
  }, [stopAllResources]);

  // ── Live Caption Preview for Local-WS Mode ─────────────────────────

  const startLiveCaptionPreview = useCallback(() => {
    const SpeechRec = getSpeechRecognitionCtor();
    if (!SpeechRec || !activeRef.current) return;
    // Keep existing continuous recognition warm across turns to eliminate per-turn cold-start delay
    if (previewRecognitionRef.current) return;

    try {
      const rec = new SpeechRec();
      rec.lang = "en-IN";
      rec.continuous = true;
      rec.interimResults = true;
      rec.maxAlternatives = 1;
      previewRecognitionRef.current = rec;
      previewCursorRef.current = 0;
      latestPreviewLenRef.current = 0;

      rec.onresult = (event: SpeechRecognitionEvent) => {
        if (!activeRef.current) return;
        latestPreviewLenRef.current = event.results.length;
        if (stateRef.current !== "listening" && stateRef.current !== "user_speaking") {
          // Advance cursor past any tokens captured while KAM was speaking
          previewCursorRef.current = event.results.length;
          return;
        }
        let text = "";
        for (let i = previewCursorRef.current; i < event.results.length; i++) {
          const t = event.results[i][0]?.transcript || "";
          if (t) text += (text ? " " : "") + t;
        }
        const trimmed = text.trim();
        if (trimmed) {
          hasBrowserPreviewRef.current = true;
          lastBrowserPreviewAtRef.current = performance.now();
          setInterimTranscript(trimmed);
          if (!hasSpokenRef.current) {
            hasSpokenRef.current = true;
            updateState("user_speaking");
          }
        }
      };

      rec.onerror = (event: SpeechRecognitionErrorEvent) => {
        hasBrowserPreviewRef.current = false;
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          previewRecognitionRef.current = null;
        }
      };

      rec.onend = () => {
        if (previewRecognitionRef.current === rec) {
          previewRecognitionRef.current = null;
        }
        previewCursorRef.current = 0;
        latestPreviewLenRef.current = 0;
        hasBrowserPreviewRef.current = false;
        if (
          activeRef.current &&
          modeRef.current === "local-ws" &&
          (stateRef.current === "listening" || stateRef.current === "user_speaking")
        ) {
          window.setTimeout(() => {
            if (
              activeRef.current &&
              modeRef.current === "local-ws" &&
              (stateRef.current === "listening" || stateRef.current === "user_speaking")
            ) {
              startLiveCaptionPreview();
            }
          }, 150);
        }
      };

      rec.start();
    } catch {
      previewRecognitionRef.current = null;
      hasBrowserPreviewRef.current = false;
    }
  }, [updateState]);

  // ── Local WebSocket Pipeline (faster-whisper + Piper) ──────────────

  const beginWsUtteranceCapture = useCallback(() => {
    const stream = mediaStreamRef.current;
    const ws = wsRef.current;
    if (!activeRef.current || !stream || !ws || ws.readyState !== WebSocket.OPEN) return;

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      try {
        mediaRecorderRef.current.onstop = null;
        mediaRecorderRef.current.stop();
      } catch {
        // ignore
      }
    }
    if (vadTimerRef.current !== null) {
      window.clearInterval(vadTimerRef.current);
      vadTimerRef.current = null;
    }

    chunksRef.current = [];
    hasSpokenRef.current = false;
    forceSendRef.current = false;
    hasBrowserPreviewRef.current = false;
    lastBrowserPreviewAtRef.current = 0;
    previewCursorRef.current = latestPreviewLenRef.current;
    setInterimTranscript("");

    const mimeType = getSupportedMimeType();
    const recorder = mimeType
      ? new MediaRecorder(stream, { mimeType })
      : new MediaRecorder(stream);
    mediaRecorderRef.current = recorder;

    let silenceStart: number | null = null;
    let speechStartAt = 0;
    let lastPartialSent = 0;
    let noiseSamples = 0;
    let noiseSum = 0;
    let noiseFloor = 0.004;
    const startedAt = performance.now();

    recorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        chunksRef.current.push(e.data);
      }
    };

    recorder.onstop = async () => {
      if (vadTimerRef.current !== null) {
        window.clearInterval(vadTimerRef.current);
        vadTimerRef.current = null;
      }
      previewCursorRef.current = latestPreviewLenRef.current;
      hasBrowserPreviewRef.current = false;

      const chunks = chunksRef.current;
      const shouldSend = hasSpokenRef.current || forceSendRef.current;
      chunksRef.current = [];
      hasSpokenRef.current = false;
      forceSendRef.current = false;

      if (!activeRef.current || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
        return;
      }

      if (!shouldSend || chunks.length === 0) {
        setInterimTranscript("");
        if (activeRef.current && stateRef.current === "listening") {
          beginWsUtteranceCapture();
        }
        return;
      }

      try {
        updateState("processing");
        const blob = new Blob(chunks, { type: mimeType || "audio/webm" });
        const buffer = await blob.arrayBuffer();
        wsRef.current.send(JSON.stringify({ type: "audio_start" }));
        wsRef.current.send(buffer);
        wsRef.current.send(JSON.stringify({ type: "audio_end" }));
      } catch (err) {
        console.error("Failed to send audio utterance:", err);
        setInterimTranscript("");
        if (activeRef.current) {
          updateState("listening");
          beginWsUtteranceCapture();
        }
      }
    };

    recorder.start(100);
    updateState("listening");
    startLiveCaptionPreview();

    try {
      if (!audioCtxRef.current) {
        const AudioCtx =
          window.AudioContext ||
          (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        audioCtxRef.current = new AudioCtx();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === "suspended") {
        ctx.resume().catch(() => {});
      }
      const source = ctx.createMediaStreamSource(stream);
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 1024;
      source.connect(analyser);
      const data = new Float32Array(analyser.fftSize);

      vadTimerRef.current = window.setInterval(() => {
        if (!activeRef.current) return;
        if (stateRef.current !== "listening" && stateRef.current !== "user_speaking") {
          setAudioLevel(0);
          return;
        }

        analyser.getFloatTimeDomainData(data);
        let sumSq = 0;
        for (let i = 0; i < data.length; i++) {
          sumSq += data[i] * data[i];
        }
        const rms = Math.sqrt(sumSq / data.length);
        const level = Math.min(100, Math.round(rms * 650));
        setAudioLevel(level);

        // Adaptive noise floor from first ~500ms
        if (!hasSpokenRef.current && noiseSamples < 8) {
          noiseSamples++;
          noiseSum += rms;
          noiseFloor = Math.min(0.012, Math.max(0.002, noiseSum / noiseSamples));
        }

        const speechThreshold = Math.max(0.007, noiseFloor * 2.2);
        const now = performance.now();

        if (hasSpokenRef.current && speechStartAt === 0) {
          speechStartAt = now;
        }

        if (rms > speechThreshold) {
          if (!hasSpokenRef.current) {
            hasSpokenRef.current = true;
            speechStartAt = now;
            lastPartialSent = 0;
            updateState("user_speaking");
          }
          silenceStart = null;
        } else if (hasSpokenRef.current) {
          if (silenceStart === null) {
            silenceStart = now;
          } else if (now - silenceStart >= 900) {
            if (recorder.state === "recording") {
              recorder.stop();
            }
            return;
          }
        } else if (now - startedAt >= 15000) {
          if (recorder.state === "recording") {
            recorder.stop();
          }
          return;
        }

        // Stream fast server partial snapshots right away when browser Web Speech isn't active or pauses
        const browserPreviewStale =
          !hasBrowserPreviewRef.current || now - lastBrowserPreviewAtRef.current > 850;
        if (
          hasSpokenRef.current &&
          browserPreviewStale &&
          now - speechStartAt >= 260 &&
          (lastPartialSent === 0 || now - lastPartialSent >= 450) &&
          chunksRef.current.length > 0 &&
          wsRef.current?.readyState === WebSocket.OPEN
        ) {
          lastPartialSent = now;
          const snapshot = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
          blobToBase64(snapshot)
            .then((b64) => {
              if (
                activeRef.current &&
                stateRef.current === "user_speaking" &&
                wsRef.current?.readyState === WebSocket.OPEN
              ) {
                wsRef.current.send(JSON.stringify({ type: "audio_partial", data: b64 }));
              }
            })
            .catch(() => {});
        }
      }, 60);
    } catch {
      // If Web Audio API fails, live caption preview + manual finishTurn() still work
    }
  }, [startLiveCaptionPreview, updateState]);

  const tryConnectLocalWs = useCallback((wsUrl: string): Promise<WebSocket> => {
    return new Promise((resolve, reject) => {
      let settled = false;
      const ws = new WebSocket(wsUrl);
      ws.binaryType = "blob";

      const timer = window.setTimeout(() => {
        if (!settled) {
          settled = true;
          try {
            ws.close();
          } catch {
            // ignore
          }
          reject(new Error("Voice WebSocket connection timed out"));
        }
      }, 1500);

      ws.onopen = () => {
        if (!settled) {
          settled = true;
          window.clearTimeout(timer);
          resolve(ws);
        }
      };

      ws.onerror = () => {
        if (!settled) {
          settled = true;
          window.clearTimeout(timer);
          reject(new Error("Voice WebSocket unavailable"));
        }
      };
    });
  }, []);

  // ── Browser Fallback Mode (Web Speech API) ─────────────────────────

  const speakBrowserText = useCallback(
    (text: string): Promise<void> => {
      return new Promise((resolve) => {
        if (
          isMutedRef.current ||
          typeof window === "undefined" ||
          !("speechSynthesis" in window) ||
          !text.trim()
        ) {
          resolve();
          return;
        }

        try {
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.lang = "en-IN";
          utterance.rate = voiceSettingsRef.current.speechRate;
          utterance.pitch = 1.0;

          const voices = window.speechSynthesis.getVoices();
          const preferred =
            voices.find((v) => /en[-_]IN/i.test(v.lang) && /neerja|natural|google|india/i.test(v.name)) ||
            voices.find((v) => /en[-_]IN/i.test(v.lang)) ||
            voices.find((v) => v.lang.startsWith("en"));
          if (preferred) utterance.voice = preferred;

          let done = false;
          const finish = () => {
            if (!done) {
              done = true;
              window.clearTimeout(safetyTimer);
              resolve();
            }
          };
          const safetyTimer = window.setTimeout(finish, Math.max(5000, text.length * 95));

          utterance.onend = finish;
          utterance.onerror = finish;

          updateState("assistant_speaking");
          window.speechSynthesis.speak(utterance);
        } catch {
          resolve();
        }
      });
    },
    [updateState]
  );

  const startBrowserListening = useCallback(() => {
    const SpeechRec = getSpeechRecognitionCtor();
    if (!SpeechRec || !activeRef.current) return;

    if (recognitionRef.current) {
      try {
        recognitionRef.current.onend = null;
        recognitionRef.current.abort();
      } catch {
        // ignore
      }
    }

    const recognition = new SpeechRec();
    recognition.lang = "en-IN";
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognitionRef.current = recognition;

    let handledFinal = false;

    recognition.onstart = () => {
      if (activeRef.current) {
        updateState("listening");
        setAudioLevel(20);
      }
    };

    recognition.onspeechstart = () => {
      if (activeRef.current) {
        updateState("user_speaking");
        setAudioLevel(65);
      }
    };

    recognition.onresult = async (event: SpeechRecognitionEvent) => {
      let interim = "";
      let finalText = "";
      for (let i = 0; i < event.results.length; i++) {
        const res = event.results[i];
        const txt = res[0]?.transcript || "";
        if (res.isFinal) {
          finalText += (finalText ? " " : "") + txt;
        } else {
          interim += (interim ? " " : "") + txt;
        }
      }

      const combined = `${finalText} ${interim}`.trim();
      if (combined) {
        setInterimTranscript(combined);
        updateState("user_speaking");
      }

      const allFinal =
        event.results.length > 0 &&
        event.results[event.results.length - 1].isFinal;

      if (allFinal && finalText.trim() && !handledFinal) {
        handledFinal = true;
        const cleanText = finalText.trim();
        setInterimTranscript("");
        setAudioLevel(0);
        try {
          recognition.stop();
        } catch {
          // ignore
        }

        addMessage("user", cleanText, "voice");
        updateState("processing");

        try {
          const reply = await chat({
            message: cleanText,
            channel: "voice",
            conversation_id: conversationIdRef.current,
          });
          if (reply.conversation_id && reply.conversation_id !== "new") {
            conversationIdRef.current = reply.conversation_id;
          }
          addMessage("assistant", reply.response_text, "voice", reply.tool_activity, {
            specialistsConsulted: reply.specialists_consulted ?? undefined,
            recommendationIds: reply.recommendation_ids,
          });

          const toSpeak = reply.spoken_text || reply.response_text;
          if (activeRef.current) {
            await speakBrowserText(toSpeak);
          }
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Failed to reach KAM backend";
          setError(msg);
          addMessage(
            "assistant",
            `Sorry, I hit an error reaching the assistant (${msg}).`,
            "voice"
          );
        }

        if (activeRef.current) {
          startBrowserListening();
        }
      }
    };

    recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
      setAudioLevel(0);
      if (event.error === "aborted") return;

      if (event.error === "no-speech") {
        return;
      }

      if (event.error === "not-allowed" || event.error === "service-not-allowed") {
        setPermissionDenied(true);
        setError("Microphone access denied. Please allow microphone permission in your browser.");
        activeRef.current = false;
        updateState("error");
        return;
      }

      if (event.error === "network") {
        setError(
          "Browser speech recognition requires internet access. For offline voice, start voice-service (port 8765)."
        );
        activeRef.current = false;
        updateState("error");
        return;
      }

      setError(`Voice recognition error: ${event.error}`);
      activeRef.current = false;
      updateState("error");
    };

    recognition.onend = () => {
      setAudioLevel(0);
      if (!handledFinal) {
        setInterimTranscript("");
      }
      if (
        activeRef.current &&
        !handledFinal &&
        stateRef.current !== "processing" &&
        stateRef.current !== "assistant_speaking"
      ) {
        window.setTimeout(() => {
          if (
            activeRef.current &&
            stateRef.current !== "processing" &&
            stateRef.current !== "assistant_speaking"
          ) {
            startBrowserListening();
          }
        }, 150);
      }
    };

    try {
      recognition.start();
    } catch {
      // Ignore if already started
    }
  }, [addMessage, speakBrowserText, updateState]);

  // ── Public Controls ────────────────────────────────────────────────

  const start = useCallback(async () => {
    if (stateRef.current !== "idle" && stateRef.current !== "error") return;

    setError(null);
    setPermissionDenied(false);
    activeRef.current = true;
    updateState("connecting");

    let stream: MediaStream;
    try {
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("Microphone API unavailable in this browser context.");
      }
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });
      mediaStreamRef.current = stream;
    } catch {
      activeRef.current = false;
      setPermissionDenied(true);
      setError("Microphone permission denied or no microphone device found.");
      updateState("error");
      return;
    }

    if (!activeRef.current) {
      stream.getTracks().forEach((t) => t.stop());
      return;
    }

    // Attempt local WebSocket voice-service first (with strict timeouts so we never stall in "connecting")
    try {
      const session = await Promise.race([
        getVoiceSession(),
        new Promise<never>((_, reject) =>
          window.setTimeout(() => reject(new Error("Voice session request timed out")), 2500)
        ),
      ]);
      const ws = await tryConnectLocalWs(session.pipecat_ws_url);
      if (!activeRef.current) {
        ws.close();
        return;
      }

      wsRef.current = ws;
      modeRef.current = "local-ws";
      setMode("local-ws");

      let readyTimer: number | null = null;
      let greetTimer: number | null = null;
      let audioWaitTimer: number | null = null;

      const clearHandshakeTimers = () => {
        if (readyTimer !== null) {
          window.clearTimeout(readyTimer);
          readyTimer = null;
        }
        if (greetTimer !== null) {
          window.clearTimeout(greetTimer);
          greetTimer = null;
        }
        if (audioWaitTimer !== null) {
          window.clearTimeout(audioWaitTimer);
          audioWaitTimer = null;
        }
      };

      const startListeningAfterAudioWait = () => {
        if (audioWaitTimer !== null) window.clearTimeout(audioWaitTimer);
        audioWaitTimer = window.setTimeout(() => {
          audioWaitTimer = null;
          if (activeRef.current && stateRef.current === "assistant_speaking" && !audioPlayerRef.current) {
            beginWsUtteranceCapture();
          }
        }, 12000);
      };

      // If voice-service doesn't emit "ready" within 2s, fall through to listening immediately
      readyTimer = window.setTimeout(() => {
        readyTimer = null;
        if (activeRef.current && stateRef.current === "connecting") {
          addMessage("assistant", GREETING_TEXT, "voice");
          beginWsUtteranceCapture();
        }
      }, 2000);

      greetedRef.current = false;
      pendingChunkMetaRef.current = null;
      audioQueueRef.current = [];
      awaitingMoreChunksRef.current = false;

      const playNextQueuedAudio = () => {
        if (!activeRef.current || isMutedRef.current) {
          stopPlayback();
          if (activeRef.current) beginWsUtteranceCapture();
          return;
        }
        const nextItem = audioQueueRef.current.shift();
        if (!nextItem) {
          if (awaitingMoreChunksRef.current) {
            startListeningAfterAudioWait();
            return;
          }
          stopPlayback();
          if (activeRef.current) beginWsUtteranceCapture();
          return;
        }

        if (audioPlayerRef.current) {
          try {
            audioPlayerRef.current.onended = null;
            audioPlayerRef.current.onerror = null;
            audioPlayerRef.current.pause();
          } catch {
            // ignore
          }
          audioPlayerRef.current = null;
        }
        if (audioObjectUrlRef.current) {
          URL.revokeObjectURL(audioObjectUrlRef.current);
          audioObjectUrlRef.current = null;
        }

        const url = URL.createObjectURL(nextItem.blob);
        audioObjectUrlRef.current = url;
        const audio = new Audio(url);
        audioPlayerRef.current = audio;
        updateState("assistant_speaking");
        if (voiceSettingsRef.current.autoBargeIn) {
          startBargeInMonitor();
        }

        const finishChunk = () => {
          if (audioPlayerRef.current === audio) {
            audioPlayerRef.current = null;
          }
          if (audioObjectUrlRef.current === url) {
            URL.revokeObjectURL(url);
            audioObjectUrlRef.current = null;
          }
          if (nextItem.isFinal && audioQueueRef.current.length === 0) {
            awaitingMoreChunksRef.current = false;
            stopPlayback();
            if (activeRef.current) beginWsUtteranceCapture();
          } else {
            playNextQueuedAudio();
          }
        };

        audio.onended = finishChunk;
        audio.onerror = finishChunk;
        audio.play().catch(finishChunk);
      };

      ws.onmessage = (event) => {
        if (!activeRef.current) return;

        if (typeof event.data === "string") {
          try {
            const msg = JSON.parse(event.data);
            if (msg.type === "ready") {
              if (readyTimer !== null) {
                window.clearTimeout(readyTimer);
                readyTimer = null;
              }
              if (Array.isArray(msg.available_voices) && msg.available_voices.length > 0) {
                setAvailableVoices(msg.available_voices);
              }
              if (msg.tts_voice) {
                const isOffline = String(msg.tts_voice).startsWith("offline-");
                setActiveEngineLabel(isOffline ? "Offline Local Voice" : "Indian Neural Voice");
              }
              if (!greetedRef.current) {
                greetedRef.current = true;
                ws.send(JSON.stringify({ type: "greet", text: GREETING_TEXT }));
                // Fallback in case older voice-service doesn't handle "greet"
                greetTimer = window.setTimeout(async () => {
                  greetTimer = null;
                  if (activeRef.current && stateRef.current === "connecting") {
                    addMessage("assistant", GREETING_TEXT, "voice");
                    await speakBrowserText(GREETING_TEXT);
                    if (activeRef.current) beginWsUtteranceCapture();
                  }
                }, 1500);
              }
            } else if (msg.type === "tts_chunk_meta") {
              pendingChunkMetaRef.current = {
                mimeType: msg.mime_type || "audio/wav",
                isFinal: Boolean(msg.is_final),
                voiceId: msg.voice_id,
              };
              awaitingMoreChunksRef.current = !msg.is_final;
              if (msg.voice_id) {
                setActiveEngineLabel(
                  String(msg.voice_id).startsWith("offline-")
                    ? "Offline Local (Piper)"
                    : "Indian Neural Voice"
                );
              }
            } else if (msg.type === "greeting" && msg.text) {
              if (greetTimer !== null) {
                window.clearTimeout(greetTimer);
                greetTimer = null;
              }
              addMessage("assistant", msg.text, "voice");
              if (isMutedRef.current) {
                beginWsUtteranceCapture();
              } else {
                updateState("assistant_speaking");
                awaitingMoreChunksRef.current = true;
                startListeningAfterAudioWait();
              }
            } else if (msg.type === "partial_transcript" && msg.text) {
              if (
                stateRef.current === "user_speaking" &&
                (!hasBrowserPreviewRef.current ||
                  performance.now() - lastBrowserPreviewAtRef.current > 700)
              ) {
                setInterimTranscript(msg.text);
              }
            } else if (msg.type === "transcript" && msg.text) {
              setInterimTranscript("");
              addMessage("user", msg.text, "voice");
              updateState("processing");
            } else if (msg.type === "response" && msg.text) {
              setInterimTranscript("");
              if (msg.conversation_id) {
                conversationIdRef.current = msg.conversation_id;
              }
              addMessage("assistant", msg.text, "voice", msg.tool_activity, {
                specialistsConsulted: msg.specialists_consulted,
                recommendationIds: msg.recommendation_ids,
                actionPerformed: msg.action_performed,
              });
              if (msg.action_performed) {
                window.dispatchEvent(new CustomEvent("kam:recommendations-updated"));
              }
              if (isMutedRef.current) {
                beginWsUtteranceCapture();
              } else {
                updateState("assistant_speaking");
                awaitingMoreChunksRef.current = true;
                startListeningAfterAudioWait();
              }
            } else if (msg.type === "no_speech" || msg.type === "audio_unavailable") {
              if (audioWaitTimer !== null) {
                window.clearTimeout(audioWaitTimer);
                audioWaitTimer = null;
              }
              awaitingMoreChunksRef.current = false;
              setInterimTranscript("");
              if (activeRef.current) {
                beginWsUtteranceCapture();
              }
            } else if (msg.type === "error") {
              if (audioWaitTimer !== null) {
                window.clearTimeout(audioWaitTimer);
                audioWaitTimer = null;
              }
              awaitingMoreChunksRef.current = false;
              setInterimTranscript("");
              setError(msg.message || "Voice service error");
              if (activeRef.current) {
                beginWsUtteranceCapture();
              }
            }
          } catch {
            // ignore malformed JSON
          }
        } else if (event.data instanceof Blob) {
          if (audioWaitTimer !== null) {
            window.clearTimeout(audioWaitTimer);
            audioWaitTimer = null;
          }
          const meta = pendingChunkMetaRef.current;
          pendingChunkMetaRef.current = null;
          const typedBlob = new Blob([event.data], { type: meta?.mimeType || "audio/wav" });
          const isFinal = meta ? meta.isFinal : true;
          awaitingMoreChunksRef.current = !isFinal;

          if (isMutedRef.current) {
            if (isFinal && activeRef.current) beginWsUtteranceCapture();
            return;
          }

          audioQueueRef.current.push({
            blob: typedBlob,
            isFinal,
            voiceId: meta?.voiceId,
          });
          if (!audioPlayerRef.current) {
            playNextQueuedAudio();
          }
        }
      };

      ws.onclose = () => {
        clearHandshakeTimers();
        if (activeRef.current) {
          stopAllResources();
          modeRef.current = "none";
          setMode("none");
          updateState("idle");
        }
      };

      ws.onerror = () => {
        clearHandshakeTimers();
        if (activeRef.current) {
          setError("Voice connection lost. Switched back to text mode.");
          stopAllResources();
          modeRef.current = "none";
          setMode("none");
          updateState("error");
        }
      };

      ws.send(
        JSON.stringify({
          type: "config",
          seller_id: session.seller_id,
          session_id: session.session_id,
          conversation_id: conversationIdRef.current,
          voice_id: voiceSettingsRef.current.voiceId,
          speech_rate: voiceSettingsRef.current.speechRate,
          stt_model: voiceSettingsRef.current.sttModel,
        })
      );
      return;
    } catch {
      // Local voice-service unavailable — fall back to Browser Web Speech API
    }

    const SpeechRec = getSpeechRecognitionCtor();
    if (!SpeechRec) {
      stream.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
      activeRef.current = false;
      modeRef.current = "none";
      setMode("none");
      setError(
        "Local voice-service (port 8765) is not running and this browser does not support Web Speech Recognition. Use Chrome/Edge or start voice-service."
      );
      updateState("error");
      return;
    }

    stream.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;

    modeRef.current = "browser";
    setMode("browser");
    addMessage("assistant", GREETING_TEXT, "voice");
    await speakBrowserText(GREETING_TEXT);
    if (activeRef.current) {
      startBrowserListening();
    }
  }, [
    addMessage,
    beginWsUtteranceCapture,
    speakBrowserText,
    startBargeInMonitor,
    startBrowserListening,
    stopAllResources,
    stopPlayback,
    tryConnectLocalWs,
    updateState,
  ]);

  const stop = useCallback(() => {
    updateState("stopping");
    stopAllResources();
    modeRef.current = "none";
    setMode("none");
    updateState("idle");
  }, [stopAllResources, updateState]);

  const interrupt = useCallback(() => {
    stopPlayback();
    setInterimTranscript("");
    if (modeRef.current === "local-ws" && wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "interrupt" }));
      updateState("interrupted");
      beginWsUtteranceCapture();
    } else if (modeRef.current === "browser" && activeRef.current) {
      updateState("interrupted");
      startBrowserListening();
    }
  }, [beginWsUtteranceCapture, startBrowserListening, stopPlayback, updateState]);

  const finishTurn = useCallback(() => {
    if (modeRef.current === "local-ws" && mediaRecorderRef.current?.state === "recording") {
      forceSendRef.current = true;
      mediaRecorderRef.current.stop();
    } else if (modeRef.current === "browser" && recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }
  }, []);

  const toggleMute = useCallback(() => {
    const next = !isMutedRef.current;
    isMutedRef.current = next;
    setIsMuted(next);
    if (next) {
      stopPlayback();
      if (stateRef.current === "assistant_speaking") {
        if (modeRef.current === "local-ws") {
          beginWsUtteranceCapture();
        } else if (modeRef.current === "browser" && activeRef.current) {
          startBrowserListening();
        }
      }
    }
  }, [beginWsUtteranceCapture, startBrowserListening, stopPlayback]);

  const setActiveSessionId = useCallback((id: string | null) => {
    setActiveSessionIdState(id);
    conversationIdRef.current = id || undefined;
  }, []);

  const hydrateSessionMessages = useCallback(
    (
      sessionId: string,
      rows: Array<{ role: "user" | "assistant"; content: string; sequence_no: number }>
    ) => {
      setActiveSessionIdState(sessionId);
      conversationIdRef.current = sessionId;
      setError(null);
      setMessages(
        rows.map((r) => ({
          id: `${sessionId}-${r.sequence_no}`,
          role: r.role,
          content: r.content,
          timestamp: new Date(),
          channel: "text",
        }))
      );
    },
    []
  );

  const resetChatPane = useCallback(() => {
    setActiveSessionIdState(null);
    conversationIdRef.current = undefined;
    setMessages([]);
    setInterimTranscript("");
    setError(null);
  }, []);

  const sendText = useCallback(
    async (text: string, sessionIdOverride?: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;

      if (sessionIdOverride) {
        setActiveSessionIdState(sessionIdOverride);
        conversationIdRef.current = sessionIdOverride;
      }

      setError(null);
      addMessage("user", trimmed, "text");

      const prevState = stateRef.current;
      updateState("processing");

      try {
        const response = await chat({
          message: trimmed,
          channel: "text",
          conversation_id: sessionIdOverride ?? conversationIdRef.current,
        });
        if (response.conversation_id && response.conversation_id !== "new") {
          conversationIdRef.current = response.conversation_id;
        }
        addMessage("assistant", response.response_text, "text", response.tool_activity, {
          specialistsConsulted: response.specialists_consulted ?? undefined,
          recommendationIds: response.recommendation_ids,
        });
      } catch (err) {
        const msg = err instanceof Error ? err.message : "Unknown error";
        setError(msg);
        addMessage(
          "assistant",
          `Sorry, I couldn't process that right now (${msg}).`,
          "text"
        );
      } finally {
        if (activeRef.current) {
          updateState(prevState === "idle" ? "listening" : prevState);
        } else {
          updateState("idle");
        }
      }
    },
    [addMessage, updateState]
  );

  const summarizeCall = useCallback(async () => {
    setError(null);
    if (modeRef.current === "local-ws" && wsRef.current?.readyState === WebSocket.OPEN) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
        try {
          mediaRecorderRef.current.onstop = null;
          mediaRecorderRef.current.stop();
        } catch {
          // ignore
        }
      }
      previewCursorRef.current = latestPreviewLenRef.current;
      hasBrowserPreviewRef.current = false;
      addMessage("user", "Please summarise our call, recommendations, and next steps.", "voice");
      updateState("processing");
      wsRef.current.send(JSON.stringify({ type: "text_turn", text: SUMMARY_PROMPT }));
      return;
    }

    if (modeRef.current === "browser" && activeRef.current) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.onend = null;
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
      addMessage("user", "Please summarise our call, recommendations, and next steps.", "voice");
      updateState("processing");
      try {
        const reply = await chat({
          message: SUMMARY_PROMPT,
          channel: "voice",
          conversation_id: conversationIdRef.current,
        });
        if (reply.conversation_id && reply.conversation_id !== "new") {
          conversationIdRef.current = reply.conversation_id;
        }
        addMessage("assistant", reply.response_text, "voice", reply.tool_activity, {
          specialistsConsulted: reply.specialists_consulted ?? undefined,
          recommendationIds: reply.recommendation_ids,
        });
        await speakBrowserText(reply.spoken_text || reply.response_text);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to summarize call");
      }
      if (activeRef.current) {
        startBrowserListening();
      }
      return;
    }

    await sendText(SUMMARY_PROMPT);
  }, [
    addMessage,
    sendText,
    speakBrowserText,
    startBrowserListening,
    updateState,
  ]);

  const clearError = useCallback(() => {
    setError(null);
    if (stateRef.current === "error") {
      updateState("idle");
    }
  }, [updateState]);

  useEffect(() => {
    stopPlaybackRef.current = stopPlayback;
    beginWsUtteranceCaptureRef.current = beginWsUtteranceCapture;
  }, [stopPlayback, beginWsUtteranceCapture]);

  return {
    state,
    mode,
    transcript: messages,
    messages,
    interimTranscript,
    audioLevel,
    isVoiceSupported,
    permissionDenied,
    isMuted,
    error,
    voiceSettings,
    availableVoices,
    activeEngineLabel,
    activeSessionId,
    setActiveSessionId,
    hydrateSessionMessages,
    resetChatPane,
    start,
    stop,
    interrupt,
    finishTurn,
    toggleMute,
    sendText,
    summarizeCall,
    updateVoiceSettings,
    clearError,
  };
}

const VoiceContext = createContext<UseVoiceReturn | null>(null);

export function VoiceProvider({ children }: { children: ReactNode }) {
  const value = useVoiceSession();
  return createElement(VoiceContext.Provider, { value }, children);
}

export function useVoice(): UseVoiceReturn {
  const ctx = useContext(VoiceContext);
  if (!ctx) {
    throw new Error("useVoice must be used within a VoiceProvider");
  }
  return ctx;
}
