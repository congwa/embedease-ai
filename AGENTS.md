# Repository Guidelines

## Project Structure & Module Organization
This repo is split into `frontend/` and `backend/`. `frontend/` is a Next.js 16 app: keep routes in `app/`, reusable UI in `components/`, helpers in `lib/`, state in `stores/`, the widget in `embed/`, and SDKs in `packages/`. `backend/` is a FastAPI + LangGraph service: use `app/routers/` for APIs, `app/services/` for business flows, `app/repositories/` for persistence, `app/schemas/` and `app/models/` for contracts, and `app/core/` for shared config. Shared docs and deployment assets live in `docs/` and `docker/`.

## Build, Test, and Development Commands
- `cd frontend && pnpm dev`: start the Next.js app on port 3000.
- `cd frontend && pnpm lint`: run the frontend ESLint config.
- `cd frontend && pnpm build && pnpm build:embed`: build the main UI and the embed bundle.
- `cd backend && uv sync`: install backend dependencies into the local `uv` environment.
- `cd backend && uv run uvicorn app.main:app --reload --port 8000`: run the API locally.
- `cd backend && uv run pytest`: run backend tests.
- `cd backend && uv run ruff check --fix`: apply Python lint fixes.

## Coding Style & Naming Conventions
Use 2-space indentation in TypeScript/TSX and 4 spaces in Python. Keep React components and exported types in `PascalCase`, hooks in `camelCase` with a `use` prefix, and Python modules, functions, and test files in `snake_case`. Follow the existing `@/` import alias in the frontend. Python linting runs through Ruff with a 100-character target; frontend linting uses `frontend/eslint.config.mjs`. Every file and method should include business-focused comments or docstrings explaining purpose, constraints, or usage context.

## Testing Guidelines
Backend tests live under `backend/tests/` and follow `test_*.py` naming, grouped by area such as `tests/services/` or `tests/routers/`. Use markers like `-m integration`, `-m slow`, and `-m webtest` when scoping runs. Integration tests require `LLM_API_KEY` and `LLM_PROVIDER`. The frontend currently relies on linting; for UI changes, include verification steps in the PR.

## Commit & Pull Request Guidelines
Recent history favors concise Conventional Commit prefixes such as `feat:`, `chore:`, and `docs:` with short Chinese summaries. Prefer `type: summary`, for example `feat: 优化客服工作台会话切换`. PRs should describe scope, risk, commands run, related issues, and screenshots for `frontend/` changes.

## Agent-Specific Instructions
For code search, use `fast-context` MCP first; fall back to `rg` only if results are incomplete or unavailable. If you fall back, note that in your handoff. Never commit secrets; use example config files such as `backend/.env.json.example/` as templates.
