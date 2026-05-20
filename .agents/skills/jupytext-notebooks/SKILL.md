---
name: jupytext-notebooks
description: Use when Codex is asked to edit, create, refactor, or review research notebooks paired with Jupytext percent-format Python files, especially .ipynb plus .py:percent workflows where notebook content should be edited through the paired Python file instead of raw notebook JSON.
---

# Jupytext Notebooks

## Overview

Use Jupytext percent-format Python files as the primary editing surface for research notebooks. Prefer editing the paired `.py` file because it is more efficient, readable, and reviewable than editing `.ipynb` JSON directly.

## Workflow

1. Locate the target `.ipynb` notebook and check whether the paired `.py` file exists.
2. Ensure the notebook is paired as `ipynb,py:percent`. If the repository already configures Jupytext with `[tool.jupytext] formats = "ipynb,py:percent"` in `pyproject.toml`, do not run a separate `jupytext --set-formats` step. Otherwise, run:

   ```bash
   jupytext --set-formats ipynb,py:percent <notebook.ipynb>
   ```

3. Create or refresh the paired `.py` file:

   ```bash
   jupytext --sync <notebook.ipynb>
   ```

4. Edit notebook text and code in the percent-format `.py` file.
5. Preserve `# %%` cell markers and the markdown/code cell structure. For details, read `references/percent_format.md`.
6. Do not hand-edit Jupytext pairing metadata; let `jupytext --set-formats` and `jupytext --sync` manage it. Edit `.ipynb` JSON directly only for notebook data that cannot be represented through the paired `.py` file.
7. After editing, sync the notebook again:

   ```bash
   jupytext --sync <notebook.ipynb>
   ```

8. Inspect diffs for both files and avoid committing stale or unintended notebook output changes unless the user requested them.

## Validation

After editing the paired `.py` file and before the final sync, run the bundled validator:

```bash
python3 <skill-dir>/scripts/validate_percent_notebook.py <notebook.ipynb>
```

The validator accepts either the `.ipynb` file or the paired `.py` file. It checks that the percent-format file exists, contains valid cell markers, keeps markdown cell text commented, does not look like raw notebook JSON, and has no unresolved merge conflict markers.
