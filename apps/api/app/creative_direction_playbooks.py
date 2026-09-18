"""First-party creative reference: format playbooks and seed ad structures.

Static curated content, not model output and not third-party vendor text, so it needs
neither the hash-pinned manifest of app.creative_skills nor Pydantic validation. It is
still supplied to the director as reference data, never as instructions.

Hook lines are seeds in plain spoken register. An empty hook means the structure opens
on visual action with no spoken line. Mechanism slugs satisfy CreativeMechanism so the
director can reuse them directly; hookType values match CreativePlan.hookStrategy.
"""

import hashlib
import math
import re
from collections import Counter

FORMAT_PLAYBOOKS = {
    "ugc_review": {
        "label": "UGC Review",
        "userIntent": "Make the offer look noticed by a real person instead of sold by a narrator.",
        "bestFor": ["physical product", "cosmetics", "gadget", "home product", "professional device"],
        "notFor": ["strict technical demo", "formal compliance messaging"],
        "firstThreeSeconds": {
            "purpose": "Establish a person reacting to something specific, not an announcement.",
            "allowedHookTypes": ["curiosity", "verbal", "visual", "contradiction"],
            "forbiddenOpenings": ["brand name recital", "slogan", "list of features"],
        },
        "productIntegration": {
            "heroRole": "The product is held, examined or used on camera.",
            "supportingRole": "One detail carries the reason to care.",
            "forbiddenRole": "Product only named, never seen.",
        },
        "qualityGate": [
            "A human reaction, not a corporate pitch",
            "One concrete detail or use case",
            "No invented personal experience",
            "Shootable in 15 seconds",
        ],
    },
    "product_unboxing": {
        "label": "Product Unboxing",
        "userIntent": "Build anticipation and deliver a reveal of what the offer actually is.",
        "bestFor": ["physical product", "kit", "gift item", "professional equipment"],
        "notFor": ["service with nothing to reveal", "software only"],
        "firstThreeSeconds": {
            "purpose": "Withhold the full view while showing that something is about to appear.",
            "allowedHookTypes": ["curiosity", "visual", "demonstration"],
            "forbiddenOpenings": ["full product already centred and static", "price announcement"],
        },
        "productIntegration": {
            "heroRole": "The product is the reveal itself.",
            "supportingRole": "Hands, surface and scale reference only.",
            "forbiddenRole": "Inventing packaging or accessories that were never supplied.",
        },
        "qualityGate": [
            "The reveal actually shows something new",
            "No fabricated box or accessories",
            "Product is visually central",
            "Fits 15 seconds without rushing",
        ],
    },
    "problem_solution": {
        "label": "Problem to Solution",
        "userIntent": "Open on recognizable friction and introduce the offer as the practical answer.",
        "bestFor": ["tool", "service", "b2b offer", "time-saving product"],
        "notFor": ["offers with no articulable problem", "pure aesthetic products"],
        "firstThreeSeconds": {
            "purpose": "Name or show the friction before naming the offer.",
            "allowedHookTypes": ["situational", "contradiction", "emotional", "verbal"],
            "forbiddenOpenings": ["product beauty shot", "invented crisis", "fear framing"],
        },
        "productIntegration": {
            "heroRole": "The product appears as the resolution of the shown friction.",
            "supportingRole": "Environment shows where the friction lives.",
            "forbiddenRole": "Promising outcomes the offer cannot evidence.",
        },
        "qualityGate": [
            "Friction is real and recognizable",
            "Offer arrives as a logical answer",
            "No fabricated proof or result",
            "One problem, not a list",
        ],
    },
    "product_demo": {
        "label": "Product Demo",
        "userIntent": "Show the offer working or in its real situation rather than listing features.",
        "bestFor": ["device", "tool", "kit", "software with visible interface", "equipment"],
        "notFor": ["offers with nothing visible to operate"],
        "firstThreeSeconds": {
            "purpose": "Start on action, not introduction.",
            "allowedHookTypes": ["demonstration", "visual", "situational"],
            "forbiddenOpenings": ["long verbal preamble", "feature list", "logo card"],
        },
        "productIntegration": {
            "heroRole": "The product performs one clear action.",
            "supportingRole": "Hands and workspace make the action readable.",
            "forbiddenRole": "Talking about the product while it sits unused.",
        },
        "qualityGate": [
            "Something visibly happens",
            "One action arc, not a catalogue",
            "No invented specifications",
            "Action readable at small screen size",
        ],
    },
    "testimonial": {
        "label": "Testimonial",
        "userIntent": "Build trust from a real perspective without fabricating a customer.",
        "bestFor": ["offers with supplied quotes or sources", "professional services", "courses"],
        "notFor": ["no supplied source and no honest creator framing available"],
        "firstThreeSeconds": {
            "purpose": "Establish whose perspective this is and why it is legitimate.",
            "allowedHookTypes": ["verbal", "contradiction", "emotional"],
            "forbiddenOpenings": ["invented customer story", "unsourced result claim"],
        },
        "productIntegration": {
            "heroRole": "The offer is what the perspective is about.",
            "supportingRole": "Shown while being discussed.",
            "forbiddenRole": "Claiming ownership, long-term use or results without evidence.",
        },
        "qualityGate": [
            "Perspective is honest about what is known",
            "No invented customer, quote or outcome",
            "Offer stays concrete and visible",
            "Reads as a person talking, not a review script",
        ],
    },
    "trending_style": {
        "label": "Trending Style",
        "userIntent": "Feel like native social content rather than a polished advertisement.",
        "bestFor": ["consumer product", "cosmetics", "gadget", "food", "apparel", "app"],
        "notFor": ["formal b2b tone", "compliance-heavy offers"],
        "firstThreeSeconds": {
            "purpose": "Break the scroll with rhythm or surprise while staying about the offer.",
            "allowedHookTypes": ["pattern_interrupt", "situational", "curiosity", "verbal"],
            "forbiddenOpenings": ["random chaos unrelated to the offer", "copying a specific creator's trend"],
        },
        "productIntegration": {
            "heroRole": "Product stays central despite the loose style.",
            "supportingRole": "Handheld movement and real setting carry authenticity.",
            "forbiddenRole": "Style so busy the offer disappears.",
        },
        "qualityGate": [
            "Pattern interrupt earns attention honestly",
            "Offer still clearly central",
            "Low-polish but readable",
            "No borrowed specific trend or audio claim",
        ],
    },
    "hook_cta": {
        "label": "Hook to CTA",
        "userIntent": "Build the whole spot around one strong opening and one clear action.",
        "bestFor": ["direct response", "single offer", "promotion with a real source-backed date"],
        "notFor": ["offers needing explanation before any ask"],
        "firstThreeSeconds": {
            "purpose": "Earn attention with one move, no warm-up.",
            "allowedHookTypes": ["verbal", "curiosity", "visual", "situational"],
            "forbiddenOpenings": ["generic audience callout", "vague promise", "invented urgency"],
        },
        "productIntegration": {
            "heroRole": "Product is clear in frame when the ask lands.",
            "supportingRole": "Single supporting detail only.",
            "forbiddenRole": "Ask with no visible offer.",
        },
        "qualityGate": [
            "One hook, one ask",
            "Audience is specific",
            "No invented deadline or discount",
            "Ask is a next step, not pressure",
        ],
    },
    "before_after": {
        "label": "Before / After",
        "userIntent": "Show a contrast of state, scene or workflow without fabricating results.",
        "bestFor": ["organizers", "tools", "workspace equipment", "setup-dependent offers"],
        "notFor": ["medical or treatment outcomes", "offers whose change cannot be shown"],
        "firstThreeSeconds": {
            "purpose": "Establish the 'before' state clearly enough that the change reads later.",
            "allowedHookTypes": ["visual", "situational", "curiosity"],
            "forbiddenOpenings": ["result claim up front", "implied treatment outcome"],
        },
        "productIntegration": {
            "heroRole": "The product causes the visible change.",
            "supportingRole": "Scene carries the contrast.",
            "forbiddenRole": "Contrast implying a physical or medical result.",
        },
        "qualityGate": [
            "Contrast is scene or workflow, never a body or health outcome",
            "Both states readable in 15 seconds",
            "No fabricated outcome or timeframe",
            "Product visibly connects the two states",
        ],
    },
    "self_presentation": {
        "label": "Self-presentation",
        "userIntent": "A specialist or founder presents themselves and their own service to camera.",
        "bestFor": ["freelancer or consultant", "agency or studio owner", "coach or trainer", "local professional"],
        "notFor": ["a physical product the person only presents"],
        "firstThreeSeconds": {
            "purpose": "Name the viewer's problem in their words before the person introduces themselves.",
            "allowedHookTypes": ["verbal", "contradiction", "situational"],
            "forbiddenOpenings": ["name and job title first", "company history", "slogan"],
        },
        "productIntegration": {
            "heroRole": "The person is the offer: face, voice and one concrete credential.",
            "supportingRole": "Their real working context makes the credential believable.",
            "forbiddenRole": "Inventing a product, packaging or client result the brief does not give.",
        },
        "qualityGate": [
            "Problem before introduction",
            "One concrete credential, not a list",
            "One low-effort next step",
            "A supplied script is spoken as written",
        ],
    },
}

