# Следующий план реализации

Обновлено: 2026-09-13. Этот документ заменяет старый план, в котором playbooks и structure retrieval ошибочно оставались будущей работой.

## Уже завершено

### Creative Director

- [x] 8 `FORMAT_PLAYBOOKS`.
- [x] 45 `WINNING_AD_STRUCTURES`.
- [x] 13 niche vocabularies и 13 category overlays.
- [x] 10 consumption models.
- [x] Adaptive deterministic retrieval: 6 карточек для точного оффера, 10 для гибридного/неоднозначного.
- [x] Auto-format получает широкий индекс, explicit format — приоритет своего playbook.
- [x] Библиотека работает как reference seed, Claude обязан дать library match, другую family и hybrid/original.
- [x] Product/person role rule.
- [x] Narrative-media payoff rule.
- [x] `evidenceAvailable` вычисляется backend-кодом.
- [x] Ровно 3 materially different candidates и 8 quality scores.
- [x] Role, spoken-register, ratio и quality validators.
- [x] `Change concept` с `contextFingerprint` и исключением прежних mechanisms.
- [x] Audit сохраняется в `recipe.planning.creativeAudit`, usage — в `recipe.planning.usage`; добавлен server log.
- [x] Prompt caching на Director system + schemas подтверждён реальным cache write/read.
- [x] Vision resize до 1024 без изменения оригиналов.
- [x] Расширенные mock-тесты и live-eval, включая narrative/hybrid кейсы.

### Video и frontend

- [x] Wan 3.0 через OpenRouter как рабочая VPS-модель.
- [x] Native audio, 15 секунд, 9:16 / 1:1 / 16:9.
- [x] Автосохранение completed generations в историю.
- [x] Фейковые failed-карточки скрыты, старый Seedance baseline исключён.
- [x] Вертикальный preview и корректное MP4 playback/download на VPS.
- [x] Полноразмерный WebGL fluid overlay для Auto Planning и video generation; один status без бейджей, подложки и filler-текста.
- [x] Удалена вводящая в заблуждение кнопка Cancel generation.
- [x] Горизонтальная и вертикальная showcase-галереи с muted autoplay.
- [x] Hover останавливает движение карусели, но не video playback.
- [x] Collapsible sidebar с временным hover-expand.
- [x] Каталог Templates сокращён до 8 актуальных generative-форматов на backend и frontend; старые Render/Remotion-карточки исключены из runtime-каталога.
- [x] Отдельный Product Look Studio `/try-on` добавлен в сайдбар и задеплоен как
  responsive frontend по утверждённому макету.
- [x] На странице есть `1 hero photo`, `4 angles` и параллельный прямой путь
  `Generate Video Instead`; `Background` и дублирующий disabled-helper удалены.
- [x] Финальный шаг hero проигрывает пользовательский MP4 через muted autoplay loop
  без player controls.

### Product Look Studio — ближайшая функциональная работа

- [ ] Подключить UI загрузки к `POST /api/assets/bulk`.
- [ ] Подключить `1 hero photo` и `4 angles` к существующему `POST /api/try-on`.
- [ ] Определить и подключить прямой video path без промежуточного фото.
- [ ] Подключить credits, project/version persistence и Library/history.
- [ ] Заменить текущие frontend-only status notices реальными loading/error/result
  состояниями.

До выполнения этих пунктов `/try-on` является готовым frontend-макетом поверх уже
существующих backend-примитивов, а не завершённым end-to-end модулем.

## Приоритет 0 — создать единый источник истины

Это блокирует безопасные крупные деплои.

1. Создать настоящий git baseline проекта.
2. Взять за основу фактический runtime `/opt/storyflow/app`, не теряя локальные tests, docs, vault и scripts.
3. Сохранить уже синхронизированные VPS-исправления MP4 download и chat styling.
4. Сохранить подтверждённую локальную и VPS-модель `alibaba/wan-3.0`.
5. Зафиксировать baseline commit и deploy manifest.
6. После этого деплоить только проверяемый commit/worktree.

