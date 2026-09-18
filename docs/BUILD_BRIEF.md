You are the lead engineer responsible for assembling a production-ready AI UGC video SaaS.

This is NOT a greenfield design exercise.

The product architecture, visual direction, MVP scope, and repository references are already defined below.

Your job is to:

1. inspect the current repository;
2. inspect the specified open-source reference repositories;
3. create the project documentation and local agent/design rules;
4. scaffold the production architecture;
5. implement the approved frontend faithfully from the supplied visual references;
6. prepare and implement the backend interfaces;
7. reuse/adapt proven open-source patterns where appropriate;
8. connect everything through stable typed contracts;
9. leave the application ready for real AI provider credentials and production deployment.

Do not invent an unrelated architecture.
Do not redesign the approved UI.
Do not build unnecessary features.

==================================================
0. PRIMARY GOAL
==================================================

Build a standalone white-label SaaS for generating UGC / advertising videos.

Primary user workflow:

PRODUCT / PRODUCT URL
        +
OPTIONAL PERSON IMAGE
        +
OPTIONAL EXISTING VIDEO
        ↓
SELECT VIDEO TEMPLATE
        ↓
DESCRIBE PRODUCT / CAMPAIGN
        ↓
AI GENERATES EDITABLE PRODUCTION PROMPT
        ↓
SELECT DURATION / ASPECT RATIO
        ↓
GENERATE VIDEO
        ↓
WAIT FOR ASYNC JOB
        ↓
VIDEO RESULT
        ↓
GENERATION HISTORY

The user must NOT need to understand AI models or prompt engineering.

Model selection should default to:

AUTO

Provider/model details belong to backend routing.

==================================================
1. OPEN-SOURCE REPOSITORIES TO INSPECT
==================================================

Inspect these repositories before designing implementation details.

Do not blindly merge them.
Use them as implementation references and selectively reuse/adapt code only where their licenses permit.

PRIMARY — GENERATION / MODEL PROVIDER REFERENCE

https://github.com/Anil-matcha/Open-Generative-AI

Use this repository primarily to study/reuse patterns for:

- AI model registry
- video generation providers
- image generation providers
- text-to-video
- image-to-video
- provider request normalization
- asynchronous generation patterns
- polling/job state
- model configuration
- provider abstraction
- multi-model support

IMPORTANT:

Do NOT allow the final application architecture to depend directly on MuAPI or any single provider.

Any provider-specific implementation must live behind our own provider adapter.

--------------------------------------------------

SAAS / AUTH / STORAGE / BILLING REFERENCE

https://github.com/nanoartApp/nanoart

Use this repository primarily as a reference for:

- production Next.js SaaS structure
- authentication
- PostgreSQL/Supabase patterns
- Prisma/database patterns if useful
- Stripe
- subscriptions
- credit accounting
- storage
- Cloudflare R2 patterns
- user-scoped assets
- generation persistence
- SaaS account architecture

Do not copy its visual design.

--------------------------------------------------

PRODUCT / AD DOMAIN REFERENCE

https://github.com/jasonca2023/dart

Use this repository as a reference for:

- product-oriented workflow
- product inputs
- audience/brief concepts
- structured ad specifications
- saved advertisements
- product → advertising workflow
- Supabase-backed user persistence
- backend/frontend separation

Do not reproduce its UI.

--------------------------------------------------

FUTURE STORYBOARD REFERENCE — NOT MVP

https://github.com/GongLingRui/ai-video-generation

Inspect only to ensure our architecture will later support:

- scenes
- storyboard nodes
- multi-scene generation
- first/last frame continuity
- chained video generation

DO NOT implement Canvas or storyboard editor in the current MVP.

==================================================
2. LICENSE RULE
==================================================

Before copying or adapting source code from any repository:

1. inspect its actual LICENSE file;
2. record the license in:
   docs/THIRD_PARTY.md
3. record exactly what code/pattern was reused;
4. do not assume licensing from README text;
5. do not reuse code from repositories without a compatible license.

Prefer:
- MIT
- Apache-2.0
- BSD
- similarly permissive licenses

Do not introduce AGPL/GPL code into the application without explicit approval.

==================================================
3. REQUIRED PROJECT STRUCTURE
==================================================

Target structure:

/
├── AGENTS.md
├── README.md
├── .env.example
├── docker-compose.yml
│
├── apps/
│   ├── web/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── lib/
│   │   ├── services/
│   │   ├── hooks/
│   │   ├── types/
│   │   ├── public/
│   │   └── tests/
│   │
│   └── api/
│       ├── app/
│       │   ├── main.py
│       │   ├── api/
│       │   ├── core/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── services/
│       │   ├── providers/
│       │   ├── repositories/
│       │   ├── workers/
│       │   └── templates/
│       └── tests/
│
├── packages/
│   ├── contracts/
│   ├── config/
│   └── ui/
│
├── docs/
│   ├── PRODUCT_SPEC.md
│   ├── UI_SYSTEM.md
│   ├── REFERENCES.md
│   ├── API_CONTRACTS.md
│   ├── BACKEND_ARCHITECTURE.md
│   ├── GENERATION_ARCHITECTURE.md
│   ├── DATABASE_SCHEMA.md
│   ├── IMPLEMENTATION_RULES.md
│   ├── DECISIONS.md
│   ├── THIRD_PARTY.md
│   └── references/
│       ├── dashboard-reference.png
│       ├── hero-woman.webp
│       └── make-it-real.svg
│
└── skills/
    └── frontend-design/
        └── SKILL.md

If the existing repository already has a reasonable structure,
adapt to it instead of destructively restructuring everything.

==================================================
4. FRONTEND STACK
==================================================

Use:

- Next.js
- TypeScript
- React
- Tailwind CSS
- shadcn/ui only as implementation primitives
- Lucide icons
- typed API client

Do NOT use shadcn default styling as the product identity.

The reference screenshot is the visual source of truth.

==================================================
5. BACKEND STACK
==================================================

Use a backend designed to survive future model/provider changes.

Preferred stack:

- FastAPI
- Python
- PostgreSQL
- Supabase where appropriate
- Redis
- background worker / job queue
- Cloudflare R2 or S3-compatible object storage
- Stripe
- webhooks
- provider adapter architecture

The frontend must never call AI provider APIs directly.

Architecture:

Frontend
    ↓
Our API
    ↓
Generation Service
    ↓
Model Router
    ↓
Provider Adapter
    ↓
Provider API

Example providers:

MuAPIProvider
FalProvider
ReplicateProvider
KlingProvider
SeedanceProvider
VeoProvider
HiggsfieldProvider

Do NOT implement all providers immediately.

Implement the abstraction and one or two adapters first.

==================================================
6. CORE PROVIDER INTERFACE
==================================================

Create provider-neutral interfaces similar to:

VideoProvider

generate()
get_status()
cancel()
normalize_result()
estimate_cost()

ImageProvider

generate()
edit()
get_status()
normalize_result()
estimate_cost()

Provider responses must be normalized into our domain types.

Never expose raw provider response structures to frontend components.

==================================================
7. MODEL REGISTRY
==================================================

Create our own model registry.

Example conceptual fields:

id
provider
providerModelId
type
capabilities
durations
aspectRatios
resolutions
supportsAudio
supportsImageInput
supportsVideoInput
supportsReferenceImages
supportsFirstFrame
supportsLastFrame
enabled
priority
costRules

The application frontend must work with our model IDs, not provider IDs.

==================================================
8. AUTO MODEL ROUTER
==================================================

Default user model:

AUTO

Create backend routing logic capable of selecting models based on:

- template
- duration
- input type
- desired style
- aspect ratio
- quality
- price
- availability

Initial implementation may be rule-based.

Example:

realistic UGC
→ Seedance-like model

high motion
→ Kling-like model

premium cinematic
→ Veo-like model

Fallback routing should be possible.

Do not hardwire templates to one provider.

==================================================
9. VIDEO TEMPLATE ARCHITECTURE
==================================================

Templates are core business logic.

Create template definitions independent of models.

Initial templates:

ugc_review
product_unboxing
problem_solution
product_demo
testimonial
trending_style
hook_cta
before_after

Template should be capable of defining:

id
name
description
thumbnail
category
supportedDurations
supportedAspectRatios
promptInstructions
structure
defaultTone
defaultCameraStyle
defaultVoiceStyle
recommendedCapabilities

Example conceptual template:

problem_solution

0–3 sec:
hook

3–7 sec:
problem

7–11 sec:
product

11–13 sec:
result

13–15 sec:
CTA

Do NOT implement a visual scene editor yet.

The internal representation should nevertheless support future scenes.

==================================================
10. DATABASE
==================================================

Design at minimum:

users

subscriptions

credit_accounts

credit_transactions

projects

assets

templates

models

providers

generations

generation_jobs

generation_outputs

