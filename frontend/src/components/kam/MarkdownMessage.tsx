"use client";

import { Fragment, type ReactNode } from "react";

interface MarkdownMessageProps {
  content: string;
  className?: string;
}

const INLINE_TOKEN_RE = /(\*\*[^*]+\*\*|__[^_]+__|`[^`]+`|\*[^*\n]+\*|_(?!_)[^_\n]+_)/g;

function renderInline(text: string): ReactNode[] {
  const parts = text.split(INLINE_TOKEN_RE);
  return parts.map((part, idx) => {
    if (!part) return null;
    if (
      (part.startsWith("**") && part.endsWith("**") && part.length > 4) ||
      (part.startsWith("__") && part.endsWith("__") && part.length > 4)
    ) {
      return (
        <strong key={idx} className="font-semibold text-foreground">
          {renderInline(part.slice(2, -2))}
        </strong>
      );
    }
    if (part.startsWith("`") && part.endsWith("`") && part.length > 2) {
      return (
        <code
          key={idx}
          className="px-1.5 py-0.5 rounded bg-muted text-foreground font-mono text-[0.85em]"
        >
          {part.slice(1, -1)}
        </code>
      );
    }
    if (
      (part.startsWith("*") && part.endsWith("*") && part.length > 2) ||
      (part.startsWith("_") && part.endsWith("_") && part.length > 2)
    ) {
      return (
        <em key={idx} className="italic">
          {renderInline(part.slice(1, -1))}
        </em>
      );
    }
    return <Fragment key={idx}>{part}</Fragment>;
  });
}

function isTableSeparator(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.includes("|") && /^\|?[\s:|-]+\|?$/.test(trimmed);
}

function parseTableCells(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((c) => c.trim());
}

export function MarkdownMessage({ content, className }: MarkdownMessageProps) {
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    // Fenced code block
    if (trimmed.startsWith("```")) {
      const codeLines: string[] = [];
      i += 1;
      while (i < lines.length && !lines[i].trim().startsWith("```")) {
        codeLines.push(lines[i]);
        i += 1;
      }
      i += 1;
      blocks.push(
        <pre
          key={`code-${i}`}
          className="my-2 rounded-lg bg-muted/80 border border-border p-3 overflow-x-auto text-xs font-mono text-foreground"
        >
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      continue;
    }

    // Horizontal rule
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push(<hr key={`hr-${i}`} className="my-3 border-border/70" />);
      i += 1;
      continue;
    }

    // Headings (# .. ####)
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const headingText = headingMatch[2];
      const headingClasses =
        level === 1
          ? "text-base font-bold text-foreground mt-3 mb-1.5 first:mt-0"
          : level === 2
          ? "text-[15px] font-bold text-foreground mt-3 mb-1.5 first:mt-0"
          : "text-sm font-semibold text-primary mt-3 mb-1 first:mt-0 tracking-tight";
      blocks.push(
        <h4 key={`h-${i}`} className={headingClasses}>
          {renderInline(headingText)}
        </h4>
      );
      i += 1;
      continue;
    }

    // Markdown table
    if (
      trimmed.includes("|") &&
      i + 1 < lines.length &&
      isTableSeparator(lines[i + 1])
    ) {
      const headers = parseTableCells(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().includes("|")) {
        rows.push(parseTableCells(lines[i]));
        i += 1;
      }
      blocks.push(
        <div key={`tbl-${i}`} className="my-2.5 overflow-x-auto rounded-lg border border-border">
          <table className="w-full text-xs text-left border-collapse">
            <thead className="bg-muted/70 text-foreground">
              <tr>
                {headers.map((h, hi) => (
                  <th key={hi} className="px-3 py-1.5 font-semibold border-b border-border">
                    {renderInline(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr key={ri} className="border-b border-border/50 last:border-b-0">
                  {headers.map((_, ci) => (
                    <td key={ci} className="px-3 py-1.5 text-foreground/90">
                      {renderInline(row[ci] || "")}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Blockquote
    if (trimmed.startsWith(">")) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith(">")) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i += 1;
      }
      blocks.push(
        <blockquote
          key={`bq-${i}`}
          className="my-2 border-l-2 border-primary/60 pl-3 text-sm text-muted-foreground italic"
        >
          {renderInline(quoteLines.join(" "))}
        </blockquote>
      );
      continue;
    }

    // Bullet or numbered list block (preserves nested indentation)
    const listMatch = line.match(/^(\s*)([-*•]|\d+\.)\s+(.+)$/);
    if (listMatch) {
      const items: Array<{ indent: number; ordered: boolean; marker: string; text: string }> = [];
      while (i < lines.length) {
        const lm = lines[i].match(/^(\s*)([-*•]|\d+\.)\s+(.+)$/);
        if (!lm) break;
        const indentSpaces = lm[1].length;
        const ordered = /^\d+\./.test(lm[2]);
        items.push({
          indent: Math.min(2, Math.floor(indentSpaces / 2)),
          ordered,
          marker: lm[2],
          text: lm[3],
        });
        i += 1;
      }
      blocks.push(
        <ul key={`list-${i}`} className="my-1.5 space-y-1">
          {items.map((item, idx) => (
            <li
              key={idx}
              className="flex items-start gap-2 text-sm leading-relaxed text-foreground"
              style={{ paddingLeft: `${item.indent * 1.1}rem` }}
            >
              <span className="shrink-0 font-semibold text-primary/80 select-none mt-[1px]">
                {item.ordered ? item.marker : "•"}
              </span>
              <span className="min-w-0 flex-1">{renderInline(item.text)}</span>
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Regular paragraph
    const paraLines: string[] = [];
    while (i < lines.length) {
      const cur = lines[i];
      const curTrim = cur.trim();
      if (
        !curTrim ||
        curTrim.startsWith("#") ||
        curTrim.startsWith("```") ||
        curTrim.startsWith(">") ||
        /^(\s*)([-*•]|\d+\.)\s+/.test(cur) ||
        /^(-{3,}|\*{3,}|_{3,})$/.test(curTrim) ||
        (curTrim.includes("|") && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
      ) {
        break;
      }
      paraLines.push(curTrim);
      i += 1;
    }
    blocks.push(
      <p key={`p-${i}`} className="text-sm leading-relaxed text-foreground my-1.5 first:mt-0 last:mb-0">
        {renderInline(paraLines.join(" "))}
      </p>
    );
  }

  return <div className={className}>{blocks}</div>;
}
