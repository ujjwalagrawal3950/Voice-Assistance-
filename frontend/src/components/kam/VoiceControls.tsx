/** Voice start/stop control with full state machine UI. */
import { Mic, MicOff, RefreshCw, AlertCircle, Loader2, Speaker } from 'lucide-react'
import type { VoiceState } from '@/hooks/useVoice'
import { cn } from '@/lib/utils'

interface VoiceControlsProps {
  state: VoiceState
  isVoiceSupported: boolean
  permissionDenied: boolean
  error: string | null
  onStart: () => Promise<void>
  onStop: () => void
}

export function VoiceControls({
  state,
  isVoiceSupported,
  permissionDenied,
  error,
  onStart,
  onStop,
}: VoiceControlsProps) {
  const labels: Record<string, { label: string; sub: string; icon: React.ElementType }> = {
    idle: { label: 'Start voice', sub: 'Hold to speak', icon: Mic },
    connecting: { label: 'Connecting…', sub: 'Establishing voice session', icon: Loader2 },
    listening: { label: 'Listening', sub: 'Speak now', icon: Mic },
    user_speaking: { label: 'You are speaking', sub: '…', icon: Mic },
    processing: { label: 'Thinking', sub: 'KAM is reasoning', icon: Loader2 },
    assistant_speaking: { label: 'KAM is speaking', sub: '…', icon: Speaker },
    reconnecting: { label: 'Reconnecting…', sub: 'Restoring session', icon: RefreshCw },
    error: { label: 'Voice unavailable', sub: 'Use text below', icon: AlertCircle },
    stopping: { label: 'Stopping…', sub: '…', icon: MicOff },
  }

  const info = labels[state] || labels.idle
  const busy = ['connecting', 'listening', 'user_speaking', 'processing', 'assistant_speaking', 'reconnecting', 'stopping'].includes(state)

  return (
    <div className="rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <div className={cn('h-2.5 w-2.5 rounded-full', state === 'error' || permissionDenied ? 'bg-destructive' : busy ? 'bg-green-500' : 'bg-muted')}>
            {busy && state !== 'error' && state !== 'idle' && state !== 'stopping' && (
              <span className="sr-only">active</span>
            )}
          </div>
          <div>
            <div className="text-sm font-medium text-foreground">{info.label}</div>
            <div className="text-xs text-muted-foreground">{info.sub}</div>
          </div>
        </div>
      </div>

      {!isVoiceSupported && (
        <div className="mb-3 p-2 rounded bg-amber-50/50 text-amber-800 text-xs border border-amber-100">
          Microphone API not detected in this browser. Voice is unavailable; text works normally.
        </div>
      )}

      {permissionDenied && (
        <div className="mb-3 p-2 rounded bg-amber-50/50 text-amber-800 text-xs border border-amber-100">
          Microphone permission was denied. Click “Start voice” to retry, or use text input below.
        </div>
      )}

      {error && state === 'error' && (
        <div className="mb-3 p-2 rounded bg-destructive/10 text-destructive text-xs border border-destructive/30">{error}</div>
      )}

      <div className="flex items-center gap-3">
        {state === 'idle' ? (
          <button
            onClick={onStart}
            disabled={!isVoiceSupported || permissionDenied}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-primary text-primary-foreground px-6 py-2.5 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:bg-primary/90 transition-colors"
          >
            <Mic size={16} strokeWidth={2} /> {isVoiceSupported ? 'Start voice' : 'Voice unsupported'}
          </button>
        ) : state === 'error' || permissionDenied ? (
          <button
            onClick={onStart}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg border border-destructive text-destructive px-6 py-2.5 text-sm font-medium hover:bg-destructive/10 transition-colors"
          >
            <MicOff size={16} strokeWidth={2} /> Retry voice
          </button>
        ) : (
          <button
            onClick={onStop}
            className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-destructive text-destructive-foreground px-6 py-2.5 text-sm font-medium hover:bg-destructive/90 transition-colors"
          >
            <MicOff size={16} strokeWidth={2} /> Stop
          </button>
        )}
      </div>
    </div>
  )
}
