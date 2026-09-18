# Локальная копия и VPS — состояние и расхождения

Read-only проверка выполнена 2026-09-12, Europe/Warsaw.

## 1. Где находится проект

| Среда | Путь | Роль |
|---|---|---|
| Локальная | `/Users/stas/Documents/UGC` | разработка, тесты, vault |
| VPS | `netcup-cerebro:/opt/storyflow/app` | фактически работающий runtime `ugc.cerebroos.io` |

Это отдельный Storyflow/UGC runtime. `/opt/cerebro/app` относится к другому продукту Cerebro и не должен использоваться для этого проекта.

## 2. CBM preflight

- CBM MCP exposed: no.
- CBM CLI fallback used: yes.
- Project: `Users-stas-Documents-UGC`.
- На момент первого `list_projects`: 3185 nodes / 8999 edges.
- Выполненные запросы: Claude provider, Preparation/Director, prompt v3, `CreativeAudit`, `FORMAT_PLAYBOOKS`, `WINNING_AD_STRUCTURES`, retrieval, `ContextBundle`, agent behavior.
- Возвращённые ключевые файлы: `providers/claude.py`, `creative_direction_playbooks.py`, `creative_audit.py`, `services/chat_context.py`, `scripts/agent_bus.py` и тесты.
- `detect_changes` перед анализом: indexed changes отсутствовали.

## 3. Состояние VPS

### Контейнеры и health

На момент проверки:

- `api` — Up;
- `worker` — Up;
- `web` — Up;
- `redis` — Up;
- `postgres` — Up/healthy;
- `/health/live` — 200;
- `/health/ready` — 200;
- внутренний web — 200.

### Фактическая конфигурация без секретов

```yaml
app_env: development
auth_mode: mock
storage_mode: local
chat_provider: claude
claude_model: claude-sonnet-5
claude_effort: medium
claude_max_rounds: 4
claude_max_web_searches: 2
claude_max_web_fetches: 2
claude_max_input_tokens: 24000
claude_max_output_tokens: 8192
claude_session_budget_cents: 100
video_provider: openrouter
openrouter_video_model: alibaba/wan-3.0
openrouter_video_enabled: true
duration: 15
credits_per_second: 3
formats: 8
structures: 45
niches: 13
overlays: 13
```

### Данные

Read-only counts:

- generations: 3 completed, 6 failed;
- chat sessions: 8;
- recipe versions: 7.

## 4. Состояние локальной копии

Локальные проверки:

- API: 312 passed, 12 skipped;
- ruff: passed;
- Web: 47 passed;
- typecheck: passed;
- lint: passed;
- production build: passed.

Локальная конфигурация без секретов:

```yaml
app_env: development
auth_mode: mock
storage_mode: local
chat_provider: claude
claude_model: claude-sonnet-5
claude_effort: medium
video_provider: openrouter
openrouter_video_model: alibaba/wan-3.0
openrouter_video_enabled: true
duration: 15
credits_per_second: 3
```

Локальный `OPENROUTER_VIDEO_MODEL` синхронизирован с VPS на `alibaba/wan-3.0`. Секреты и остальные environment values при сравнении не выводились и в vault не записывались.

## 5. Что совпадает побайтово

Проверены SHA-256 локального файла и файла в `/opt/storyflow/app`:

| Файл | SHA-256 |
|---|---|
| `apps/api/app/providers/claude.py` | `fb6dc4686a34dd4b56ce8dec2a0ef4d744473cb9407b9a5e211dbfa4ed210131` |
| `apps/api/app/prompts/video_chat/v3.py` | `72ab00eedd57a83ec641cfc4df87a417ff69b3cad96a6e7c7aa5deda4f7441b6` |
| `apps/api/app/creative_direction_playbooks.py` | `167a44632d2d9bf547fdde4a7a98ce8b54a3611394d41656f0cd3fd391a9bd03` |
| `apps/api/app/creative_audit.py` | `6dacebb7674f044fd3af569b6bc6cd2f3626343c6c1e871ab0443a5d72e3e99a` |
| `apps/api/app/services/chat_context.py` | `db5d4ca129c3fa36c99d04bdea5bcf0a5afda4a213dfa62daa10ae92d82819a2` |
| `apps/api/app/services/chat.py` | `d39af6cefe7bf598769acc761c4ae12b480129ab89a7078f947a0ea88fbe864a` |
| `apps/web/features/create/showcase-rail.tsx` | `cb16a548ec72f137d28cab338fb519b4afd33b5306130b932ccf8b7f6572ed02` |
| `apps/web/features/create/preview.tsx` | `b6dec1f05f584198e45ed242ebe1eeaa90ba4ecee9e06b42d63214279672238c` |