NICHE_KEYWORDS = {
    "narrative_media": (
        "book", "książk", "ksiazk", "powieś", "powies", "novel", "read", "czyta",
        "film", "movie", "serial", "komiks", "comic", "audiobook", "słuchowisk",
        "story", "histori", "opowieś", "opowies", "gra ", "gry", "gier", "game",
        "fabuł", "fabul", "wydani", "edition", "rozdzia", "chapter",
    ),
    "ecommerce_physical": ("product", "shop", "store", "order", "delivery", "produkt", "sklep"),
    "beauty_cosmetics": ("cream", "serum", "skin", "cosmetic", "makeup", "krem", "kosmetyk", "skóra"),
    "beauty_device": ("device", "apparatus", "laser", "salon", "clinic", "cabinet", "urządzenie", "gabinet"),
    "gadget_tech": ("gadget", "electronic", "charger", "headphone", "camera", "smart", "gadżet"),
    "home_goods": ("home", "kitchen", "furniture", "storage", "organizer", "dom", "kuchnia"),
    "apparel": ("wear", "clothing", "shirt", "shoes", "fabric", "ubranie", "buty"),
    "food_beverage": ("food", "drink", "coffee", "tea", "snack", "taste", "kawa", "jedzenie"),
    "course_education": ("course", "lesson", "learn", "training", "language", "kurs", "nauka"),
    "saas_digital": ("app", "software", "platform", "subscription", "dashboard", "aplikacja"),
    "b2b_professional": ("business", "professional", "equipment", "office", "clinic", "firma", "biznes"),
    "local_service": ("service", "booking", "appointment", "studio", "usługa", "wizyta"),
    "health_wellness": ("health", "wellness", "fitness", "supplement", "zdrowie", "fitness"),
}

