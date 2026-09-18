# Аудит продуктовых разрывов Forma относительно конкурентов

Дата: 2026-09-12  
Объект: текущий Forma / Storyflow UGC runtime и локальный код  
Конкуренты: Predis, Topview, Arcads, Creatify  
Решение по scope: **Phase 2 не выполняется**.

## 1. Что именно исключено

В этот аудит и ближайший план не входят:

- автоматический сбор рекламы из YouTube, TikTok, Meta или других площадок;
- scraper, `AdStructureResearcher`, embeddings и vector DB;
- собственная автоматически обновляемая библиотека winning ads;
- оптимизация креативов по рекламным метрикам и импорт campaign performance;
- копирование чужих сценариев или роликов дословно.

Здесь рассматриваются только улучшения существующего product-to-video потока, которые можно сделать на собственных данных пользователя и на уже созданной Phase 1 архитектуре.

## 2. Метод и ограничения

Сравнение основано на:

1. фактическом коде `/Users/stas/Documents/UGC`;
2. зафиксированном состоянии VPS из vault;
3. официальных продуктовых страницах конкурентов, проверенных 2026-09-12;
4. собственных заявлениях вендоров о возможностях продукта. Их маркетинговые показатели не считаются независимым доказательством качества.

Источники:

- Predis: https://predis.ai/product-video-maker/
- Topview Advertising: https://www.topview.ai/use-cases/advertising
- Topview API: https://www.topview.ai/openapi
- Arcads Agent: https://agent.arcads.ai/
- Arcads Help Center: https://intercom.help/arcads/en/collections/7500987-how-to-use-arcads-platform
- Creatify Features: https://creatify.ai/features
- Creatify Docs: https://docs.creatify.ai/introduction

## 3. Где Forma уже сильна

Forma уже не является простым prompt wrapper.

- Claude Creative Director анализирует offer, изображения, URL и выбранный формат.
- Поддерживаются product image, person image, product URL и existing video.
- Existing video представлен директору тремя извлечёнными кадрами и передаётся video provider как reference.
- Есть 8 format playbooks, 45 рекламных структур, 13 niche vocabularies, 13 category overlays и 10 consumption models.
- Retrieval адаптивно отдаёт 6 или 10 совместимых структур и не требует embeddings.
- Внутри каждого ответа создаются ровно 3 разных кандидата, затем применяются scoring и quality gates.
- Есть правила роли продукта и персонажа, evidence control, защита от выдуманных claims, контроль естественности реплик и механизм `change concept`.
- Готовый ролик автоматически сохраняется в истории и доступен для просмотра и скачивания.
- Поддерживаются 9:16, 1:1 и 16:9, native audio, idempotent job flow, кредитный ledger и S3-compatible storage abstraction.

По качеству планирования Forma уже ближе к Arcads/Topview, чем обычный URL-to-video генератор. Главный разрыв находится между хорошим планом и полностью готовым рекламным материалом.

## 4. Матрица возможностей

Обозначения: **есть**, **частично**, **нет**, **вне scope**.

| Возможность | Forma сейчас | Predis | Topview | Arcads | Creatify | Вывод |
|---|---|---|---|---|---|---|
| URL/image → сценарий → видео | есть | есть | есть | есть | есть | Базовый parity достигнут |
| Осмысленный выбор рекламного механизма | есть | частично заявлен | есть | есть | есть | Сильная сторона Forma |
| Несколько концепций до генерации | внутренние 3, пользователь видит 1 | variants | dozens of variants | variations/batches | 5–10 scripts/ads | Критический UX-разрыв |
| Точные captions/headline/CTA | нет | есть | есть | есть | есть | Самый заметный разрыв готовности результата |
| Редактирование текста до расхода video credits | частично: итоговый prompt | есть | есть | есть | есть | Нужен структурированный контроль hook/script/CTA |
| Brand Kit и brand memory | заглушка | есть | частично | есть | есть | Критический разрыв повторного использования |
| Сохранённый профиль продукта | нет | store/catalog flow | URL workflow | memory | URL workflow | Пользователь повторяет один и тот же ввод |
| Выбор извлечённых с URL материалов | частично, автоматический `og:image` | есть | есть | есть | есть | Нет прозрачности, что уйдёт модели |
| User-supplied reference ad → адаптация структуры | existing video передаётся, семантика слабая | частично | есть | hook repurposing | ad clone | Можно сделать без Phase 2 |
| Постоянный creator/avatar profile | нет | AI avatar | есть | есть | есть | Важен для серий, но не первый релиз |
| Точная озвучка/произношение | native audio, без гарантии | voiceover | voice/avatar | voice/avatar | 75+ languages | Ограничение текущего video provider |
| Разрешение 1080p | нет, жёстко 480p | ready-to-post export | заявлено 1080 | готовые ads | platform output | Сильный технический разрыв |
| Длительности | только 15s | несколько | широкий диапазон | workflow dependent | несколько | Расширять после проверки провайдера |
| Форматы 9:16 / 1:1 / 16:9 | есть | есть | есть + 4:5 | есть | есть | Почти parity; 4:5 не срочен |
| Batch generation | нет | есть | есть | есть | есть | Нужен после выбора концепций и контроля цены |
| Localization variants | язык передаётся агенту | 18+ languages | multilingual | translation | 75+ languages | Есть основа, нет управляемого дубляжа |
| Export bundle: MP4 + SRT + copy | только MP4 | MP4/publishing | platform assets | edited ad | export | Полезный небольшой разрыв |
| Social scheduling/publishing | нет | есть | не ядро | не ядро | не ядро | Не требуется сейчас |
| Автоматическая ad library/research | нет | отдельные функции | сильная сторона | research agent | AdMax | **вне scope** |
| Performance analytics/optimization | заглушка | A/B workflow | testing | variations | performance tools | **вне ближайшего scope** |