Следовательно, основная логика агента, prompt v3, playbooks/retrieval, сохранение audit, vision resize и актуальная showcase-логика одинаковы локально и на VPS.

## 6. Runtime-расхождения устранены 2026-09-12 21:45 CEST

По решению пользователя VPS `/opt/storyflow/app` принят источником истины для текущего runtime. С VPS снят read-only snapshot с исключением `.env*`, database/storage volumes, логов, caches, `.next` и `node_modules`.

Checksum-сравнение нашло два содержательных расхождения runtime-кода:

1. `apps/api/app/main.py` — локально отсутствовали production-настройки имени `generated-video.mp4` и `content_disposition_type="inline"`;
2. `apps/web/features/chat/chat.css` — локально отсутствовали актуальные размеры composer, тёмная рамка и согласованный disabled Send.

Оба файла перенесены из VPS snapshot в локальную копию и повторно проверены через `cmp`: побайтовое совпадение подтверждено. Повторный checksum-аудит `apps/api` и `apps/web` без environment/runtime artifacts не нашёл содержательных отличий production source.

Намеренно сохранены локальные отличия, которые не являются runtime drift:

- более новые и дополнительные unit/e2e tests;
- `scripts/`, включая ручную agent bus и eval-инструменты;
- полная локальная документация и Obsidian vault;
- `.env.local`, `.venv`, `.next`, test results и локальные test assets;
- корневой `docker-compose.yml` для loopback local development.

Фактический VPS compose `deploy/storyflow-vps/docker-compose.yml` совпадает побайтово. Автоматически генерируемый `apps/web/next-env.d.ts` различается только ссылкой на dev/build Next types и не является исходным поведением приложения.

Проверки после синхронизации:

- API: 320 passed, 12 skipped;
- ruff: passed;
- Web unit: 48 passed;
- TypeScript: passed;
- ESLint: passed;
- production build: passed;
- desktop/mobile visual capture: без browser errors; desktop без overflow;
- mobile capture сохранил существующий горизонтальный overflow showcase-галереи, который не создан этой синхронизацией.

## 7. Риск источника истины

VPS `/opt/storyflow/app` не является git worktree. Локальный `/Users/stas/Documents/UGC` отвечает `true` на `git rev-parse`, но `git ls-files` возвращает 0, а все файлы отображаются untracked.

Оставшийся практический риск:

- невозможно доказать полноту deploy через commit SHA;
- после этой синхронизации известных runtime-исправлений только на VPS нет, но новый ручной hotfix снова способен создать drift;
- deploy из локальной папки без предварительного checksum-сравнения способен откатить будущий VPS hotfix;
- backup не заменяет историю изменений и reviewable diff.

VPS принят текущим источником истины, а локальная runtime-копия приведена к нему. Для воспроизводимой истории всё ещё нужен tracked baseline: импортировать подтверждённый VPS snapshot и локальные инструменты в проверяемый worktree, зафиксировать baseline commit и затем деплоить из него.

## 8. Текущая operational truth

Пока единый git baseline не создан:

1. VPS `/opt/storyflow/app` является текущим источником истины для runtime;
2. перед любым deploy сравниваются локальные файлы и `/opt/storyflow/app`;
3. локальная папка не считается более новой без явного решения;
4. нельзя массово синхронизировать каталог в одну сторону;
5. secrets не копируются и не записываются в vault;
6. любые VPS-изменения проходят отдельный preflight и явную авторизацию.

