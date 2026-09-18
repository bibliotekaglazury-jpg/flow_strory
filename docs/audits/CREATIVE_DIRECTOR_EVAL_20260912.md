# Creative Director live eval — 2026-09-12

## Fourth pass — real product generation, Alice case, user-verified

A second, independent live run of the Alice/Wonderland brief through the actual product
(not the eval script) produced:

> *Myślałam, że to tylko bajka dla dzieci. Ale otworzyłam pierwszą stronę i nagle
> wszystko dookoła nabrało sensu. Teraz nie mogę przestać o tym myśleć — sama sprawdź,
> co w tobie zostanie.*

Payoff is internal/emotional ("everything around made sense", "can't stop thinking about
it"), not visual admiration — the `narrative_media` overlay's requiredPayoff held on a
second, independently generated concept, not just the eval script's sample. CTA ("check
for yourself what stays with you") no longer carries the residual visual verb
("zobaczycie") flagged in the third-pass report below.

The shot plan itself placed the subject inside the fully fantastical pink-gold Wonderland
environment for the entire 15s (no realistic framing device, unlike the eval's
hands-holding-a-book reveal). User generated the actual video through the real product
flow and confirmed it is excellent — see `CREATIVE_DIRECTOR.md` "Video and verification"
for what this resolves about fantastical-scene generation feasibility.

---

## Third pass — Phase 1.5 (offer understanding), 4 narrative/hybrid cases, 33.7¢

Trigger: a live interactive case — *"wypromuj ksiazke w nowej niezwyklej kolorowej edycji
alicja w krainie czarów"* with a surreal illustration — produced good craft selling the
wrong value. Its entire payoff was visual admiration (*"Kolory są tak gęste, że chce się
w nie wejść... sama zobaczysz"*): it sold the artefact, not the reading. Root cause was
not the CTA wording but that nothing required the payoff to match **how the offer is
consumed**; a book was routed through mechanics built for physical goods.

Shipped (deliberately minimal — see `CREATIVE_DIRECTOR.md` "Phase 1.5"): `narrative_media`
niche + 5 narrative structures, `consumptionModels` from Preparation (1 primary + at most
1 secondary), `CATEGORY_OVERLAYS` injecting **only the matched category's** requiredPayoff
+ 2-4 forbiddenReductions, code-computed `evidenceAvailable`, adaptive retrieval (6
precise / 10 hybrid), word-anchored keyword matching, and a three-candidate rule with no
artificial ratio. Full pyramid (buyer role, campaign objective as separate layers)
deferred until the eval shows failures there.

| # | Case | Selected mechanism | Verdict |
|---|---|---|---|
| 16 | Illustrated edition (the Alice case) | `colorful-edition-becomes-a-page-pull` (own hybrid) | **PASS** |
| 17 | Book as a gift | `one-more-page-bedtime-ribbon` (own hybrid) | **PASS** |
| 18 | Numbered collector's edition | `unboxing-page-pull-hybrid` (own hybrid) | **PASS** |
| 19 | Audio-drama subscription | `one-episode-pull` | **PASS** |

The edition/object became the *entry* and the story became the *payoff* in all four:

- 16: *"Chciałam tylko zobaczyć okładkę. Otworzyłam na jednej stronie... i się nie
  zatrzymałam. Ten Kapelusznik nie daje mi spokoju."* (The Hatter is canonical to this
  public-domain work, not invented plot.)
- 17: child *"Jeszcze jedna strona, proszę"* → ribbon marks the place → *"Ten prezent
  naprawdę czytają, noc po nocy"* — gifting and reading sold together; the supplied
  ribbon fact is used functionally, not recited.
- 18: *"I only meant to check the slipcase and the foil stamp. Then I opened to page one.
  I'm still reading. Five hundred of these exist"* — scarcity used but grounded in the
  supplied 500-copy fact.
- 19: *"Miałam wysiąść trzy przystanki wcześniej... musiałam usłyszeć, co dalej"* — the
  experience lands before the price/cadence facts, directly countering the category's
  "explain the tariff" reduction.

**Library became a support, not a ceiling:** candidate sets show library mechanisms
(`one-page-pull`, `character-question`, `unfinished-moment`) alongside the director's own
hybrids, and the hybrid was *selected* in 3 of 4 cases — the intended behaviour, and
evidence that a hard 6-10 card allow-list would have capped the result.

**Two residues, recorded not fixed:**

1. Case 16's CTA still says *"sami zobaczycie, jak wciąga"* — the verb is still visual
   even though its object is now the narrative pull ("how it draws you in"), not the
   colours. Semantically corrected, lexically not. Not gated, for the same reason the
   referral-CTA gate was rejected: the distinction is semantic.
2. All four narrative cases chose format `hook_cta`. Plausibly correct for "make them
   want to read", but monotony across a category is a risk worth watching; likely caused
   by 2 of the 5 new narrative structures carrying `hook_cta` as their primary
   `formatBias`. Not changed without more data.

---

## Update — re-run of cases 4, 5, 9 after fixes (same day)

Three fixes were applied and deployed, then cases 4, 5, and 9 were re-run live
(45.2¢, within the ~$0.40–0.55 estimate):

1. **Deterministic offer/CTA gate** (`validate_offer_role` in `creative_audit.py`) plus
   a `v3.py` prompt rule: reject a plan whose spoken CTA books a clinic
   appointment/exam while the stated audience is evaluating or buying a product.
2. **Pydantic validation-error logging** for repair rounds — field path (`loc`) and
   error `type` only, never raw values or model text.
3. Both prior fixes (page-imagery retrieval, reference-slug rendering) deployed to VPS.

**Case 9 — now PASS.** CTA: *"Warto to sprawdzić do swojego gabinetu"* (worth checking
for your own clinic) — points at a purchase decision, not an appointment. The model
self-imposed `negativeRules: ["Nie zapraszać widzów na wizytę czy badanie u tego
lekarza"]` — a direct echo of the new `v3.py` rule. This run happened to pass on the
first Director attempt (no repair round triggered), so it confirms the *prompt* rule
helps, not that the deterministic gate itself fired live — the gate's mechanics are
proven separately by regex unit tests against the exact pre-fix case-9 text
(`test_offer_role_gate_catches_the_2026_09_12_case_9_regression`), including two
negative controls (case 2's legitimate purchase CTA, case 8's legitimate appointment
CTA) confirming it won't false-positive on those shapes.

**Case 5 — slug leak confirmed fixed live.** `negativeRules`/`productRules` are now
plain Polish prose (no `no_invented_specs`-style tokens) on a real API response.

**Case 4 — passed clean, prior failure not reproduced.** Booksy resolved fine, real
facts used (5.0/33 reviews), no fabricated claims. The original `CHAT_INVALID_RESPONSE`
looks like a one-off model instability rather than a reproducible bug; the new
validation-error logging is now in place if it recurs.

**Revised total: 7 clean PASS, 2 originally-failing cases now fixed and confirmed live
(9, and the slug-leak aspect of 5) = effectively 9/9 on this pass**, with case 4's root
cause still unconfirmed (didn't recur, so nothing left to diagnose from this run).

---


Live planning-only run against the real Anthropic API. No video generation, no video
provider/model calls, no DB persistence — each case calls
`ClaudeCreativeDirectorAdapter.send_message` directly via
`scripts/chat/eval-creative-director.py`. Real spend: **$0.9964** across 9 live calls
(one, case 4, errored before producing a plan). Raw records: `.local/creative-director-eval/case-*.json`
(gitignored, local only).

## Result summary

| # | Case | URL/image resolved | Format | Mechanism | Verdict |
|---|---|---|---|---|---|
| 1 | Ecommerce product (Medivon) | resolved | ugc_review | `one-specific-use` | **PASS** |
| 2 | Medical/B2B device (USG) | resolved | product_demo | `static-to-working` | **PASS** |
| 3 | Course (British Council) | failed → `web_fetch` fallback used | problem_solution | `problem-solution-app-fatigue` | **PASS** |
| 4 | Local specialist (Booksy) | resolved | — | — | **FAIL (inconclusive)** |
| 5 | SaaS B2B (NextFlow) | resolved | problem_solution | `old-way-dropped` | **PASS*** |
| 6 | Tourism (Food Tour Krakow) | resolved | trending_style | `pov-moment` | **PASS** |
| 7 | Product image only | n/a (image) | ugc_review | `doubt-then-one-reason` | **PASS*** |
| 8 | Massage photo only | n/a (image) | problem_solution | `everyday-tension-relief` | **PASS** |
| 9 | Person image + device offer | n/a (image) | problem_solution | `old-way-dropped` | **FAIL** |

`*` = passed the scenario's core criterion but ran on code that predates the reference-slug
fix below; not yet re-verified live against the fixed code.

**7 / 9 pass outright, 1 clear fail (case 9), 1 inconclusive error (case 4).**

## Detailed findings

### Case 1 — Ecommerce product: PASS
Offer resolved precisely: *"Masażer limfatyczny Medivon Lumina do nóg – kompresja
powietrzna, 6 trybów, 12 poziomów intensywności, bezprzewodowy"* — not generic wellness.
`spokenScript`: *"Nogi ciążyły mi po całym dniu. Wkładam to na piętnaście minut i czuję,
jak napięcie znika."* — plain spoken Polish, no slogans. Model self-imposed
`productRules`: *"Nie wymyślaj dodatkowych specyfikacji poza dostarczonymi faktami."*
Scores 3–5, all above threshold.

### Case 2 — Medical/B2B device: PASS
Offer correctly framed as the device: *"Air Essence UltraLite L4 – profesjonalny,
przenośny aparat USG (15-calowy obracany ekran, do 120 min pracy na baterii...)"*.
Objective explicit: *"Pozyskać nowych klientów B2B... zainteresowanych **zakupem**
przenośnego aparatu USG"* — purchase intent, not an exam-booking service. Character
role correctly bounded: *"Lekarz/technik medyczny (aktor-prezenter, nie osoba z
materiału referencyjnego jeśli taka istnieje)"*.
Found here: `negativeRules` leaked raw internal slugs
(`["no_invented_specs", "no_fake_usage_result", "no_unsafe_use"]`) instead of prose —
see Fix 2 below.

### Case 3 — Course: PASS
`britishcouncil.pl` failed direct fetch (`PRODUCT_UNAVAILABLE`); the model correctly
used the `web_fetch` tool fallback (`fetches: 1`, `sourceDomains: ["www.britishcouncil.pl"]`)
rather than inventing content — this is the exact fallback path fixed earlier this
session (the `count_tokens`-with-`tools` bug). Self-imposed rule: *"Nie wymyślaj
konkretnej ceny ani rabatu."* No fake guarantees.

### Case 4 — Local specialist (Booksy): FAIL, inconclusive
```
error.code: CHAT_INVALID_RESPONSE
error.message: "No acceptable new concept was produced. Adjust the brief and try again."
```
Page resolved fine (12,000 chars of evidence, 1 page image). The adapter's repair loop
exhausted both attempts with a schema/parse failure (`CHAT_INVALID_RESPONSE` specifically,
not `CREATIVE_QUALITY_LOW` or `CREATIVE_MECHANISM_REPEATED`, which map to different
codes) — meaning the model produced two consecutive malformed/invalid envelopes. The
adapter deliberately discards raw invalid output and model reasoning
(`app/providers/claude.py` — "No raw invalid output or model thinking enters repair
context or logs"), so the exact malformed field is not recoverable from this run's
records without instrumented re-run. Suspected file: `apps/api/app/providers/claude.py`
(`parse_director_envelope` / `DirectorEnvelope` validation), possibly triggered by
Booksy's page content (customer photos/reviews mixed into page text) confusing schema
fields — not confirmed. **Needs a clean re-run with temporary diagnostic logging before
any code fix is justified; not fixed in this session.**

### Case 5 — SaaS B2B: PASS on substance, ran pre-fix
Correctly B2B, Polish business context: *"Kiedyś przepisywałem NIP, adres i PKD
ręcznie... Teraz wpisuję dziesięć cyfr i mam to w sekundę."* `negativeRules` shows the
same raw-slug leak as case 2 (`["no_invented_specs", "no_fake_testimonial", ...]`) —
confirmed this ran before the reference-slug fix reached the running process (see
Timing note below).

### Case 6 — Tourism: PASS
*"I got to Krakow this morning with zero idea what to eat here. My guide just handed
me taste one of fourteen."* — natural spoken English, booking CTA present.
`productRules` pinned to sourced facts only (13–14 tastings, 3.5h, price, meeting
point). No invented dish names. This case's `negativeRules` were already prose, not
slugs — the leak is probabilistic, not universal (see Timing note).

### Case 7 — Product image only: PASS on substance, ran pre-fix
Correctly stayed within visible evidence: *"Nie wolno wymyślać dodatkowych funkcji ani
danych technicznych spoza tego co widoczne na zdjęciu."* Also leaked slugs in
`negativeRules`. Secondary finding: `researchUsed: true` — Preparation decided the
image-only brief needed a live web search, which returned generic competitor wellness
content (`renpho.com`, `tomsguide.com`, etc.) that the model then correctly declined to
use as product fact — but the search was paid for and unused. Minor cost inefficiency,
not a correctness bug.

### Case 8 — Massage photo only: PASS
Correctly framed as a service, not a product: *"Usługa masażu świadczona osobiście
przez masażystkę... Usługa masażu jest przedmiotem promocji, nie wizerunek klientki."*
`negativeRules` already prose in this run.

### Case 9 — Person image + device offer: **FAIL**
This is the case the person/product role rule exists for, and the top-level fields look
correct in isolation:
- `offer`: *"Przenośny aparat USG do gabinetu lekarskiego"* (the device)
- `characters`: *"Lekarz - referencyjny wizerunek z dostarczonego zdjęcia, występuje
  jako prezenter/użytkownik urządzenia, **nie jako promowany podmiot**"* (correctly
  bounded presenter role)
- `audience`: *"Lekarze i właściciele małych gabinetów medycznych... rozważający
  **własny sprzęt USG**"* (doctors considering **buying** their own device — B2B buyer
  audience)

