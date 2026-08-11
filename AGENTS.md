# recursive-tune · Agent Working Agreement

> Created 2026-08-11 via `/setup-matt-pocock-skills`.

## Agent skills

### Issue tracker
GitHub Issues at https://github.com/Fectivnfy112357/recursive-tune (default branch `main`). Use the `gh` CLI for all ops. See `docs/agents/issue-tracker.md`.

### Domain docs
Single-context layout: `docs/CONTEXT.md` (glossary) + `docs/adr/` (ADRs). See `docs/agents/domain.md`.

### Triage labels
Not configured. The `triage` skill is installed but the repo currently has no inbound external-issue flow (only self-authored specs/tickets via `to-spec` → `to-tickets`). `triage` will use its built-in defaults if ever invoked. Add `docs/agents/triage-labels.md` only when external issues actually start arriving.
