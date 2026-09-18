# Storyflow UGC — индекс проекта

Обновлено: 2026-09-13, Europe/Warsaw.

## Актуальное состояние

- [[01_Project_State]] — что уже работает, текущий продуктовый поток, ограничения и проверки. **Начни отсюда после перезапуска** — там раздел «Если контекст обнулился».
- [[09_Try_On_And_Bulk_Upload]] — bulk upload, try-on backend и новый Product Look
  Studio `/try-on`: что задеплоено, как устроен frontend и какая API-интеграция ещё
  не выполнена.
- [[04_Creative_Director_Runtime_Architecture]] — устройство Claude Creative Director, промпты, playbooks, retrieval, quality gate и стоимость.
- [[05_Local_VPS_State_and_Drift]] — состояние локальной копии и VPS, совпадения, расхождения и риски источника истины.
- [[06_Claude_Codex_Agent_Bus]] — ручная шина обмена backend-комментариями между Claude и Codex.
- [[07_Competitive_Gap_Audit_No_Phase2]] — актуальная матрица продуктовых разрывов с Predis, Topview, Arcads и Creatify; Phase 2 исключена.
- [[08_Billing_Auth_Admin_Launch_Plan]] — план реальной авторизации, Stripe billing, изоляции пользователей и готовой admin-аналитики.
- [[03_Next_Implementation_Plan]] — завершённые этапы и следующий порядок работ.

## Исследования и история решений

- [[02_Competitor_Playbook_Audit_RU_V2]] — указатель на актуальный подробный аудит конкурентов.
- [[02_Competitor_Playbook_Audit_RU]] — предыдущая русская версия.
- [[02_Competitor_Playbook_Audit]] — исходная версия аудита.

## Главные исходные документы

- `docs/BUILD_BRIEF.md`
- `docs/PRODUCT_SPEC.md`
- `docs/API_CONTRACTS.md`
- `docs/DECISIONS.md`
- `docs/audits/UGC_CREATIVE_COMPETITOR_PLAYBOOK_AUDIT_20260911_RU_V2.md`
- `docs/audits/CREATIVE_DIRECTOR_EVAL_20260912.md`

Vault находится внутри общего проекта `/Users/stas/Documents/UGC`, поэтому Claude/Codex видят его при работе из корня проекта. Эти заметки описывают фактическое состояние, но не заменяют код, тесты и runtime-проверку VPS.
