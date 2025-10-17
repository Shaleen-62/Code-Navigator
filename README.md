# Code-Navigator
<br>
CodeNavigator is an interactive tool for analyzing and visualizing Python codebases.  
It helps developers understand project structure by displaying files, functions, and call dependencies as an interactive directed graph.  
The application is built using Streamlit for the interface, NetworkX for graph construction, and PyVis for visualization.  
  
<br>
  

## Overview

CodeNavigator performs static analysis of Python source files to extract:
- Function definitions
- Function calls
- Cross-file relationships

It then generates an interactive network graph that allows users to explore how different components of a project are connected.
<br>
<br>

## Features

- **Repository Parsing**  
  Recursively scans and parses Python projects to extract functions and their relationships.

- **Interactive Visualization**  
  Visualize call graphs interactively using PyVis:
  - Hover over nodes to view docstrings, parameters, and line counts.
  - Pan and zoom freely.
  - Filter or focus on specific nodes.

- **File and Function Relationship Mapping**  
  - Blue dashed arrows represent `calls` relationships between functions.
  - Orange solid arrows represent `defined_in` relationships connecting functions to their source files.

- **Persistent Codebase Storage**  
  Once a codebase is parsed, it can be stored in the database and re-used for queries without reprocessing.

- **Efficient and Modular Design**  
  Clear separation of parsing, graph construction, and visualization logic.

<br>
<br>

## Project Structure

CodeNavigator/<br>
├── main.py                 # Streamlit application entry point<br>
├── parser.py               # Parses Python code using AST<br>
├── graph_builder.py        # Builds NetworkX graph from parsed data<br>
├── visualizer.py           # Generates PyVis graph visualization<br>
├── utils/<br>
│   ├── file_utils.py       # File and path utilities<br>
│   └── filters.py          # Search and filtering logic<br>
├── tests/<br>
│   ├── test_parser.py<br>
│   ├── test_graph_builder.py<br>
│   └── test_visualizer.py<br>
├── requirements.txt<br>
└── README.md<br>
<br>
<br>
 


## Installation

### 1. Clone the repository

```
git clone https://github.com/<your-username>/CodeNavigator.git
cd CodeNavigator
```

### 2. Create a virtual environmet

```
python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate      # Windows
```

### 3. Install dependencies

```
pip install -r requirements.txt
```
<br>
<br>

## Usage

### 1. Run the Streamlit app

```
streamlit run main.py
```

### 2. Steps

1. **Select or upload a Python project directory.**  
2. **CodeNavigator parses all `.py` files recursively.**  
3. **View the generated graph in your browser.**  
4. **Hover on nodes to see:**
   - Function signatures  
   - Line count (LOC)  
   - Docstring (truncated)  
   - Containing file  
<br>
<br>

## How It Works

- **Static Analysis (AST)**
Uses Python's built-in `ast` module to safely parse files without executing code.

- **Graph Construction (NetworkX)**
Builds a directed graph connecting files and functions through defined relationships.

- **Visualization (PyVis)**
Renders the graph as an interactive HTML canvas embedded within Streamlit.

- **Database Integration**
Parsed codebases are stored for future queries without reprocessing.
<br>
<br>

## Dependencies

| Library   | Purpose |
|------------|----------|
| Streamlit  | User interface framework |
| NetworkX   | Graph construction and traversal |
| PyVis      | Interactive graph visualization |
| ast        | Static code analysis |
| pathlib, os, io | File management and parsing utilities |