WINNING_AD_STRUCTURES = [
    {
        "id": "ugc_first_noticed_detail",
        "niche": ["ecommerce_physical", "beauty_cosmetics", "gadget_tech", "home_goods"],
        "formatBias": ["ugc_review"],
        "hookType": "curiosity",
        "mechanism": "first-noticed-detail",
        "hook": "First thing I noticed was this bit here.",
        "productRole": "Held and turned so the noticed detail is visible",
        "ctaStyle": "Say why that detail is what made you stop",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_fake_usage_result", "no_invented_specs"],
    },
    {
        "id": "ugc_doubt_then_one_reason",
        "niche": ["ecommerce_physical", "beauty_cosmetics", "gadget_tech", "saas_digital"],
        "formatBias": ["ugc_review", "testimonial"],
        "hookType": "contradiction",
        "mechanism": "doubt-then-one-reason",
        "hook": "I figured it would be like all the others. Then I saw this.",
        "productRole": "Doubt is stated, then one visible detail answers it",
        "ctaStyle": "Say what changed your mind, not where to read about it",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_fake_conversion_claim", "no_fake_usage_result"],
    },
    {
        "id": "ugc_plain_talk_walkthrough",
        "niche": ["course_education", "saas_digital", "local_service", "b2b_professional"],
        "formatBias": ["ugc_review", "product_demo"],
        "hookType": "verbal",
        "mechanism": "plain-talk-walkthrough",
        "hook": "No big claims, I will just show you what this is.",
        "productRole": "Offer shown plainly while being described",
        "ctaStyle": "Say plainly what it actually did, no pointing elsewhere",
        "assetRequirements": [],
        "forbidden": ["no_corporate_ad_tone", "no_invented_specs"],
    },
    {
        "id": "ugc_one_specific_use",
        "niche": ["home_goods", "gadget_tech", "ecommerce_physical", "food_beverage"],
        "formatBias": ["ugc_review", "product_demo"],
        "hookType": "situational",
        "mechanism": "one-specific-use",
        "hook": "I use this for one thing, and that is it.",
        "productRole": "Product in the single situation it is good for",
        "ctaStyle": "Ask whether that situation matches theirs",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_unsupported_result", "no_feature_dump"],
    },
    {
        "id": "ugc_closer_look_edge",
        "niche": ["ecommerce_physical", "apparel", "home_goods", "beauty_device"],
        "formatBias": ["ugc_review", "before_after"],
        "hookType": "visual",
        "mechanism": "closer-look-single-edge",
        "hook": "Come closer, look at this edge.",
        "productRole": "Macro detail carries the whole argument",
        "ctaStyle": "Describe what noticing that edge felt like, not just where to look",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_invented_specs", "no_false_luxury_claim"],
    },
    {
        "id": "unbox_open_and_see",
        "niche": ["ecommerce_physical", "gadget_tech", "beauty_cosmetics", "home_goods"],
        "formatBias": ["product_unboxing"],
        "hookType": "curiosity",
        "mechanism": "open-and-see",
        "hook": "Alright, let us see what is actually in here.",
        "productRole": "Product is the reveal",
        "ctaStyle": "Invite a closer look at the product",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_fake_packaging"],
    },
    {
        "id": "unbox_desk_first_look",
        "niche": ["b2b_professional", "beauty_device", "gadget_tech", "saas_digital"],
        "formatBias": ["product_unboxing", "product_demo"],
        "hookType": "visual",
        "mechanism": "desk-first-look",
        "hook": "Straight out, no box. Here it is on the table.",
        "productRole": "Stable first full view without packaging fiction",
        "ctaStyle": "Say what the first look told you, not where to read more",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_fake_packaging", "no_claiming_usage_result"],
    },
    {
        "id": "unbox_size_in_hand",
        "niche": ["ecommerce_physical", "gadget_tech", "home_goods", "beauty_device"],
        "formatBias": ["product_unboxing", "product_demo"],
        "hookType": "demonstration",
        "mechanism": "size-in-hand",
        "hook": "Photos do not show the size. In my hand it is this big.",
        "productRole": "Product against hand or a known object for scale",
        "ctaStyle": "Describe how the size actually felt, not just the number",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_fake_dimensions"],
    },
    {
        "id": "unbox_material_finish",
        "niche": ["apparel", "home_goods", "beauty_cosmetics", "ecommerce_physical"],
        "formatBias": ["product_unboxing", "ugc_review"],
        "hookType": "visual",
        "mechanism": "material-finish-closeup",
        "hook": "You notice the finish straight away.",
        "productRole": "Texture and material fill the frame",
        "ctaStyle": "Say what the finish felt like to touch, not just to see",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_false_luxury_claim", "no_invented_specs"],
    },
    {
        "id": "unbox_whole_kit_laid_out",
        "niche": ["b2b_professional", "beauty_device", "gadget_tech", "ecommerce_physical"],
        "formatBias": ["product_unboxing", "product_demo"],
        "hookType": "demonstration",
        "mechanism": "whole-kit-laid-out",
        "hook": "Everything laid out, so you can see what you get.",
        "productRole": "Full supplied set in one frame",
        "ctaStyle": "Say whether it felt complete, not just what is listed",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_invented_accessories"],
    },
    {
        "id": "ps_twice_as_long",
        "niche": ["saas_digital", "home_goods", "b2b_professional", "local_service"],
        "formatBias": ["problem_solution"],
        "hookType": "situational",
        "mechanism": "takes-twice-as-long",
        "hook": "You know the thing that takes twice as long as it should?",
        "productRole": "Offer arrives as the shorter path",
        "ctaStyle": "Show where to see how it works",
        "assetRequirements": [],
        "forbidden": ["no_exaggerated_pain", "no_time_guarantee"],
    },
    {
        "id": "ps_old_way_dropped",
        "niche": ["home_goods", "gadget_tech", "saas_digital", "local_service"],
        "formatBias": ["problem_solution", "before_after"],
        "hookType": "contradiction",
        "mechanism": "old-way-dropped",
        "hook": "I used to do it like this. Now I do not.",
        "productRole": "Old method shown, then replaced on camera",
        "ctaStyle": "Say what got better the moment you switched",
        "assetRequirements": [],
        "forbidden": ["no_competitor_attack", "no_overpromise"],
    },
    {
        "id": "ps_five_steps_for_simple",
        "niche": ["saas_digital", "course_education", "b2b_professional", "local_service"],
        "formatBias": ["problem_solution", "hook_cta"],
        "hookType": "situational",
        "mechanism": "too-many-steps",
        "hook": "Why does something this simple need five steps?",
        "productRole": "Offer collapses the steps visibly",
        "ctaStyle": "Ask them to check if it fits their case",
        "assetRequirements": [],
        "forbidden": ["no_overpromise", "no_invented_metrics"],
    },
    {
        "id": "ps_empty_corner",
        "niche": ["b2b_professional", "local_service", "beauty_device", "home_goods"],
        "formatBias": ["problem_solution", "before_after"],
        "hookType": "situational",
        "mechanism": "empty-space-activated",
        "hook": "That corner has been empty for months.",
        "productRole": "Offer occupies and justifies the unused space",
        "ctaStyle": "Invite an enquiry about configuration",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_roi_promise", "no_revenue_promise"],
    },
    {
        "id": "ps_did_not_know_which",
        "niche": ["course_education", "ecommerce_physical", "beauty_cosmetics", "health_wellness"],
        "formatBias": ["problem_solution", "hook_cta"],
        "hookType": "emotional",
        "mechanism": "undecided-narrowed-to-one",
        "hook": "I did not know which one to pick either.",
        "productRole": "Offer presented as one concrete candidate, not the only answer",
        "ctaStyle": "Say what made the choice clear, not where the comparison lives",
        "assetRequirements": [],
        "forbidden": ["no_false_recommendation", "no_fake_authority"],
    },
    {
        "id": "demo_one_action_through",
        "niche": ["gadget_tech", "b2b_professional", "beauty_device", "home_goods"],
        "formatBias": ["product_demo"],
        "hookType": "demonstration",
        "mechanism": "one-action-start-to-finish",
        "hook": "One thing, start to finish. Watch.",
        "productRole": "Single uninterrupted interaction",
        "ctaStyle": "Invite a closer look at the product",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_unsafe_use", "no_invented_specs"],
    },
    {
        "id": "demo_three_steps_done",
        "niche": ["gadget_tech", "saas_digital", "home_goods", "beauty_device"],
        "formatBias": ["product_demo", "trending_style"],
        "hookType": "demonstration",
        "mechanism": "three-steps-done",
        "hook": "Three steps and it is done.",
        "productRole": "Setup, use, result in three readable beats",
        "ctaStyle": "Say how quick it actually felt, not just that it is documented",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_time_guarantee", "no_step_inflation"],
    },
    {
        "id": "demo_silent_action_first",
        "niche": ["gadget_tech", "home_goods", "food_beverage", "apparel"],
        "formatBias": ["product_demo", "hook_cta"],
        "hookType": "visual",
        "mechanism": "silent-action-first",
        "hook": "",
        "productRole": "Product moves before anyone speaks",
        "ctaStyle": "One spoken line at the end only",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_long_verbal_opening"],
    },
    {
        "id": "demo_real_room",
        "niche": ["b2b_professional", "beauty_device", "local_service", "home_goods"],
        "formatBias": ["product_demo", "problem_solution"],
        "hookType": "situational",
        "mechanism": "real-room-context",
        "hook": "This is it in the room where it actually gets used.",
        "productRole": "Product working inside its real environment",
        "ctaStyle": "Ask whether it fits their setup",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_wrong_environment", "no_fake_results"],
    },
    {
        "id": "demo_part_that_matters",
        "niche": ["gadget_tech", "b2b_professional", "ecommerce_physical", "beauty_device"],
        "formatBias": ["product_demo", "ugc_review"],
        "hookType": "demonstration",
        "mechanism": "part-that-matters",
        "hook": "This part here is the one that matters.",
        "productRole": "One feature shown, then its practical use",
        "ctaStyle": "Say why that detail mattered, not where to read about it",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_unsupported_benefit", "no_invented_specs"],
    },
    {
        "id": "test_supplied_question_answered",
        "niche": ["course_education", "saas_digital", "local_service", "ecommerce_physical"],
        "formatBias": ["testimonial"],
        "hookType": "verbal",
        "mechanism": "supplied-question-answered",
        "hook": "Someone asked this, so here is the answer.",
        "productRole": "Offer answers a sourced question",
        "ctaStyle": "Give the real answer here, not a pointer to find it",
        "assetRequirements": ["source_fact"],
        "forbidden": ["no_fake_quote", "no_proof_beyond_source"],
    },
    {
        "id": "test_same_question_before_buying",
        "niche": ["ecommerce_physical", "beauty_cosmetics", "gadget_tech", "course_education"],
        "formatBias": ["testimonial", "hook_cta"],
        "hookType": "contradiction",
        "mechanism": "buyer-objection-answered",
        "hook": "I would have the same question before buying.",
        "productRole": "Offer addresses the stated doubt",
        "ctaStyle": "Answer the doubt directly, not with a link to more info",
        "assetRequirements": [],
        "forbidden": ["no_fake_experience", "no_unsupported_answer"],
    },
    {
        "id": "test_first_impression_only",
        "niche": ["beauty_cosmetics", "ecommerce_physical", "gadget_tech", "food_beverage"],
        "formatBias": ["testimonial", "ugc_review"],
        "hookType": "verbal",
        "mechanism": "first-impression-only",
        "hook": "I have not lived with this for months. First impression though.",
        "productRole": "Honest impression of what is visible",
        "ctaStyle": "Invite them to look themselves",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_claiming_ownership", "no_fake_usage_result"],
    },
    {
        "id": "test_professional_viewpoint",
        "niche": ["b2b_professional", "beauty_device", "local_service", "health_wellness"],
        "formatBias": ["testimonial", "problem_solution", "self_presentation"],
        "hookType": "verbal",
        "mechanism": "professional-viewpoint",
        "hook": "I look at this from behind the counter, so I notice different things.",
        "productRole": "Offer judged as a work tool",
        "ctaStyle": "Invite a business enquiry",
        "assetRequirements": ["person_image"],
        "forbidden": ["no_medical_outcome_claims", "no_fake_credentials"],
    },
    {
        "id": "test_recurring_question",
        "niche": ["course_education", "saas_digital", "ecommerce_physical", "local_service"],
        "formatBias": ["testimonial", "trending_style"],
        "hookType": "verbal",
        "mechanism": "recurring-question-answered",
        "hook": "The same question keeps coming up, so let us do it.",
        "productRole": "Offer answers the repeated question",
        "ctaStyle": "Answer it plainly here, not with a pointer to documentation",
        "assetRequirements": [],
        "forbidden": ["no_invented_faq", "no_fake_customer"],
    },
    {
        "id": "trend_sudden_open",
        "niche": ["beauty_cosmetics", "gadget_tech", "food_beverage", "apparel"],
        "formatBias": ["trending_style"],
        "hookType": "pattern_interrupt",
        "mechanism": "sudden-open",
        "hook": "",
        "productRole": "Abrupt close-up or motion lands on the product",
        "ctaStyle": "One quick spoken ask",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_random_chaos", "no_borrowed_trend_copy"],
    },
    {
        "id": "trend_pov_moment",
        "niche": ["beauty_cosmetics", "home_goods", "food_beverage", "course_education"],
        "formatBias": ["trending_style", "problem_solution"],
        "hookType": "situational",
        "mechanism": "pov-moment",
        "hook": "POV: it is seven in the morning and you have four minutes.",
        "productRole": "Offer solves the moment on camera",
        "ctaStyle": "Short spoken ask at the end",
        "assetRequirements": [],
        "forbidden": ["no_irrelevant_pov", "no_overpromise"],
    },
    {
        "id": "trend_comment_answer",
        "niche": ["saas_digital", "course_education", "beauty_cosmetics", "gadget_tech"],
        "formatBias": ["trending_style", "testimonial"],
        "hookType": "verbal",
        "mechanism": "comment-answer",
        "hook": "Someone asked me this in the comments, so.",
        "productRole": "Offer is the answer being given",
        "ctaStyle": "Give the actual answer, then let them decide",
        "assetRequirements": [],
        "forbidden": ["no_fake_comment_as_real"],
    },
    {
        "id": "trend_three_things_fast",
        "niche": ["ecommerce_physical", "gadget_tech", "home_goods", "beauty_cosmetics"],
        "formatBias": ["trending_style", "hook_cta"],
        "hookType": "verbal",
        "mechanism": "three-things-fast",
        "hook": "Three things, fast.",
        "productRole": "Three visible product facts in rhythm",
        "ctaStyle": "State the three things plainly, not a link to read them",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_more_than_three_points", "no_invented_specs"],
    },
    {
        "id": "trend_i_was_wrong",
        "niche": ["beauty_cosmetics", "gadget_tech", "food_beverage", "health_wellness"],
        "formatBias": ["trending_style", "before_after"],
        "hookType": "contradiction",
        "mechanism": "assumption-corrected",
        "hook": "I was wrong about this one.",
        "productRole": "Visible detail causes the correction",
        "ctaStyle": "Say exactly what proved you wrong",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_false_claim", "no_fake_result"],
    },
    {
        "id": "hcta_specific_audience",
        "niche": ["b2b_professional", "local_service", "saas_digital", "course_education"],
        "formatBias": ["hook_cta"],
        "hookType": "verbal",
        "mechanism": "specific-audience-call",
        "hook": "If you run a small shop, this one is for you.",
        "productRole": "Offer clear in frame as the ask lands",
        "ctaStyle": "One direct ask",
        "assetRequirements": [],
        "forbidden": ["no_generic_audience", "no_vague_promise"],
    },
    {
        "id": "hcta_ordinary_until_closer",
        "niche": ["ecommerce_physical", "apparel", "home_goods", "gadget_tech"],
        "formatBias": ["hook_cta", "ugc_review"],
        "hookType": "curiosity",
        "mechanism": "ordinary-until-closer",
        "hook": "Looks ordinary from here. Come closer.",
        "productRole": "Close-up delivers the promised reason",
        "ctaStyle": "Say what changed once you looked closer",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_fake_secret", "no_invented_specs"],
    },
    {
        "id": "hcta_quick_question",
        "niche": ["saas_digital", "course_education", "local_service", "health_wellness"],
        "formatBias": ["hook_cta"],
        "hookType": "verbal",
        "mechanism": "quick-question-then-ask",
        "hook": "Quick question, then I will let you go.",
        "productRole": "Offer shown as the answer to that question",
        "ctaStyle": "Single next step",
        "assetRequirements": [],
        "forbidden": ["no_pressure_tactics", "no_vague_promise"],
    },
    {
        "id": "hcta_silent_visual_open",
        "niche": ["apparel", "food_beverage", "beauty_cosmetics", "ecommerce_physical"],
        "formatBias": ["hook_cta", "product_demo"],
        "hookType": "visual",
        "mechanism": "silent-visual-open",
        "hook": "",
        "productRole": "Image earns attention before any words",
        "ctaStyle": "Final spoken ask only",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_weak_action", "no_text_overlay_dependency"],
    },
    {
        "id": "hcta_dated_offer",
        "niche": ["ecommerce_physical", "local_service", "course_education", "food_beverage"],
        "formatBias": ["hook_cta"],
        "hookType": "situational",
        "mechanism": "source-backed-date",
        "hook": "This one is only up until Friday.",
        "productRole": "Offer and its real date shown together",
        "ctaStyle": "Act before the sourced date",
        "assetRequirements": ["source_fact"],
        "forbidden": ["no_fake_deadline", "no_invented_discount"],
    },
    {
        "id": "ba_everything_everywhere",
        "niche": ["home_goods", "b2b_professional", "local_service", "ecommerce_physical"],
        "formatBias": ["before_after"],
        "hookType": "visual",
        "mechanism": "scattered-to-ordered",
        "hook": "Before: everything everywhere.",
        "productRole": "Product creates the order",
        "ctaStyle": "Show where to see how it works",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_fake_outcome"],
    },
    {
        "id": "ba_space_did_nothing",
        "niche": ["b2b_professional", "beauty_device", "local_service", "home_goods"],
        "formatBias": ["before_after", "problem_solution"],
        "hookType": "situational",
        "mechanism": "unused-space-equipped",
        "hook": "This space did nothing for months.",
        "productRole": "Equipment fills and justifies the space",
        "ctaStyle": "Invite an enquiry",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_roi_promise", "no_revenue_promise"],
    },
    {
        "id": "ba_cannot_see_from_here",
        "niche": ["ecommerce_physical", "apparel", "gadget_tech", "beauty_device"],
        "formatBias": ["before_after", "ugc_review"],
        "hookType": "curiosity",
        "mechanism": "hidden-then-visible",
        "hook": "You cannot see it from here. Closer, you can.",
        "productRole": "Detail reveal is the change",
        "ctaStyle": "Say what you noticed up close, not just where to look",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_invented_detail"],
    },
    {
        "id": "ba_used_to_take_all_morning",
        "niche": ["b2b_professional", "saas_digital", "local_service", "home_goods"],
        "formatBias": ["before_after", "product_demo"],
        "hookType": "demonstration",
        "mechanism": "long-process-shortened",
        "hook": "This used to take the whole morning.",
        "productRole": "Product performs the shortened version",
        "ctaStyle": "Show where to see the process",
        "assetRequirements": [],
        "forbidden": ["no_time_guarantee", "no_invented_metrics"],
    },
    {
        "id": "ba_shelf_to_working",
        "niche": ["gadget_tech", "home_goods", "ecommerce_physical", "beauty_device"],
        "formatBias": ["before_after", "product_demo"],
        "hookType": "visual",
        "mechanism": "static-to-working",
        "hook": "It looks like nothing on the shelf. Here it is working.",
        "productRole": "Same product static then active",
        "ctaStyle": "Say what changed when it started working, not just where to see it",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_fake_usage_result", "no_unsafe_use"],
    },
    {
        "id": "self_problem_then_who",
        "niche": ["local_service", "b2b_professional", "saas_digital"],
        "formatBias": ["self_presentation", "problem_solution"],
        "hookType": "verbal",
        "mechanism": "problem-then-who-i-am",
        "hook": "Your customers find the competition first? Here is why.",
        "productRole": "Person names the viewer's problem, then who they are and why they can fix it",
        "ctaStyle": "Offer one small free first step and say what the viewer gets from it",
        "assetRequirements": ["person_image"],
        "forbidden": ["no_invented_client_results", "no_fake_credentials"],
    },
    {
        "id": "self_one_credential",
        "niche": ["b2b_professional", "course_education", "local_service"],
        "formatBias": ["self_presentation", "testimonial"],
        "hookType": "contradiction",
        "mechanism": "one-credential-proof",
        "hook": "Most people who promise this have never done it themselves.",
        "productRole": "One concrete credential from the brief carries the trust",
        "ctaStyle": "State what the viewer gets from the first conversation",
        "assetRequirements": ["person_image"],
        "forbidden": ["no_fake_credentials", "no_invented_metrics"],
    },
    {
        "id": "self_personal_handling",
        "niche": ["local_service", "course_education", "b2b_professional"],
        "formatBias": ["self_presentation", "hook_cta"],
        "hookType": "situational",
        "mechanism": "personal-handling-promise",
        "hook": "No account manager, no hand-offs. You talk to me.",
        "productRole": "Person at their real workplace promises to handle the work personally",
        "ctaStyle": "Ask for the one detail needed to start, framed as what they get back",
        "assetRequirements": ["person_image"],
        "forbidden": ["no_time_guarantee", "no_invented_client_results"],
    },
]

