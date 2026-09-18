# Storyflow UGC — аудит конкурентов и playbook’и для Creative Director

> Исторический аудит от 2026-09-11. Предложенные здесь playbooks и retrieval уже реализованы. Фактическое устройство находится в [[04_Creative_Director_Runtime_Architecture]], оставшиеся задачи — в [[03_Next_Implementation_Plan]].

Дата: 2026-09-11  
Статус: продуктово-стратегический аудит. Платные генерации для этого документа не запускались.

## Главный вывод

Storyflow не должен конкурировать как “ещё один интерфейс к видеомодели”. Сильные конкуренты продают не модель, а полный workflow для рекламного UGC:

```text
URL товара / фото товара / фото человека
→ понимание оффера
→ несколько разных креативных механизмов
→ выбранный концепт
→ сценарий + визуальный план
→ генерация видео
→ титры / заголовки / CTA / варианты
→ история / экспорт
```

Wan, Seedance или любая другая модель — это исполнитель. Ценность Storyflow должна быть в Creative Director: он понимает продукт, выбирает рекламный угол, пишет короткий сценарий, строит видео-план и даёт несколько сильных вариантов, а не один случайный prompt.

## Таблица конкурентов

| Конкурент | Что они продают пользователю | Входные данные | Как устроен workflow | Варианты | Что важно для Storyflow |
|---|---|---|---|---|---|
| **Predis** | Видео и рекламные креативы для продукта из ссылки/изображения | Product URL, product image, ecommerce-интеграции | Берут фото, цену, описание; генерируют script, voiceover, captions, music, templates; дают редактор | Несколько версий, A/B testing, resize под платформы, brand kit | Нам нужен не “prompt generator”, а URL/image → script/scenes/captions → editable concept до платной генерации. Источники: https://predis.ai/product-video-maker/ и https://predis.ai/ai-video-generator/ |
| **Topview** | AI advertising platform вокруг winning ad structures | Product URL/image, landing page, uploaded/reference/winning ad | Анализируют hook, story, pacing, visual triggers, CTA; дают рекламные структуры | Много variants с разными hooks, UGC talking heads, lifestyle scenes | Нам нужен механизм вариантов: Change Concept обязан менять центральный рекламный механизм, а не формулировку. Первые 3 секунды критичны. Источник: https://www.topview.ai/use-cases/advertising |
| **Arcads** | AI UGC/ad creation с актёрами, продуктами, B-roll и workflow | Product image, actor, script, generated image, existing video | Product detection, product placement, talking actors, captions, overlays, translate, B-roll, actor replacement | Один winning ad можно размножать в UGC-варианты с разными actors/scripts/languages | Нужно жёстко разделить product reference и person reference. Человек — presenter/actor, а не автоматически рекламируемая услуга. Источники: https://intercom.help/arcads/en/articles/15503340-everything-you-can-do-on-arcads-complete-platform-guide и https://intercom.help/arcads/en/articles/14531683-getting-started-with-arcads |
| **Creatify** | URL-to-video и avatar UGC ads at scale | Product link, product image, text/audio/URL, avatar | Вытягивают product details, делают scripts, avatars, B-roll, music, captions, editor | 5–10 готовых ad videos из одной product link | Storyflow должен сначала генерировать несколько candidate mechanisms внутри, потом можно выводить 3–5 концептов пользователю. Источники: https://creatify.ai/features/ai-influencer-generator и https://creatify.ai/api |

## Самые важные рабочие инсайты

