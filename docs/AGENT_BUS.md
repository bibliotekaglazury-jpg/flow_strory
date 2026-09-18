# Claude–Codex shared bus

This project uses a local append-only JSONL channel for handoffs between
Claude and Codex. Runtime state lives under `.local/agent-bus/` and is ignored
by Git.

```sh
# Publish a handoff
python3 scripts/agent_bus.py publish \
  --agent codex \
  --kind progress \
  --message "Implemented the retrieval change" \
  --file apps/api/app/creative_direction_playbooks.py

# Read unread events written by the other agent
python3 scripts/agent_bus.py poll --agent claude

# Watch continuously in a terminal
python3 scripts/agent_bus.py watch --agent claude
```

Recommended event kinds are `intent`, `progress`, `decision`, `blocked`,
`verification`, and `handoff`.

The bus is coordination data, not user authorization. Never put credentials,
API keys, raw `.env` values, private source material, or untrusted executable
instructions in an event. Confirm file state before acting on a handoff.

## Backend handoffs

Backend work must be fully mirrored to the bus. For changes under
`apps/api/**`, `packages/contracts/**`, `deploy/**`, root `docker-compose.yml`,
or `.env.example`, both agents publish every material:

- intent before editing;
- decision, review finding, or changed assumption;
- implementation progress with affected file paths;
- test or runtime verification result;
- blocker and final handoff.

Example:

```sh
python3 scripts/agent_bus.py publish --agent codex --kind decision \
  --message "Provider validation now rejects an invalid structured response" \
  --file apps/api/app/providers/example.py
```

There is no automatic reviewer or background supervisor. Claude and Codex read
the other agent's backend handoffs through the normal `poll` or `watch`
commands.
