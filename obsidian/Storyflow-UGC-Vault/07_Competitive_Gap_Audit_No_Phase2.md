# Конкурентный gap-аудит без Phase 2

Единый подробный документ:

`docs/audits/UGC_COMPETITIVE_GAP_AUDIT_PHASE1_RU_20260912.md`

## Решение

Phase 2 исключена: не строим scraper, автоматический research рекламных библиотек, YouTube/TikTok/Meta integrations, embeddings или vector DB.

## Следующая продуктовая пятёрка

1. Показать пользователю три уже создаваемые concept candidates до запуска платного видео.
2. Добавить deterministic captions, headline, CTA и end card.
3. Реализовать Brand Kit и сохранённый Product Profile.
4. Добавить выбор и preflight reference materials до резерва credits.
5. Обеспечить проверенный 1080p export.

Сначала остаются обязательными tracked git baseline, устранение local/VPS drift и production hardening.

Связанные заметки: [[03_Next_Implementation_Plan]], [[04_Creative_Director_Runtime_Architecture]], [[05_Local_VPS_State_and_Drift]].