| Приоритет | Инсайт | Почему это даёт буст | Как внедрять без развала системы |
|---:|---|---|---|
| 1 | Форматы должны быть playbook’ами, а не короткими labels | Сейчас “UGC Review” или “Product Demo” слишком слабые инструкции; Claude скатывается в “человек показывает продукт и говорит CTA” | Добавить backend `FORMAT_PLAYBOOKS`. Схемы не ломать, просто давать Claude больше режиссёрского контекста. |
| 2 | Product reference и person reference нужно разделить | Тест с УЗИ показал: Claude может решить, что рекламируем врача, хотя пользователь хотел рекламировать аппарат | Правило: product URL/image = рекламируемый оффер; person image = presenter/actor, если пользователь не сказал иначе. Добавить тесты. |
| 3 | Change Concept должен менять механизм | Рынок продаёт variants. Variant — это другой hook/story/payoff, а не синонимы | Хранить mechanism slug; при Change Concept исключать прошлые механизмы и требовать новый central action/payoff. Частично уже есть, надо усилить playbook’ами. |
| 4 | URL/image context нужно сжимать в offer facts | Generic concepts появляются, когда Claude не понимает товар | Перед финальным планированием делать компактный `OfferFacts`: название, аудитория, use case, benefits, proof, ограничения, визуальная идентичность. |
| 5 | Первые 3 секунды должны быть отдельной логикой | Topview и performance market живут вокруг hook в первые секунды | Добавить `openingHook` или усилить hookStrategy + first beat. Provider менять не нужно. |
| 6 | Титры/CTA/заголовки лучше делать после генерации | AI-video модели плохо держат точный польский текст | Сейчас оставить на потом: Wan генерирует чистое видео, потом OverlayRenderer добавит точные captions/CTA. |
| 7 | Variants — это будущая сильная фича | Predis/Creatify/Topview продают пачку вариантов | Сейчас: 3 candidates внутри. Потом: кнопка “Generate 3 concepts”. Потом batch render после контроля стоимости. |
| 8 | Рынку нужен “готовый рекламный ролик”, а не art demo | Малый бизнес хочет видео, которое можно опубликовать | UI должен показывать Concept, Hook, Story, Script, Look, CTA, потом Generate. Без внутреннего JSON. |

## Текущий runtime Storyflow на VPS

| Область | Факт |
|---|---|
| Runtime path | `/opt/storyflow/app` |
| Git на VPS | `NO_GIT`; риск: runtime не является проверенным git worktree |
| Публичный домен | `https://ugc.cerebroos.io` |
| Chat provider | `claude` |
| Claude model | `claude-sonnet-5` |
| Video provider | `openrouter` |
| Активная видео-модель | `alibaba/wan-3.0` |
| Длина видео | Только 15 секунд |
| Aspect ratio | 9:16, 1:1, 16:9 |
| Native audio | Включён в provider payload |
| Внутренняя цена Storyflow | `VIDEO_CREDITS_PER_SECOND=3`, значит 15s = 45 internal credits |
| Реальные успешные генерации | 2 completed generations, каждая estimated/charged 45 internal credits |
| Failed reference jobs | refund внутри Storyflow: charged 0 |
| Production gap | На публичном VPS всё ещё `APP_ENV=development`; до продаж нужно hardened production setup |
| Storage/media | Signed media route теперь отдаёт `video/mp4` и filename `generated-video.mp4` |

## С какими проблемами столкнулись

| Проблема | Что произошло | Решение / урок |
|---|---|---|
| URL товара был слабым или игнорировался | Claude иногда больше верил фото/person image, чем URL | Нужны offer facts и жёсткое разделение product/person. |
| Фото человека “перехватывало” оффер | Фото врача заставило Claude рекламировать услугу врача, а не УЗИ-аппарат | Добавить правило: person reference — presenter only, если пользователь явно не просит продвигать специалиста/услугу. |
| Seedance плохо с польским | На польском были проблемы с произношением/качеством | Вернули Wan как активную модель. Seedance не использовать в текущей фазе. |
| Reference images rejected | OpenRouter не мог прочитать reference images | Сделан публичный HTTPS-домен/path; позже нужен preflight перед платной генерацией. |
| Download из history шёл как `.json`/битый файл | Browser показывал unavailable file | Media route исправлен: content-type MP4, filename `generated-video.mp4`. |
| Путаница со стоимостью | Пользователь ожидал другой OpenRouter расход | Внутренний Storyflow ledger ≠ внешний OpenRouter billing. Нужно показывать provider job id/cost, если API отдаёт. |
| VPS source-of-truth | `/opt/storyflow/app` не git worktree | До продаж нужен нормальный git-backed deploy или immutable release archive. |

## Playbook’и форматов

Это не фиксированные сценарии. Это инструкции для Creative Director. Каждый формат должен передавать Claude:

- цель формата;
- психологию зрителя;
- допустимые creative mechanisms;
- запрещённый generic fallback;
- правила product/person/source;
- грамматику opening hook;
- визуальную грамматику;
- грамматику сценария;
- CTA;
- quality checks.

## Универсальные правила режиссёра

