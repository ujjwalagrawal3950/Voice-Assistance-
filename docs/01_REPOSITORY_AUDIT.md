# 01 — Repository Audit and Technical Plan

## Goal

Understand the existing project before making changes. Produce a verified architecture map and a staged implementation plan.

## Instructions

1. Inspect the repository tree, README, package/dependency manifests, environment examples, entry points, routing, backend services, database models, tests and deployment files.
2. Identify:
   - Frontend framework, version, build tool and styling system.
   - Backend framework, language and runtime version.
   - Database, ORM and migration strategy.
   - Authentication and authorisation approach.
   - Existing API conventions and error handling.
   - Existing AI/LLM integrations and prompt locations.
   - Existing audio, microphone, WebSocket, WebRTC or streaming code.
   - Test, lint, formatting and type-check commands.
3. Inspect the installed versions of any voice/AI packages. Do not rely on remembered APIs.
4. Determine whether the app is already deployed and whether any environment-specific configuration exists. Do not print secret values.
5. Identify reusable UI components and existing design conventions.
6. Do not change unrelated files and do not replace the current stack just because another stack is familiar.

## Required output

Create `docs/architecture/repository-audit.md` containing:
- Verified repository structure.
- Current architecture and request/data flow.
- Dependency/version summary.
- Existing reusable components.
- Missing capabilities for Virtual KAM.
- Risks and compatibility issues.
- Proposed architecture that extends the current project.
- Ordered implementation plan and exact files likely to change.

## Architecture decisions to make

Recommend, with reasons:
- Whether the existing backend can host analytics and Pipecat, or whether a separate voice service is justified.
- Whether existing storage can hold seller, SKU, sales, inventory, recommendations and conversation records.
- Whether a separate Python analytics service is needed.
- The browser audio transport compatible with the current client and installed Pipecat version.
- How the frontend obtains a scoped session connection without exposing provider secrets.

Do not silently assume Ollama, the Pipecat server and browser are on the same machine. Document the expected topology.

## Acceptance criteria

- [ ] Existing stack and versions are verified from repository files or runtime commands.
- [ ] No application code was modified during the audit unless a change was explicitly necessary and documented.
- [ ] Existing audio/AI code is identified.
- [ ] Proposed architecture is compatible with the actual repository.
- [ ] `docs/architecture/repository-audit.md` exists and distinguishes verified facts from recommendations.
- [ ] The next stage can begin without guessing the project's structure.
