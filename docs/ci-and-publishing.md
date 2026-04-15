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
| `.github/workflows/ci.yml` | `pip install -r requirements.txt`, `python scripts/build_docs_pdf.py --no-pdf`, `pytest tests/`. |
| `.github/workflows/docs-pages.yml` | `bundle install` + `jekyll build` from `docs/`, deploy with **deploy-pages**. |
| `.github/workflows/docs-pdf.yml` | Build `pdf/diy-bacnet-server-docs.pdf` and `.txt`; open a PR when outputs change. |

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
pip install -r requirements.txt
pytest tests/ -v --tb=short
```

## License

MIT License. See `LICENSE` in the repository root.
