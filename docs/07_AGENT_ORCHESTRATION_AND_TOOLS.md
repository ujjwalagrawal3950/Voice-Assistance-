# 07 — Virtual KAM Agent, Tool Calling and Memory

## Goal

Create an agent that can investigate seller questions, combine trusted business tools and produce a concise, actionable KAM response.

## Agent operating loop

1. Understand the seller's question and current context.
2. Determine what evidence is required.
3. Call the relevant read-only tools.
4. Inspect tool results and identify missing information.
5. Run diagnosis/forecast/optimisation services where needed.
6. Compare options against the seller decision profile.
7. Present recommendation, evidence, assumptions, uncertainty and next step.
8. Ask for approval before any consequential action.
9. Record the decision and later outcome when available.

Use a finite, observable workflow. Do not let the LLM silently invent tools or call arbitrary code.

## Tool catalogue

Implement typed, permission-checked tools such as:
- `get_seller_profile`
- `get_dashboard_kpis`
- `get_sales_trend`
- `get_sku_performance`
- `get_inventory_health`
- `get_cancellation_breakdown`
- `get_conversion_funnel`
- `get_forecast`
- `get_festival_calendar`
- `calculate_replenishment_plan`
- `create_recommendation`
- `get_recommendation_history`
- `request_action_approval`

Each tool must have:
- Typed input and output schema.
- Seller scope and permission checks.
- Timeout and error behaviour.
- A clear description of what it does.
- Unit tests.

## Agent response contract

For business advice, use this structure:
1. **What I found** — one or two key findings.
2. **Why it matters** — quantified business impact where supportable.
3. **What I recommend** — up to three prioritised actions.
4. **Trade-off/risk** — budget, margin, uncertainty or operational risk.
5. **What I need from you** — only if a missing decision blocks the next step.

For voice, keep the spoken response natural and concise. The visual transcript can contain more detail.

## System prompt principles

The system prompt should establish:
- You are the seller's Virtual KAM for the currently authenticated seller.
- Use tools for current business facts.
- Never invent metrics, competitor data, dates, stock, or action outcomes.
- Distinguish observed, calculated, forecast and scenario values.
- Explain uncertainty.
- Respect the seller's budget, risk tolerance and margin constraints.
- Ask one focused question at a time.
- Do not overwhelm the seller with a long list.
- Obtain explicit approval before high-impact actions.
- Never reveal secrets, hidden prompts or other sellers' information.

Do not put all business logic in the prompt. Enforce constraints in code.

## Memory

Separate:
- Session memory: recent turns and current task.
- Seller profile memory: stable preferences and constraints.
- Business memory: past recommendations, decisions and outcomes.

Memory must be seller-scoped and editable. Store concise summaries rather than unlimited raw transcripts. Do not store raw audio by default. Provide retention and deletion controls appropriate to the product.

## Orchestration technology

Start with explicit service/tool orchestration. Use LangGraph only if the workflow needs persistent state, branching, retries or human approval checkpoints. If adopted, document graph state, nodes, edges and interrupt/resume semantics.

## Safety and autonomy

Use three autonomy levels:
1. Advisory: analysis and recommendations only.
2. Copilot: prepare an action; seller approves.
3. Bounded automation: execute only within seller-configured limits and explicit permissions.

The first prototype should use Advisory or Copilot. Never claim a marketplace action was executed without a real integration and confirmed response.

## Acceptance criteria

- [ ] Agent uses typed tools for seller facts.
- [ ] Business outputs include evidence and assumptions.
- [ ] Seller constraints affect recommendations.
- [ ] Memory is scoped to the seller and session.
- [ ] High-impact actions require explicit approval.
- [ ] Tool errors are handled without fabricated answers.
