/** A single transcript message bubble. */
import { Bot, User as UserIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface MessageProps {
  text: string
  sender: 'user' | 'assistant'
}

export function Message({ text, sender }: MessageProps) {
  const isUser = sender === 'user'
  return (
    <div className={`flex gap-3 ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="p-1.5 rounded-full bg-primary/10 text-primary flex-shrink-0">
          <Bot size={16} strokeWidth={2} />
        </div>
      )}
      <div
        className={cn(
          'rounded-2xl px-4 py-2.5 text-sm text-foreground break-words max-w-[85%] shadow-sm border',
          isUser
            ? 'bg-primary text-primary-foreground ml-auto border-transparent'
            : 'bg-muted text-muted-foreground border-border'
        )}
      >
        {text}
      </div>
      {isUser && (
        <div className="p-1.5 rounded-full bg-secondary/50 text-secondary-foreground flex-shrink-0">
          <UserIcon size={16} strokeWidth={2} />
        </div>
      )}
    </div>
  )
}
