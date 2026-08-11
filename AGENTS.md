# recursive-tune · Agent Working Agreement

> Created 2026-08-11 via `/setup-matt-pocock-skills`.

## Agent skills

### Issue tracker
GitHub Issues at https://github.com/Fectivnfy112357/recursive-tune (default branch `main`). Use the `gh` CLI for all ops. See `docs/agents/issue-tracker.md`.

### Domain docs
Single-context layout: `docs/CONTEXT.md` (glossary) + `docs/adr/` (ADRs). See `docs/agents/domain.md`.

### Triage labels
Not configured as a full taxonomy. The `triage` skill is installed but the repo currently has no inbound external-issue flow (only self-authored specs/tickets via `to-spec` → `to-tickets`). `triage` will use its built-in defaults if ever invoked. Add `docs/agents/triage-labels.md` only when external issues actually start arriving.

**Note on `ready-for-agent`**: the `/to-spec` skill applies this label directly on the issue it publishes — that one label is owned by `to-spec` and does not require triage-labels.md to be set up first. Anything beyond that label belongs to the triage taxonomy and follows the rule above.
