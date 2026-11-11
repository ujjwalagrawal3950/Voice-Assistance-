# 08 — Real-Time Voice: Pipecat + Local Ollama

## Goal

Add natural two-way voice to the existing Virtual KAM. The user speaks into a browser microphone; speech is transcribed; the local Ollama model generates a response; TTS produces audio; the browser plays it.

Required conceptual flow:

`Browser microphone → audio transport → Pipecat → STT → Virtual KAM agent / local Ollama → TTS → audio transport → browser speaker`

Pipecat orchestrates the pipeline. It is not itself the STT engine, LLM or TTS engine.

## Mandatory first step: inspect and verify

Before coding:
- Inspect the repository and current Python version/dependency manager.
- Check installed Pipecat version.
- Verify current Pipecat integrations, package extras, import paths, constructors, lifecycle methods and transport APIs from current documentation or installed package metadata.
- Verify the selected STT, Ollama and TTS integration APIs.
- Do not invent imports or copy outdated examples.
- If an API cannot be verified, state the exact uncertainty and isolate it behind an adapter.

Do not replace unrelated app code or introduce another frontend framework.

## LLM: Ollama only

- Use a locally running Ollama model for the LLM step.
- Do not send prompts or conversation content to OpenAI or another hosted LLM.
- Use the model configured by the project; do not invent a model name.
- Prefer the currently supported Pipecat Ollama integration if compatible.
- Otherwise implement a small isolated adapter to Ollama's local API.
- Support streaming output where supported.
- Preserve conversation context using the agent's defined session state.
- Configure:
  - `OLLAMA_BASE_URL=http://localhost:11434`
  - `OLLAMA_MODEL=<your-installed-model>`
- Never expose the Ollama endpoint as a public browser setting.
- Never add an OpenAI key or OpenAI fallback for this LLM step.

## STT choice

Use a replaceable STT interface.

Recommended private/local prototype default: `faster-whisper`, if the machine has enough CPU/GPU and the latency is acceptable. Verify installation and model size against available hardware. A smaller model may be faster but less accurate, especially for Indian English, Hinglish, names and product terms.

Requirements:
- Clearly state whether audio remains local.
- Support partial/final transcript events if the chosen component supports them.
- Prevent duplicate final transcripts from generating duplicate assistant responses.
- Configure language and audio format only when supported.
- Provide a provider interface so a hosted STT can be added later without rewriting the pipeline.

## TTS choice

Use a replaceable TTS interface.

Recommended private/local prototype default: Piper, subject to verifying a suitable installed voice and current integration support. Explain voice installation and model path. Check pronunciation quality for Indian English/Hinglish before choosing it.

Requirements:
- Stream audio when supported.
- Match output sample rate, channels and encoding to the transport.
- Show assistant text as well as playing audio.
- Handle TTS failure gracefully by showing text.

## Audio transport

Choose only after inspecting the current client and Pipecat version. Prefer a real-time browser transport supported by the installed Pipecat release (for example, a supported WebRTC transport). Use WebSocket only if it is genuinely appropriate for the required audio streaming and interruption behaviour.

Document:
- Browser ↔ Pipecat server protocol.
- Whether a session token is needed.
- How the backend creates and scopes that token.
- Which process can reach Ollama.
- Whether services run on one machine, a LAN or separate hosts.

Do not assume `localhost` in a browser, Docker container and remote backend refers to the same machine.

## Turn-taking and natural conversation

- Use supported VAD/turn-detection components.
- Prefer semantic turn detection if a compatible, verified component is available; otherwise use VAD plus a configurable end-of-turn silence threshold.
- Avoid responding to every short pause.
- Support barge-in where transport and pipeline support it.
- On interruption, cancel or stop assistant audio generation/playback where possible.
- Handle silence, timeouts, duplicate events, session end and reconnect.
- Explain limitations if the selected local STT/TTS stack is not truly low-latency streaming.

## Client requirements

Implement:
- Explicit microphone permission request.
- Start/stop voice session.
- Mute/unmute if supported.
- Send microphone audio and receive assistant audio.
- Play assistant audio.
- Display connection/listening/processing/speaking/interrupted states.
- Show user transcript and assistant text.
- Text fallback.
- Handle denied permission, device unavailable, disconnect, server failure and session termination.

Do not automatically activate the microphone without a user action.

## Configuration

Use a sample environment file with placeholders only. Include only variables required by the selected setup, such as:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=<your-installed-model>
STT_PROVIDER=faster_whisper
TTS_PROVIDER=piper
STT_MODEL=<verified-model-name>
TTS_MODEL_PATH=<path-to-installed-voice>
VOICE_TRANSPORT=<verified-transport>
```

For hosted alternatives, keep provider keys on the backend. Never commit real secrets.

Validate settings at startup and return useful errors:
- Ollama unreachable.
- Configured model missing.
- STT model/voice file unavailable.
- Required hosted key missing.
- Transport configuration invalid.

## Reliability and privacy

Handle:
- Ollama unavailable, timeout or inference error.
- STT/TTS failure.
- Transport disconnection.
- User cancellation and server shutdown.
- Session/audio resource cleanup.
- Session duration, input-size and concurrency limits.
- Avoid logging raw audio, secrets or sensitive conversation text.
- Do not store raw audio by default.

Document exactly which data stays local and which leaves the machine. If all selected components are local, say so only after verifying the actual deployment topology.

## Tests

Mock external components and test:
- Configuration parsing/validation.
- Ollama adapter success, timeout and error.
- Transcript finalisation and duplicate suppression.
- Session/pipeline creation and cleanup.
- Interruption/cancellation handling where practical.
- Client state transitions.

## Documentation

Update project docs with:
- Supported Python and Pipecat versions.
- System dependencies.
- Ollama installation and model download commands.
- STT/TTS model installation.
- Environment configuration.
- Start commands for each process.
- Complete microphone-to-speaker test procedure.
- Network topology and privacy/data-flow explanation.
- Hardware and latency considerations.
- Troubleshooting audio devices, sample rates, Ollama and missing models.
- Any external service costs.

## Acceptance criteria

- [ ] Browser can start and stop a real voice session.
- [ ] Speech reaches STT and transcript is visible.
- [ ] Transcript is passed to the Virtual KAM agent and local Ollama.
- [ ] Assistant response is visible and spoken through TTS.
- [ ] Duplicate final transcript events do not cause duplicate replies.
- [ ] Turn-taking is usable and interruptions work where supported.
- [ ] Text fallback remains available.
- [ ] No hosted LLM is used; Ollama is the LLM.
- [ ] No secrets or private provider endpoints are exposed to the browser.
- [ ] Actual local/remote data flow is documented.
- [ ] Tests and run instructions are present.
