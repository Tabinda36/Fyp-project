# .claude/ — Claude Code project configuration for ALVIX

```
.claude/
├── README.md                      this index
├── settings.json                  shared permissions (safe commands allowed; .env reads denied)
├── agents/                        project subagents
│   ├── django-backend-engineer.md   models, migrations, views, DRF API, tests
│   ├── react-frontend-engineer.md   React/Vite pages, 1:1 template ports
│   ├── ui-parity-reviewer.md        read-only diff of template vs React page
│   └── ai-services-engineer.md      Gemini, curriculum, slides, grading, recommendation
├── skills/                        reusable workflows (SKILL.md each)
│   ├── port-template-to-react/      step-by-step page port with zero UI change
│   ├── add-api-endpoint/            DRF conventions: auth, CSRF, ownership, shape, tests
│   ├── gemini-ai-feature/           prompt → call → parse → fallback → log → persist → test
│   └── run-dev-stack/               install/run/test backend + frontend on Windows
└── docs/                          project documentation (audited 2026-11-14)
    ├── architecture.md              stack, folder structure, current vs target flow
    ├── data-model.md                every model, relationships, scoring settings
    ├── url-map.md                   every URL → view → template, auth level
    ├── ai-services.md               every service module, external APIs, lifecycle
    ├── frontend-ui-inventory.md     CDN libs, theme tokens, layouts, per-page forms/JS, player API
    ├── known-issues.md              verified bugs & risks with severity
    └── react-migration-plan.md      target structure, phases, page checklist, risks
```

Personal overrides go in `.claude/settings.local.json` (git-ignored by Claude Code).
