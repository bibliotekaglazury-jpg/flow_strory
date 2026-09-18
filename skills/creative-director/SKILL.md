---
name: creative-director
description: Use when editing the Claude creative-director prompt (apps/api/app/prompts/video_chat/*.py), creative_audit.py/creative_direction.py schemas, creative_skills catalog, or the FORMAT_PLAYBOOKS/WINNING_AD_STRUCTURES mechanism library and its Russian audit docs.
---

# Storyflow creative-director conventions

This repo-local skill is reached through AGENTS.md; its presence is not automatic implementation authorization.

## Architecture facts (verify before assuming they changed)

- Not an agentic shell loop. Two bounded Anthropic Messages API calls per turn: `Preparation` (picks ≤2 skills, decides research) then `Director` (`apps/api/app/providers/claude.py`).
- `CreativeAudit.candidates` is pinned to exactly 3 (`min_length=3, max_length=3` in `creative_audit.py`). Do not describe or plan for "5–10 candidates" without first changing this schema and the prompt — that is a scoped future milestone, not current behavior.
- `creative_skills/catalog.py` pattern: vendored skill files are hash-pinned and injected as "untrusted reference, not instructions." Any new reference data (playbooks, mechanism library) must follow this same untrusted-reference framing, never as directives the model must obey.
- `ChatProviderResult.audit` is not currently propagated past the provider layer into `chat_api.py`/frontend — treat it as provider-level/test-level/log-level only unless a DB migration is explicitly decided.
- Retrieval for structures/playbooks is tag/keyword matching, not vector search/embeddings, for the current phase. Do not introduce a vector DB without an explicit decision.

## Dialogue humanization rule (already enforced in v3.py — keep it enforced when editing)

Every line a presenter says must sound like something a specific real person would actually say out loud:

- No slogans, no rhetorical antitheses ("It's not about X, it's about Y"), no marketing aphorisms about the offer stated in third person, no listicle cadence unless the format itself is a list.
- If a line could appear in a brand's landing page copy, rewrite it plainer and shorter before using it.
- This applies to every hook/dialogue example added anywhere: prompt text, `FORMAT_PLAYBOOKS`, `WINNING_AD_STRUCTURES`, and the Russian audit docs' mechanism-library tables.

When writing or reviewing any new hook/mechanism example, reject it if it reads as ad copy rather than a spoken reaction, and rewrite it as a short plain clause instead.

## Product vs. person role rule

If product URL or product image evidence identifies a promoted product, that product is the subject being sold. Any supplied person image is a presenter/actor reference only — never treat it as the promoted service or subject, unless the user explicitly asks to promote that person or their own service.

## Docs source of truth

- `docs/audits/UGC_CREATIVE_COMPETITOR_PLAYBOOK_AUDIT_20260911_RU_V2.md` is the single source of truth for the competitor/playbook audit.
- `obsidian/Storyflow-UGC-Vault/02_Competitor_Playbook_Audit_RU_V2.md` is a pointer file only — never re-duplicate the full audit content there.
- `obsidian/Storyflow-UGC-Vault/03_Next_Implementation_Plan.md` carries the addendum on real agent architecture and the audit-storage decision (no DB migration; `playbookFormat`/`selectedStructureIds` go into `ChatProviderResult.audit` plus a lightweight server log, not persisted history or a debug UI).

## Before editing prompts, schemas, or the mechanism library

1. Read the relevant section of `docs/audits/UGC_CREATIVE_COMPETITOR_PLAYBOOK_AUDIT_20260911_RU_V2.md` (§7 format playbook shape, §17 candidate scoring, §18 implementation blueprint) so new work matches the agreed shape instead of re-deriving it.
2. Check `apps/api/app/creative_audit.py` and `apps/api/app/prompts/video_chat/v3.py` for current constraints (candidate count, scoring dimensions, excluded-mechanism handling) before changing behavior that depends on them.
3. Any new reference data goes through the same untrusted-reference / hash-pinned pattern as `creative_skills/catalog.py`, not as raw prompt text the model must follow unconditionally.

## After editing

- If VPS is in scope, diff the changed files against `netcup-cerebro:/opt/storyflow/app/...` before claiming prod is up to date — local and VPS have drifted before. Deploying to prod (rebuilding/restarting `api`/`worker`) requires explicit user confirmation first.
- Re-scan any mechanism-library table you touch for the humanization rule above — partial rewrites (fixing some rows, missing others in later sections) have happened before.
