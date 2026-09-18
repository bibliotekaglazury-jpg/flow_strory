# Storyflow UGC — подробный конкурентный разбор и рабочий blueprint Creative Director V2

Дата: 2026-09-11  
Статус: рабочий продуктово-технический документ для реализации.  
Язык документа: русский.  
Цель: заменить общий концепт конкретным разбором конкурентов, форматом playbook’ов и планом внедрения в Storyflow.

---

## 0. Короткий вывод

Предыдущий документ был полезен как направление, но недостаточен как ТЗ. В нём не хватало трёх вещей:

1. **Единого формата анализа конкурента** — что именно делаем как Predis / Topview / Arcads / Creatify, а что не делаем.
2. **Чёткого определения creative mechanism** — что значит “несколько разных механизмов”, чем они отличаются от перефразировки.
3. **Точного формата playbook’а для Claude** — какие поля передаём, какие правила применяем, как выбираем сценарий, как проверяем качество.

Главный вывод: Storyflow должен строиться не как “UI к Wan”, а как **рекламный режиссёр**, который превращает product URL / image / person reference в несколько продающих UGC-концептов, выбирает лучший и только потом отправляет один 15-секундный план в видеомодель.

Правильная продуктовая формула:

```text
Product evidence
→ Offer understanding
→ Format playbook
→ Creative mechanisms
→ Candidate scoring
→ Selected concept
→ 15s VideoPlan
→ Wan generation
→ saved preview/history
→ later captions/CTA overlay
```

---

## 1. Что такое creative mechanism

**Creative mechanism** — это не “вариант текста” и не “другой camera angle”. Это рекламный двигатель ролика.

Он отвечает на 5 вопросов:

| Вопрос | Что означает |
|---|---|
| Почему зритель останавливается? | Hook / stopping power в первые 1–3 секунды. |
| Что происходит визуально? | Конкретное действие, сцена, reveal, comparison, demo, конфликт. |
| Какая мысль удерживает внимание? | Tension, curiosity, problem, opportunity, doubt, transformation. |
| Как продукт встроен в историю? | Product is hero / solution / object of inspection / proof / tool / reveal. |
| Почему досмотреть до CTA? | Payoff: viewer понял, зачем кликать/спросить/купить/проверить. |

### Пример плохих “вариантов”

Это НЕ разные mechanisms:

| Вариант | Почему плохо |
|---|---|
| “Покажи продукт крупным планом” | Это camera instruction, не идея. |
| “Скажи CTA другими словами” | Это copy rewrite, не механизм. |
| “Пусть человек держит продукт слева, потом справа” | Это staging, не story. |
| “Сделай более эмоционально” | Нет visual action и payoff. |

### Пример настоящих разных mechanisms для одного продукта

Продукт: портативный аппарат УЗИ для кабинета.

| Mechanism | Hook | Visual action | Payoff |
|---|---|---|---|
| Empty room opportunity | “Masz w gabinecie miejsce, z którym jeszcze nic nie robisz?” | Пустое место/стол → появляется устройство | Оборудование как расширение предложения кабинета. |
| Client demand | “Klienci pytają o szybszą diagnostykę?” | Владелец смотрит сообщение/запрос → показывает аппарат | Продукт как ответ на спрос. |
| Portable demo | “To USG wygląda bardziej jak sprzęt, który można zabrać ze sobą, niż wielka stacja w gabinecie.” | Presenter открывает/переносит устройство | Компактность и мобильность. |
| Detail inspection | “Pokażę, co widać od razu, zanim zaczniemy mówić o parametrach.” | Камера идёт по экрану, клавиатуре, sondzie | Понятная визуальная презентация деталей. |
| Offer expansion | “Nie chodzi o większy gabinet. Chodzi o to, co możesz w nim jeszcze zaoferować.” | Presenter рядом с устройством | CTA запросить оферту/конфигурацию. |

Это и есть то, что должен генерировать Claude.

---

## 2. Подробный разбор Predis

Источник: https://predis.ai/product-video-maker/ и https://predis.ai/ai-video-generator/

### 2.1 Product promise

Predis продаёт не “AI model”, а быстрый ecommerce workflow:

> вставь product link или product image → получи ready-to-post product video.

Они обещают:

- продуктовые видео без съёмки;
- AI сам пишет script;
- voiceover, music, captions;
- editable draft;
- export/schedule;
- bulk variants;
- ecommerce/store integrations.

### 2.2 Input model

| Input | Для чего нужен |
|---|---|
| Product URL | Вытянуть название, фото, цену, описание, ecommerce context. |
| Product image | Если URL нет или нужен visual identity. |
| Store integration | Массовая генерация для каталога. |
| Brand kit | Цвета, шрифты, стиль. |
| Language/platform | Под формат Reels/TikTok/Shorts и рынок. |

### 2.3 Context understanding

Predis делает важную вещь: он не просит пользователя писать длинный prompt. Он берёт то, что уже есть:

```text
product URL → images + price + description → script + scenes
```

Для Storyflow вывод:

- product URL должен быть не “строкой в prompt”, а источником `OfferFacts`;
- product image должен быть не “просто reference image”, а evidence of product identity;
- если URL недоступен, Claude обязан честно сказать, что URL не был прочитан.

### 2.4 Script engine

Predis пишет script в brand tone и добавляет voiceover/captions. Нам сейчас не нужен TTS, но нужен тот же принцип разделения:

```text
script != visual direction != captions != CTA
```

Для Storyflow:

- `spokenScript` — что говорит персонаж;
- `visualDirection` — что происходит;
- `captionBeats` — оставить на следующий этап overlay;
- `ctaText` — фиксировать уже сейчас как planning output, даже если overlay будет позже.

### 2.5 Creative mechanisms Predis-подхода

Predis в ecommerce обычно строит ролики вокруг таких механизмов:

| # | Mechanism | Как применить в Storyflow |
|---:|---|---|
| 1 | Product benefit lead | Начать с пользы, а не названия товара. |
| 2 | Product demo | Показать товар в использовании. |
| 3 | Product teaser | Сначала частичный reveal, потом товар. |
| 4 | Offer/promo | Если есть цена/скидка/source, показать как reason to act. |
| 5 | Catalog variant | Один продукт → несколько рекламных углов. |
| 6 | Use-case angle | Один товар — разные ситуации применения. |
| 7 | Visual lifestyle | Товар помещается в lifestyle context. |
| 8 | Educational explainer | Коротко объяснить “для чего это”. |
| 9 | Product comparison without competitor | “обычный способ vs этот продукт”, без чужих брендов. |
| 10 | Seasonal/promo moment | Привязка к сезону/поводу, если пользователь дал повод. |

