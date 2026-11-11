# 11 — Security, Deployment and Privacy

## Goal

Run the Virtual KAM reliably while protecting seller data, local model endpoints, provider credentials and voice sessions.

## Secrets and configuration

- Keep secrets in server-side environment variables or a secret manager.
- Commit only `.env.example` placeholders.
- Do not expose Ollama base URL, hosted STT/TTS keys or internal service URLs to the browser.
- Validate required configuration at startup.
- Redact secrets from logs and error messages.

## Authentication and authorisation

- Use existing authentication if present.
- Scope every seller record and tool call to the authenticated seller.
- Never trust a seller ID from an untrusted client payload.
- Prevent one seller from reading another seller's transcripts, forecasts or recommendations.
- Protect approval endpoints against CSRF/replay as appropriate to the stack.

## Ollama networking

- If backend and Ollama run on the same host, configure the correct local address.
- If backend runs in Docker, remember `localhost` refers to the container itself; configure host networking appropriately.
- If Ollama runs on another machine, use a private network and firewall rules.
- Do not expose Ollama port 11434 directly to the public internet.
- Document the actual topology.

## Voice privacy

- Request microphone permission explicitly.
- Explain whether audio is processed locally or sent to a third party.
- Do not store raw audio by default.
- If transcripts are persisted, disclose purpose and retention.
- Provide a way to clear conversation history where feasible.
- Avoid logging raw audio or sensitive transcript content.
- Use secure transport for hosted deployments.

## Deployment profiles

Document at least one tested profile:
1. **Local demo:** browser + app backend + Pipecat + Ollama on one computer.
2. **Split local network:** browser and backend on separate devices, Ollama reachable only on private network.
3. **Hosted frontend/backend:** explicitly document which inference services remain local and which data leaves the seller's device.

Do not claim a fully local/private architecture if any STT, TTS, transport relay or logging provider receives user data.

## Operational controls

- Rate-limit session creation and chat requests.
- Set request, audio duration and concurrent-session limits.
- Add health checks for backend, database, Ollama and voice service.
- Set timeouts and graceful shutdown.
- Add structured, privacy-conscious logs and request IDs.
- Back up persistent data where applicable.
- Pin compatible dependency versions and document upgrade procedure.

## Acceptance criteria

- [ ] No secrets are committed or sent to browser.
- [ ] Seller data is properly isolated.
- [ ] Ollama is not publicly exposed.
- [ ] Voice data flows and retention are documented.
- [ ] Health checks and useful startup errors exist.
- [ ] At least one deployment profile is tested and documented.
