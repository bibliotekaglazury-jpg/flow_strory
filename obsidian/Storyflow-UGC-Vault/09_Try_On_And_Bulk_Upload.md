# Bulk upload + Try On / Product Look Studio — статус на 2026-09-13

Backend bulk upload и примерки задеплоен. Отдельный frontend-модуль **Product Look
Studio** также задеплоен на `https://ugc.cerebroos.io/try-on` и доступен через пункт
**Try On** между Create и Templates.

Важно различать два слоя:

1. действующий backend `POST /api/assets/bulk` и `POST /api/try-on`;
2. новая страница Product Look Studio — пока frontend-макет с локальными
   интерактивными состояниями, ещё не подключённый к этим endpoints, списанию
   кредитов, проектам или истории.

## Зачем

Модуль предназначен для e-commerce: пользователь загружает до пяти предметов,
может добавить модель, выбирает сцену и формат, а затем получает один hero-кадр,
четыре согласованных ракурса либо сразу запускает создание видео.

## Backend, который уже работает

### Bulk upload

- `LOOK_SIZE = 5` — общая константа в `apps/api/app/schemas.py` и
  `packages/contracts/index.ts`.
- `POST /api/assets/bulk` принимает несколько файлов одним запросом.
- Фронтовые API-адаптеры уже содержат `assets.uploadMany`; существующий Create-flow
  использует bulk upload.

### Try-on preview

- `OpenRouterImageProvider` использует `google/gemini-3-pro-image`.
- `MockImageProvider` возвращает валидную PNG для dev и тестов.
- `apps/api/app/prompts/tryon.py` содержит фиксированные ракурсы `front`,
  `three_quarter`, `back`, `detail`.
- `apps/api/app/services/try_on.py` выполняет синхронную image-generation отдельно
  от видеоочереди Quote/Generation/Job/worker.
- `POST /api/try-on` вызывает `try_on.preview()`.
- Production env на VPS содержит `IMAGE_PROVIDER=openrouter`,
  `OPENROUTER_IMAGE_MODEL=google/gemini-3-pro-image` и
  `IMAGE_CREDITS_PER_GENERATION=1`.

Существующая условная `try-on-panel.tsx` на странице Create остаётся отдельным
интерфейсом: она появляется при наличии модели и двух или более товаров.

## Новый Product Look Studio

Основные файлы:

- `apps/web/app/try-on/page.tsx`;
- `apps/web/features/try-on/product-look-studio.tsx`;
- `apps/web/components/shell.tsx`;
- блок `Product Look Studio` в `apps/web/app/globals.css`;
- ассеты в `apps/web/public/try-on/`.

### Текущий экран

- отдельный пункт **Try On** в сайдбаре;
- instructional hero `Products → multiple angles → video`;
- загрузка до пяти product images и необязательной модели;
- выбор `Studio / Lifestyle / Outdoor / Custom`;
- форматы фото `9:16 / 1:1 / 4:5 / 16:9`;
- блок `Background` удалён по решению пользователя;
- два photo outputs:
  - `1 hero photo` — один ключевой кадр;
  - `4 angles` — Front, ¾, Back, Detail; выбран по умолчанию и помечен Recommended;
- отдельный гибридный маршрут `Generate Video Instead`: пользователь может не
  создавать промежуточные фотографии и сразу перейти к видео;
- подпись `Add products to get started` удалена как дублирующая upload-блок;
- CTA фотографий меняется между `Generate hero photo` и `Generate 4 photos`.

### Hero-видео

В третьем шаге `Turn the best look into a video` статическая заглушка заменена
пользовательским `hero-video.mp4` (исходный файл `try on.mp4`). Видео имеет
`autoplay`, `loop`, `muted`, `playsInline`, `preload="auto"`; controls, play-overlay
и фиктивный таймкод отсутствуют.

## Подключение к API (2026-09-13, задеплоено на прод вечером того же дня)

Проверено на проде: `GET /api/assets?role=person` → 200 (только свои фото моделей),
`role=product` → 422; 4:5 принимается схемой и провайдером; `/try-on` отдаёт подключённую
версию без макетных текстов и захардкоженного баланса; в логах чисто.

**Второй деплой, 2026-09-13 ~21:00:** миграции `0006` (`assets.source`) и `0007`
(`look_projects`, `look_photos`), библиотека только из примерочной, инструкция `tryon-v2`,
Clear imports, папки. Перед этим бэкап базы
`/opt/storyflow/backups/ugc-before-0007-202609132052.dump`. На проде: версия миграций
`0007`; `GET /api/look-projects` → 200 `[]`; библиотека `role=person&source=try_on` → 200
`[]` (старые 11 фото из Create скрыты); без `source` → 422; чужой/несуществующий проект →
404; логи чистые.

**Ручное восстановление папки (по разрешению пользователя на одну запись):** 5 фото,
снятых в 20:19–20:22 до выкатки папок, сложены в проект `4abc2009-8162-4bf1-8e70-e6df890b6cd4`.
Входы восстановлены по времени загрузки: колье (главный), браслет, шляпа, платье + модель;
9:16, Studio; подписи Front, ¾, Back, Detail, ¾ (пятый кадр проверен визуально). Дата
папки — время первого кадра. Проверено через API: 1 папка, 5 фото, модель и 4 товара.

