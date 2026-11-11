# 04 — Backend APIs, Persistence and Service Boundaries

## Goal

Create secure, typed backend services that provide seller data to the UI, business intelligence and agent. Preserve the existing backend if suitable.

## Service boundaries

Keep these responsibilities separate, even if they initially live in one application:
1. Seller and catalogue service.
2. Analytics/KPI service.
3. Forecasting service.
4. Recommendation/decision service.
5. KAM agent service.
6. Voice session service (Pipecat).
7. Persistence and audit service.

Do not create microservices without a concrete deployment or scaling reason. A modular monolith is acceptable for the prototype.

## Minimum API surface

Adapt paths to current conventions. Suggested endpoints:

- `GET /api/seller/profile`
- `PATCH /api/seller/profile`
- `GET /api/dashboard/summary`
- `GET /api/analytics/sales`
- `GET /api/products`
- `GET /api/products/{sku_id}`
- `GET /api/inventory/health`
- `GET /api/forecasts/{sku_id}`
- `GET /api/recommendations`
- `GET /api/recommendations/{id}`
- `POST /api/recommendations/{id}/approve`
- `POST /api/recommendations/{id}/reject`
- `POST /api/assistant/chat`
- `POST /api/voice/session` or the secure session bootstrap required by the chosen Pipecat transport.

## API rules

- Validate query parameters, date ranges, seller ownership and payload size.
- Use typed schemas and consistent error responses.
- Enforce seller-level authorisation on every data endpoint.
- Paginate product/order lists.
- Add sensible timeouts and request limits.
- Use idempotency for approval/execution endpoints where relevant.
- Never trust seller_id supplied by the browser when authenticated identity can determine it.
- Do not expose internal stack traces or provider credentials.
- Add request IDs and structured logs, while avoiding sensitive transcript/audio logging.

## Storage

Use the current database if available. Otherwise:
- SQLite is acceptable for a single-user local prototype.
- Use PostgreSQL for concurrent users or hosted deployment.
- Keep schema/migrations explicit.
- Persist seller profile, SKUs, performance, inventory, calendar events, recommendations, approvals and conversation summaries.
- Do not persist raw voice recordings unless explicitly required and consented to.

## Data access and calculations

- Analytics queries should be deterministic and independently testable.
- Use parameterised database queries or ORM methods.
- Do not ask the LLM to calculate revenue totals from raw rows.
- Return provenance and timestamp/freshness metadata with analytics.
- Distinguish no data from zero activity.

## Acceptance criteria

- [ ] API contracts are documented and typed.
- [ ] Seller ownership is enforced server-side.
- [ ] Dashboard and SKU endpoints return consistent data.
- [ ] Recommendations and approvals are persisted.
- [ ] Migrations or schema setup are repeatable.
- [ ] Secrets and internal endpoints are not returned to the client.
- [ ] Tests cover validation, authorisation and common failure responses.
