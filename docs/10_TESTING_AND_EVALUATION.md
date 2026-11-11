# 10 — Testing, Evaluation and Quality Gates

## Goal

Prove the product works technically and gives sensible business advice. A successful build is not just a UI that looks complete.

## Engineering tests

### Unit tests
- KPI formulas and percentage changes.
- Date/time and INR formatting helpers.
- Stock cover and reorder calculations.
- Forecast feature generation.
- Recommendation prioritisation.
- Tool input validation and seller scoping.
- Agent response schema validation.
- Voice state machine and duplicate transcript suppression.

### Integration tests
- API + database.
- Analytics service + demo data.
- Forecast service + evaluation dataset.
- Agent + mocked tools/Ollama adapter.
- Pipecat pipeline creation with mocked STT/TTS/transport.
- Recommendation approval workflow.

### End-to-end tests
- Seller dashboard loads.
- Seller asks a text question and gets evidence-based answer.
- Seller starts voice session, speaks and hears response.
- User interrupts assistant where supported.
- Voice failure falls back to text.
- Recommendation is created and approval state persists.

## Business-answer evaluation set

Create at least 20 test questions, including:
- Revenue decline diagnosis.
- Stable ASP but falling order count.
- Stockout impact.
- Cancellation increase.
- Return-rate increase.
- Dead-stock identification.
- Replenishment with limited budget.
- Festival preparation with strong historical evidence.
- Festival preparation with no historical evidence.
- SKU with sparse history.
- Missing conversion data.
- Conflicting seller goals.
- Competitor-price question when no competitor source exists.
- Request to execute an action without approval.

For each question define:
- Required tools.
- Expected facts.
- Forbidden claims.
- Expected clarification if information is missing.
- Acceptable recommendation characteristics.

## Voice quality evaluation

Test:
- Indian English and, if intended, Hinglish.
- Product/SKU names and numbers.
- Background noise and quiet speech.
- Short pauses inside a sentence.
- Long pauses between turns.
- User interruption during assistant speech.
- Device permission denied.
- Audio device unplugged.
- Network drop/reconnect.
- STT final event delivered more than once.

Measure end-to-end latency by stages: end-of-turn detection, STT, LLM first token, full response, TTS first audio and playback. Report actual measured results on the target hardware; do not invent expected latency.

## Forecast evaluation

- Chronological backtesting.
- Baseline comparison.
- SKU/category breakdown.
- Event-window performance.
- Forecast bias.
- Interval coverage when intervals are provided.
- Stockout periods identified separately.

## Quality gates

Do not mark the release ready if:
- A KPI formula is undefined.
- Recommendations cannot cite evidence.
- Forecasts are not compared to a baseline.
- The agent invents unavailable marketplace or competitor data.
- Voice secrets are exposed in client code.
- The voice flow cannot recover or provide text fallback.
- A high-impact action can execute without approval.

## Acceptance criteria

- [ ] Unit and integration tests run and results are reported.
- [ ] Business evaluation set exists with expected outcomes.
- [ ] Voice failure cases are tested or explicitly listed as untested.
- [ ] Forecasts are evaluated against a baseline.
- [ ] Known limitations and measured latency are documented.
