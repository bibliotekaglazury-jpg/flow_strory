# Local Claude creative director

The current server adapter is `ClaudeCreativeDirectorAdapter`, using Anthropic Messages and prompt `creative-director-v3`. Storyflow's database owns visible conversation history. Codex login, a Codex executable and provider-native resume history are not required. Old reports documenting those transports remain historical evidence.

## Start

Install the backend dependencies from `apps/api/pyproject.toml`, including the Anthropic SDK. Configure the following server process settings through your normal secret manager or local configuration; do not expose the key in a frontend variable or command-line argument:

```dotenv
APP_ENV=development
AUTH_MODE=mock
CHAT_PROVIDER=claude
CLAUDE_MODEL=claude-sonnet-5
CLAUDE_EFFORT=medium
```

A server-only `ANTHROPIC_API_KEY` is required for real planning. The model above is the implementation default, not evidence that this account can access it. Missing credentials return `CHAT_UNAVAILABLE`; there is no silent provider fallback. Configuration values in this document do not mean the user's local settings were inspected or changed.

The existing `sh scripts/chat/run-local-api.sh` launcher now selects Claude, development authentication and loopback port 8000. It preserves video settings and defaults its local database to port 55432 unless `DATABASE_URL` is already configured. It does not run migrations.

With the intended local database configured, apply migrations from `apps/api`:

```sh
.venv/bin/alembic upgrade head
```

Migration `0005_chat_planning_usage` adds durable session budget state. Start the API on loopback from `apps/api`:

```sh
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Start the frontend from the repository root with `pnpm dev`. To exercise the actual local API, use frontend `NEXT_PUBLIC_USE_MOCK_API=false` and the existing development auth configuration. `NEXT_PUBLIC_USE_MOCK_API=true` selects browser-only simulation. Backend `CHAT_PROVIDER=mock` is the separate explicit mock adapter for offline API tests. Start/reset a conversation after changing providers; historical sessions are not migrated into Claude threads.

The generation worker is separate. Starting the planning API does not authorize starting a worker, claiming queued video jobs, running a paid test or deploying.

## Bounds

Default backend settings are defined in `app/config.py`:

| Setting | Default | Scope |
| --- | --- | --- |
| `CLAUDE_MAX_ROUNDS` | 4 | Preparation, optional research, final answer and at most one repair together |
| `CLAUDE_MAX_WEB_SEARCHES` | 2 | Maximum uses in the one optional search round |
| `CLAUDE_MAX_WEB_FETCHES` | 2 | Maximum uses in the one optional fetch round |
| `CLAUDE_MAX_INPUT_TOKENS` | 24000 | Accumulated input budget across a turn |
| `CLAUDE_MAX_OUTPUT_TOKENS` | 8192 | Output limit per model request |
| `CLAUDE_SESSION_BUDGET_CENTS` | 100 | Durable estimated monetary limit for a conversation |
| `CLAUDE_VALIDATION_BUDGET_CENTS` | 100 | Separate real-validation harness limit |
| `CLAUDE_TIMEOUT_SECONDS` | 120 | Model-turn deadline; context enrichment has a separate bounded timeout |

These are controls, not expected consumption or vendor billing promises. Token counting precedes inference. Before each model request, the service commits a conservative reservation; provider usage settles it. Unknown costs remain reserved after interruptions. Session planning spend is separate from video credits. Reset deletes the conversation and its session budget record; this is not an account-wide spending limit.

## Evidence and verification

Owned product/person images are validated, normalized to PNG and attached as native image blocks. A supplied public page first goes through the existing bounded SSRF-protected resolver. An eligible failed/partial page can lead to one optional public fetch round; missing relevant context can lead to one optional search round. The director loads at most two reviewed allowlisted skill references. Reference text and research are data, never permission to execute instructions.

Automated tests use mocked Messages responses and never consume inference or video credits. Regenerate public planning schemas with:

```sh
apps/api/.venv/bin/python scripts/chat/export-schema.py
```

The real quality matrix has not been run. Candidate self-scores and offline pass counts do not prove compelling advertising, semantic novelty, account/model access or production readiness. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md) for the implementation boundary and [verification/claude-chat/README.md](verification/claude-chat/README.md) for mocked UI evidence. Existing OpenRouter generation, private asset delivery, billing and deployment requirements remain separate.

### Unscoped Anthropic keys

A key that is not scoped to a workspace requires `ANTHROPIC_WORKSPACE_ID=wrkspc_…`.
The adapter passes it as `anthropic-workspace-id` on every SDK request, including token counting.
A missing workspace produces `CHAT_CONFIGURATION_REQUIRED`, without exposing provider errors to the browser.
The Default workspace ID is visible in Claude Console → Settings → Workspaces; the List Workspaces API omits Default.
See [Anthropic authentication](https://platform.claude.com/docs/en/manage-claude/authentication).
For an untouched `.env`, export the non-secret workspace ID in the launcher environment.