NARRATIVE_MEDIA_STRUCTURES = [
    {
        "id": "story_unfinished_moment",
        "niche": ["narrative_media"],
        "formatBias": ["hook_cta", "trending_style"],
        "hookType": "curiosity",
        "mechanism": "unfinished-moment",
        "hook": "She opens the door and — no, I am not telling you that part.",
        "productRole": "The work is the only place the ending exists",
        "ctaStyle": "Say you need to know what happens next, not that it looks nice",
        "assetRequirements": [],
        "forbidden": ["no_invented_plot", "no_full_payoff_reveal"],
    },
    {
        "id": "story_world_entry",
        "niche": ["narrative_media"],
        "formatBias": ["product_demo", "before_after"],
        "hookType": "visual",
        "mechanism": "story-world-entry",
        "hook": "",
        "productRole": "Opening the work is shown as stepping into its world",
        "ctaStyle": "Say what pulled you in, then leave the question open",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_visual_only_payoff", "no_invented_edition_details"],
    },
    {
        "id": "story_character_question",
        "niche": ["narrative_media"],
        "formatBias": ["ugc_review", "testimonial"],
        "hookType": "verbal",
        "mechanism": "character-question",
        "hook": "I keep arguing with one character in my head.",
        "productRole": "A character's choice is the reason to keep reading",
        "ctaStyle": "Say which question kept you up, not how the pages look",
        "assetRequirements": [],
        "forbidden": ["no_invented_plot", "no_fake_reader_results"],
    },
    {
        "id": "story_returning_reader",
        "niche": ["narrative_media", "ecommerce_physical"],
        "formatBias": ["ugc_review", "product_unboxing"],
        "hookType": "contradiction",
        "mechanism": "known-story-new-encounter",
        "hook": "I already know this story. This time it got me anyway.",
        "productRole": "A familiar work made new by this edition or retelling",
        "ctaStyle": "Say what felt different reading it again, not what changed visually",
        "assetRequirements": ["product_image"],
        "forbidden": ["no_visual_only_payoff", "no_invented_edition_details"],
    },
    {
        "id": "story_one_page_pull",
        "niche": ["narrative_media"],
        "formatBias": ["hook_cta", "problem_solution"],
        "hookType": "situational",
        "mechanism": "one-page-pull",
        "hook": "I sat down for one page. That was an hour ago.",
        "productRole": "The work's pull on attention is the demonstrated value",
        "ctaStyle": "Say how far it carried you, not how it looked on the shelf",
        "assetRequirements": [],
        "forbidden": ["no_fake_reader_results", "no_invented_plot"],
    },
]