### Frontend deploy 2026-09-12 20:47 CEST

На VPS синхронизированы `workspace.tsx`, `preview.tsx` и `globals.css`, затем пересобран и перезапущен только сервис `web`. Новый fluid overlay покрывает область от `AI Chat / Auto` до `Production prompt` во время Auto Planning и video generation. Удалены `VIDEO PREVIEW`, `Product Demo / 15s`, оба вторичных пояснения и тёмная подложка статуса. В production bundle присутствуют только короткие статусы `Creating your concept…` и `Generating your video…`. Контейнер после перезапуска отвечает HTTP 200.

### Frontend deploy 2026-09-12 20:57 CEST

В desktop-сайдбар добавлена серебристая ribbon-графика из пользовательского ассета. Исходный PNG 2172×724 и 148 КБ преобразован в прозрачный WebP 600×200 и 17,9 КБ. Элемент не перехватывает ввод, скрывается в collapsed/mobile состояниях. Пересобран и перезапущен только `web`; ассет внутри контейнера отвечает HTTP 200.

### Catalog deploy 2026-09-12 21:05 CEST

Backend больше не объединяет 8 generative-шаблонов с файловым Remotion-manifest; mock-каталог приведён к тому же составу. Production-таблица `templates` проверена до deploy и уже содержала только нужные 8 ID, поэтому миграция или удаление строк не выполнялись. После пересборки `api`, `worker` и `web` живой backend возвращает ровно 8 generative-записей; API OpenAPI и `/templates` отвечают HTTP 200.

### Frontend deploy 2026-09-12 21:20 CEST

Серебристая ribbon-графика увеличена до 720 CSS px, смещена влево и обрезается контейнером сайдбара. Пользователь видит только крупный фрагмент изгиба, а не всю длину исходника. Для элемента явно снято глобальное ограничение `max-width: 100%`. Пересобран и перезапущен только `web`; HTTP 200, локальный и VPS CSS совпадают по SHA-256.

### Product Look Studio deploy 2026-09-13 16:50–17:10 CEST

На VPS последовательно задеплоен новый frontend-маршрут `/try-on` и пункт Try On в
сайдбаре. Синхронизировались только конкретные файлы `apps/web` и пользовательские
ассеты `apps/web/public/try-on/`; массового local→VPS sync не было.

Финальное состояние после трёх web-only обновлений:

- Product Look Studio повторяет утверждённый desktop-макет и имеет responsive
  одноколоночную mobile-компоновку;
- блок `Background` удалён;
- photo output явно разделён на `1 hero photo` и `4 angles`;
- прямой `Generate Video Instead` сохранён одновременно с photo-flow;
- `Add products to get started` удалён;
- в hero-шаге `Turn the best look into a video` используется `hero-video.mp4`:
  autoplay, loop, muted, playsInline, без controls, play-overlay и таймкода.

Каждый раз пересобирался и пересоздавался только контейнер `web`; `api`, `worker`,
`postgres` и `redis` оставались running. Последняя внутренняя проверка: `/try-on` —
HTTP 200, MP4 — HTTP 200, `video/mp4`, 3 921 230 bytes. Production HTML содержит
`autoPlay`, `loop`, `muted`, `playsInline` и не содержит `controls` в hero-video tag.
Публичный URL без Basic Auth по-прежнему возвращает ожидаемый 401.

## 9. Визуальные доказательства

- `docs/verification/creative-director/`
- `docs/verification/developer-generation-preview/`
- `docs/verification/auto-planning-loader/desktop-1440.png`
- `docs/verification/auto-planning-loader/mobile-390.png`
- `docs/verification/showcase-autoplay/desktop-1440.png`
- `docs/verification/showcase-autoplay/mobile-390.png`
- `docs/verification/sidebar-collapsed-1440.png`
- `docs/verification/sidebar-expanded-1440.png`
- `docs/verification/sidebar-silver-ribbon/desktop-1440.png`
- `docs/verification/sidebar-silver-ribbon/mobile-390.png`
- `docs/verification/result-placement/`
