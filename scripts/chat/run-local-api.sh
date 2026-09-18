#!/bin/sh
# Local development only. Never use this launcher for deployment.
set -eu
cd "$(dirname "$0")/../../apps/api"
export APP_ENV=development
export AUTH_MODE=mock
# Anthropic key is read server-side by Settings; never copy it into this launcher.
export CHAT_PROVIDER=claude
export TEXT_PROVIDER=deterministic
export TEXT_PROVIDER_ENABLED=false
unset OPENAI_API_KEY OPENAI_PROJECT_ID OPENAI_ORG_ID
# Video configuration stays independent in the ignored root .env.
: "${DATABASE_URL:=postgresql+psycopg://ugc@127.0.0.1:55432/ugc}"
export DATABASE_URL
# Video settings still come from existing configuration; chat never submits video.
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-access-log
