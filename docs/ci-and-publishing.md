---
title: CI & publishing
nav_order: 11
---

# CI & publishing

Same pattern as **[easy-aso](https://github.com/bbartling/easy-aso)**: GitHub Actions for tests, Jekyll docs on Pages, and a Pandoc + WeasyPrint PDF bundle.

## Workflows

| Workflow | Purpose |
|----------|---------|
| `.github/workflows/ci.yml` | **Python 3.12** on `ubuntu-latest`: `pip install ".[dev]"` (see `pyproject.toml`), `python scripts/build_docs_pdf.py --no-pdf`, `pytest tests/`. |
| `.github/workflows/docs-pages.yml` | `bundle install` + `jekyll build` from `docs/`, deploy with **deploy-pages**. |
| `.github/workflows/docs-pdf.yml` | Build `pdf/diy-bacnet-server-docs.pdf` and `.txt`; upload artifacts only (no bot PR/branch creation). |

## What the CI job runs

The **CI** workflow installs the project with **`pip install ".[dev]"`** (runtime deps + `dev` extras from `pyproject.toml`), runs `scripts/build_docs_pdf.py --no-pdf` (combined Markdown + text bundle sanity), then runs **`pytest tests/`** — the full test tree, including the **Docker Compose** smoke test in `tests/test_docker_bacnet_server.py` (skipped automatically when Docker Compose is not on `PATH`).

## Docs PDF workflow behavior

The Docs PDF workflow publishes the generated PDF and `.txt` bundle as workflow artifacts and does **not** create a branch or PR automatically.

## GitHub Pages (first time)

Repository **Settings → Pages → Build and deployment → Source: GitHub Actions**.

Published site (user pages + repo name): **`https://bbartling.github.io/diy-bacnet-server/`** — must match **`baseurl`** in `docs/_config.yml`.

## PDF output

Generated files:

- `pdf/diy-bacnet-server-docs.pdf`
- `pdf/diy-bacnet-server-docs.txt`

The `pdf/` directory is tracked with **`pdf/.gitkeep`** until CI commits the first bundle.

Local combined text (no Pandoc):

```bash
pip install pyyaml
python scripts/build_docs_pdf.py --no-pdf
```

## Tests locally

```bash
pip install -e ".[dev]"
pytest tests/ -v --tb=short
```

## License

MIT License. See `LICENSE` in the repository root.