### 2.6 Что забрать из Predis

| Забираем | Как внедрить |
|---|---|
| Product link/image as starting point | `OfferFacts` + image evidence. |
| Script + scenes before export | У нас уже есть CreativePlan/VideoPlan; усилить playbook. |
| Editable draft | User sees Concept/Hook/Story/Script before paid Generate. |
| Captions readable without sound | Later OverlayRenderer, не видеомодель. |
| Bulk variants | Сейчас internal candidates; позже visible variants. |
| Store/product catalogue thinking | Позже, не сейчас. |

### 2.7 Что не копировать сейчас

- store integrations;
- scheduler/autoposting;
- massive catalogue generation;
- full drag-and-drop video editor;
- stock library;
- TTS/voiceover layer.

---

## 3. Подробный разбор Topview

Источник: https://www.topview.ai/use-cases/advertising

### 3.1 Product promise

Topview продаёт performance advertising system:

> не угадывай рекламу — бери winning structures, hooks, pacing, CTA и делай variants.

Они явно говорят о:

- 10M+ ad library;
- proven hooks;
- competitor ad replication;
- hook/story/pacing/CTA analysis;
- multi-variant testing;
- URL-to-video remix;
- viral 3-second hooks.

### 3.2 Input model

| Input | Для чего нужен |
|---|---|
| Product URL/image | Автоматически создать product ad. |
| Landing page URL | Понять offer + audience + CTA. |
| Reference/winning ad URL | Разобрать structure, hook, pacing. |
| Product assets | Держать visual identity. |
| Platform | Под TikTok/Reels/Shorts/Meta/YouTube. |

### 3.3 Context understanding

Topview важен тем, что он продаёт “DNA” рекламы:

```text
hook + story pattern + visual trigger + CTA placement
```

Для Storyflow это значит, что Claude должен строить не просто сцену, а **ad structure**:

- `hookType`;
- `opening3s`;
- `storyMechanism`;
- `visualTrigger`;
- `ctaPlacement`;
- `reasonToWatchToEnd`.

### 3.4 Creative mechanisms Topview-подхода

| # | Mechanism | Что это значит для Storyflow |
|---:|---|---|
| 1 | 3-second visual hook | Первые секунды — яркое действие/визуальный reveal. |
| 2 | Competitor/reference remix | Позже: пользователь даёт ссылку на рекламу, мы копируем структуру, не контент. |
| 3 | Hook variant testing | Один продукт → разные hooks. |
| 4 | UGC talking head | Presenter говорит как creator, не как бренд. |
| 5 | Lifestyle scene | Продукт в контексте жизни/работы. |
| 6 | Product-in-motion | Static product image превращается в product-use scene. |
| 7 | CTA placement | CTA не случайный, а привязан к payoff. |
| 8 | Pattern interrupt | Начало ломает ожидание. |
| 9 | Pain-first ad | Боль → продукт. |
| 10 | Opportunity-first ad | Возможность/выгода → продукт. |
| 11 | Proof-first ad | Если есть proof, начать с него. |
| 12 | Objection-first ad | Начать с сомнения покупателя. |

### 3.5 Что забрать из Topview

| Забираем | Как внедрить |
|---|---|
| First 3 seconds as separate planning object | Добавить в playbook/CreativePlan `openingHook` или явно требовать first beat. |
| Mechanism variants | Сейчас код генерирует ровно 3 candidate mechanisms через `CreativeAudit`; 5–10 — отдельная будущая миграция schema/prompt/tests/cost profile. |
| Change Concept means new mechanism | Запрещать повтор central story/payoff. |
| Quality scoring | У нас уже есть CreativeAudit; усилить критерии. |
| URL-to-video remix | Сейчас product URL; позже reference ad URL. |

### 3.6 Откуда брать Winning Ad Structures Library

Эту библиотеку нельзя считать встроенным знанием модели. Storyflow должен собрать её сам, но это отдельный объём работ, а не маленькая техническая правка.

Scope decision на 2026-09-12:

1. **Phase 1**: не строим большой research-пайплайн. Делаем 8 `FORMAT_PLAYBOOKS` — по одному на каждый UI-шаблон — и компактный seed `WINNING_AD_STRUCTURES`: 4-5 mechanisms внутри каждого playbook, всего 32-40 тщательно проверенных структур, вручную выведенных из этого аудита и восьми форматов. Это достаточно, чтобы перестать просить модель “придумать хороший hook” из воздуха.
2. **Phase 1 retrieval**: простой keyword/tag matching по `niche`, `offerType`, `selectedFormat`, `assetRequirements`, `riskRules`, `rejectedMechanisms`. Без embeddings, vector DB, RAG-инфраструктуры и внешнего поиска.
3. **Phase 1 candidates**: текущий код остаётся на ровно 3 candidates, потому что `CreativeAudit.candidates` валидирует `min_length=3`, `max_length=3`, а prompt `v3.py` требует three materially different mechanisms.
4. **Future migration**: 5-10 candidates можно делать только отдельной задачей: изменить `CreativeAudit`, Claude prompt, repair loop, tests, UI/debug output и бюджет токенов. Это не входит в ближайший дешёвый этап.
5. **Phase 2 research**: `AdStructureResearcher`, YouTube Shorts API, TikTok Creative Center, Meta Ad Library, product review videos, competitor pages и user reference ads — отдельный milestone после проверки ToS/legal risks. Нельзя молча делать scraper production dependency.

Из каждого видео/референса в Phase 2 можно сохранять только рекламную структуру, не чужой сценарий: first 3 seconds, hook type, mechanism, visual trigger, pacing, product role, CTA placement, asset requirements, risks, source URL, performance signals.

Creative Director должен получать небольшую подборку подходящих структур. Если есть URL + product image + person image — используются более нишевые структуры. Если есть только текст или только фото — используются общие структуры, но всё равно из библиотеки, а не из пустого “придумай hook”.

Минимальный объект структуры:

```json
{
  "id": "beauty_device_empty_room_opportunity",
  "niche": ["beauty_device", "professional_service"],
  "formatBias": ["Problem → Solution", "Hook → CTA"],
  "hookType": "opportunity",
  "mechanism": "empty_space_opportunity",
  "opening3s": "empty workspace or unused table, then product appears",
  "visualPattern": "empty space → product reveal → presenter explains business use",
  "storyArc": "unused capacity → new offer → ask for configuration",
  "scriptPattern": "Nie chodzi o większy gabinet. Chodzi o to, co możesz w nim jeszcze zaoferować.",
  "assetRequirements": ["product image"],
  "optionalAssets": ["person image", "business interior"],
  "ctaType": "ask_for_offer",
  "riskRules": ["no ROI promise", "no medical outcome claims"]
}
```