## 5. Что отсутствует критически

### 5.1. Видимый выбор концепции до платной генерации

Сейчас Claude создаёт три кандидата, но пользователь получает только выбранный системой результат. Это скрывает уже оплаченную интеллектуальную работу и заставляет использовать `Change concept` вслепую.

Нужно показывать три компактные карточки:

- механизм и обещание ролика;
- hook первых трёх секунд;
- короткая логика story;
- spoken script;
- CTA;
- причина соответствия доступным материалам.

Пользователь выбирает одну карточку, редактирует текст при необходимости, и только затем запускает платное видео. Число Claude candidates остаётся равным 3. Дополнительного вызова модели и увеличения prompt budget не требуется.

**Критерий готовности:** ни один video job не создаётся до явного выбора или подтверждения концепции; `change concept` исключает уже отклонённые механизмы.

### 5.2. Детерминированный слой captions, headline и CTA

Конкуренты продают ready-to-post результат. Forma пока отдаёт чистое generative video, поэтому точный польский текст, брендовый CTA и безопасные зоны нельзя гарантировать.

Правильный поток:

```text
Wan clean video
→ deterministic post-render
→ captions / headline / CTA / end card
→ final MP4
```

Первая версия должна содержать один сильный preset для 9:16:

- exact text из утверждённого recipe version;
- построчные captions с безопасными зонами;
- один headline style;
- один CTA/end-card style;
- возможность выключить каждый слой;
- отдельный clean MP4 и captioned MP4.

Это повышает качество без изменения Creative Director и без Phase 2.

### 5.3. Реальный Brand Kit и память продукта

`/brand-kit` сейчас является заглушкой. Из-за этого каждый ролик начинается почти с нуля.

Минимальная модель Brand Kit:

- название бренда;
- logo asset;
- основные цвета;
- основной и акцентный шрифт;
- tone of voice;
- запрещённые фразы и claims;
- обязательная legal line;
- CTA по умолчанию;
- pronunciation glossary для названий бренда и продукта.

Отдельный Product Profile:

- canonical product URL;
- утверждённые facts и claims;
- выбранные product images/video;
- audience и offer;
- прошлые одобренные и отклонённые механизмы.

Эти данные следует передавать Claude как owned reference. Пользователь должен видеть и менять их; внешняя страница не становится скрытым постоянным источником истины.

### 5.4. Контроль материалов до отправки платной job

URL resolver сейчас автоматически берёт страницу и основное `og:image`. Пользователь не видит полный набор фактов и материалов, на которых строится ролик.

Нужен небольшой шаг `Review product`:

- найденное название и описание;
- извлечённые проверяемые facts;
- выбранное основное изображение;
- предупреждение, если изображение недоступно;
- выбор, какие загруженные assets являются product/person/source video;
- preflight MIME, размера, expiry и доступности provider URL до резерва credits.

Это снижает дорогие provider failures и предотвращает ролики с неверным изображением товара.

### 5.5. 1080p delivery

Текущий `OpenRouterVideoProvider` принимает только 15 секунд и всегда отправляет `resolution: 480p`. Для рекламного продукта это серьёзный разрыв: Topview прямо заявляет 1080×1920, 1080×1080 и 1920×1080 для основных placements.

Не следует просто открыть селектор 1080p в интерфейсе. Сначала нужно выбрать и измерить один из путей:

1. подтверждённый 1080p output того же provider/model;
2. детерминированный upscale после Wan;
3. другой provider только для финального render/export.

**Критерий готовности:** реальный файл проверяется через ffprobe, а UI показывает фактическое разрешение output asset.

## 6. Следующий уровень после критических разрывов

### 6.1. Reference-ad mode на видео пользователя

Это не Phase 2. Пользователь сам загружает законно доступный reference video. Forma извлекает:

