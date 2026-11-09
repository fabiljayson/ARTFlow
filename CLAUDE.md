# CLAUDE.md

This file gives Claude Code the repo-specific context it should not have to rediscover.

## Package manager

- Use `npm` for this workspace. Confirm this before installing dependencies.
- Run package scripts with `npm run <script>`.

## Runtime assets and packaging

- `dist/` is ignored, so build before launching, testing, or packaging.

## Comment style

- Never place comments on the first two lines of a source file; start with imports or declarations.
- Prefer concise section headings such as `// ── Constants ──` or a three-line banner for major sections so files remain easy to scan.
- Use JSDoc blocks only when an API, intent, edge case, or constraint needs explanation; do not restate the code.

## Boundaries

- Prefer existing local patterns and helper APIs before adding new abstractions.
- Keep generated, packaged, and runtime asset boundaries intact; do not move files across host/webview ownership without updating build and packaging config.

## Claude Code workflow

- For broad or uncertain changes, explore first and propose a plan before editing.
- Prefer focused verification commands while iterating, then run the full gate before finishing.
- Keep this file concise; move shared agent instructions to `AGENTS.md` if that file is added later.
