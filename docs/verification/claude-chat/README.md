# Creative concept UI verification — 2026-09-11

Reference: REF-001, `docs/references/dashboard-reference.png` (1222 × 1287), plus the approved chat extension in `docs/UI_SYSTEM.md` and Claude implementation plan Task 8. Runtime: existing loopback Next development server at http://127.0.0.1:3000. All API requests in browser tests were intercepted by the existing deterministic mock adapter; no paid planning or video request was made.

The change reuses the existing summary typography and divider with five labels: Concept, Hook, Story, Script and Look. It adds an explicit `intent` to Send without changing the existing Change concept composer behavior. Manual keeps chat hidden and preserves its state for switching back.

| Viewport (CSS pixels, device scale 1) | Screenshots |
| --- | --- |
| 1222 × 1287 | `chat-empty-1222.png`, `chat-concept-1222.png`, `chat-manual-1222.png` |
| 390 × 844 | `chat-empty-390.png`, `chat-concept-390.png`, `chat-manual-390.png` |
| 1280 × 720 | `chat-loading-disabled.png`, `chat-quality-error.png` |

Visual comparison against REF-001 preserves the existing dark shell, white workspace, imagery, lime controls and result placement below chat. The intentional change is the extra labeled summary content, increasing the populated chat height. Mobile text and actions wrap without horizontal overflow. Existing differences from the original reference (authorized chat/Auto/result extensions, gallery imagery and application copy) are outside this change. No new CSS, cards or preview components were introduced. The mobile reference is not a pixel-match target; verification uses the existing responsive layout. Next development indicator and native video controls may appear in screenshots.

Checks: 9 mocked Playwright chat scenarios passed, including explicit intent, intent retained after quality failure, accepted-plan preservation, Apply without generation, and Manual mode. Screenshot tests also check keyboard Tab focus and overflow. Frontend 38 unit tests, TypeScript, lint and production webpack build passed. Backend `chat_api.py` Ruff passed. Full-page capture resets scroll to zero to avoid offscreen fixed-element artifacts.