- тип hook;
- порядок beats;
- pacing и частоту смены сцен;
- способ появления продукта;
- placement CTA;
- визуальные приёмы, которые можно реализовать с текущими assets.

Результатом становится новая оригинальная концепция под факты текущего продукта. Сейчас три sampled frames дают только слабое понимание ролика. Для этого режима нужны ещё duration, scene-change timestamps и transcript/audio analysis либо явное сообщение об отсутствии такой информации.

### 6.2. Batch из выбранной концепции

После выбора одной концепции пользователь может заказать:

- три разных hook opening;
- тот же hook с разными CTA;
- разные aspect ratios;
- разные языковые версии.

Перед запуском показывается число jobs и общая цена. Никакой автоматической траты credits. Первая реализация может клонировать утверждённый recipe и менять только один контролируемый параметр.

### 6.3. Saved creator profile

Нужно сохранять person reference вместе с инструкциями: роль, подача, допустимый wardrobe, язык, голос и ограничения. Это даст повторяемость между роликами. Нельзя обещать identity consistency или lip sync, пока это не подтверждено серией реальных тестов Wan.

### 6.4. Структурированное редактирование без timeline editor

Полный видеоредактор сейчас не нужен. Достаточно редактируемых полей:

- hook;
- spoken script;
- CTA;
- product facts;
- caption style;
- язык;
- visual constraints.

После изменения сервер заново валидирует recipe и показывает новую quote. Это сохраняет сильную автоматизацию, но возвращает пользователю контроль над продающим текстом.

### 6.5. Export bundle

Для каждого готового ролика:

- clean MP4;
- captioned MP4;
- SRT/VTT;
- финальный script;
- headline и CTA copy;
- технические параметры файла.

Это повышает практическую ценность без scheduler, campaign manager или analytics.

## 7. Что сознательно не строить сейчас

- 5–10 платных видео по умолчанию;
- большой timeline/node editor;
- собственный stock library;
- сотни avatars;
- social publishing и calendar;
- campaign analytics;
- performance optimization;
- store integrations;
- 4:5 до подтверждения спроса;
- новые длительности до проверки качества и цены;
- новый video provider только ради длинного списка моделей;
- любая часть Phase 2.

Большинство этих функций расширяет поверхность продукта, но не исправляет текущий разрыв между хорошей идеей и готовым рекламным файлом.

## 8. Рекомендуемый порядок без Phase 2

### Этап A — надёжность основания

1. Создать tracked git baseline и однозначный deploy source.
2. Сверить локальный код с VPS и устранить известный drift.
3. Перевести production с mock auth/local storage или явно оставить закрытым test environment.
4. Добавить reference preflight и provider/worker observability.

### Этап B — готовый рекламный результат

1. Показать пользователю текущие 3 concept candidates.
2. Добавить редактирование hook/script/CTA до video submit.
3. Реализовать deterministic captions/headline/CTA для 9:16.
4. Отдавать clean и captioned export.
5. Добавить проверенный 1080p delivery path.

### Этап C — повторное использование

1. Реальный Brand Kit.
2. Saved Product Profile.
3. Saved Creator Profile с честно обозначенными ограничениями consistency.
4. Reusable approved recipe.

### Этап D — контролируемое масштабирование

1. Reference-ad mode только для user-supplied video.
2. Batch hooks/CTA/ratios с общей quote до запуска.
3. Language variants и pronunciation tests.
4. Offline eval и ограниченный live eval для каждого изменения качества.

**Phase 2 после этапа D автоматически не начинается.** Для неё потребуется отдельное решение пользователя.

## 9. Приоритетная пятёрка

Если выбрать только пять работ, которые дадут максимальный рыночный эффект:

1. показать три уже существующие concept candidates до траты credits;
2. deterministic captions + CTA + end card;
3. Brand Kit и Product Profile;
4. provider reference preflight с выбором материалов;
5. проверенный 1080p export.

Это превращает Forma из сильного генератора идеи в повторяемый product-ad workflow. Для этого не требуется Phase 2, новый research backend или увеличение числа Claude candidates.

## 10. Технические доказательства текущего состояния

- `apps/api/app/providers/openrouter.py`: единственная разрешённая модель `alibaba/wan-3.0`, 15 секунд, 480p, native audio.
- `apps/web/app/[section]/page.tsx`: Brand Kit и Analytics являются scope placeholders.
- `apps/web/features/chat/chat-parts.tsx`: интерфейс показывает один выбранный recipe/concept.
- `apps/api/app/creative_audit.py`: CreativeAudit формирует ровно три кандидата.
- `apps/api/app/creative_direction_playbooks.py`: 8 playbooks, 45 structures и deterministic retrieval.
- `apps/api/app/services/chat_context.py`: URL evidence, images и sampled frames existing video.
- `apps/api/app/services/storage.py`: local/S3 abstraction и signed provider URLs уже существуют.

