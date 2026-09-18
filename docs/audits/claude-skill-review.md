# Creative skill source and transformation review — 2026-09-11

Reviewer: Codex implementation agent `/root/skills` (self-review; no independent human approval claimed).
Decision: **approved for bounded local creative-reference loading**, all six IDs below.
This does not approve deployment or claim model-level prompt-injection immunity.

Pinned commits were resolved with GitHub commits/HEAD REST endpoints, and all original
texts and LICENSE files fetched successfully using curl from raw.githubusercontent.com
at those exact commits. No Git command, repository script, paid API, or .env access was used.
Both LICENSE files explicitly grant MIT terms, copyright 2025 Corey Haines and 2025
Creative Ad Agent respectively; they are preserved byte-for-byte beside derivatives.

`claude-skill-transformations.json` records original URLs/paths, immutable commit SHA,
original and derivative SHA-256, exact section boundaries, exact removed lines,
exact replacements, and the entire added attribution/scope prefix. The six neighboring
`.diff` files are full human-readable unified diffs against the pinned originals.
They contain deleted upstream instructions as audit evidence and MUST NOT be loaded
as runtime skills. The runtime loads only the explicit vendor manifest paths.

| ID | Preserved methodology | Deliberate exclusions and meaning review | Decision |
| --- | --- | --- | --- |
| customer-research | Existing-evidence extraction, functional/emotional/social jobs, pains, triggers, vocabulary, synthesis, confidence and sampling bias | Online gathering, outreach/interviews, filesystem context lookup, deliverables and handoffs excluded. Sample minimum reframed as provisional interpretation, preserving uncertainty without blocking a short concept. | Approved |
| product-marketing | All 12 positioning categories, offer/audience, competition, differentiation, switching forces, voice, proof and goals | Codebase scan, interactive document creation, migration, changelog and file saving removed. Categories are a context checklist, not mandatory questions or invented customer facts. | Approved |
| offers | Attributed value equation and its four levers; honest concrete offer wording | Building new guarantees/bonuses/pricing, reference loading, unsupported conversion-lift figures and campaign advice excluded. Only existing verified offer terms can be expressed. | Approved |
| ad-creative | Distinct motivations and angle categories, variations, grounded specific headline/body quality | Campaign CLI commands, generation providers, batch writes, roadmap, upload formats and mutable platform specs removed. Variations inform creative planning, not platform management. | Approved |
| copywriting | Clarity, benefits, specificity, customer language, one idea, writing checks, CTA and voice | Filesystem lookups, references/handoffs, website output schemas and unsupported uplift statistics removed. Spoken-copy adaptation intentionally omits webpage layout requirements. | Approved |
| hook-method | Research-first extraction categories, ten hook types, source-to-hook matching, construction, body/CTA, diversity, final checks and failure modes | Brand-file read and hook-bank write removed; unavailable categories remain unknown. Hidden-reasoning-style field changed to concise FIT evidence. Mortgage examples remain explicitly illustrative, not current-offer facts. | Approved |

Reviewed selected text against the originals for factual meaning, missing qualifiers,
behavioral directives, authority escapes and surviving action/tool requests. Remaining
imperatives concern creative methodology only; CTA examples such as “Download the Guide”
are sample ad text, not commands to tools. Scope prefaces and the JSON-quoted boundary
make the reference status explicit. No executable tools, provider identifiers, arbitrary
paths or credentials are supplied through summaries. Loader hash checking fails closed
on post-review text edits. A content update requires new hashes, a new diff and review.

Validation: initial test run failed at import because the catalog package did not exist;
implementation then passed the targeted tests. Final command results are in the task report.
The filesystem is a trusted deployment asset; the loader is not a protection against a
host administrator concurrently replacing directories or editing both manifest and code.