Нельзя выполнять массовый local→VPS sync до этого шага: локальная копия сейчас способна откатить рабочие пользовательские исправления.

## Приоритет 1 — production hardening

Публичный runtime пока использует development/mock/local режимы.

- перевести `APP_ENV` в production;
- заменить mock auth на реальную authentication/authorization;
- перевести generated media из local storage в устойчивое object storage;
- определить backup/restore и retention;
- добавить health/alerting для worker queue и provider failures;
- отделить internal credits от фактической OpenRouter cost в observability.

Это отдельный инфраструктурный этап и требует проверки миграции данных и rollback.

## Приоритет 2 — reference preflight до платной генерации

Перед резервом/submit:

1. проверить доступность каждого reference URL со стороны provider path;
2. проверить MIME type, размер, срок жизни signed URL и отсутствие HTML/JSON вместо media;
3. для image/video reference подтвердить поддерживаемый формат;
4. вернуть пользователю конкретную ошибку до отправки платной job;
5. покрыть сценарии expired URL, private host, redirect, wrong MIME и oversized file.

## Приоритет 3 — captions, headline и CTA как deterministic overlay

Если пользователю нужны точные титры или надписи, их не следует поручать генеративной video model.

```text
Wan clean video
→ deterministic renderer
→ approved font/layout/safe zones
→ exact Polish text
→ final MP4
```

Сначала один минимальный caption preset и один CTA preset для 9:16. Затем 1:1/16:9, brand kit и несколько styles. Текст должен брать финальный script/CTA из recipe version, а не заново генерироваться.

## Приоритет 4 — eval и наблюдаемость качества

1. Сделать offline fixture-набор для всех 8 formats и 13 categories без платных API-вызовов.
2. Добавить controlled live-eval только для изменений prompt/retrieval/validator.
3. Считать:
   - clarification rate;
   - repair rate;
   - `qualityGatePassed=false` fallback rate;
   - format distribution по нишам;
   - reuse/rejection механизмов;
   - input/output/cache/research cost;
   - human review естественности реплик.
4. Добавить специальные кейсы на польские окончания, CTA semantics и books/media.
5. Следить, не сводит ли `narrative_media` слишком много офферов к `hook_cta`.

Нельзя оценивать смысл речи одной универсальной regex. Детерминированные validators ловят очевидные ошибки, а semantic quality подтверждается eval-набором.

## Заморожено решением пользователя — Phase 2

Phase 2 не выполняется и не является следующим milestone. Не планируем:

- расширение библиотеки через массовый внешний research;
- Topview-подобную автоматически обновляемую ad library;
- YouTube/TikTok/Meta integrations или scraping;
- `AdStructureResearcher`, embeddings и vector DB.

Текущих 45 карточек достаточно для работающей Phase 1. Возврат к расширению возможен только по отдельному решению пользователя. Актуальные продуктовые приоритеты без Phase 2 зафиксированы в [[07_Competitive_Gap_Audit_No_Phase2]].

## Что пока не расширяем

- число candidates выше 3;
- длительности больше 15 секунд;
- новые video providers без доказанного преимущества;
- отдельный TTS вместо native audio;
- timeline editor;
- embeddings/vector DB для 45 карточек;
- автоматический scraping рекламных библиотек;
- debug audit panel во frontend.

## Критерий следующего безопасного релиза

Следующая backend-фаза готова к VPS только когда:

1. существует tracked git baseline;
2. local/VPS diff объяснён;
3. unit/integration tests и ruff проходят;
4. controlled eval не ухудшает role accuracy, mechanism diversity и natural speech;
5. стоимость измерена до и после;
6. runtime health и rollback проверены;
7. vault обновлён фактическим результатом.

## Связанные заметки

- [[01_Project_State]]
- [[04_Creative_Director_Runtime_Architecture]]
- [[05_Local_VPS_State_and_Drift]]
- [[02_Competitor_Playbook_Audit_RU_V2]]