1. Product URL/product image определяет рекламируемый оффер.
2. Person image определяет presenter/actor/reference identity, а не автоматически то, что продаём.
3. Если пользователь пишет “promote this product / wypromuj ten produkt”, нельзя превращать это в рекламу услуги человека на фото.
4. Делать один 15-секундный concept, обычно один clip с внутренними beats.
5. Генерировать минимум 3 механизма внутри, выбирать сильнейший.
6. На Change Concept менять mechanism и central payoff.
7. Не выдумывать доказательства: результаты, сертификации, скидки, клинические эффекты, гарантии, ROI.
8. Креативность должна быть в ситуации, hook, framing, contrast, visual action и CTA.
9. Dialogue должен быть коротким, говоримым и стабильным по языку.
10. Для технических/медицинских товаров говорить о дизайне, use case, workflow, convenience, availability, inquiry CTA; не обещать результаты лечения.

---

# UGC Review

| Поле | Инструкция |
|---|---|
| Цель | Сделать так, чтобы продукт выглядел замеченным живым человеком, а не проданным “телемагазином”. |
| Психология | “Человек вроде меня смотрит на это и объясняет, почему это может быть интересно.” |
| Подходит для | ecommerce, beauty, gadgets, home products, professional devices, apps, simple services |
| Избегать | Фейковый long-term experience, клинические/финансовые результаты, слишком corporate tone |
| Script style | First-person осторожно: “pierwsze co zauważyłem…”, “to może się sprawdzić gdy…”, “warto sprawdzić…” |

| # | Механизм | Как должно работать |
|---:|---|---|
| 1 | First impression | Presenter видит продукт и называет одну деталь, ради которой стоит смотреть дальше. |
| 2 | “I didn’t expect this” | Hook через неожиданную feature, размер, дизайн или use case. |
| 3 | Detail inspection | История строится на close-up детали: кнопка, ручка, экран, упаковка, кабель, ингредиент. |
| 4 | Everyday problem noticed | Presenter показывает обычную боль, продукт становится практичным ответом. |
| 5 | Buyer question | “Jeśli szukasz X…” и один сфокусированный ответ. |
| 6 | Comparison without competitor | “Zamiast kolejnej rzeczy, która tylko wygląda dobrze…” и видимое отличие. |
| 7 | Gift/use-case review | Продукт как решение для конкретной ситуации/человека. |
| 8 | Skeptical review | Presenter начинает осторожно, но одна видимая деталь вызывает интерес. |
| 9 | Mini checklist | 3 коротких наблюдения и один CTA. |
| 10 | “Would I click?” | Creator объясняет, что заставило бы его открыть оффер. |

# Product Unboxing

| Поле | Инструкция |
|---|---|
| Цель | Создать ожидание и раскрыть ценность через reveal/discovery. |
| Психология | “Что внутри / что меняется после открытия?” |
| Подходит для | physical products, packaging, kits, gadgets, cosmetics, apparel, accessories |
| Избегать | Не выдумывать коробку, если её нет. Если упаковки нет — делать “first look” или “desk reveal”. |
| Script style | “zobaczmy”, “pierwsze wrażenie”, “od razu widać…” |

| # | Механизм | Как должно работать |
|---:|---|---|
| 1 | Classic reveal | Закрытая коробка/продукт вне кадра → reveal → key detail → CTA. |
| 2 | Desk reveal | Продукт появляется на чистом столе; presenter даёт first impression. |
| 3 | Mystery object | Начать с частичного close-up, раскрыть полный продукт через 2–3 секунды. |
| 4 | First-use setup | Подготовка/открытие продукта без обещаний результата. |
| 5 | What’s included | Показать продукт и реально видимые части, не выдумывать аксессуары. |
| 6 | Texture/material reveal | Фокус на finish/material/packaging quality. |
| 7 | Size surprise | Показать scale в руке/на столе. |
| 8 | Giftable reveal | Распаковка как buyer/gift moment. |
| 9 | Professional kit reveal | Для B2B/pro devices: reveal как business equipment. |
| 10 | “Before I even use it” | Что можно оценить сразу: build, layout, portability, clarity. |

# Problem → Solution

| Поле | Инструкция |
|---|---|
| Цель | Дать зрителю почувствовать реальную боль до появления продукта. |
| Психология | “Это моя проблема; этот оффер может помочь.” |
| Подходит для | services, courses, B2B, wellness devices, home tools, SaaS, local businesses |
| Избегать | Фейковые outcomes, overclaiming transformation. |
| Script style | Простая боль → продукт как practical next step. |

