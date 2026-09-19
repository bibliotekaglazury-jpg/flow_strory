# Найденный код Przelewy24

Снимок локальных исходников от 2026-09-19 для переноса в новое приложение. Это архив существующей реализации, а не готовый проверенный платёжный модуль. Исходные файлы проекта не изменены. Production/VPS не проверялся, платежи не запускались.

Источник: локальный worktree `booster-engine`, HEAD `99de6bfddf386566361011d66cb63d397c45c1d6`. В рабочем дереве были незакоммиченные изменения, в том числе в PHP интеграции. В архив попало текущее содержимое файлов, а не только HEAD. Относительные пути, SHA-256 и изменения при экспорте записаны в `manifest.json`.

## Использование в Storyflow

Этот каталог является reference-пакетом и не подключён к рабочему Stripe billing. Перед интеграцией P24 нужно исправить перечисленные ниже проблемы и адаптировать реализацию к моделям заказов, кредитов и идемпотентности Storyflow.

Настоящие sandbox-данные хранятся только в корневом `.env` локального checkout и исключены через `.gitignore`. В Git находится только `.env.example` с пустыми значениями. Не переносите значения из `.env` в код, тесты, документацию или frontend.

## Что переносить

| Файл в source/ | Назначение |
| --- | --- |
| api/p24-register.php | Основной общий endpoint регистрации; SHA-384, Basic Auth, token, redirectUrl, сохранение pending заказа |
| api/srm-payment.php | Альтернативный SRM checkout: планы, расчёт НДС, выбор метода оплаты |
| api/srm-payment-callback.php | Уведомление P24, проверка платежа, paid/verify_failed, письма и аналитика |
| api/_security.php | Загрузка конфигурации, CORS, rate limiting, honeypot |
| api/posthog.php | Зависимость callback для аналитики; встроенный ключ заменён на POSTHOG_API_KEY |
| api/order-email.php | Отдельная отправка заказа/писем из checkout; не является подтверждением платежа |
| api/p24-notify.php | Отключённый legacy endpoint, возвращает HTTP 410 |
| srm-app/backend/p24_manager.py | Python requests: calculate_sign, create_transaction, verify_transaction |
| srm-app/backend/db_manager.py | Схема SQLite и соединение с БД Python приложения |
| srm-app/saas_app_v2/state.py | State.create_payment: выбор плана, pending в БД, redirect |
| srm-app/saas_app_v2/pages/payment.py | UI оплаты Reflex |
| srm-app/saas_app_v2/saas_app_v2.py | payment_webhook и POST /api/payment/status |
| js/ai-booster.js, js/ai-booster-v2.js | Checkout AI Visibility Booster |
| seo-redirect-manager.html | Checkout SRM |
| seo-pogotowie/index.html | Checkout SEO Pogotowie |
| apps/llm.txt/landing/index.html | Checkout LLM.txt |
| apps/index-guard/landing/index.html | Checkout Index Guard |

HTML, State и файлы приложения включены целиком для контекста; они содержат и код, не относящийся к оплате. Зависимости всего старого приложения в архив не включены.

## Существующий поток

Checkout → POST `/api/p24-register.php` → P24 `/api/v1/transaction/register` → `redirectUrl` → страница P24 → отдельное уведомление на `/api/srm-payment-callback.php` → проверка → изменение статуса заказа.

В PHP `amount` принимается в PLN и переводится в гроши; Python принимает сумму уже в грошах. PHP сохраняет заказы в `/home/u285877296/srm_orders`, callback пишет логи в `/home/u285877296/logs`. Эти пути относятся к старой реализации и не подтверждают расположение текущего production.

PHP требует cURL и переменные `P24_MERCHANT_ID`, `P24_POS_ID`, `P24_API_KEY`, `P24_CRC`; `P24_BASE_URL` без `/api/v1`. Без явного base URL код выбирает production. `.env.example` содержит только пустые значения и sandbox URL; PHP сам по себе этот файл не загружает. `_security.php` читает окружение или внешний `booster-engine-secrets.php`, который не включён.

Python manager зависит от `requests`; обвязка использует Reflex, Request/JSONResponse и SQLite. Конфигурация manager сейчас пустая, SANDBOX=True; URL в State указывают localhost.

