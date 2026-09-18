# Product understanding verification — 2026-09-10

Implementation extends the existing chat and asset services, without frontend layout changes or a second agent service.

- Owned product/person images are validated, resized (at most 1600px), stripped of EXIF by re-encoding, and attached to Codex using official CLI --image, including resume.
- Public page text and OG photography use existing bounded SSRF-protected downloads. Codex interprets evidence and may use built-in live web research. No category rules or form.
- Initial URL resolution imports available page photography through owned storage and returns it beside product metadata. The frontend adopts it only when no product image was uploaded. Apply never refetches the remote page.
- Original compiler blanket advertising-claims suffix removed. Creative direction remains model-led, with sourced facts distinguishable from suggestions.
- Real CLI rejected the previous schema: defaulted domain fields were missing from required. Strict transport schema now requires all properties; domain compatibility remains unchanged.

Verification:

- Backend suite: 109 passed, 11 PostgreSQL integration tests skipped without their dedicated test setup. Focused chat/context follow-up: 22 passed. Ruff passed.
- Real Codex ChatGPT login confirmed. Real API upload/chat detected woman, pale cosmetic jar, unreadable label and home background. A follow-up through resume produced a schema-valid 15-second 9:16 recipe with matching pl-PL dialogue. Initial test assertion expected pl exactly; corrected to accept the documented BCP-47 regional variant. No video generation invoked.
- Live public URL https://www.apple.com/airpods-pro/ supplied 16,840 characters of evidence and one valid image. Mock tests verify URL failure, image data, strict schema, resumed attachments, search event handling, URL image import/ownership and no job creation during Apply.
- API restarted locally with existing Codex launcher. No frontend code changed, so no new visual comparison is claimed. Existing upload/URL/Send/Apply contracts are reused.
- CBM MCP available; initial project listing used CLI, subsequent search_graph/detect_changes used MCP. Verified project Users-stas-Documents-UGC, root /Users/stas/Documents/UGC, 2,042 nodes / 4,896 edges. Query: CodexLocalAdapter chat product context. Returned resolve_product, public_target, download_public, ChatContext and related route symbols. detect_changes empty (repository files currently untracked).

Limits: reading occurs when a message is sent, not automatically on upload. Inaccessible/JS-only pages may need another source or an uploaded image. Live web-search invocation was not independently exercised; its configuration and event handling were tested. Uploaded video is not analyzed frame-by-frame. Video generation remains independently gated by worker and externally reachable asset storage; no tunnel or additional paid video call was authorized or launched by this change.