webhook_events

Required generation status:

idle
uploading
queued
generating
completed
failed
cancelled

Store provider job IDs only server-side.

==================================================
11. CREDIT SYSTEM
==================================================

Credits must use a ledger.

Never simply store:

user.credits = 500

Use:

credit_accounts
credit_transactions

Transactions:

purchase
subscription_grant
generation_reserve
generation_charge
generation_refund
manual_adjustment

Generation flow:

estimate cost
↓
reserve credits
↓
submit generation
↓
complete:
charge actual amount

OR

failure:
release/refund reservation

This must be transaction-safe.

==================================================
12. AUTHENTICATION
==================================================

Do not custom-build authentication UI unless required.

Prefer a mature service/library.

Candidate:
- Clerk

or Supabase Auth if the project architecture strongly favors it.

Support:

email
Google OAuth
session
protected application routes

Keep auth implementation replaceable.

==================================================
13. BILLING
==================================================

Use Stripe.

Do NOT build a complex custom billing frontend.

Use:

Stripe Checkout
+
Stripe Customer Portal
+
webhooks

Billing page may initially show:

Current Plan
Credits Remaining
Renewal Date
Manage Subscription

==================================================
14. STORAGE
==================================================

Assets include:

product images
person images
reference videos
generation outputs
thumbnails

Store binary assets in:

Cloudflare R2
or compatible S3 storage.

Database stores metadata/URLs.

Do not store video blobs in PostgreSQL.

Use signed upload URLs where appropriate.

==================================================
15. ASYNC GENERATION
==================================================

Video generation is asynchronous.

Required lifecycle:

POST generation
↓
validate
↓
estimate credits
↓
reserve credits
↓
create generation record
↓
queue job
↓
worker submits provider request
↓
provider job ID stored
↓
poll or webhook
↓
download/copy output to our storage
↓
mark completed
↓
charge credits
↓
frontend updates

Handle:

provider timeout
provider failure
invalid output
job retry
duplicate webhook
user refresh
worker restart

==================================================
16. FRONTEND VISUAL DIRECTION
==================================================

The supplied dashboard reference is APPROVED.

Do not redesign it.

Primary visual characteristics:

- dark overall application shell
- deep navy/charcoal background
- cinematic ambient background glow
- white central "Create Your Video" workspace
- acid/lime accent
- premium editorial hero typography
- compact navigation
- clean creation workflow
- high-quality UGC imagery
- restrained UI chrome
- strong contrast
- minimal cognitive load

The main Create workspace must remain white.

==================================================
17. HERO IMPLEMENTATION
==================================================

Do not make the entire hero a single flattened image.

Structure:

Hero
├── dark background
├── cinematic ambient CSS glow
├── text HTML
├── transparent woman image
├── make-it-real.svg
├── engagement metric
└── optional brand row

Use:

docs/references/hero-woman.webp

for the person.

Use:

docs/references/make-it-real.svg

for the handwritten graphic.

Hero typography must remain HTML.

==================================================
18. CINEMATIC HERO BACKGROUND
==================================================

Implement the background in CSS.

Use this direction:

:root {
  --bg: #06131c;
  --cyan-1: rgba(38, 148, 174, 0.56);
  --cyan-2: rgba(20, 92, 115, 0.34);
  --amber-1: rgba(205, 122, 58, 0.48);
  --amber-2: rgba(120, 66, 36, 0.30);
  --lime: rgba(216, 255, 47, 0.26);
}

Use layered:

- cool cyan ambient bloom
- warm amber bloom
- secondary blue depth
- small lime halo
- dark vignette
- subtle film grain

Do not replace this with a generic linear gradient.

==================================================
19. CREATE VIDEO WORKSPACE
==================================================

This is the primary application surface.

WHITE background.

Sections:

Create Your Video

Steps:

1 Input
2 Style
3 Prompt
4 Generate

INPUTS

Product
- image upload
- From URL

Person
- optional image

Existing video
- optional video upload

STYLE

Show visual templates:

UGC Review
Unboxing
Problem → Solution
Lifestyle Demo
Testimonial
Trending

plus additional templates when needed.

CAMPAIGN BRIEF

Large textarea:

Describe your product or campaign

PROMPT

Generate Prompt

Editable Prompt Preview

SETTINGS

Duration:
15s
20s
30s

Aspect ratio:
9:16
1:1
16:9

Advanced:
collapsed

Inside Advanced:

Model:
Auto

Voice:
Auto

