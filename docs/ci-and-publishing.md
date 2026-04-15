---
layout: default
title: CI & publishing
nav_order: 11
---

# CI & publishing

Same pattern as **[easy-aso](https://github.com/bbartling/easy-aso)** and **[open-fdd](https://github.com/bbartling/open-fdd)**: GitHub Actions for tests, Jekyll docs on Pages, and a Pandoc + WeasyPrint PDF bundle.

## Workflows

| Workflow | Purpose |
|----------|---------|
| `.github/workflows/ci.yml` | **Python 3.14** on `ubuntu-latest`: `pip install ".[dev]"` (see `pyproject.toml`), `python scripts/build_docs_pdf.py --no-pdf`, `pytest tests/`. |
| `.github/workflows/docs-pages.yml` | `bundle install` + `jekyll build` from `docs/`, deploy with **deploy-pages**. |
| `.github/workflows/docs-pdf.yml` | Build `pdf/diy-bacnet-server-docs.pdf` and `.txt`; upload artifacts; try to open a PR when outputs change. |

## What the CI job runs

The **CI** workflow installs the project with **`pip install ".[dev]"`** (runtime deps + `dev` extras from `pyproject.toml`), runs `scripts/build_docs_pdf.py --no-pdf` (combined Markdown + text bundle sanity), then runs **`pytest tests/`** — the full test tree, including the **Docker Compose** smoke test in `tests/test_docker_bacnet_server.py` (skipped automatically when Docker Compose is not on `PATH`).

## Docs PDF workflow: PR permission

If you see *“GitHub Actions is not permitted to create or approve pull requests”*, the workflow can still succeed: PDF and `.txt` outputs are **always uploaded as workflow artifacts**. To also get automatic PRs, enable **Settings → Actions → General → Workflow permissions → Allow GitHub Actions to create and approve pull requests** (repo or org policy may override `permissions:` in the YAML file).

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