### 3.7 Что копировать и что не копировать

Здесь важно не изобретать колесо. Winning ads ценны потому, что их структура уже доказала жизнеспособность. Поэтому Storyflow должен копировать **формулу**, но не воровать дословный чужой креатив.

Копируем как есть:

- рекламную структуру;
- hook logic;
- pacing;
- central mechanism;
- visual trigger;
- product role;
- CTA placement;
- логику payoff.

Не копируем дословно:

- чужой полный script;
- уникальные брендовые фразы;
- чужие claims, proof, цены, гарантии;
- чужих людей, голос, видео, лица;
- competitor-ad scraping как production dependency;
- paid media optimization;
- campaign launch workflow;
- dozens of rendered variants.

Правило для Creative Director: `copy the proven structure, rewrite the spoken script for the current offer, source facts and natural language`.

---

## 4. Подробный разбор Arcads

Источник: https://intercom.help/arcads/en/articles/15503340-everything-you-can-do-on-arcads-complete-platform-guide

### 4.1 Product promise

Arcads — это AI content/ad platform вокруг actors, products и editing tools:

- talking actors;
- product upload;
- show product in video;
- unboxing;
- product showcase;
- captions;
- text overlay;
- actor replacement;
- resize/trim/layers.

### 4.2 Input model

| Input | Для чего нужен |
|---|---|
| Product image | Определить, что показываем/держим/размещаем. |
| Actor/avatar | Кто говорит и показывает. |
| Script | Что говорит actor. |
| Existing video | Repurpose/actor replacement/trim. |
| Product/tool preset | Unboxing/Product Showcase/Camera Movement. |

### 4.3 Самый важный урок Arcads

Arcads явно разделяет:

```text
product = что показываем / продаём
actor = кто говорит / держит / презентует
```

Это ровно наша боль. В Storyflow ошибка была такая:

```text
product image: УЗИ аппарат
person image: врач
user: promote this product
bad Claude: рекламирует услугу врача
correct: рекламировать аппарат, врач только presenter
```

### 4.4 Creative mechanisms Arcads-подхода

| # | Mechanism | Что это значит для Storyflow |
|---:|---|---|
| 1 | Product held by actor | Presenter держит продукт и говорит короткий script. |
| 2 | Product on surface | Продукт лежит на столе, камера показывает детали. |
| 3 | Lifestyle placement | Продукт в естественном окружении. |
| 4 | Unboxing POV | Руки/POV раскрывают продукт. |
| 5 | Product Showcase | Hero close-ups и feature callouts. |
| 6 | Talking actor + product cutaways | Лицо + B-roll продукта. |
| 7 | App show | Для SaaS/app — UI рядом с talking head. |
| 8 | Actor replacement | Та же структура, другой presenter. |
| 9 | Captions overlay | Текст отдельно от video generation. |
| 10 | Hook repurposer | Один hook адаптируется под другой продукт. |
| 11 | Text overlay | Title/CTA/offer как programmatic layer. |
| 12 | Resize/remix | Один output адаптируется под платформы. |

### 4.5 Что забрать из Arcads

| Забираем | Как внедрить |
|---|---|
| Product/person role split | `productEvidence` и `presenterEvidence` в planning context. |
| Show product in video | PromptCompiler должен явно писать, как продукт появляется. |
| Unboxing from image | Даже без коробки — first-look reveal. |
| Product showcase preset | Наш Product Demo / Product Showcase должен иметь close-up grammar. |
| Captions/Text Overlay | Later OverlayRenderer. |
| Actor replacement | Позже: same concept, different person reference. |

### 4.6 Что не копировать сейчас

- full actor library;
- actor replacement engine;
- layer editor;
- multi-model tooling;
- Sora-specific preset.

---

## 5. Подробный разбор Creatify

Источники: https://creatify.ai/features/ai-video-generator, https://creatify.ai/, https://creatify.ai/blog/ugc-creator-how-to-produce-user-generated-content-at-scale

### 5.1 Product promise

Creatify продаёт:

> paste product URL → get 5–10 optimized UGC script/video variations with avatars.

Ключевые элементы:

- product URL crawler;
- 5–10 script variations;
- platform-specific hooks;
- CTAs;
- benefit-driven copy;
- avatars;
- voices;
- B-roll;
- captions;
- editor before export.

### 5.2 Input model

| Input | Для чего нужен |
|---|---|
| Product URL | Понять товар и сделать scripts. |
| Product description/reviews | Если URL нет. |
| Avatar | Presenter. |
| Voice/language | Delivery. |
| Platform | Hook/CTA/format. |
| B-roll/product media | Visual support. |

### 5.3 Главное, что забрать

Creatify прямо говорит о 5–10 variations с разными:

- hooks;
- angles;
- emotional approaches;
- CTAs;
- benefit copy.

Для Storyflow сейчас это должно быть так:

```text
Target future state: Claude may generate 5–10 candidate mechanisms internally. Current runtime is exactly 3 candidates.
→ scores them
→ returns 1 selected concept
→ later UI can expose 3–5 alternatives
→ render only after user explicitly chooses
```

### 5.4 Creative mechanisms Creatify-подхода

| # | Mechanism | Что это значит для Storyflow |
|---:|---|---|
| 1 | URL-to-script variants | Product URL даёт разные scripts. |
| 2 | Emotional angle variants | Один товар: fear, curiosity, aspiration, convenience, status. |
| 3 | Platform-specific hook | TikTok/Reels/YouTube Shorts требуют разные первые секунды. |
| 4 | Avatar-led UGC | Presenter style меняет perception. |
| 5 | Benefit-driven copy | Не features list, а benefit narrative. |
| 6 | B-roll support | Product close-ups/usage cutaways поддерживают speech. |
| 7 | Edit before export | User правит script до траты export/video credits. |
| 8 | Multilingual adaptation | Тот же concept, другой язык/рынок. |
| 9 | Custom avatar | Позже reusable presenter/avatar. |
| 10 | Batch ad set | Один продукт → несколько ads. |

### 5.5 Что забрать из Creatify

| Забираем | Как внедрить |
|---|---|
| 3 script/mechanism candidates now; 5–10 later | Сейчас `CreativeAudit` жёстко валидирует ровно 3 candidates. |
| Different emotional approaches | В playbook: `emotional_angle`. |
| Edit before export | Уже есть Use Concept before Generate. Усилить clarity. |
| Avatar as presenter | Сейчас person image; позже avatar library. |
| Product URL first | OfferFacts mandatory when URL present. |

