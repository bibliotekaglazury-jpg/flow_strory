FROM node:24-bookworm-slim AS build

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH
RUN corepack enable
WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/contracts/package.json packages/contracts/package.json
COPY packages/config/package.json packages/config/package.json
COPY packages/ui/package.json packages/ui/package.json
RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages packages
ARG NEXT_PUBLIC_USE_MOCK_API=true
ARG API_INTERNAL_URL=http://127.0.0.1:8000
ENV NEXT_PUBLIC_USE_MOCK_API=$NEXT_PUBLIC_USE_MOCK_API
ENV API_INTERNAL_URL=$API_INTERNAL_URL
RUN pnpm --filter @ugc/web build

EXPOSE 3000
CMD ["pnpm", "--filter", "@ugc/web", "exec", "next", "start", "--hostname", "0.0.0.0", "--port", "3000"]