Quality:
Auto

GENERATE

Large lime button:

Generate Video

Display estimated credits beside/in button.

==================================================
20. VIDEO PREVIEW
==================================================

Right side on desktop.

Vertical video preview.

States:

empty
queued
generating
completed
failed

Completed state:

video player
duration
template label
download
regenerate only if later enabled

Do not implement unnecessary editing tools.

==================================================
21. TEMPLATE SECTION
==================================================

Below main creation area:

Templates

horizontal visual cards.

Each contains:

thumbnail
template name
one-line explanation

Do not overload with controls.

==================================================
22. RECENT CREATIONS
==================================================

Below templates:

Recent Creations

Cards contain:

thumbnail
duration
status
created time

Click opens generation details.

==================================================
23. SIDEBAR
==================================================

Desktop sidebar:

Logo

Create
Templates
Library
Brand Kit
Analytics
Billing
Settings

At bottom:

Plan
Account/User

Only Create must be fully implemented for MVP.

Other destinations may use placeholder routes/screens but should not become full projects yet.

==================================================
24. ANTI-AI-SLOP RULES
==================================================

FORBIDDEN:

- generic purple AI gradients
- excessive gradients
- glassmorphism everywhere
- giant meaningless hero blocks
- decorative metrics
- random badge spam
- fake analytics
- dozens of cards
- unnecessary rounded containers
- giant 24–32px radius everywhere
- random iconography
- 3D blobs
- excessive shadows
- rainbow colors
- redesigning supplied reference
- replacing premium typography with generic SaaS typography
- excessive marketing copy inside application UI

The application should look designed by a product designer,
not generated from a generic SaaS prompt.

==================================================
25. DESIGN SYSTEM DOCUMENTATION
==================================================

Before implementation create:

docs/UI_SYSTEM.md

Document exact:

colors
type scale
font choices
spacing scale
sidebar width
workspace widths
radii
borders
shadows
button sizes
input sizes
template-card dimensions
responsive rules

Use design tokens.

==================================================
26. LOCAL FRONTEND DESIGN SKILL
==================================================

Create:

skills/frontend-design/SKILL.md

It must instruct every future agent:

BEFORE UI WORK

1. Read AGENTS.md
2. Read docs/UI_SYSTEM.md
3. Read docs/PRODUCT_SPEC.md
4. Read docs/REFERENCES.md
5. Inspect supplied screenshots
6. Inspect current components
7. Do not redesign

AFTER UI WORK

1. run app
2. capture screenshot
3. compare reference
4. identify visible deviations
5. fix them
6. repeat
7. run lint
8. run typecheck
9. run tests
10. run production build

Never claim pixel accuracy without screenshot comparison.

==================================================
27. API CONTRACTS
==================================================

Frontend-facing endpoints:

POST /api/assets

POST /api/product/resolve

POST /api/prompts/generate

GET /api/templates

GET /api/models

POST /api/generations

GET /api/generations/:id

GET /api/generations

POST /api/generations/:id/cancel

GET /api/credits

POST /api/billing/checkout

POST /api/billing/portal

POST /api/webhooks/stripe

Provider webhooks must use separate protected routes where needed.

Create explicit request/response schemas.

==================================================
28. FRONTEND SERVICE ABSTRACTION
==================================================

Create typed frontend services:

AssetService

ProductService

TemplateService

PromptService

GenerationService

CreditsService

BillingService

Frontend components must never directly call fetch() throughout random components.

Centralize API access.

==================================================
29. MOCK MODE
==================================================

The frontend must be usable before real provider credentials exist.

Create:

NEXT_PUBLIC_USE_MOCK_API=true

Mock:

uploads
templates
prompt generation
generation lifecycle
video history
credit balance

Mock generation should simulate:

queued
→ generating
→ completed

This allows visual development independently from backend providers.

==================================================
30. ENVIRONMENT
==================================================

Create a complete:

.env.example

Groups:

DATABASE

SUPABASE

REDIS

R2 / S3

STRIPE

AUTH

AI PROVIDERS

APPLICATION

Never commit secrets.

==================================================
31. DOCKER / LOCAL DEVELOPMENT
==================================================

Provide local development using Docker where practical.

At minimum:

Postgres
Redis

Optionally object storage emulator if useful.

Commands should be simple:

docker compose up -d

pnpm install

pnpm dev

API development command documented separately.

==================================================
32. TESTING
==================================================

Backend:

unit tests for:
- cost calculation
- credit ledger
- provider normalization
- router
- templates
- generation state transitions

