/** Scrollable transcript list. */
import { Message } from './Message'

interface TranscriptProps {
  items: string[]
}

export function Transcript({ items }: TranscriptProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-1">
      {items.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-muted-foreground text-sm">
          No conversation yet. Start by typing a question or using voice.
        </div>
      )}
      {items.map((line, i) => {
        const sender = line.startsWith('You:') ? 'user' : 'assistant'
        const text = line.replace(/^(You:|KAM:)\s*/, '')
        return <Message key={i} text={text} sender={sender} />
      })}
    </div>
  )
}
