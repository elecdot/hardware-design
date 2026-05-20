# Percent Format Structure

Treat the paired `.py` file as a notebook represented by cell markers:

```python
# %% [markdown]
# # Research note
# Explain the question or result here.

# %%
import pandas as pd

# %%
result = pd.DataFrame({"x": [1, 2, 3]})
result
```

- Start each cell with `# %%`.
- Use `# %% [markdown]` for markdown cells.
- Keep markdown content as commented text after a markdown cell marker.
- Keep code cells as normal Python after a `# %%` marker.
- Preserve existing cell boundaries unless the user asks to reorganize the notebook.

Jupytext may also write a metadata header before the first cell, commonly as a commented YAML block delimited by `# ---`. The exact content depends on Jupytext and repository configuration, so do not treat it as a stable format and do not hand-edit it unless the user specifically asks for metadata changes. Let `jupytext --set-formats` and `jupytext --sync` manage notebook pairing metadata.