### 5.6 Что не копировать сейчас

- voice synthesis;
- avatar marketplace;
- custom avatar creation;
- full B-roll editor;
- export credit editor.

---

## 6. Feature matrix

| Capability | Predis | Topview | Arcads | Creatify | Storyflow now | Storyflow target V1.1 |
|---|---|---|---|---|---|---|
| Product URL input | сильный ecommerce URL workflow | URL-to-video ads | не главный, больше product upload/tools | ключевой URL-to-video | есть, но нестабилен/слабый context | compact OfferFacts + failure gate |
| Product image input | да | да | сильный product upload/detection | да | есть | product identity + role separation |
| Person/avatar | частично avatars | UGC avatars | actor system | avatars | person image reference | presenter role, not offer |
| Script generation | да | да | script/actor workflows | 5–10 scripts | есть через Claude | mechanism-based script |
| Hook strategy | базово | очень сильная | hook tools | platform hooks | есть поле hookStrategy | opening3s + mechanism library |
| Variants | bulk/A-B | dozens variants | actor/script variants | 5–10 videos | internal 3 candidates уже есть | Phase 1: richer playbook-driven 3 candidates; Phase 2: optional 5–10 migration + UI alternatives |
| Captions | burn-in captions | captions likely | Add Captions tool | captions | нет overlay | later deterministic overlay |
| Product demo | да | product-in-motion | Product Showcase | да | template label | detailed Product Demo playbook |
| Unboxing | tutorial/how-to/unboxing | possible | Unboxing POV | possible | template label | no fake box; first-look if no packaging |
| Testimonial | UGC/product ads | UGC-style testimonials | actor-led | UGC avatar | template label | no fake testimonial without source |
| Editor | drag-and-drop | customize messaging | tools/layers | built-in editor | limited prompt edit | keep simple, later concept alternatives |
| Export/history | export/schedule | campaign workflow | generated assets/tools | export | history works | keep, improve metadata/cost |
| Model exposure | hidden/orchestrated | hidden/orchestrated | hidden/orchestrated | hidden/orchestrated | mostly hidden | keep hidden |

---

## 7. Единый формат Storyflow Format Playbook

Каждый playbook должен быть структурирован так:

```yaml
format_id: string
label: string
user_intent: string
best_for: list[string]
not_for: list[string]
required_context:
  minimum: list[string]
  useful: list[string]
offer_role_rule: string
person_role_rule: string
first_3_seconds:
  purpose: string
  allowed_hook_types: list[string]
  forbidden_openings: list[string]
visual_grammar:
  camera: list[string]
  product_handling: list[string]
  environment: list[string]
script_grammar:
  opening_line: string
  body: string
  CTA: string
product_integration:
  hero_role: string
  supporting_role: string
  forbidden_role: string
mechanism_library:
  - mechanism_id
  - name
  - hook
  - visual_action
  - story_logic
  - product_role
  - CTA_style
  - forbidden
quality_gate:
  stopping_power: string
  relevance: string
  product_integration: string
  distinctiveness: string
  feasibility_15s: string
examples:
  - product_type
  - good_direction
  - bad_direction
```

Claude не обязан показывать это пользователю. Это internal director input.

---

## 8. Universal rules для Claude

Эти правила должны быть выше любого playbook:

1. **Product source priority**: если есть product URL или product image, это главный promoted offer.
2. **Person role**: person image = presenter/actor/reference identity, не promoted service/person, если пользователь явно не сказал иначе.
3. **URL truthfulness**: если URL не fetched/read, нельзя делать вид, что данные из URL известны.
4. **No fake proof**: не выдумывать отзывы, результаты, клинические эффекты, ROI, скидки, сертификации, сроки доставки.
5. **Mechanism diversity**: candidates должны отличаться central action/payoff, не только wording/camera.
6. **15-second feasibility**: один ролик = один понятный action arc.
7. **Native audio only**: script должен быть speakable; без TTS instructions.
8. **Text overlay later**: не просить модель рисовать точный текст в кадре; captions/CTA — deterministic overlay later.
9. **Polish language**: если пользователь пишет по-польски, dialogue по-польски; не переключать язык.
10. **Medical/professional caution**: можно говорить о бизнес-презентации/оборудовании/запросе оферты, нельзя обещать результаты процедур.
11. **Natural spoken register**: реплика должна звучать как то, что реально скажет вслух конкретный человек — короткие простые фразы, без слоганов, без риторических антитез ("речь не о X, а о Y"), без маркетинговых афоризмов про оффер, без listicle-каденции, если формат сам не список. Если строка могла бы быть текстом с лендинга — переписать проще и короче.

---

## 9. Playbook: UGC Review

### Назначение

UGC Review нужен, чтобы продукт выглядел замеченным живым человеком, а не проданным корпоративным диктором.

### Когда использовать

- ecommerce product;
- beauty/cosmetics;
- gadgets;
- home product;
- professional device;
- course/service, если можно сделать first-person impression.

### Когда не использовать

- когда нужен строгий technical demo;
- когда нет права делать личный опыт;
- когда продукт требует formal compliance.

### First 3 seconds

| Hook type | Пример |
|---|---|
| Curiosity | “Tego akurat nie spodziewałem się po tym produkcie.” |
| Buyer question | “Szukasz czegoś, co ogarnie ten konkretny problem?” |
| Visual detail | Камера сразу показывает необычную деталь. |
| Skepticism | “Na początku myślałem, że to kolejny zwykły…” |

### Mechanism library