## Обнаруженные проблемы перед переносом

1. PHP callback отправляет POST на `/transaction/verify`, тогда как официальная спецификация описывает PUT. Python manager использует PUT.
2. PHP callback считает входящую подпись по полям запроса verify. Для уведомления документация задаёт другой набор и порядок: merchantId, posId, sessionId, amount, originAmount, currency, orderId, methodId, statement, crc. Требуется отдельная проверка подписи уведомления.
3. PHP регистрация принимает цену из браузера (`amount` / `netto`). Для нового приложения цену нужно определять на сервере по продукту/плану и сверять сумму, валюту и владельца с сохранённым заказом до выдачи доступа.
4. Callback формирует путь к заказу из sessionId; нужны строгая валидация идентификатора и безопасное хранилище. Повторные уведомления и параллельные запросы должны обрабатываться идемпотентно. Сейчас повторная ошибка verify может перезаписать paid статус.
5. PHP callback возвращает ok также при отсутствии локального заказа или неуспешной проверке. Сохранение заказа и ошибки записи требуют явной обработки; доступ нельзя выдавать на основании `payment=success` в адресе браузера.
6. Python State и webhook используют `payments.details`, но обе найденные CREATE TABLE payments в db_manager.py этот столбец не создают. Ошибки БД местами подавляются. В файле регистрации webhook есть вызов p24_manager, но импорт этого модуля в нём не найден.
7. Домены возврата, callback, CORS, почтовые адреса, тарифы, product-specific логика, пути файлов и аналитика привязаны к старому приложению. Их нужно адаптировать.

Документация, сверенная 2026-09-19: https://developers.przelewy24.pl/yaml/en_documentation_1.0.yaml . Замечания 1–2 основаны на ней; остальные — на найденных исходниках. Исправления в исходную бизнес-логику при экспорте не вносились.

## Другие найденные файлы

Три копии p24_manager.py побайтово совпадают с версией в этом архиве:

- `local/NEW_UI/saas_app_v2/backend/p24_manager.py`
- `local/NEW_UI/saas_app_v2_LATEST/saas_app_v2/backend/p24_manager.py`
- `local/NEW_UI/VERIFIED_BACKUP/saas_app_v2/backend/p24_manager.py`

Рядом с ними есть собственные State, payment UI и webhook. Их эквивалентность не подтверждена; в архив включена обвязка из текущего workspace.

`api/p24-test.php` — старый sandbox testAccess скрипт. Он не включён в Git; найденные в нём sandbox-значения перенесены только в игнорируемый локальный `.env`. `js/ai-booster.min.js` — найденный минифицированный frontend; для чтения включены обычные JS. Упоминания P24 также есть в `srm-app/llm.txt`, `product.html`, `apps/llm.txt/instrukcja.html`, `regulamin.html`, `polityka-prywatnosci.html`; это документация/контент, а не отдельный API-клиент.

## Проверка источников и архива

- CBM MCP exposed: yes; CLI fallback used: no.
- CBM project: Users-stas-Documents-CEREBRO_VPS_SOURCE_MIRROR_CLEAN; 105181 nodes, 186244 edges.
- Выполнены list_projects, search_graph query `przelewy24 p24 przelew`, search_graph name_pattern `.*[Pp](24|rzelew).*`, detect_changes.
- CBM не вернул файлов/символов по этим запросам; detect_changes: 0 changed files. Это результат для индекса Cerebro, не для рабочего дерева SHOPER.
- Далее выполнен файловый поиск в текущем workspace, Documents, NEW_UI и Cerebro mirror. В индексе нет текущего SHOPER workspace. Поиск не доказывает отсутствие иных реализаций на других дисках или серверах.
- Экспорт проверяется по manifest.json; это проверка целостности снимка, не интеграционный тест P24.
- Перед добавлением в Storyflow также проверен CBM-проект `Users-stas-Documents-UGC`: запрос `payments billing environment secrets integration` и `detect_changes`. Найдена текущая Stripe-реализация в `apps/api/app/services/billing.py`; поэтому P24 оставлен изолированным reference-пакетом.