integration tests:
- create generation
- generation failure
- credit refund
- duplicate webhook

Frontend:

component tests where useful

E2E critical flow:

upload
→ choose template
→ brief
→ generate prompt
→ generate video
→ observe progress
→ completed history item

==================================================
33. OBSERVABILITY
==================================================

Structure application so production can later support:

structured logs
request IDs
generation IDs
provider request IDs
error tracking

Do not expose provider secrets in logs.

==================================================
34. DOCUMENTATION TO CREATE FIRST
==================================================

Before implementing application code create:

AGENTS.md

docs/PRODUCT_SPEC.md
docs/UI_SYSTEM.md
docs/REFERENCES.md
docs/API_CONTRACTS.md
docs/BACKEND_ARCHITECTURE.md
docs/GENERATION_ARCHITECTURE.md
docs/DATABASE_SCHEMA.md
docs/IMPLEMENTATION_RULES.md
docs/DECISIONS.md
docs/THIRD_PARTY.md

skills/frontend-design/SKILL.md

Populate them with the decisions from this prompt.

Do not create empty placeholder documentation.

==================================================
35. EXECUTION PHASES
==================================================

Execute in this order.

PHASE 1
Repository inspection.

PHASE 2
Inspect reference open-source repositories and licenses.

PHASE 3
Create architecture/design documentation.

PHASE 4
Create application structure.

PHASE 5
Implement shared contracts/types.

PHASE 6
Implement backend core:
- DB
- storage abstractions
- generation domain
- provider interface
- model registry
- router
- credits

PHASE 7
Implement mock provider.

PHASE 8
Implement frontend faithfully from reference.

PHASE 9
Connect frontend to our API.

PHASE 10
Implement first real provider adapter using the most suitable provider pattern identified in Open-Generative-AI.

PHASE 11
Auth.

PHASE 12
Stripe billing.

PHASE 13
Visual verification.

PHASE 14
Tests/build verification.

==================================================
36. IMPORTANT IMPLEMENTATION PRINCIPLE
==================================================

Do not create a giant monolith.

Keep these domains isolated:

auth

billing

credits

assets

templates

models

providers

generations

prompt generation

product resolution

frontend presentation

Each domain must expose a clear interface.

==================================================
37. DO NOT OVERBUILD
==================================================

Do NOT implement yet:

timeline editor

node canvas

manual storyboard editor

social publishing

team collaboration

campaign management

advanced analytics

native mobile app

browser extension

complex admin dashboard

marketplace

public community functionality

Keep architecture extensible for these features,
but do not build them.

==================================================
38. VISUAL VERIFICATION
==================================================

The reference screenshot is mandatory.

Once the Create screen is implemented:

1. run it at desktop width matching reference;
2. capture screenshot;
3. compare side-by-side;
4. inspect:
   - hero height
   - sidebar width
   - image positioning
   - white workspace dimensions
   - typography
   - card sizes
   - spacing
   - lime usage
   - template dimensions
   - preview dimensions
5. correct deviations;
6. repeat until visually close.

Also test:
1440
1280
1024
768
mobile

Do not destroy the desktop composition just to satisfy mobile.

==================================================
39. COMPLETION CRITERIA
==================================================

Do not report the project as complete unless:

- app boots successfully
- frontend renders
- API boots
- mock generation works end-to-end
- database migrations work
- generation history works
- credit ledger works
- upload flow works
- API contracts are typed
- frontend does not know provider-specific formats
- provider abstraction exists
- at least one real provider adapter exists or is fully ready for credentials
- lint passes
- typecheck passes
- tests pass
- production frontend build passes
- backend tests pass
- screenshot comparison has been performed
- documentation is complete
- THIRD_PARTY.md accurately records reused open-source code

==================================================
40. FINAL REPORT
==================================================

At the end provide:

1. architecture summary
2. final repository tree
3. reused/open-source components and licenses
4. backend endpoints
5. database tables
6. provider architecture
7. implemented providers
8. mock-mode instructions
9. local startup instructions
10. required environment variables
11. test results
12. lint/typecheck/build results
13. remaining TODOs
14. known visual deviations from reference

Do not merely say "done".

Provide verification evidence.

BEGIN BY INSPECTING THE CURRENT REPOSITORY AND THE FOUR REFERENCE REPOSITORIES.
THEN CREATE THE DOCUMENTATION.
THEN PROCEED THROUGH THE PHASES IN ORDER.