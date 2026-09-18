# Current authority — restored Codex chat (2026-09-10)

**Chat: current ChatGPT/Codex subscription through CodexLocalAdapter and codex exec/resume. Video only: OpenRouter → Seedance 2.0 Mini, 15s native audio.** The user explicitly reversed the OpenAI Responses chat change. No OpenAI API key transfer or Responses integration is required for chat. The experimental adapter/test launcher were removed; previous experiment notes below are historical and superseded. See [CHAT_ARCHITECTURE.md](CHAT_ARCHITECTURE.md).

Current single-model results and limitations: [SINGLE_MODEL_VERIFICATION.md](SINGLE_MODEL_VERIFICATION.md). Historical results below are not a live acceptance claim for the new route.

# Backend verification — 2026-09-10

Local execution was explicitly authorized by the user (“делаем пока локально”). No production host, production data, paid provider call, real Stripe transaction, deployment, or commit was used.

## Verified results

- `apps/api/.venv/bin/ruff check app tests`: **passed**.
- Complete Python suite with PostgreSQL integration enabled: **50 passed, 2 dependency deprecation warnings, 18.57 seconds**.
- Alembic `upgrade head` on a new isolated PostgreSQL database: **passed**, revisions `0001` and `0002`.
- Alembic `check`: **passed**, “No new upgrade operations detected.”
- Standalone Uvicorn API boot: **passed**, localhost port 8000.
- `curl http://127.0.0.1:8000/health/ready`: **200**, `{"status":"ok"}`.
- Real upload → owned asset → deterministic editable prompt → matching persisted quote → two concurrent identical submissions → one generation/reservation → worker → valid owned MP4 → history/poll response: **passed** against PostgreSQL.
- Output media was actually decoded with external FFmpeg. Verified first integration output: 15 seconds, 360×640, MP4; nine original fixtures cover all 15/20/30-second and 9:16/1:1/16:9 combinations.
- PostgreSQL concurrent first Checkout creates one customer mapping; hosted Stripe calls were dependency-injected test doubles, not real transactions.
- Signed Stripe invoice webhook grant and duplicate-event handling, cancellation/refund, append-only PostgreSQL ledger trigger, final ledger projections, exact idempotency, quote/provenance validation, ownership, expired worker lease recovery, definitive upstream failure refund and uncertain poll reservation retention: **passed**.
- Provider/text adapter tests include fail-closed configuration, capability routing, request shape, safe normalization, uncertain submissions/polls, and prompt-context instruction separation. External calls use injected HTTP transports.

The two warnings come from installed Starlette/AnyIO test-client deprecations (httpx compatibility and BlockingPortal alias). They are not failed assertions. No test was silently skipped in the 50-test PostgreSQL-enabled run.

## Reproducible local commands

The Docker daemon was unavailable, so an isolated native PostgreSQL cluster was created outside the repository. Local connection and shared-memory restrictions required targeted sandbox escalation; no approval was rejected.

```sh
/usr/local/bin/initdb -D /private/tmp/ugc-postgres-backend -A trust -U ugc
/usr/local/bin/pg_ctl -D /private/tmp/ugc-postgres-backend \
  -l /private/tmp/ugc-postgres-backend.log \
  -o '-p 55432 -h 127.0.0.1 -k /private/tmp' start
/usr/local/bin/createdb -h 127.0.0.1 -p 55432 -U ugc ugc
```

From `apps/api`, with project Python 3.12.9 virtual environment:

```sh
export DATABASE_URL=postgresql+psycopg://ugc@127.0.0.1:55432/ugc
.venv/bin/alembic upgrade head
.venv/bin/alembic check
RUN_POSTGRES_TESTS=1 .venv/bin/python -m pytest -q
.venv/bin/ruff check app tests
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
# Separate terminal with the same environment:
.venv/bin/python -m app.worker
```

For video validation, set `FFPROBE_PATH` to a separately installed LGPL-only ffprobe, or `FFMPEG_PATH` to a separately installed external FFmpeg. The verified local run used an explicit uncommitted path to an already-installed FFmpeg binary and exercised its actual one-frame decode fallback. The path is machine-specific and is not a required dependency or redistributed binary. The fallback parses FFmpeg's actual input format, duration and dimensions and rejects invalid/undecodable media.

## Runtime and evidence locations

- API source/commands: `apps/api`.
- PostgreSQL data: `/private/tmp/ugc-postgres-backend`.
- PostgreSQL log: `/private/tmp/ugc-postgres-backend.log`.
- Development private assets: `apps/api/var/assets` (ignored runtime data).
- Original playable simulation media: `apps/api/app/fixtures/demo-{duration}-{ratio}.mp4`.
- Test cases: `apps/api/tests/test_postgres_integration.py`, `test_domain.py`, `test_generations.py`, `test_billing.py`, `test_worker.py`, `test_security.py`, provider/text tests.
- API and worker are separate processes. Redis is a best-effort post-commit wakeup; the durable worker recovers via database scanning if Redis is absent.

## Media dependency decision and limits

Inspection showed that PyAV and imageio-ffmpeg binary wheels include GPL codecs. Both were **removed from application dependencies**. They are not required by the final backend and are not included in its Docker image. Original generated media is our own output, not third-party application code.

The Dockerfile instead defines a separate FFmpeg **7.1.1 LGPL-only source build**, with `--disable-gpl --disable-nonfree --disable-autodetect`, no x264/x265 libraries, and the built-in MPEG-4 encoder. Source: `https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz`; SHA-256: `733984395e0dbbe5c046abda2dc49a5544e7e0e1e2366bba849222ae9e3a03b1`. The final image includes LGPL notices. Matching source/build instructions must accompany redistribution.

The Docker build itself was **not run** because no Docker daemon was available. A local source-build attempt was stopped by the host compiler's SDK header discovery (`ctype.h` not found for host-C11 probe); this does not establish that the Docker build passes. Existing local FFmpeg verified the actual application/media path without introducing bundled GPL runtime dependencies into the distributable.

Real Supabase/JWKS sessions, private S3/R2 credentials, Redis wakeup delivery, Stripe hosted sessions and paid video/text generation remain credentialed integration checks. Development defaults are mock-only; nondevelopment settings reject development auth/storage/video/text modes. Unknown provider submission outcomes remain reserved and internally marked for operational reconciliation; no unsafe blind resubmission/refund is implemented. A reconciliation administration UI is outside MVP scope.

Root-agent connected Playwright verification subsequently passed **2 browser E2E tests in 1.4 minutes**, exercising the real FastAPI/PostgreSQL/worker adapter, video download and persisted history. API access logging was then disabled and the local API restarted with `--no-access-log`; this prevents signed asset query strings from appearing in normal access logs.