| ID | Name | Hook | Visual action | Story logic | Product role | CTA style | Forbidden |
|---|---|---|---|---|---|---|---|
| ugc_first_impression | First impression | “Od razu zwróciłem uwagę na jedną rzecz.” | Presenter берёт/смотрит на продукт | Первое впечатление → одна причина интереса | Hero | “Zobacz, czy to pasuje do Twojego przypadku” | fake long-term use |
| ugc_skeptic_to_interest | Skeptic to interest | “Myślałem, że to kolejny zwykły produkt. Ale jedno mnie zatrzymało.” | Presenter сначала сомневается, потом показывает detail | Doubt → visible reason | Hero | “Przejrzyj ofertę” | fake conversion claim |
| ugc_detail_inspection | Detail inspection | “Spójrz na ten detal, bo widać w nim wszystko.” | Close-up детали | Деталь объясняет ценность | Hero detail | “Zobacz, co dokładnie obejmuje” | невыдуманные specs |
| ugc_buyer_question | Buyer question | “Szukasz czegoś takiego?” | Presenter смотрит в камеру + product | Вопрос покупателя → ответ | Solution | “Sprawdź, czy to pasuje do tego, czego szukasz” | generic audience |
| ugc_mini_checklist | Mini checklist | “Trzy rzeczy widać od razu, bez czytania opisu.” | 3 коротких product angles | Быстрая структура | Hero | “Zajrzyj do pełnego opisu” | too many points |
| ugc_use_case | Specific use-case | “To przydaje się, kiedy…” | Product in use environment | Use case → relevance | Tool | “Zapytaj o dostępną konfigurację” | unsupported result |
| ugc_unexpected_feature | Unexpected feature | “Tego po nim nie widać na pierwszy rzut oka.” | Reveal feature/detail | Surprise → attention | Hero | “Obejrzyj produkt na stronie” | exaggerated surprise |
| ugc_plain_talk | Plain talk | “Bez wielkich haseł — pokażę, o co tu chodzi.” | Natural talking head + product | Low-ad tone | Product as proof | “Sprawdź to samodzielnie” | corporate ad tone |
| ugc_problem_noticed | Problem noticed | “Znasz to, jak coś niby działa, ale wkurza?” | Small everyday friction | Problem → product relevance | Answer | “Zobacz, jak można to rozwiązać” | fake outcome |
| ugc_click_test | Would I click? | “Co musiałbym zobaczyć, żeby to sprawdzić?” | Presenter points to one reason | Meta-review of offer | Offer object | “Przejdź do oferty” | too abstract |

### Quality gate

- Есть ли человекоподобная реакция, а не corporate pitch?
- Есть ли конкретная product detail/use case?
- Не выдуман ли личный опыт?
- Можно ли снять это за 15 секунд?

---

## 10. Playbook: Product Unboxing

### Назначение

Unboxing строит ожидание и reveal. Если коробки нет, формат должен превращаться в **first look / desk reveal**, а не выдумывать packaging.

### First 3 seconds

- руки тянут коробку/товар в кадр;
- частичный close-up без полного reveal;
- “Dobra, zobaczmy, co faktycznie tu jest.”;
- продукт появляется на столе.

### Mechanism library

| ID | Name | Hook | Visual action | Story logic | Product role | CTA style | Forbidden |
|---|---|---|---|---|---|---|---|
| unbox_classic_reveal | Classic reveal | “Otwórzmy i zobaczmy, co jest w środku.” | Открытие коробки | Anticipation → reveal | Hero | “Obejrzyj produkt dokładniej” | fake packaging |
| unbox_first_look | First look | “Pierwsze wrażenie, zanim cokolwiek uruchomimy…” | Product slides into frame | First sight → detail | Hero | “Obejrzyj produkt dokładniej” | claiming usage result |
| unbox_mystery_closeup | Mystery close-up | “Na razie widać tylko kawałek.” | Частичный detail → full reveal | Curiosity → reveal | Hero | “Przejdź do oferty” | unreadable fake text |
| unbox_desk_reveal | Desk reveal | “Kładę to na stole, sami zobaczcie.” | Product placed on desk | Stable product view | Hero | “Przejrzyj opis produktu” | fake accessories |
| unbox_professional_kit | Professional kit | “Tak wygląda sprzęt do gabinetu.” | Equipment reveal in professional setting | Business context | Business tool | “Zapytaj o konfigurację” | consumer toy framing |
| unbox_whats_visible | What’s visible | “Nawet nie włączając, widać już sporo.” | Pan over visible parts | Evaluate visible facts | Visual evidence | “Parametry najlepiej sprawdzić w opisie” | invented specs |
| unbox_size_scale | Size scale | “Na zdjęciu trudno ocenić rozmiar, a na żywo widać.” | Product in hand/next to object | Scale → practical sense | Hero | “Wymiary sprawdź w opisie produktu” | fake dimensions |
| unbox_texture_material | Texture/material | “To wykończenie od razu rzuca się w oczy.” | Close-up texture/material | Visual feel | Hero detail | “Obejrzyj zdjęcia produktu” | unsupported premium claims |
| unbox_setup_start | Setup start | “Pierwszy krok jest prosty — rozkładam i patrzę.” | Simple setup motion | Opening → ready position | Tool | “Zobacz, jak wygląda przygotowanie” | showing unsafe use |
| unbox_gift_moment | Gift moment | “To akurat gotowy pomysł na prezent.” | Present-like reveal | Occasion → product | Gift/object | “Sprawdź dostępność” | unsupported occasion promise |

### Quality gate

- Czy reveal naprawdę coś pokazuje?
- Czy nie wymyślono pudełka?
- Czy produkt jest centralny wizualnie?
- Czy 15 sekund wystarczy?

---

## 11. Playbook: Problem → Solution

### Назначение

Начать с боли/трения, потом показать продукт как практичный ответ.

### First 3 seconds

- “Masz z tym problem na co dzień?”;
- визуальная путаница/хаос/пустое место;
- владелец получает вопрос клиента;
- старый неудобный способ.

### Mechanism library

| ID | Name | Hook | Visual action | Story logic | Product role | CTA style | Forbidden |
|---|---|---|---|---|---|---|---|
| ps_daily_friction | Daily friction | “Znasz ten problem z własnej pracy?” | Small annoyance shown | Pain → product | Solution | “Zobacz, jak można to rozwiązać” | exaggerated pain |
| ps_lost_time | Lost time | “Ile razy traciłeś czas na coś, co powinno być proste?” | Clock/slow process | Time friction → product | Time-saver framing | “Zobacz, jak można to uprościć” | exact time claims |
| ps_empty_space | Empty space opportunity | “Masz w gabinecie wolne miejsce? Zobacz, co można z nim zrobić.” | Empty desk/room → product | unused capacity → offer | Business asset | “Zapytaj o ofertę” | ROI promise |
| ps_customer_request | Customer demand | “Klient pyta o coś, czego jeszcze nie masz w ofercie.” | Message/question → product | demand → response | Expansion tool | “Zapytaj o dostępną konfigurację” | fake customer quote as fact |
| ps_old_new_way | Old way / new way | “Do tej pory wyglądało to tak…” | Old setup → product | contrast | Better option | “Przyjrzyj się tej opcji” | competitor attack |
| ps_too_complicated | Too complicated | “Czemu to ma tyle kroków, skoro to prosta rzecz?” | confusing process | simplification | simplifying tool | “Sprawdź, czy pasuje do Twojego przypadku” | overpromise |
| ps_decision_anxiety | Decision anxiety | “Nie wiesz, od czego zacząć?” | Presenter compares options abstractly | uncertainty → one clear option | candidate solution | “Porównaj szczegóły w opisie” | false recommendation |
| ps_professional_readiness | Professional readiness | “Chcesz, żeby pacjent od razu widział dobrze wyposażony gabinet?” | Product setup in workspace | presentation upgrade | Professional tool | “Zapytaj o ofertę” | guaranteed outcome |
| ps_portability | Portability problem | “Ten sprzęt nie musi stać cały czas w jednym miejscu.” | Carry/setup product | location friction → portable option | Portable tool | “Obejrzyj ten model” | invented weight |
| ps_offer_gap | Offer gap | “Klienci coraz częściej pytają o coś, czego jeszcze nie masz w ofercie?” | Service menu/space → product | gap → expansion | offer enabler | “Zapytaj o konfigurację pod swój gabinet” | revenue promise |

