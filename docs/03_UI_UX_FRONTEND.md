# 03 — UI/UX and Frontend Implementation

## Goal

Build a polished seller workspace that makes the Virtual KAM feel like a business partner. Voice is a first-class interaction, but every important result must also be visible and usable in text.

## Design direction

Use the existing design system. If none exists, create a clean, responsive B2B analytics interface:
- Clear hierarchy and readable typography.
- Neutral surfaces with restrained accent colour.
- Consistent spacing, accessible contrast and keyboard focus.
- Avoid decorative charts that do not communicate a decision.
- Use INR formatting and Indian date conventions where appropriate.
- Responsive desktop-first layout that remains usable on mobile.

## Required screens

### 1. Seller overview
- Seller name, category, region and selected date range.
- Revenue, orders, units, ASP, cancellation, return and stockout KPIs.
- Period-over-period change with comparison dates.
- Sales trend and category/SKU contribution.
- Inventory health and urgent alerts.
- “What needs attention today?” prioritised summary.

### 2. Virtual KAM workspace
- Persistent assistant panel or dedicated conversation page.
- Large, obvious voice start/stop control.
- Listening, processing, speaking, interrupted, reconnecting and error states.
- Live user transcript and assistant response text.
- Text input fallback.
- Suggested prompts grounded in the loaded seller data.
- Conversation history and clear-session control.
- Recommendation cards with evidence, impact range, risk, confidence and approval action.

### 3. Product/SKU view
- Search/filter/sort SKU table.
- Sales trend, current stock, stock cover, cancellation/return signals.
- Forecast and replenishment suggestion.
- Show assumptions and confidence intervals.

### 4. Recommendations
- Prioritised action queue.
- Status: new, viewed, approved, rejected, completed, expired.
- Evidence and calculation details.
- Approval confirmation for high-impact actions.

### 5. Seller settings
- Business goals, budget, risk tolerance, margin floor.
- Supplier lead time and storage constraints.
- Location/region and category.
- Data source/prototype status.

## Voice interaction states

Implement an explicit state machine, not a collection of loosely related booleans:

`idle → connecting → listening → user_speaking → processing → assistant_speaking`

Additional transitions:
- `assistant_speaking → listening` on supported barge-in.
- Any active state → `reconnecting` on recoverable disconnect.
- Any state → `error` on unrecoverable failure.
- Any active state → `stopping → idle` when user ends session.

The UI must never show “Listening” if microphone permission is denied or the connection is not active.

## Accessibility and usability

- Microphone permission explanation before first use.
- Visible mute/end controls.
- Keyboard-accessible text fallback.
- Announce important state changes to assistive technology.
- Do not rely on colour alone to indicate status.
- Provide transcript visibility and a way to correct misunderstandings.
- Avoid auto-starting the microphone without an explicit user action.

## Frontend engineering

- Follow existing routing, state management and component patterns.
- Keep audio/session logic in a dedicated hook/service, not inside a large page component.
- Keep API calls in a typed client layer.
- Handle loading, empty, stale and error states.
- Do not put Ollama URLs, STT/TTS secrets or provider credentials in browser environment variables.
- Avoid hardcoded analytics; use API responses.

## Acceptance criteria

- [ ] Dashboard renders from backend data.
- [ ] Seller can navigate between overview, SKUs, recommendations and KAM.
- [ ] Voice UI has all required states and handles permission denial.
- [ ] Text fallback works without voice services.
- [ ] Recommendations display evidence, confidence and approval status.
- [ ] Responsive layout and basic accessibility checks pass.