Страница `/try-on` теперь работает на реальных эндпоинтах:

- товары — `assets.uploadMany` (`POST /api/assets/bulk`), модель — `assets.upload(file, "person")`;
- `1 hero photo` — один `POST /api/try-on`; `4 angles` — сначала Front, затем ¾/Back/Detail
  пересъёмкой Front через `baseAssetId`, чтобы весь набор был одним образом;
- у выбранного фото — Another angle и Download;
- `Generate Video Instead` — существующий поток `chat.create → send → apply →
  credits quote → generations.create → pollGeneration`, видео показывается на странице и
  попадает в обычную историю;
- реальный баланс кредитов вместо захардкоженного числа;
- `4:5` разрешён для фото (`TryOn.aspectRatio`, `OpenRouterImageProvider.RATIOS`,
  `PhotoAspectRatio` в contracts), для видео отклоняется на клиенте с понятным текстом.
- **Меняется только импортированное** (`prompts/tryon.py`, `tryon-v2`): живой тест показал,
  что модель в брюках получила платье, а её сумка — другую сумку. Причина — фраза
  «worn together as one complete outfit», модель достраивала наряд сама. Теперь: всё,
  что человек носит на фото, остаётся как есть; поставленный товар заменяет только вещь
  того же вида, остальное не трогается и ничего не добавляется. Это инструкция для
  генератора, программно результат не проверяется.
- Видимая кнопка **Clear imports** сбрасывает товары и модель, чтобы загрузить новый набор.

Проверки: API try_on+bulk 11 passed, web vitest 56 passed, tsc/eslint чисто, Playwright
`product-look-studio.spec.ts` 2 passed + `try-on.spec.ts` 1 passed (API замокан),
консоль без ошибок, desktop/mobile скриншоты просмотрены.

## Что всё ещё не сделано

- Фото без модели (product-only) — бэкенд требует фото человека, если нет `baseAssetId`;
  на странице кнопка фото заблокирована без модели и это прямо написано.
- Идемпотентность `try-on` защищает только списание кредитов, но не повторный платный
  вызов провайдера.
- ~~Фото пропадают после перезагрузки~~ — сделано: проекты-папки (миграция `0007`,
  таблицы `look_projects` и `look_photos`). Правило пользователя: одна генерация = один
  проект = одна модель = одна папка; вторая генерация — вторая папка. Эндпоинты
  `POST/GET /api/look-projects`, `GET /api/look-projects/{id}`; `POST /api/try-on` принимает
  `projectId` (чужой проект отклоняется до платного вызова). На странице: сразу после
  генерации результат по-прежнему снизу; ниже блок «Your looks» — клик по папке открывает её
  фото и восстанавливает модель, товары, сцену и формат. Пустой проект (генерация упала) не
  показывается. Видео в проекты пока не входит — оно в обычной истории Library.
- ~~«Choose from library» без выбора~~ — сделано: `GET /api/assets?role=person&source=try_on`
  отдаёт только фото модели, загруженные **в примерочной** (новые сверху), выбор ставит
  модель. Решение пользователя: загрузки со страницы Create остаются в её истории, но в
  примерочной не показываются; отдельного каталога моделей не делаем. Реализовано полем
  `assets.source` (миграция `0006`): старые фото метки не имеют и в библиотеку примерочной
  не попадают, ничего не удаляется. Разделение «по клиентам» заработает само после включения
  реальной авторизации — сейчас mock auth, все запросы идут от одного `development-user`.
- Видео строится из исходных товаров и модели, не из выбранного фото.

## Проверки и deploy

- Targeted ESLint: passed.
- TypeScript: passed.
- Next.js production build: passed.
- Vitest: 52 passed.
- Desktop/mobile visual QA: `design-qa.md`.
- VPS runtime: `netcup-cerebro:/opt/storyflow/app`.
- Пересобирался и перезапускался только сервис `web`; API и worker не менялись.
- Production HTML `/try-on` возвращает 200 внутри контейнера.
- `hero-video.mp4` возвращает 200, `video/mp4`, 3 921 230 bytes.
- В production HTML подтверждены video-атрибуты autoplay/loop/muted/playsInline и
  отсутствие `controls`.

## Решения, которые больше не открыты

- ~~Деплоить ли bulk upload + try-on backend~~ — задеплоено.
- ~~Добавлять ли отдельный пункт в сайдбар~~ — добавлен Product Look Studio.
- ~~Один кадр или несколько~~ — доступны оба режима: 1 hero и 4 angles.
- ~~Фотографии перед видео обязательны~~ — нет, сохранён прямой video path.
- ~~Показывать Background~~ — нет, блок удалён.

## Связанные заметки

- [[01_Project_State]]
- [[03_Next_Implementation_Plan]]
- [[05_Local_VPS_State_and_Drift]]
