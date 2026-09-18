# Billing, Auth и Admin Analytics — план запуска

Актуальный полный план хранится в одном источнике:

- `docs/plans/BILLING_AUTH_ADMIN_LAUNCH_PLAN_RU_20260912.md`

Ключевое решение: сохранить существующий FastAPI + Supabase Auth + Stripe backend, сначала включить реальную identity и доказать двухпользовательскую изоляцию, затем подключить Stripe. Для готовой внутренней статистики использовать Stripe/Supabase Dashboards и отдельный self-hosted Metabase с read-only доступом к analytics views.

Порядок: real Supabase Auth → ownership tests → Stripe test mode → payment projection → Metabase → live Stripe.
