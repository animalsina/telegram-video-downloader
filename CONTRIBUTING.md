# Developer Guide for telegram-video-downloader

This document provides detailed instructions, best practices, and code-specific notes for developers who want to contribute or extend this project.

---

## 1. Codebase Overview

- **Entry point:** `run.py` – launches the main logic asynchronously.
- **Core logic:** `func/` – contains main features (compression, download, etc).
- **Configuration:** via `tg-config.txt` (see README for structure).
- **Commands/Rules:** See `/README-commands.md` and `/README-rules.md`.

---

## 2. Environment Setup

### Prerequisites

- Python **3.9+**
- `ffmpeg` and `ffprobe` installed and in your system PATH
- (Recommended) Use a virtualenv

### Setup Steps

```bash
git clone https://github.com/animalsina/telegram-video-downloader.git
cd telegram-video-downloader
python -m venv venv
source venv/bin/activate  # (Windows: venv\Scripts\activate)
pip install -r requirements.txt
ffmpeg -version  # Should print version info
```

---

## 3. Code Style and Linting

- **PEP8** style enforced (`.pylintrc` included).
- Use [Black](https://black.readthedocs.io/en/stable/) for formatting.
- Lint before commits:  
  `pylint func/ run.py`
- Use clear, descriptive variable/function names (avoid abbreviations).
- Write docstrings for all public functions and complex logic.

**Special Notes:**  
- Prefer type annotations for all functions.
- Maintain logical separation: utilities in `func/`, business logic in `main`.
- Avoid magic numbers; declare constants at the top of files.

---

## 4. Configuration and Secrets

- Never commit real Telegram API credentials.
- Sensitive settings go in `tg-config.txt` (excluded from version control).
- Document any new config parameters in both the code and README.

---

## 5. Adding or Modifying Features

### General Guidelines

- Keep functions short (preferably <50 lines).
- Split complex logic into smaller helper functions.
- Use async/await for I/O-bound tasks (e.g., downloads, compression).
- Always handle exceptions and print informative error messages.
- Add logging where appropriate (replace `print` with proper logging for production).

### Compression (`func/compression.py`)

- All input/output files must be validated before processing.
- When adding new codecs/algorithms, ensure backwards compatibility.
- Monitor process status and implement timeouts to avoid hanging subprocesses.
- Use callback functions properly (support both sync and async).

### Main Entrypoint (`run.py`)

- Only loads and runs `func.main.main()` asynchronously.
- Do not add business logic here.
- Catch and log all top-level exceptions.

---

## 6. Testing

- Place all tests in the `/tests` directory.
- Use [pytest](https://docs.pytest.org/) for writing and running tests.
- Cover:
  - File validation
  - Compression logic (mock subprocesses)
  - Error handling edge cases
- Run tests with:  
  `pytest tests/`

---

## 7. Git and Commit Rules

- Use [Conventional Commits](https://www.conventionalcommits.org/):
  - `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, etc.
- Write clear, descriptive commit messages.

---

## 8. Adding Dependencies

- Only add dependencies after verifying they are well-maintained and compatible.
- Explain why the dependency is needed in the PR.
- Update `requirements.txt` and test locally.

---

## 9. Pull Request Process

1. Fork the repo and create a feature branch.
2. Ensure your code passes linting and all tests.
3. Submit a clear PR description, referencing any related issues.
4. Be prepared to make changes after code review.

---

## 10. Code Quality Checklist

- [ ] No hardcoded credentials or paths.
- [ ] All functions have docstrings and type hints.
- [ ] Error handling is robust and user-friendly.
- [ ] No commented-out or dead code.
- [ ] Code is modular and reusable.
- [ ] All new features are documented.
- [ ] All new logic is covered by tests.

---

## 11. Known Code Issues & Improvements

- `func/compression.py`:
  - Consider extracting progress logic and subprocess management into separate helpers/classes for testability.
  - Avoid using print for progress; use logging or callback for UI.
  - Always check for file existence before operations.
  - Future: Refactor for more robust resume logic and better error messages.
- Review all TODO/FIXME comments in the code; address or remove them before PR.
- Watch for duplicate or similar utility functions across modules.

---

## 12. Useful Resources

- [PEP8](https://www.python.org/dev/peps/pep-0008/)
- [Telethon Docs](https://docs.telethon.dev/)
- [FFmpeg Docs](https://ffmpeg.org/documentation.html)
- [pytest](https://docs.pytest.org/)

---

For any questions, open an issue or start a discussion on GitHub.
