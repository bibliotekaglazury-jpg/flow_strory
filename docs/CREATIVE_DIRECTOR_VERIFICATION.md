## Update: authorized live attempt completed with provider rejection

The user approved the two-photo relay. HTTPS access passed, but the single real submission was rejected with HTTP 402. Storyflow recorded the failed generation and refunded all 45 reserved credits. No MP4 was produced. The relay is closed. Read-only account data reports USD 10 total credits and USD 10.047505731 usage. See [REAL_VIDEO_TEST_20260910.md](REAL_VIDEO_TEST_20260910.md). Earlier “not executed / approval pending” statements below are historical.

# Creative Director verification — 2026-09-10

Local implementation verified through mock video output. Live reference-video quality gate remains incomplete. No production deployment.

## Preflight

CBM MCP exposed: yes. CLI used for initial list_projects: yes. Project: Users-stas-Documents-UGC, verified root `/Users/stas/Documents/UGC`, 2,074 nodes / 5,298 edges. search_graph query: `VideoRecipe compile_recipe ChatSession templates useCreation provider_input`, limit 12. Returned relevant symbols include VideoRecipe/valid_timing, compile_recipe, ChatSession, useCreation, provider_input and the templates route. detect_changes returned no tracked changes; the existing repository baseline is untracked, so that is not evidence of no local edits. No Cerebro/VPS graph was used as UGC evidence.

## Required report

1. **ContextBundle:** existing page resolver evidence, current text/brief/format/ratio, owned asset metadata and visible conversation are normalized. Unknown business fields remain optional; no industry form or classifier.
2. **CreativeDirector:** existing CodexLocalAdapter with a versioned v2 system prompt and strict DirectorAnswer output. No new conversation provider. The conflicting Responses/gpt-5.6-terra instruction is awaiting clarification; Responses was not implemented or tested.
3. **CreativePlan:** objective/audience/offer/tension/angle/format/hook/tone/visual/languages/characters/presentation/audio/confidence, validated before compilation.
4. **VideoPlan:** exactly one 0–15 clip; speech, visual action, camera, performance and audio stored separately.
5. **Beats:** optional, ordered, non-overlapping, within 15s; passed into the final recipe without fixed timing presets.
6. **Format biases:** one shared definition used by director and existing prompt service. No provider bindings or canned scene timings.
7. **Auto:** default creation choice; accepted concept resolves it to an existing format. Manual selection preserved; changed format/assets require re-planning.
8. **Language:** conversation/spoken languages separate in plans; compiler uses spoken language. Real validation returned pl-PL consistently. Mock tests also cover Polish preservation and explicit override behavior in the existing suite.
9. **PromptCompiler:** compile_plan creates the existing canonical recipe; compile_recipe serializes it for existing jobs, including beats and native-audio instructions.
10. **CanonicalVideoRecipe:** alias of existing VideoRecipe; no second provider recipe model. Historical recipes remain readable.
11. **OpenRouter/Seedance:** existing adapter/model registry reused unchanged; only real model remains `bytedance/seedance-2.0-mini`. Worker additionally records sanitized request metadata for review.
12. **Native audio:** existing generate_audio=true and output validation preserved; no TTS or separate audio system added.
13. **Real 15-second video:** NOT EXECUTED. Local media has no reachable HTTPS origin/private S3 configuration. Prior public-tunnel approval rejection remains unresolved; no additional paid video attempt was made.
14. **Technical MP4 validation:** new pipeline completed through the real local worker/storage/history/ledger with the mock provider. Output metadata reports approximately 15s. No new real-provider MP4 exists to assess audio/duration or creative quality.
15. **Tests:** backend 123 passed; 12 PostgreSQL tests skipped by the default command, then all 12 passed explicitly on isolated `storyflow_director_test_20260910`. Final targeted director→worker regression passed again after apply guards. Frontend unit tests: 38 passed. Browser: 12 unique scenarios passed across chat/Create/product-URL/result-placement suites, all external APIs mocked. Existing regression tests remain intact apart from expected new labels and text-only input semantics.
16. **Lint:** frontend ESLint and backend Ruff passed.
17. **Typecheck:** TypeScript passed, including after production build.
18. **Build/migrations:** Next.js production webpack build passed. Existing Alembic migrations upgraded an empty isolated PostgreSQL DB to head. No new migration required because existing JSON storage holds versioned plans.
19. **Remaining issues:** HTTPS asset storage/explicit narrowly scoped relay authorization; one real video test and manual creative review; conflicting request to switch Codex to Responses remains unanswered. Manual editing retains the prior approved behavior: edit the production prompt after applying a concept. This is local single-account development, not production multi-tenant inference.
20. **Scope:** no 30/45/60-second work, stitching, new video models/providers, TTS, premium routing, editor, canvas or deployment.

## Live director evidence

One Codex subscription validation succeeded, HTTP 200, session `9e0e03ac-5af2-44b5-961a-28cad2cac495`. One real model turn, no paid video call. Full visible answer and input/planning data saved in ignored `.local/creative-director-validation.json`, mode 0600, with DB recipe version. The reusable script refuses to repeat an existing attempt: `scripts/chat/check-creative-director.py`.

Validated: `ugc_review`, 15s, 9:16, pl-PL conversation/spoken language, one clip with independently chosen 0–4 / 4–10 / 10–15 beats, separate Polish dialogue, native speech/ambience, no music. The director recognized the supplied jar/person image and proposed a continuous phone shot. This establishes schema/transport behavior, not marketing effectiveness or generated-video quality.

## Visual verification

Reference: `docs/references/dashboard-reference.png` plus already approved chat/result-placement changes. Screens: existing Create with empty and ready concept states. Viewports: 1440×1100 and 390×844.

Screenshots:
- `docs/verification/creative-director/empty-1440.png`
- `docs/verification/creative-director/recipe-1440.png`
- `docs/verification/creative-director/empty-390.png`
- `docs/verification/creative-director/recipe-390.png`

Both were rendered and visually inspected. Dark shell, white workspace, lime controls, hero, photo cards and preview placement remain. Intentional differences: Auto control and concept actions; chat increases workspace height relative to the original static mockup. Mobile uses the existing stacked adaptation; no separate mobile reference is supplied. No horizontal overflow or browser runtime errors. No claim of pixel accuracy. Screenshots use simulated content, not the real director answer. Mock-only 20/30 duration presets remain for historical visual tests; the real model advertises only 15s.

Static browser-bundle scan found no OpenRouter/OpenAI secret-key patterns or the server director system prompt. API restarted locally; readiness check returned ok. No general worker was started, to avoid claiming unrelated queued jobs.