### Quality gate

- Боль реальна и понятна?
- Продукт появляется как логичный ответ?
- Нет ли fake proof/result?
- История не перегружена?

---

## 12. Playbook: Product Demo

### Назначение

Показать продукт в действии или в рабочей ситуации. Не список характеристик.

### First 3 seconds

- product action first;
- hands interacting;
- setup begins;
- presenter says one clear task.

### Mechanism library

| ID | Name | Hook | Visual action | Story logic | Product role | CTA style | Forbidden |
|---|---|---|---|---|---|---|---|
| demo_one_action | One action demo | “Pokażę jedną rzecz, zamiast gadać o wszystkim naraz.” | One clear interaction | action → explanation | Hero tool | “Obejrzyj produkt dokładniej” | no action |
| demo_three_steps | Three-step demo | “W trzech krokach widać, do czego to służy.” | setup → use → close | sequence | Hero | “Zobacz pełny opis produktu” | too many steps |
| demo_detail_tour | Detail tour | “Przejdźmy po szczegółach, bo warto je zobaczyć.” | Pan over 2–3 details | detail understanding | Hero details | “Przejrzyj opis” | invented specs |
| demo_hands_only | Hands-only demo | “Bez długiego wstępu — po prostu zobacz, jak to działa.” | Hands demonstrate | visual clarity | Hero | “Przejrzyj ofertę” | hidden product |
| demo_presenter_product | Presenter + product | “Jak tego używam, od razu widać, po co to jest.” | Presenter interacts | human + product | Hero with presenter | “Zapytaj o ofertę” | presenter only talks |
| demo_use_environment | Use environment | “W takim miejscu widać, po co to jest.” | Product in realistic setting | context → relevance | Tool in environment | “Sprawdź, czy pasuje do Twojego przypadku” | wrong environment |
| demo_portable_setup | Portable setup | “Rozkładasz to i od razu widać, jak z tym pracować.” | Carry/open/place | portability | Portable tool | “Sprawdź dostępne konfiguracje” | fake weight/time |
| demo_professional_workflow | Professional workflow | “Pokażę to w pracy, nie tylko na zdjęciu.” | Product enters workflow | business routine | Work tool | “Zapytaj o ofertę” | fake results |
| demo_show_then_say | Show then say | visual action first | product moves before speech | visual proof → line | Hero | “Przejrzyj szczegóły w opisie” | opening with long speech |
| demo_feature_benefit | Feature to benefit | “Ten element warto pokazać z bliska.” | show feature → use case | visible feature → benefit | Feature object | “Przejrzyj opis produktu” | unsupported benefit |
| demo_before_use | Before first use | “Zanim zaczniemy, zobacz, jak to jest ułożone.” | inspection/prep | pre-use clarity | Object of evaluation | “Sprawdź parametry” | showing unsafe operation |
| demo_side_by_side | Side-by-side setup | “Pokażmy cały zestaw w jednym kadrze.” | product + accessory if visible | full view | Kit | “Obejrzyj cały zestaw” | invented accessories |

---

## 13. Playbook: Testimonial

### Назначение

Создать доверие. Но если нет реального отзыва/source, нельзя выдумывать testimonial. Тогда формат превращается в **creator/professional impression**.

### Mechanism library

| ID | Name | Hook | Visual action | Story logic | Product role | CTA style | Forbidden |
|---|---|---|---|---|---|---|---|
| test_real_quote | Real quote | starts from supplied quote | Presenter reads/reacts | quote → product | proof object | “Przeczytaj opinię i sprawdź ofertę” | fake quote |
| test_objection_answer | Objection answer | “Też miałbym tu jedno pytanie przed zakupem.” | Presenter addresses doubt | doubt → answer | answer source | “Sprawdź odpowiedź w opisie” | fake experience |
| test_creator_impression | Creator impression | “Moje pierwsze wrażenie jest proste…” | product inspection | impression, not result | hero | “Obejrzyj produkt na stronie” | claiming ownership/use |
| test_professional_pov | Professional POV | “Jako ktoś z gabinetu, patrzę na to inaczej.” | professional setting | expert framing | business tool | “Zapytaj o ofertę” | medical result claim |
| test_social_proof_source | Source-backed proof | “Na stronie można sprawdzić…” | page/product shown | source fact → reason | offer with proof | “Sprawdź to na stronie” | proof not in source |
| test_mini_story | Mini story | “Problem jest prosty…” | problem setup | factual mini narrative | solution | “Zobacz, jak można to rozwiązać” | fabricated story |
| test_user_type | User-type statement | “Dla tych, którzy szukają dokładnie czegoś takiego…” | presenter describes target user | audience fit | fit object | “Sprawdź, czy to dla Ciebie” | fake customer |
| test_skeptic_interest | Skeptic to interest | “Nie przekonują mnie hasła. Patrzę na to, co widać.” | detail shown | skepticism → visible detail | proof detail | “Obejrzyj ten detal na stronie” | overclaim |
| test_founder_note | Founder note | only if founder/user supplied | direct to camera | founder explains offer | offer | “Napisz, żeby dostać ofertę” | fake founder |
| test_review_pattern | Review pattern | “Najczęściej pytacie o jedno…” | question/list | objection → answer | answer | “Sprawdź FAQ/ofertę” | invented FAQ |

---

## 14. Playbook: Trending Style

### Назначение

Сделать ролик похожим на social content, а не на polished ad. Не копировать конкретный чужой тренд.

### Mechanism library