But the delivered `spokenScript` breaks this:
> *"Kiedyś odsyłałem pacjenta na USG gdzieś indziej i czekaliśmy razem na wynik. Teraz
> aparat mam tu, na miejscu, widzę obraz od razu. **Zapytajcie w recepcji o badanie USG
> u nas.**"*

The CTA — "ask at our reception about an ultrasound exam" — addresses **patients**
booking an **exam at this doctor's clinic**, not the stated audience of **other doctors
deciding whether to buy the device**. The scene's internal logic (a doctor talking
diegetically about his own practice) naturally produces patient-facing clinic messaging,
even though every structured field claims a B2B buyer audience and a device offer. This
is exactly the failure mode the original audit's person/product role bug described:
the ad **functions** as ultrasound-service advertising despite the schema saying
"device." Compare case 2, whose CTA correctly points at a purchase decision ("Zobaczcie
sami na stronie" — check the offer online) rather than at booking an appointment.

**Root cause is a structural gap, not a simple field bug:** nothing in `v3.py`'s
product/person role rule or in the offered structures
(`professional-viewpoint`, `old-way-dropped`) requires the *spoken CTA* to match the
stated *audience*. The rule governs who the *subject* is, not who the *line is talking
to*. Suspected files: `apps/api/app/prompts/video_chat/v3.py` (role rule needs an
audience/CTA-consistency clause) and/or
`apps/api/app/creative_direction_playbooks.py` (the `professional-viewpoint` /
`old-way-dropped` structures' `ctaStyle` should make the B2B-buyer framing explicit
rather than leaving it to the model to infer from a first-person clinic narrative).
**Not fixed in this session** — needs a decision on which layer should own this
constraint before writing a fix blindly.

## Fixes applied during this eval (already tested, not yet re-verified live post-fix on all cases)

### Fix 1 — page imagery ignored by structure retrieval
`select_structures()` in `apps/api/app/creative_direction_playbooks.py` only checked
`contextBundle.availableAssets` for `product_image`/`person_image` satisfaction. Images
sourced from the offer page (`og:image`, sent via `context["images"]`) never become an
owned asset, so on the most common real flow — a URL-only brief with no manually
uploaded file — product-visual structures were systematically penalised and pushed out
of the top-N offered to the director. Confirmed live: case 1 changed from mechanism
`everyday-interruption-relief` (pre-fix) to `one-specific-use` (a seed structure,
post-fix) on an identical brief.

Fix: added `image_roles` parameter to `select_structures()`; `claude.py` now passes the
roles of every image actually sent to the director. Regression tests added:
`test_page_imagery_counts_as_a_product_image`,
`test_uploaded_person_image_satisfies_person_requirements`,
`test_page_imagery_reaches_structure_retrieval` (adapter-level).

### Fix 2 — internal rule slugs leaking into delivered plan fields
Case 2 live output copied raw internal identifiers into `negativeRules` verbatim:
`["no_invented_specs", "no_fake_usage_result", "no_unsafe_use"]`. These slugs exist only
as machine-readable tags on `WINNING_AD_STRUCTURES[*]["forbidden"]` and were never meant
to reach the delivered plan — every other passing case produced prose there instead
(e.g. case 3: `["Brak wzmianek o cenach lub gwarancjach, których nie potwierdzono"]`).

Fix: added `as_reference()` in `creative_direction_playbooks.py`, which renders
`forbidden` slugs as prose (`"no_invented_specs"` → `"no invented specs"`) before they
enter the `CREATIVE_DIRECTION_REFERENCE` block sent to the director — the seed data
itself stays machine-readable. Added one line to `v3.py`: plan fields must be "plain
readable directions in the brief's language; never copy reference identifiers or rule
labels into them." Regression test:
`test_reference_rendering_hides_slugs_without_mutating_the_seed`, plus an adapter-level
assertion that no underscore-joined slug reaches the model
(`test_selected_format_supplies_its_full_playbook_and_matching_structures`).

**Not yet verified live**: cases 5, 7, 8 that showed the leak ran on the pre-fix binary
(see Timing note) — the mocked tests confirm the fix's mechanics but not that it holds
under a real model response.

### Fix 3 (earlier this session, confirmed live in cases 1, 2, 5, 6, 8, 9 above) —
`count_tokens` rejecting server tools. Fixed before this eval batch; case 3 and case 9's
successful `web_fetch`/`web_search` fallbacks in this same eval are live confirmation it
holds.

## Timing note — why 5, 7, 8 show the slug leak and 6, 9 don't

The background run for cases 4–9 was started in the same turn as cases 1–3, before the
`as_reference` fix was written to disk (`creative_direction_playbooks.py` saved at
03:27:48; the case 4–9 subprocess had already started and kept the pre-fix module in
memory for its whole run, through case 9 at 03:35:34). So **all of cases 4–9 ran on
pre-fix code** — the fact that cases 6 and 9 happened not to leak a slug just reflects
that the leak was already probabilistic before the fix (the model sometimes phrased
`negativeRules` in its own words anyway). This means Fix 2 is verified against the mock
harness (`pytest`, 264 passed) but **not yet against a live call**.

## Cross-cutting pattern worth naming

Across 1, 2, 8 the model reliably self-imposes a "don't invent specs/results beyond
what's supplied" rule into `productRules`/`negativeRules` even when not directly told
to — the `v3.py` claim-safety instructions and the `forbidden` tags on offered
structures are visibly doing their job. The one place this discipline doesn't carry
through is case 9's CTA register, which is a narrative/audience-consistency gap, not a
factual-claims gap.

## Cost

| Case | Cost | Rounds |
|---|---|---|
| 1 | 9.97¢ | 2 |
| 2 | 17.19¢ | 3 |
| 3 | 12.74¢ | 3 |
| 4 | 0¢ (errored) | — |
| 5 | 10.63¢ | 2 |
| 6 | 6.78¢ | 2 |
| 7 | 11.16¢ | 3 |
| 8 | 6.30¢ | 2 |
| 9 | 24.88¢ | 4 |
| **Total** | **$0.9964** | |

## Outstanding items from the first pass — resolution status

1. **Case 9's audience/CTA-consistency gap** — **fixed** (`validate_offer_role` +
   `v3.py` rule) and re-verified live; see "Update" section above.