WINNING_AD_STRUCTURES = WINNING_AD_STRUCTURES + NARRATIVE_MEDIA_STRUCTURES

_REQUIREMENT_ASSET_ROLES = {"product_image": "product", "person_image": "person"}
_MATCH_FIELDS = ("product", "service", "offer", "userText", "brief")


def _keyword_hit(keyword: str, text: str) -> bool:
    """Word-start match, so Polish inflection still hits but "gra" never matches "program"."""
    return re.search(r"\b" + re.escape(keyword.strip()), text) is not None


def _niche_weights() -> dict[str, float]:
    """A tag on 22 of 45 cards carries far less signal than one on 5; weight by rarity.

    Without this, any brief containing "produkt" scored 22 cards identically and the
    offered set was decided by authoring order alone (measured 2026-09-12).
    """
    counts = Counter(niche for s in WINNING_AD_STRUCTURES for niche in s["niche"])
    total = len(WINNING_AD_STRUCTURES)
    return {niche: math.log(1 + total / count) for niche, count in counts.items()}


_NICHE_WEIGHTS = _niche_weights()
_FORMAT_PRIMARY_BONUS = 10.0
_UNMET_EVIDENCE_PENALTY = 1.5
_MAX_KEYWORD_CREDIT = 3


def _fit_score(structure: dict, text: str) -> float:
    """Rarity-weighted keyword fit, discounted for cards that only partly match."""
    matched, weighted = 0, 0.0
    for niche in structure["niche"]:
        hits = sum(1 for keyword in NICHE_KEYWORDS[niche] if _keyword_hit(keyword, text))
        if hits:
            matched += 1
            weighted += _NICHE_WEIGHTS[niche] * min(hits, _MAX_KEYWORD_CREDIT)
    if not matched:
        return 0.0
    # A one-tag specialist matching its only tag beats a four-tag generalist matching one.
    specificity = matched / len(structure["niche"])
    return weighted * (0.5 + 0.5 * specificity)


