/** Prompt chips grounded in the seller's demo data. */
interface SuggestedPromptProps {
  onSelect: (prompt: string) => void
}

const prompts = [
  'Why did my sales fall this month?',
  'Which products are out of stock?',
  'What should I replenish before Diwali?',
  'What is driving cancellations?',
  'Show me my inventory health.',
  'What are my top recommendations?',
]

export function SuggestedPrompts({ onSelect }: SuggestedPromptProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {prompts.map((p, i) => (
        <button
          key={i}
          onClick={() => onSelect(p)}
          className="px-3 py-1.5 rounded-md border border-border bg-muted text-sm text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          {p}
        </button>
      ))}
    </div>
  )
}