2. **Case 4's schema failure** — re-run clean, did not reproduce; treated as a one-off
   model instability. Diagnostic logging (below) is now in place if it recurs.
3. **Fix 2 (slug leak)** — re-verified live in the same re-run; confirmed fixed.

---

## Second pass — 2026-09-12 (later): AI-tell phrasing and feature-vs-benefit root cause

User flagged a live line as slop: **"Warto to sprawdzić do swojego gabinetu"**
(case 9's re-run CTA) — grammatically valid Polish, but templated ad-copy register, not
something a specific person would actually say. This is a different defect class from
everything fixed so far: not a slogan/antithesis (already banned), not an
offer/audience mismatch (already gated) — a generic hedge-opener/filler phrase.

### Root cause 1 — no coverage for hedge-opener/filler phrasing

The existing `v3.py` humanization rule bans slogans, antitheses, and marketing
aphorisms — a real structural check. "Warto to sprawdzić" ("it's worth checking out")
matches none of those; it's short and plain by the rule's own test, so it passed. This
was a genuine coverage gap, not a bug in the existing rule or the deterministic offer
gate.

**Fix — not invented, sourced from a real public MIT-licensed skill:**
[Aboudjem/humanizer-skill](https://github.com/Aboudjem/humanizer-skill) (commit
`a58df065367550b6ce40ff3f648335018d8e0589`), `cli/lib/vocabulary.js`, lists
`"it's worth noting"` / `"it is worth noting"` as a documented AI-tell filler phrase.
"Warto..." is the direct Polish register equivalent. Added `AI_TELL_PATTERNS` +
`validate_spoken_register()` in `creative_audit.py` — a deterministic regex gate on
`spokenScript` (English tier-1 AI-vocabulary words + the "warto
zauważyć/wspomnieć/podkreślić/zaznaczyć/dodać/sprawdzić/zobaczyć/wypróbować" Polish
hedge-opener family), wired into the same non-soft-accepting repair loop as the offer
gate. Also cross-checked
[blader/humanizer](https://github.com/blader/humanizer) (MIT) — its documented
"Not X but Y" / hollow-aphorism tells independently confirm the *existing* v3.py
slogan/antithesis rule targets a real, named category, not an invented one.

Covered by **10 parametrized regression tests** across niches/languages *before*
deploying (`test_spoken_register_gate_across_niches_and_languages` in
`test_creative_audit.py`): 7 true positives (beauty-device/SaaS/course/ecommerce/
gadget/tourism/massage, PL and EN) + 2 negative controls built from real passing
dialogue (case 2's legitimate purchase CTA, case 8's legitimate appointment CTA) + 1
clarification-turn no-op case.

### Root cause 2 — the seed data itself modeled the weak-CTA pattern

Deeper investigation (user's core finding): across cases 1, 3, 4, 7, the dialogue
described **mechanism/specs/stats** (a zipper, a compression detail, a 5.0/33 review
score, "logging in") instead of the **felt effect/outcome** — a distinct, more
consequential problem than any single filler phrase. This is exactly the "Benefits
over Features" / "Show over tell" principle already present in our own **already
vendored and reviewed** skills (`docs/audits/claude-skill-review.md` approved these on
2026-09-11): `copywriting.md` ("Features: what it does. Benefits: what that means for
the customer" / "Show over tell — describe the outcome instead of using adverbs") and
`hook-method.md`'s explicit weak→strong CTA table (`"Learn more"` → `"See your
options"`).

Auditing `WINNING_AD_STRUCTURES.ctaStyle` (our own Phase 1 seed data, injected
unconditionally every turn — not skill-selected) found **21 of 40 entries** matched the
literal "weak CTA" pattern named in `hook-method.md`: e.g. `"Point to dimensions in the
description"`, `"Send them to the product description"`, `"Invite a look at the offer
page"`. Since every Director call receives 6–10 of these as reference, over half the
turns were being nudged toward exactly the register the user flagged. **This, not a
prompt-wording gap, was the primary root cause** — fixed by rewriting all 21 fields to
state the felt result instead of pointing elsewhere (e.g. → `"Say what changed your
mind, not where to read about it"`, → `"Describe how the size actually felt, not just
the number"`), plus one `v3.py` rule paragraph citing the same real, already-approved
principle. Regression test: `test_cta_style_states_outcome_not_a_pointer_to_specs`.

**Deliberately not added:** a deterministic regex gate on "referral-only" CTA phrasing
(e.g. flagging `"zobacz(cie) na stronie"` / `"check the description"`). Reasoning,
concretely: case 1's slop line — *"Zobaczcie na stronie, jak to działa"* — has zero
outcome content. Case 5's passing line — *"...samo się uzupełniło... Sprawdźcie
NextFlow — czternaście dni za darmo, bez karty"* — contains the same lexical referral
shape (`"sprawdźcie"` + product name) but *also* states the outcome right before it and
gives a concrete offer term after. A regex sees the same "check X" construction in
both and cannot distinguish "referral instead of substance" from "referral after
substance" — that line is semantic, not lexical. Forcing a hard gate here risked
false-positiving on already-correct cases 2/3/5. Decision: fix the root cause (seed
data + prompt principle) rather than police the symptom with an unreliable pattern.

### Re-verification — original 5 flagged lines, live, after both fixes (71.3¢)

| Case | Before | After |
|---|---|---|
| 1 | *"Zobaczcie na stronie, jak to działa."* | *"Po chwili nogi są lżejsze, w końcu mogę odetchnąć. Jeśli Twoje nogi też tak kończą dzień, spróbuj tego uczucia."* |
| 3 | *"...loguję się wieczorem, mam żywego nauczyciela..."* | *"...a tu loguję się wieczorem, żywy nauczyciel, mała grupa, normalna rozmowa. Po paru tygodniach pierwszy raz nie boję się mówić."* |
| 4 | *"...mam ocenę pięć na pięć od trzydziestu trzech osób."* | *"Wpadnij do mnie tutaj... umów się na masaż i sam sprawdź, jak szybko można to rozluźnić."* (rating dropped entirely) |
| 7 | *"...zobacz ten suwak, jak ładnie się zapina. I ten ucisk na łydce..."* | *"Ale nogi po całym dniu w biurze naprawdę odpoczęły. Ten ucisk robi swoje."* |
| 9 | *"Warto to sprawdzić do swojego gabinetu."* | *"Naprawdę zmieniło mi to dzień pracy — polecam każdemu, kto prowadzi swoją praktykę."* |

Quality scores and audience/role correctness held (3.5–5.0 across all dimensions on
all five); no AI-tell phrase reappeared on any of the five live re-runs.

### Generalization test — 6 new niches never seen before, 15 total live cases (42.5¢)

To check the fixes generalize rather than being overfit to the original 9, ran 6 fresh
synthetic briefs (no URL — facts supplied directly, research declined) in categories
not covered before: apparel (recycled-material sneakers), home goods (custom wardrobe
installer, London), pet care (mobile dog grooming), fintech (a budgeting app with an
explicit "no bank credentials" constraint — a claim-safety stress test), automotive
(mobile detailing, explicit `hook_cta` format), and kids/toys (a STEM subscription box
with `testimonial` format explicitly requested and **no supplied quote/source** — a
direct stress test of the "no fabricated testimonial" rule from the original audit's
§19 test plan).

**All 6 passed:**
- Every spoken line led with the felt effect ("osiem butelek nie wylądowało w wodzie",
  "checking my balance finally stopped scaring me", "Didn't think a rented flat could
  look like this"), not a spec/mechanism recitation.
- No AI-tell phrase appeared in any of the 6.
- The testimonial-without-source case correctly became a parent/creator impression
  ("I always wonder if these subscription boxes actually get touched...") with a
  self-imposed rule against a fabricated testimonial — not an invented customer quote.
- The fintech case self-imposed "Do not show or imply a bank login screen" and invented
  no savings/outcome numbers, honoring the supplied "no bank credentials" fact exactly.
- `spokenLanguage` matched the brief's language precisely in every case, including
  distinguishing `en-GB` (the London-context brief) from `en-US` (the other English
  briefs) — confirms the existing language-consistency rule, not a new fix.

### Session total live spend

$0.9964 (first pass, cases 1–9) + $0.452 (re-run 4/5/9) + $0.713 (re-run 1/3/4/7/9) +
$0.425 (6 new-niche cases) = **$2.55** across 24 live planning calls this session.
