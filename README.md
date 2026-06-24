# My_file_traverse_calculator

**My_file_traverse_calculator** is a Windows-friendly clipboard pipeline tool that
lets you traverse directories, calculate file sizes, and pipe the results through
the system clipboard — all from a single command.

---

## Features

| Module | Purpose |
|---|---|
| `file_traverser.py` | Recursive directory walking with size/count statistics, depth limiting, extension filtering |
| `clipboard_pipeline.py` | Fluent pipeline for chaining clipboard I/O, traversal, and session operations |
| `session_manager.py` | Persistent JSON-backed clipboard history and pinned snippets across sessions |
| `main.py` | CLI entry point |

---

## Quick Start

```bash
pip install -r requirements.txt
```

### Traverse a directory and copy the summary to the clipboard

```bash
python main.py traverse C:\Users\Me\Documents
```

### Read a directory path from the clipboard, traverse it, print + copy the summary

```bash
python main.py traverse --from-clipboard
```

### Filter by file type

```bash
python main.py traverse C:\Projects --ext .py .js .ts
```

### Limit recursion depth

```bash
python main.py traverse C:\Projects --max-depth 2
```

### Output a flat list of file paths instead of a summary

```bash
python main.py traverse C:\Projects --files
```

### Save the result to a named session

```bash
python main.py traverse C:\Projects --save --session work
```

---

## Session Management

```bash
# Show history for the default session
python main.py session --history

# Pin the current clipboard content under a label
python main.py session --name work --pin mydir

# Load a pinned entry back to the clipboard
python main.py session --name work --load mydir

# List all sessions
python main.py session --list

# Clear session history
python main.py session --name work --clear
```

---

## Python API

```python
from clipboard_pipeline import ClipboardPipeline

summary = (
    ClipboardPipeline(session="work")
    .read_clipboard()        # read a directory path from clipboard
    .traverse()              # walk the directory
    .summarise()             # convert result → human-readable text
    .write_clipboard()       # push summary back to clipboard
    .value                   # retrieve the string
)
print(summary)
```

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Requirements

- Python 3.9+
- `pyperclip` (optional — falls back to PowerShell / pbpaste / xclip)
