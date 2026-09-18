---
name: frontend-design
description: Use when implementing or changing this AI UGC product's frontend screens, components, styling, or responsive behavior after explicit implementation approval.
---

# Reference-led frontend implementation

Use the approved mockup as the visual authority and keep the one-page creation scope. This repository-local skill is reached through AGENTS.md; its presence is not automatic global skill installation or implementation authorization.

## Before implementation

1. Read repository-root `AGENTS.md`, including operational preflight and the phase gate.
2. Read all documentation in `docs/`, especially UI_SYSTEM, PRODUCT_SPEC, API_CONTRACTS, REFERENCES, IMPLEMENTATION_RULES, and DECISIONS.
3. After required CBM preflight, inspect existing components. If absent, record that fact rather than assuming a scaffold exists.
4. Inspect existing design tokens; reconcile them with approved UI_SYSTEM values.
5. Inspect the actual reference image identified in REFERENCES. If missing, stop affected visual implementation and document the gap. Do not substitute a generic dashboard or treat proposed tokens as extracted measurements.
6. Identify the exact screen, component, states, and viewports being changed. Resolve applicable ambiguities in documentation before implementation.
7. Produce a short implementation plan covering reused components, tokens, typed data, states, and visual verification. Confirm existing explicit implementation authorization; do not ask again if already authorized and scope is clear.

## During implementation

- Preserve reference spacing, hierarchy, proportions, typography, and placement; avoid design drift or speculative UX.
- Use reusable, focused components, semantic HTML, accessible primitives, and shared tokens. shadcn/ui is not the visual identity.
- Maintain keyboard access, focus visibility, meaningful labels, contrast, and responsive behavior.
- Use typed API adapters and display-oriented props. Keep secrets and provider logic server-side; do not bind templates to models.
- Include required loading, error, empty, disabled, and progress states without fabricated metrics or progress.

## After implementation

1. Run the frontend on the verified authorized runtime described in AGENTS; local UGC runtime is explicitly authorized; no production runtime is authorized.
2. Capture screenshots at desktop and mobile widths, including relevant changed states.
3. Compare with the supplied approved reference; use an approved responsive adaptation where no mobile reference exists.
4. Note visible deviations and record screenshot paths, viewports, and reference version.
5. Fix deviations and recapture until verified.
6. Run lint, typecheck, relevant tests, and production build using actual repository commands; record results.
7. Declare completion only when all required checks pass. Missing reference, failed checks, or unavailable runtime must be reported as blockers. Never claim pixel accuracy without visual comparison.

Documentation-only tasks end with reviewable documentation and the requested approval handoff; do not scaffold an app to satisfy these future implementation checks.