| # | Механизм | Как должно работать |
|---:|---|---|
| 1 | Daily friction | Раздражающий момент → продукт как решение. |
| 2 | Lost time | “Ile razy…” или видимая задержка/хаос. |
| 3 | Missed opportunity | Для B2B: пустой слот, неиспользованная комната, missed inquiry. |
| 4 | Too complicated | Показать сложность, продукт упрощает один шаг. |
| 5 | Old way/new way | Старый неудобный способ против нового подхода. |
| 6 | Customer request | Сообщение/вопрос клиента; продукт отвечает спросу. |
| 7 | Small business bottleneck | Владелец упирается в capacity/offer/clarity; продукт расширяет возможности. |
| 8 | Decision anxiety | Зритель не знает, что выбрать; продукт становится понятной опцией. |
| 9 | Space/portability problem | Продукт решает вопрос места/мобильности. |
| 10 | Professional readiness | Продукт помогает выглядеть/работать более подготовленно без обещаний результата. |

# Product Demo

| Поле | Инструкция |
|---|---|
| Цель | Показать продукт в действии, а не просто назвать. |
| Психология | “Я понимаю, как это используется.” |
| Подходит для | gadgets, tools, devices, SaaS, cosmetics, apps, equipment |
| Избегать | Слишком много слов, technical catalogue dump, fake interface/specs. |
| Script style | Одно видимое действие на одну фразу. |

| # | Механизм | Как должно работать |
|---:|---|---|
| 1 | One action demo | Продукт берут/открывают/ставят/включают визуально. |
| 2 | Three-step demo | Setup → key interaction → CTA. |
| 3 | Detail tour | Камера проходит по 2–3 видимым деталям. |
| 4 | Use environment | Продукт в реалистичном месте использования. |
| 5 | Feature-to-benefit | Каждая видимая feature связана с practical use. |
| 6 | Hands-only demo | Без лица; руки чисто демонстрируют продукт. |
| 7 | Presenter + product | Presenter объясняет, одновременно взаимодействуя. |
| 8 | Mobile/portable demo | Показать перенос/установку/мобильность. |
| 9 | Professional workflow | B2B продукт внутри рабочей рутины. |
| 10 | “Show, then say” | Первые 2 секунды визуальное действие, потом объяснение. |

# Testimonial

| Поле | Инструкция |
|---|---|
| Цель | Дать credible personal/social proof только при наличии фактической базы. |
| Психология | “Кто-то похожий/доверенный имел этот вопрос и нашёл это полезным.” |
| Подходит для | reviews, supplied testimonials, founder/customer quotes, case studies |
| Избегать | Выдуманный опыт, fake before/after, fake numbers, fake clinical/business outcomes. |
| Script style | Если source testimonial нет — делать creator impression, не fake customer story. |

| # | Механизм | Как должно работать |
|---:|---|---|
| 1 | Real quote expansion | Превратить реальный supplied review в короткую сцену. |
| 2 | Founder/customer POV | Только если пользователь дал такую роль. |
| 3 | Objection answered | Начать с common doubt, ответить source-backed fact. |
| 4 | “Why I checked it” | Личная curiosity без claim of result. |
| 5 | Social proof from page | Использовать review count/logos только если они есть в source. |
| 6 | Professional recommendation style | Эксперт объясняет, почему стоит проверить оффер, без fake testimonial. |
| 7 | Mini story | Problem → considered options → CTA, только factual. |
| 8 | Category credibility | Позиционировать продукт как подходящий для category need. |
| 9 | User-type testimonial | “Dla osób, które…” вместо “I achieved…”. |
| 10 | Skeptic-to-interest | Believable shift от сомнения к интересу. |

# Trending Style

| Поле | Инструкция |
|---|---|
| Цель | Выглядеть нативно для TikTok/Reels/Shorts, без копирования чужого тренда. |
| Психология | “Это social content, а не реклама.” |
| Подходит для | B2C, beauty, gadgets, fashion, lifestyle, quick offers |
| Избегать | Случайные effects, хаос, тренд ради тренда. |
| Script style | Короткие фразы, pattern interrupt, быстрый ритм. |

