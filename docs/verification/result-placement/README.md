# Result beneath chat — 2026-09-10

User-approved change to original layout: actual generation status and output now sit directly below the chat/recipe summary inside the white workspace. Right-side example video remains separate. Idle state explains where output will appear; completed output preserves its ratio with contain sizing, controls and download.

Verified with fully mocked API:
- 9:16 at1440×1000;1:1 at1440×1000;16:9 at390×1000.
- Selected aspectRatio reaches chat context and generation POST unchanged.
- Applied recipe retains the selected aspectRatio.
- Result appears below composer and frame dimensions match the job ratio.
- No horizontal page overflow; screenshot comparisons retain existing shell/hero/tokens.
- Three browser cases passed; screenshots contain clearly simulated test footage, not paid model output.
- Typecheck, ESLint and local production Webpack build passed. Frontend unit tests:38 passed.

CBM MCP preflight:UGC2033nodes/4856edges, query workspace/Preview/aspectRatio/generateVideo, detect_changes complete; no CLI fallback. Local frontend-design skill applied. No backend, credentials or provider routing changed in this UI task. No real video submission made. User reports funded OpenRouter balance; video worker/storage readiness remains separate and is not established by these mock tests.
