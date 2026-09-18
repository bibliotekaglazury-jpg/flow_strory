# Storyflow UGC — V2 audit pointer

Этот Obsidian-файл больше не является второй копией аудита.

**Source of truth:** `../../docs/audits/UGC_CREATIVE_COMPETITOR_PLAYBOOK_AUDIT_20260911_RU_V2.md`

Причина: прежняя версия была побайтовой копией `docs/audits/...V2.md`, поэтому два файла гарантированно разъехались бы при следующей правке. Все изменения вносить только в `docs/audits/UGC_CREATIVE_COMPETITOR_PLAYBOOK_AUDIT_20260911_RU_V2.md`.

Документ по ссылке фиксирует исследование и первоначальный blueprint. Он не описывает текущий runtime после реализации. Актуальная архитектура: [[04_Creative_Director_Runtime_Architecture]]. Актуальный план: [[03_Next_Implementation_Plan]].

Что реализовано после аудита:

- 8 `FORMAT_PLAYBOOKS`, 45 уникальных structures, 13 niches/overlays и 10 consumption models;
- adaptive tag/keyword retrieval возвращает 6 или 10 reference cards;
- runtime сохраняет ровно 3 Claude candidates;
- product/person separation, narrative payoff и deterministic validators;
- audit сохраняется в recipe planning и server log;
- внешний research pipeline, 80–150 карточек и больше трёх candidates остаются отдельными future milestones;
- retrieval работает без vector DB и embeddings.
- YouTube/TikTok/Meta research требует отдельной ToS/legal проверки.
