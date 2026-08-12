# Domain Docs

How the engineering skills should consume this repo's domain documentation when exploring the codebase.

> 2026-08-11 修订：本仓库是 **single-context**（无 `src/<context>/` 分目录），domain.md 的 multi-context 分支不适用——已删除对应文案并明示 File structure 单 context 形态。

## Before exploring, read these

- **`docs/CONTEXT.md`** —项目语境、glossary、版本定位（v0.1 / v0.2 / v0.3）、TODO 列表
- **`docs/adr/`** — ADRs touching the area you're about to work in
- **`docs/use-cases/`** — only when the work is tied to a specific v0.2+ use case (e.g. `text-target-hard-signal.md`)

If `CONTEXT.md` doesn't exist, **proceed silently**. The `/domain-modeling` skill creates it lazily when terms or decisions actually get resolved.

## File structure

Single-context repo (this repo) — current state after 2026-08-11 arch-pivot:

```
/
├── AGENTS.md                     (Agent Working Agreement)
├── docs/
│   ├── CONTEXT.md                (project glossary + version anchor)
│   ├── agents/
│   │   ├── issue-tracker.md      (where issues live)
│   │   ├── domain.md             (this file)
│   │   └── triage-labels.md      (only if external issues flow)
│   ├── adr/                      (5 ADR files: ADR-001, 002, 003.5, 004, 005)
│   ├── specs/                    (version-specific spec docs)
│   │   └── v0.1-skeleton-spec.md
│   └── use-cases/                (v0.2+ exploration scope, e.g. text-target-hard-signal.md)
└── src/                          (empty for v0.1; v0.2+ scripts land here)
```

## Use the glossary's vocabulary

When your output names a domain concept (in an issue title, a refactor proposal, a hypothesis, a test name), use the term as defined in `docs/CONTEXT.md`. Don't drift to synonyms the glossary explicitly avoids.

If the concept you need isn't in the glossary yet, that's a signal — either you're inventing language the project doesn't use (reconsider) or there's a real gap (note it for `/domain-modeling`).

## v0.1 anchor reminder

`docs/CONTEXT.md` §适用边界 defines:

- **v0.1 = A-class target domain** (single file / hard metrics / no multi-agent)
- **v0.2 = A + C exploration + meta layer execution**
- **v0.3 = C-class deep cultivation**

When implementing tickets in v0.1, **do not assume C-class skeleton components are instantiated** (see ADR-001 — 4 core + 3 extension). If a v0.1 ticket demands Worktrees / Plugins / Sub-agents dispatcher, that ticket belongs to v0.2.

## Flag ADR conflicts

If your output contradicts an existing ADR, surface it explicitly rather than silently overriding:

> _Contradicts ADR-XXXX (placeholder — replace with real ADR number when used; example only)_