def _tiebreak(structure_id: str, text: str) -> str:
    """Stable per-offer ordering for genuine ties, so authoring order is not destiny.

    Same brief always yields the same set (reproducible, testable), but different offers
    reach different cards instead of always the earliest-authored ones.
    """
    return hashlib.sha256(f"{structure_id}|{text}".encode()).hexdigest()


def _diversified(ordered: list[dict], limit: int) -> list[dict]:
    """Keep the strongest matches, then widen across format families not yet present."""
    strong = ordered[: max(1, limit // 2)]
    seen = {s["formatBias"][0] for s in strong}
    widened = []
    for structure in ordered[len(strong):]:
        if structure["formatBias"][0] not in seen:
            widened.append(structure)
            seen.add(structure["formatBias"][0])
    remainder = [s for s in ordered[len(strong):] if s not in widened]
    return (strong + widened + remainder)[:limit]

# How a buyer actually receives the value, which decides what the payoff must be —
# a book is read, a device is operated, a gift is given. At most one primary plus one
# secondary; hybrids (an illustrated collector's edition) legitimately carry two.
CONSUMPTION_MODELS = (
    "narrative_immersion",
    "collectible_aesthetic",
    "physical_use",
    "sensory_experience",
    "workflow_improvement",
    "skill_acquisition",
    "done_for_you_service",
    "identity_expression",
    "recurring_discovery",
    "gifting",
)

# One overlay per niche, injected only for the matched category — never the whole
# catalogue, so the director's instruction load stays flat regardless of how many
# categories exist. Each carries the payoff the ad must create and the 2-4 reductions
# that specifically destroy that category's value.
CATEGORY_OVERLAYS = {
    "narrative_media": {
        "requiredPayoff": "Make the viewer want to enter or continue the story",
        "forbiddenReductions": [
            "Do not reduce the work to its cover, illustrations or physical edition",
            "Do not make visual admiration the only payoff",
            "Do not reveal the complete narrative payoff",
            "Do not invent plot, characters or edition details",
        ],
    },
    "ecommerce_physical": {
        "requiredPayoff": "Make the viewer want the result of using it",
        "forbiddenReductions": [
            "Do not show packaging instead of the result",
            "Do not recite specifications the page already lists",
        ],
    },
    "beauty_cosmetics": {
        "requiredPayoff": "Make the viewer want that ritual and how it feels",
        "forbiddenReductions": [
            "Do not promise results that were not supplied as evidence",
            "Do not reduce it to swatches with no felt experience",
        ],
    },
    "beauty_device": {
        "requiredPayoff": "Make the professional want it in their own room",
        "forbiddenReductions": [
            "Do not advertise the operator's treatment service instead of the device",
            "Do not imply clinical or medical outcomes",
        ],
    },
    "gadget_tech": {
        "requiredPayoff": "Make the viewer want the moment it makes easier",
        "forbiddenReductions": [
            "Do not list specifications instead of showing one real use",
            "Do not invent performance numbers",
        ],
    },
    "home_goods": {
        "requiredPayoff": "Make the viewer want that calmer, sorted room",
        "forbiddenReductions": [
            "Do not shoot a pretty frame with no everyday usefulness",
            "Do not stage a home no real person lives in",
        ],
    },
    "apparel": {
        "requiredPayoff": "Make the viewer want to feel like that in it",
        "forbiddenReductions": [
            "Do not just rotate the garment in front of the camera",
            "Do not invent fabric, sizing or origin details",
        ],
    },
    "food_beverage": {
        "requiredPayoff": "Make the viewer want the taste and the moment around it",
        "forbiddenReductions": [
            "Do not describe ingredients instead of the sensation",
            "Do not invent health or sourcing claims",
        ],
    },
    "course_education": {
        "requiredPayoff": "Make the viewer want the change in themselves it leads to",
        "forbiddenReductions": [
            "Do not sell module counts, hours or curriculum size",
            "Do not promise a guaranteed result or timeline",
        ],
    },
    "saas_digital": {
        "requiredPayoff": "Make the viewer want the time it gives back",
        "forbiddenReductions": [
            "Do not talk abstractly with no interface visible",
            "Do not invent integrations, pricing or data the offer did not supply",
        ],
    },
    "b2b_professional": {
        "requiredPayoff": "Make the buyer want the risk, time or cost it removes",
        "forbiddenReductions": [
            "Do not use consumer emotional advertising for a business decision",
            "Do not promise revenue or ROI",
        ],
    },
    "local_service": {
        "requiredPayoff": "Make the viewer want the finished result in their own life",
        "forbiddenReductions": [
            "Do not show the practitioner without the outcome they deliver",
            "Do not invent reviews, credentials or guarantees",
        ],
    },
    "health_wellness": {
        "requiredPayoff": "Make the viewer want the comfort and control it supports",
        "forbiddenReductions": [
            "Do not make medical promises or imply treatment",
            "Do not invent effects, dosages or study results",
        ],
    },
}

_EVIDENCE_PAGE_STATES = {"resolved", "partial"}


def evidence_available(context_bundle: dict, image_roles=(), page_status=None) -> list[str]:
    """Deterministic inventory of what the director can actually build on."""
    roles = {str(a.get("role", "")).lower() for a in context_bundle.get("availableAssets") or []}
    roles |= {str(role).lower() for role in image_roles}
    evidence = []
    if any("product" in role for role in roles):
        evidence.append("product_image")
    if any("person" in role for role in roles):
        evidence.append("person_image")
    # An uploaded video reaches the director as sampled frames and generation as a reference.
    if any("video" in role for role in roles):
        evidence.append("source_video")
    if context_bundle.get("sourceFacts"):
        evidence.append("source_facts")
    if page_status in _EVIDENCE_PAGE_STATES:
        evidence.append("offer_page")
    if (context_bundle.get("brief") or "").strip():
        evidence.append("written_brief")
    return evidence


def matched_niches(context_bundle: dict) -> list[str]:
    """Niches whose keywords appear in the offer text, strongest first."""
    text = " ".join(str(context_bundle.get(field) or "") for field in _MATCH_FIELDS).lower()
    hits = [(sum(bool(_keyword_hit(keyword, text)) for keyword in keywords), niche)
            for niche, keywords in NICHE_KEYWORDS.items()]
    return [niche for score, niche in sorted(hits, key=lambda h: -h[0]) if score]


def category_overlay(context_bundle: dict) -> dict | None:
    """Only the single best-matched category's rules ever reach the director."""
    for niche in matched_niches(context_bundle):
        if niche in CATEGORY_OVERLAYS:
            return {"niche": niche, **CATEGORY_OVERLAYS[niche]}
    return None


def retrieval_limit(context_bundle: dict, consumption_models=()) -> int:
    """Precise match gets a tight set; ambiguous or hybrid offers get a wider one."""
    hybrid = len(consumption_models) > 1 or len(matched_niches(context_bundle)) != 1
    return 10 if hybrid else 6


def format_index() -> list[dict]:
    """Compact index of every playbook; safe to send on every request."""
    return [
        {
            "formatId": format_id,
            "label": playbook["label"],
            "userIntent": playbook["userIntent"],
            "bestFor": playbook["bestFor"],
        }
        for format_id, playbook in FORMAT_PLAYBOOKS.items()
    ]


def as_reference(structure: dict) -> dict:
    """Render rule slugs as prose so they cannot be copied into plan fields verbatim."""
    return {**structure, "forbidden": [rule.replace("_", " ") for rule in structure["forbidden"]]}


def _requirements_met(structure: dict, asset_roles: set[str], has_source_facts: bool) -> bool:
    for requirement in structure["assetRequirements"]:
        if requirement == "source_fact":
            if not has_source_facts:
                return False
        # Substring match: page-derived imagery carries roles like "product page image".
        elif not any(_REQUIREMENT_ASSET_ROLES[requirement] in role for role in asset_roles):
            return False
    return True


def select_structures(
    context_bundle: dict,
    format_hint: str | None = None,
    excluded_mechanisms=(),
    limit: int = 8,
    image_roles=(),
) -> list[dict]:
    """Tag and keyword matching only; deterministic order keeps turns reproducible.

    image_roles covers imagery reaching the director that never becomes an owned asset,
    such as a product photo taken from the offer page.
    """
    excluded = set(excluded_mechanisms)
    text = " ".join(str(context_bundle.get(field) or "") for field in _MATCH_FIELDS).lower()
    asset_roles = {
        str(asset.get("role", "")).lower() for asset in context_bundle.get("availableAssets") or []
    }
    asset_roles |= {str(role).lower() for role in image_roles}
    has_source_facts = bool(context_bundle.get("sourceFacts"))
    scored = []
    for structure in WINNING_AD_STRUCTURES:
        if structure["mechanism"] in excluded:
            continue
        if format_hint and format_hint not in structure["formatBias"]:
            continue
        score = _fit_score(structure, text)
        # A format's own structures outrank ones merely cross-listed into it.
        if format_hint and structure["formatBias"][0] == format_hint:
            score += _FORMAT_PRIMARY_BONUS
        # Unmet asset needs rank lower instead of excluding; asset-light briefs still need options.
        if not _requirements_met(structure, asset_roles, has_source_facts):
            score -= _UNMET_EVIDENCE_PENALTY
        scored.append((-score, _tiebreak(structure["id"], text), structure))
    scored.sort(key=lambda entry: (entry[0], entry[1]))
    ordered = [structure for _, _, structure in scored]
    # With an explicit format everything is one family already; auto must span families
    # so a single format cannot monopolise the offered set.
    return _diversified(ordered, limit) if format_hint is None else ordered[:limit]
