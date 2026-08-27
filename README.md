# CodeNavigator

An interactive tool for exploring and understanding Python codebases as a graph. Point it at a
local path or a GitHub URL, and it statically parses every `.py` file (via Python's `ast`
module — nothing is executed), builds a directed graph of files, classes, functions, and their
call relationships with NetworkX, and renders it as an interactive, explorable network with PyVis.

## Why

Jumping into an unfamiliar codebase usually means grepping for function names and manually
tracing imports. CodeNavigator turns that into a graph you can visually explore: hover a
function to see its signature, docstring, and line count; follow call/defined-in edges between
files; switch between a high-level file view and a full call-graph view.

## Features

- **Load from anywhere** — point at a local directory or paste a GitHub URL; remote repos are
  cloned automatically.
- **Three visualization layers** — File Layer (module-level relationships), Class/Method Layer,
  and Full Semantic Layer (every function + call edge), each rendered as an interactive PyVis
  graph embedded in the app.
- **Content-addressed caching** — each codebase is hashed (SHA-256 over file contents), and its
  parsed graph is pickled to `cache/`. Reopening the same codebase loads instantly instead of
  re-parsing.
- **Multi-codebase workspace** — a sidebar lets you register, switch between, and delete
  multiple parsed codebases without losing their cached graphs.
- **Built-in query interface** — a lightweight, rule-based natural-language query box (no LLM
  calls) answers structural questions directly from the graph: `show info for <function>`,
  `functions in <file>`, `<function> calls`, `<function> called by`. Queries and answers are
  persisted per codebase in a local SQLite chat history, so you can pick up a session where you
  left off.

## How it works

- **Static analysis (`ast`)** — parses each file without executing it, extracting function
  definitions, calls, and cross-file relationships (`code_parser.py`).
- **Graph construction (NetworkX)** — builds a directed graph connecting files, classes, and
  functions through `calls` and `defined_in` edges (`graph_utils.py`).
- **Visualization (PyVis)** — renders the graph as an interactive HTML canvas, embedded directly
  in the Streamlit app.
- **Query + history (SQLite)** — `chat_manager.py` persists registered codebases and per-codebase
  Q&A history, and answers structural queries by walking the in-memory graph.

## Repository layout

```
Code-Navigator/
├── main.py             # Streamlit app: sidebar, visualization, query UI
├── code_parser.py       # AST-based static analysis → graph nodes/edges
├── graph_utils.py        # NetworkX graph construction + PyVis layer rendering
├── chat_manager.py       # SQLite-backed codebase registry + chat history
├── cache/                 # Pickled parsed graphs, keyed by content hash
├── test_repo/              # Sample repo used for local testing
└── requirements.txt
```

## Installation

```bash
git clone https://github.com/Shaleen-62/Code-Navigator.git
cd Code-Navigator

python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

## Usage

```bash
streamlit run main.py
```

1. In the sidebar, enter a local path or GitHub URL and click **Load Codebase**.
2. Pick a visualization layer (File / Class-Method / Full Semantic).
3. Hover any node to see its function signature, file, line count, and docstring.
4. Use the query box at the bottom to ask structural questions about the loaded codebase.

## Tech

Streamlit (UI), NetworkX (graph model), PyVis (interactive visualization), Python `ast`
(static analysis), SQLite (codebase registry + query history).