| ID | Name | Hook | Visual action | Story logic | Product role | CTA style | Forbidden |
|---|---|---|---|---|---|---|---|
| trend_pattern_interrupt | Pattern interrupt | unexpected line/visual | sudden close-up/action | surprise → product | reveal | “Sprawdź teraz, jeśli to jest Twój przypadek” | random chaos |
| trend_pov | POV setup | “POV: szukasz czegoś, co nie wygląda jak kolejny gadżet.” | POV scene | situational | solution | “Zobacz, o co chodzi” | irrelevant POV |
| trend_micro_story | Micro-story | problem in 1 line | 3 beat cuts | problem → product → CTA | hero | “Przejdź do oferty” | too many scenes |
| trend_listicle | Listicle | “Trzy rzeczy, które warto zauważyć.” | fast cuts | list | feature object | “Zajrzyj do pełnego opisu” | more than 3 points |
| trend_comment_reply | Comment reply | “Ktoś zapytał mnie o to jedno, więc odpowiadam.” | answer style | question → product | answer | “Przejdź do linku” | fake comment as real |
| trend_myth | Myth/realization | “Myślałem, że wiem, czego się spodziewać…” | before/after reaction | belief shift | proof/detail | “Sprawdź to samodzielnie” | false claim |
| trend_creator_confession | Creator confession | “Nie zwróciłbym na to uwagi, gdyby nie jeden szczegół.” | direct camera | personal filter | selected object | “Zobacz, dlaczego warto to sprawdzić” | fake result |
| trend_fast_demo | Fast demo | action first | quick hands/product shots | demo rhythm | hero | “Obejrzyj produkt dokładniej” | unreadable action |
| trend_visual_metaphor | Visual metaphor | “To trochę jak…” | metaphor scene | analogy | product as answer | “Przejrzyj ofertę” | confusing metaphor |
| trend_audio_native | Native social talk | casual opening | handheld movement | low-polish authenticity | product shown | “Sprawdź” | corporate script |

---

## 15. Playbook: Hook → CTA

### Назначение

Весь ролик строится вокруг одного сильного открытия и одного действия в конце.

### Mechanism library

| ID | Name | Hook | Visual action | Story logic | Product role | CTA style | Forbidden |
|---|---|---|---|---|---|---|---|
| hcta_direct_question | Direct question | “Szukasz czegoś konkretnego, a nie kolejnej ogólnej obietnicy?” | direct camera/product | audience callout | answer | direct CTA | vague audience |
| hcta_alt_pick | Alternative pick | “Miałem już parę takich urządzeń. To jest to, które w końcu zostało.” | presenter/product contrast | comparison → solution | alternative | “Przyjrzyj się tej opcji” | false dichotomy |
| hcta_audience_callout | Audience callout | “Jeśli prowadzisz gabinet albo małą firmę…” | presenter points/product | specific audience | offer | “Zapytaj o ofertę” | generic CTA |
| hcta_opportunity | Opportunity hook | “Klient ostatnio zapytał o coś, czego jeszcze nie miałem w ofercie.” | empty → product | opportunity | enabler | “Zapytaj o konfigurację” | ROI promise |
| hcta_curiosity_gap | Curiosity gap | “Z daleka wygląda zwyczajnie. Z bliska zaczyna być ciekawiej.” | close-up detail | curiosity → reveal | hero | “Podejdź bliżej i sprawdź opis” | fake secret |
| hcta_problem_punch | Problem punch | direct pain | show pain/action | pain → answer | solution | “Zobacz, jak można to rozwiązać” | exaggerated fear |
| hcta_visual_hook | Visual hook | no words first | visual action | image earns attention | hero | final spoken CTA | weak action |
| hcta_offer_clarity | Offer clarity | “Chcesz zobaczyć od razu, do czego to się nadaje? Pokażę.” | product clear in frame | clarity | hero | “Przejdź do oferty” | jargon |
| hcta_objection | Objection hook | “Myślisz, że to kolejna taka sama opcja?” | presenter addresses doubt | objection → answer | answer | “Przejrzyj szczegóły” | unsupported answer |
| hcta_deadline | Deadline/event | source-backed date | date/offer scene | urgency | offer | “Skorzystaj do…” | fake deadline |

---

## 16. Playbook: Before / After

### Назначение

Показать контраст состояния/сцены/workflow без фейковых результатов.

### Mechanism library

| ID | Name | Hook | Visual action | Story logic | Product role | CTA style | Forbidden |
|---|---|---|---|---|---|---|---|
| ba_messy_organized | Messy → organized | “Przed: wszystko leży osobno i trudno zobaczyć sens.” | messy setup → product setup | order | organizer/tool | “Zobacz, jak można to rozwiązać” | fake outcome |
| ba_confused_clear | Confused → clear | “Na początku nie wiadomo, co wybrać.” | confusion → clear product/offer | clarity | guide/solution | “Zobacz, od czego zacząć” | overpromise |
| ba_empty_equipped | Empty → equipped | “Puste miejsce nie musi zostać puste.” | empty desk/room → product | business upgrade | equipment | “Zapytaj o ofertę” | ROI promise |
| ba_static_motion | Static → motion | product still → in use | movement | activation | hero | “Obejrzyj produkt na stronie” | unsafe use |
| ba_ordinary_premium | Ordinary → premium | plain scene → better setup | visual upgrade | premium feel | hero | “Przejdź do oferty” | false luxury claim |
| ba_long_shorter | Long process → simpler | long process hinted → simplified step | simplicity | tool | “Zobacz, jak można to poukładać” | time guarantee |
| ba_hidden_visible | Hidden detail → visible detail | “Tego nie widać od razu. Trzeba podejść bliżej.” | detail reveal | discovery | detail proof | “Obejrzyj detal w opisie” | invented detail |
| ba_no_plan_cta | No plan → clear next step | uncertain viewer → CTA | decision clarity | offer | “Napisz / sprawdź” | pressure tactics |
| ba_shelf_lifestyle | Shelf → lifestyle | product isolated → use context | relevance | lifestyle object | “Zobacz przykład zastosowania” | fake usage result |
| ba_doubt_interest | Doubt → interest | skeptical face → product detail | emotional contrast | detail | “Sprawdź to samodzielnie” | fake testimonial |

---

## 17. Как Claude должен выбирать сценарий

Процесс должен быть таким:

```text
1. Read ContextBundle.
2. Determine promoted offer.
3. Determine presenter role.
4. Resolve selected format or Auto.
5. Load selected FORMAT_PLAYBOOK.
6. Generate exactly 3 candidate mechanisms from selected playbook/structures in Phase 1, matching current `CreativeAudit` schema.
7. Reject generic mechanisms.
8. Score remaining mechanisms.
9. Select best mechanism.
10. Build CreativePlan.
11. Build VideoPlan.
12. Return concise user-facing concept.
```