| # | Механизм | Как должно работать |
|---:|---|---|
| 1 | Pattern interrupt | Неожиданный первый visual или фраза. |
| 2 | POV setup | “POV: szukasz…” ситуация. |
| 3 | Micro-story | 3 быстрых beat: problem, product, payoff. |
| 4 | Quick cuts | Быстрые, но понятные product angles. |
| 5 | Myth/realization | “Myślałem, że…, ale…” без overclaim. |
| 6 | Listicle | “3 rzeczy, które zauważysz…” |
| 7 | Reaction | Presenter реагирует на detail/use case. |
| 8 | Challenge-style | Маленькая feasible task/product challenge за 15s. |
| 9 | Creator confession | “Nie kupiłbym kolejnej rzeczy, gdyby…” |
| 10 | Comment reply | Ответ на buyer question, не fake comment proof. |

# Hook → CTA

| Поле | Инструкция |
|---|---|
| Цель | Построить всё видео вокруг сильного начала и одного действия в конце. |
| Психология | “Stop, understand, act.” |
| Подходит для | lead gen, offers, launches, services, B2B, landing page traffic |
| Избегать | Несколько CTA, vague hook, длинная середина. |
| Script style | Hook в первой фразе; CTA в последней. |

| # | Механизм | Как должно работать |
|---:|---|---|
| 1 | Direct question | “Szukasz…?” сразу открывает ролик. |
| 2 | Contrarian line | “Nie potrzebujesz X, jeśli masz Y…” |
| 3 | Specific audience callout | “Dla właścicieli gabinetów…” |
| 4 | Opportunity hook | “Jedno urządzenie może poszerzyć ofertę…” без ROI claim. |
| 5 | Curiosity gap | Сначала detail продукта, потом название. |
| 6 | Problem punch | Назвать боль в первые 2 секунды. |
| 7 | Visual hook | Начать с сильного close-up/product movement. |
| 8 | Deadline/event | Только если дата есть в source/user input. |
| 9 | Comparison hook | Old way vs new option без competitor names. |
| 10 | Offer clarity | Сразу сказать, что это и для кого. |

# Before / After

| Поле | Инструкция |
|---|---|
| Цель | Показать контраст без выдуманных невозможных результатов. |
| Психология | “Я вижу разницу в ситуации/состоянии.” |
| Подходит для | organization, setup, workflow, cleaning, beauty packaging, business offer clarity, SaaS UI, courses |
| Избегать | Fake health/body/business results, если нет source/compliance. |
| Script style | “Przed: … Po: …”, но grounded in scene, не guaranteed result. |

| # | Механизм | Как должно работать |
|---:|---|---|
| 1 | Messy → organized | Продукт делает сцену/setup более чистым. |
| 2 | Confused → clear | Product/service объясняет next step. |
| 3 | Static → in motion | Product photo превращается в активное использование. |
| 4 | Empty → equipped | Business/professional space теперь оборудован. |
| 5 | Ordinary → premium | Visual presentation upgrade, не factual claim. |
| 6 | Long process → shorter-feeling process | Показать simplification без time guarantee. |
| 7 | Hidden detail → visible detail | До — зритель не замечает; после — close-up раскрывает detail. |
| 8 | No plan → clear CTA | Для service/course: зритель получает next action. |
| 9 | Shelf → lifestyle | Product переходит из plain shot в use environment. |
| 10 | Doubt → interest | Presenter меняет реакцию после inspection. |

## Правила, которые предотвращают ошибку “врач вместо продукта”

| Ситуация | Правило |
|---|---|
| Product image = аппарат, person image = врач | Рекламируем аппарат, если пользователь не написал “рекламируй врача/услугу”. Врач — presenter/reference. |
| User says “wypromuj ten produkt” | `offer.type=product`; не превращать в service. |
| URL — ecommerce product page | Факты страницы товара сильнее догадок по person image. |
| YouTube URL provided | Если видео не fetched/transcribed, сказать, что оно не использовано. Не выдумывать содержание по ссылке. |
| Medical/professional equipment | Говорить о business fit, portability, visual design, inquiry CTA. Не обещать patient outcomes. |

## Как лучше реализовать без развала системы

Сохраняем текущую цепочку:

```text
Create UI
→ chat session
→ chat_context.enrich()
→ ContextBundle
→ ClaudeCreativeDirectorAdapter
→ CreativePlan + VideoPlan + CreativeAudit
→ compile_plan()
→ compile_recipe()
→ OpenRouterVideoProvider
→ Wan
→ storage/history
```

Добавляем только слои:

| Слой | Изменение | Риск |
|---|---|---|
| Format playbooks | Добавить `creative_direction_format_playbooks.py` или расширить prompt context selected playbook’ом | Низкий: prompt/context only |
| Offer facts | Сжимать URL/image/product interpretation в `OfferFacts` перед final planning | Средний: нужно держать token budget |
| Product/person separation | Добавить schema flags: `promotedOfferSource`, `personRole` | Низкий/средний: schema/tests |
| Hook field | Добавить `openingHook` в CreativePlan или выводить из hookStrategy + first beat | Низкий |
| Variant memory | Хранить rejected/selected mechanisms | Уже частично есть; усилить тестами |
| Overlay later | Детеминированные captions/headlines после генерации | Позже, отдельный pipeline |
| Provider preflight | Перед paid generation проверять HTTPS media URLs как их увидит provider | Средний: предотвращает wasted requests |

## Что не делать сейчас

- Не добавлять 30/45/60 секунд.
- Не добавлять второго провайдера, пока Wan path не стабилен.
- Не добавлять TTS/отдельную озвучку сейчас.
- Не строить timeline editor.
- Не показывать пользователю внутренний JSON.
- Не превращать format buttons в fixed scripts.

## Минимальный следующий implementation plan

| Шаг | Задача | Done when |
|---:|---|---|
| 1 | Добавить `FORMAT_PLAYBOOKS` для всех 8 форматов | Claude получает selected playbook в final call |
| 2 | Добавить hard product/person rules в system prompt | USG doctor case делает рекламу продукта, не услуги |
| 3 | Добавить tests для каждого формата | Каждый формат даёт materially distinct mechanism |
| 4 | Добавить Change Concept regression tests | Второй концепт не повторяет mechanism |
| 5 | Добавить URL/product image offer source tests | Product URL/image сильнее person image role |
| 6 | Добавить compact debug только для dev/audit | Можно видеть ContextBundle, selected playbook, candidates |
| 7 | Добавить reference URL preflight | Bad refs fail до paid provider submission |
| 8 | Позже добавить overlay renderer | Точные польские captions/CTA после video generation |

## Acceptance tests

| Test | Expected result |
|---|---|
| Product URL + doctor image + “promote this product” | Device/product is the offer; doctor is presenter |
| Product image only + UGC Review | First-person inspection, no fake ownership/results |
| Product image only + Unboxing | If no packaging, first-look reveal, not fake box |
| B2B device + Hook→CTA | Starts with business owner/audience callout, ends with inquiry CTA |
| Service/course + Problem→Solution | No product packaging assumptions |
| Testimonial without testimonial source | Creator impression, not fake customer story |
| Before/After medical-adjacent | Workflow/scene contrast, no treatment result |
| Change Concept after first plan | Mechanism slug and central payoff differ |
| Product URL failed | Claude says page was not used or asks one question; no pretending |
| Long page context | No “context too large”; compact facts sent |

## Рыночное обещание Storyflow

Правильное обещание:

> “Дайте ссылку на товар или фото. Storyflow превратит это в несколько UGC ad concepts, выберет сильный 15-секундный script + visual plan, сгенерирует реалистичное видео и сохранит его в history/export.”

Неправильное обещание:

> “Мы используем Wan/Seedance/OpenRouter.”

## Файлы/области для следующей реализации

| Область | Файл |
|---|---|
| format biases/schema | `apps/api/app/creative_direction.py` |
| Claude adapter | `apps/api/app/providers/claude.py` |
| system prompt | `apps/api/app/prompts/video_chat/v3.py`, `v2.py` |
| context bundle / URL/image evidence | `apps/api/app/services/chat_context.py` |
| chat persistence/apply | `apps/api/app/services/chat.py` |
| provider request | `apps/api/app/providers/openrouter.py` |
| recipe compiler | `apps/api/app/video_recipe.py` |
| frontend chat summary | `apps/web/features/chat/*` |
| preview/download | `apps/web/features/create/preview.tsx`, `/api/media` route |

## Источники

- Predis product video maker: https://predis.ai/product-video-maker/
- Predis AI video generator: https://predis.ai/ai-video-generator/
- Predis AI ad generator: https://predis.ai/
- Topview advertising use case: https://www.topview.ai/use-cases/advertising
- Arcads complete platform guide: https://intercom.help/arcads/en/articles/15503340-everything-you-can-do-on-arcads-complete-platform-guide
- Arcads getting started: https://intercom.help/arcads/en/articles/14531683-getting-started-with-arcads
- Creatify AI influencer / URL-to-video info: https://creatify.ai/features/ai-influencer-generator
- Creatify API: https://creatify.ai/api
