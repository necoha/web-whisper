# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: Python sidecar (Gradio-based), build scripts, specs, and GPU detection (`main.py`, `patch_gpu.py`, `build_sidecar.py`, `whisper-gui-core.spec`).
- `frontend/`: Tauri + Vite + TypeScript UI; Rust code under `src-tauri/`, web assets under `src/` and `public/`.
- Top-level helpers: `build.py` (orchestrates full build), `verify_setup.py` (env checks).

## Build, Test, and Development Commands
- Dev backend: `cd backend && python main.py` — runs the local Gradio backend.
- Dev app: `cd frontend && npm run tauri:dev` — launches Tauri with live reload.
- Full build: `python build.py` — builds sidecar and desktop app; see flags: `--backend-only`, `--frontend-only`, `--target <triple>`.
- Backend sidecar: `cd backend && python build_sidecar.py` — or `pyinstaller --clean whisper-gui-core.spec`.
- Frontend build: `cd frontend && npm run tauri:build` — use `-- --target <triple>` for platform-specific bundles.
- Sanity checks: `python verify_setup.py` and `cd backend && python patch_gpu.py`.

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indent, type hints where useful; modules and files `lower_snake_case.py`.
- TypeScript: 2-space indent, ES modules, React-style components `PascalCase.tsx`; avoid default exports.
- Rust (Tauri): follow `rustfmt` defaults; keep modules small and command handlers explicit.
- General: names describe intent; keep functions short and side-effect free.

## Testing Guidelines
- Current repo has minimal tests; prefer adding:
  - Backend: `pytest` under `backend/tests/` with `test_*.py` files.
  - Frontend: `vitest` under `frontend/src/__tests__/` with `*.test.ts(x)`.
  - Rust: `cargo test` within `frontend/src-tauri/` for unit tests.
- Target: meaningful coverage for new logic; include GPU-path smoke checks (mocked where possible).

## Commit & Pull Request Guidelines
- Use Conventional Commits (e.g., `feat(frontend): add GPU status badge`).
- Scope PRs narrowly; include description, platform(s) tested, screenshots of UI changes, and reproduction steps.
- Link related issues and note build commands run (e.g., `python build.py`, `npm run tauri:dev`).
- CI-style check locally: backend runs, `tauri info` passes, and build succeeds for your platform.

## Security & Configuration Tips
- Do not commit models or large artifacts; use `backend/models/` locally and keep it in `.gitignore`.
- Use `pyenv` + venv for Python isolation; standard env name: `web-whisper`.
- Ensure ffmpeg is installed and on PATH.
- macOS uses MLX/Metal; Windows uses CUDA via faster-whisper — verify with `patch_gpu.py` before PRs.

## Python Environment (pyenv)
Create and use a dedicated pyenv virtualenv named `web-whisper`:

```bash
pyenv install -s 3.10.12
pyenv virtualenv 3.10.12 web-whisper
pyenv local web-whisper   # in repo root

# Install deps
pip install -r backend/requirements.txt

# Platform-specific backend acceleration
# Apple Silicon (MLX):
pip install mlx-whisper
# Others (CUDA/CPU):
pip install faster-whisper ctranslate2

# Quick check
python -c "import gradio; print('gradio ok')"
```

Tip: if using multiple shells/editors, confirm the active env with `pyenv version` and ensure it shows `web-whisper`.