### Candidate scoring dimensions

| Критерий | Что проверяем |
|---|---|
| Stopping power | Есть ли причина остановиться в первые 3 секунды? |
| Offer relevance | Связан ли ролик с реальным продуктом/оффером? |
| Mechanism distinctiveness | Это новый механизм или перефразировка? |
| Product centrality | Продукт естественно центральный? |
| Visual action | Что реально происходит в кадре? |
| Payoff | Есть ли причина досмотреть? |
| 15s feasibility | Это реально уложить в 15 секунд? |
| Claim safety | Нет ли выдуманных фактов/результатов? |

---

## 18. Implementation blueprint

### 18.1 Backend data

Добавить серверный модуль:

```text
apps/api/app/creative_direction_playbooks.py
```

Он должен экспортировать:

```python
FORMAT_PLAYBOOKS = {
  "ugc_review": {...},
  "product_unboxing": {...},
  "problem_solution": {...},
  "product_demo": {...},
  "testimonial": {...},
  "trending_style": {...},
  "hook_cta": {...},
  "before_after": {...},
}

WINNING_AD_STRUCTURES = [
  {
    "id": "beauty_device_empty_room_opportunity",
    "niche": ["beauty_device", "professional_service"],
    "formatBias": ["problem_solution", "hook_cta"],
    "hookType": "opportunity",
    "mechanism": "empty_space_opportunity",
    "assetRequirements": ["product_image"],
    "riskRules": ["no_roi_promise", "no_medical_outcome_claims"],
  }
]
```

Phase 1 seed size: 8 playbooks × 4-5 mechanisms = 32-40 высококачественных структур. 80-150 — отдельная content-production задача после проверки первых результатов.

### 18.2 Context passed to Claude

В Claude final call добавить:

```json
{
  "selectedPlaybook": "...full selected playbook...",
  "offerRoleRules": {
    "productSourcePriority": true,
    "personIsPresenterUnlessExplicitlyPromoted": true
  }
}
```

Не передавать все playbooks сразу, только selected. Для `auto` можно передать compact index + выбранный playbook после preparatory step, либо дать Claude выбрать формат из compact index и потом финально планировать.

### 18.3 Schema changes

Минимально:

- Phase 1 не меняет schema: остаёмся на ровно 3 candidates;
- `creativeMechanism` уже есть;
- `hookStrategy` уже есть;
- `CreativeAudit.candidates` уже есть и сейчас жёстко ограничен ровно 3 candidates (`min_length=3`, `max_length=3`);
- `priorConcepts`, `excludedMechanisms`, `contextFingerprint` и quality gate уже есть в runtime; задача не строит diversity gate с нуля, а переводит его с “три механизма из prompt” на “три механизма, обогащённых playbook/structure context”;
- playbook/structures можно внедрить через prompt/context.

Позже добавить:

```text
openingHook
ctaText
captionBeats
promotedOfferSource
personRole
```

### 18.4 Prompt changes

В system prompt добавить:

```text
A creative mechanism is the central story engine: opening hook, visual action, tension, product role, payoff and CTA. Different wording, closer camera, or another CTA sentence is not a new mechanism.
```

И правило:

```text
If product URL or product image exists and the user asks to promote the product, the product/offer is the subject being sold. Person images are presenter references only unless the user explicitly asks to promote that person or service.
```

### 18.5 Frontend changes

Не менять визуально сильно.

Позже можно добавить:

- “Why this concept” для dev/debug;
- “Show 3 alternatives” после стабилизации;
- concept cards, но не сейчас.

### 18.6 Provider changes

Не менять Wan/OpenRouter сейчас.

Сейчас цель — улучшить план до provider.

---

## 19. Test plan

| Test | Expected |
|---|---|
| USG product + doctor image + “wypromuj ten produkt” | Рекламируется аппарат; врач presenter. |
| Product URL failed | Claude не притворяется, что прочитал URL. |
| UGC Review | First-person impression, no fake usage result. |
| Unboxing without box | First-look reveal, no fake packaging. |
| Problem → Solution B2B | Real business friction, product as answer. |
| Product Demo | Visible product action in first 3 seconds. |
| Testimonial without source | Creator/professional impression, not fake customer. |
| Trending Style | Pattern interrupt/social rhythm, product still central. |
| Hook → CTA | One hook, one CTA. |
| Before/After medical-adjacent | Workflow/scene contrast, no treatment claims. |
| Change Concept | Different mechanism slug and central payoff. |
| Mechanism audit | Exactly 3 candidates in Phase 1, all materially different; no wording-only variants. |
| Polish prompt | spokenLanguage remains pl/pl-PL. |
| Person-only service | If no product and user promotes person/service, service can be offer. |

---

### 19.1 Coverage gap

На 2026-09-12 test plan заметно шире текущего `apps/api/tests/test_creative_direction.py`. Следующая implementation-задача должна явно добавить все 14 сценариев из таблицы выше, а не ограничиться happy-path проверкой.

## 20. Acceptance criteria for V1.1

Storyflow Creative Director считается улучшенным, если:

1. Для каждого выбранного формата Claude получает selected playbook.
2. Для каждого ответа сохраняется selected mechanism.
3. Change Concept не повторяет предыдущий mechanism.
4. Product/person role bug закрыт тестом.
5. URL failure не приводит к fake understanding.
6. В mock tests каждый формат даёт разные механизмы.
7. Пользователь видит понятный Concept / Hook / Story / Script / Look.
8. Генерация видео остаётся через Wan/OpenRouter/15s/native audio.

---

## 21. Что оставить на потом

- deterministic captions overlay;
- visible concept alternatives;
- batch rendering;
- avatar library;
- actor replacement;
- reference ad remix;
- store integrations;
- 30/45/60 секунд;
- второй video provider;
- TTS.

---

## 22. Источники

- Predis Product Video Maker: https://predis.ai/product-video-maker/
- Predis AI Video Generator: https://predis.ai/ai-video-generator/
- Predis AI Ad Generator: https://predis.ai/
- Topview Advertising: https://www.topview.ai/use-cases/advertising
- Arcads Complete Platform Guide: https://intercom.help/arcads/en/articles/15503340-everything-you-can-do-on-arcads-complete-platform-guide
- Arcads Getting Started: https://intercom.help/arcads/en/articles/14531683-getting-started-with-arcads
- Creatify AI Video Generator: https://creatify.ai/features/ai-video-generator
- Creatify UGC at Scale: https://creatify.ai/blog/ugc-creator-how-to-produce-user-generated-content-at-scale
- Creatify API: https://creatify.ai/api
