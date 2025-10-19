import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from code_parser import CodeParser
from graph_utils import (
    generate_file_layer,
    generate_class_method_layer,
    generate_graph_html,
    generate_full_semantic_layer,
)
from chat_manager import (
    init_db,
    save_message,
    get_chat_history,
    register_codebase,
    list_codebases,
    delete_codebase,
)
import hashlib
import pickle
import tempfile
import subprocess
import networkx as nx

# ------------------------------------------------------------
# Utility functions
# ------------------------------------------------------------
def hash_codebase(repo_path):
    sha = hashlib.sha256()
    for root, _, files in os.walk(repo_path):
        for f in sorted(files):
            file_path = os.path.join(root, f)
            try:
                with open(file_path, "rb") as file:
                    while chunk := file.read(4096):
                        sha.update(chunk)
            except Exception:
                pass
    return sha.hexdigest()


def get_local_repo_path(path_or_url):
    """
    If input is a GitHub URL, clone it to a temporary dir.
    Otherwise, return absolute local path.
    """
    if not path_or_url:
        raise ValueError("Empty path provided.")

    path_or_url = path_or_url.strip()
    if path_or_url.startswith(("http://", "https://")):
        if "github.com" not in path_or_url:
            raise ValueError("Only GitHub URLs are supported.")
        tmp_dir = tempfile.mkdtemp(prefix="repo_")
        with st.spinner("Cloning GitHub repository..."):
            try:
                subprocess.run(
                    ["git", "clone", path_or_url, tmp_dir],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except subprocess.CalledProcessError as e:
                import shutil
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise ValueError("Failed to clone repository.") from e
        return tmp_dir
    if not os.path.exists(path_or_url):
        raise ValueError(f"Local path not found: {path_or_url}")
    return os.path.abspath(path_or_url)


def load_or_parse_graph(repo_path):
    """
    Returns (codebase_id, graph, parsed_flag).
    parsed_flag=True if freshly parsed, else loaded from cache.
    """
    codebase_id = hash_codebase(repo_path)
    os.makedirs("cache", exist_ok=True)
    cache_file = os.path.join("cache", f"{codebase_id}.pkl")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                graph = pickle.load(f)
            return codebase_id, graph, False
        except Exception:
            pass  # fall through to reparse

    parser = CodeParser(repo_path)
    graph = parser.parse()
    with open(cache_file, "wb") as f:
        pickle.dump(graph, f)
    return codebase_id, graph, True


# ------------------------------------------------------------
# Query processor
# ------------------------------------------------------------
def process_query(graph, query):
    """
    Mini NLQ processor:
      - show info for <func>
      - functions in <file>
      - <func> calls ...
      - <func> called by ...
    """
    if not graph:
        return "No codebase graph loaded."

    q = (query or "").lower().strip()
    if not q:
        return "Empty query."

    # --- function info ---
    if q.startswith("show info for") or q.startswith("details of"):
        func = query.split()[-1].replace("()", "").strip()
        matches = [
            n
            for n, a in graph.nodes(data=True)
            if a.get("type") == "function" and func in a.get("display_name", "")
        ]
        if not matches:
            return f"No function named '{func}' found."
        node = matches[0]
        a = graph.nodes[node]
        return (
            f"### {a.get('display_name')}\n"
            f"**File:** {a.get('file','?')}\n"
            f"**LOC:** {a.get('loc','?')}\n"
            f"**Params:** {a.get('params','[]')}\n"
            f"**Docstring:** {a.get('doc','(none)')}"
        )

    # --- list functions in file ---
    if q.startswith("functions in"):
        file = query.split("functions in")[-1].strip()
        matches = [
            n for n, a in graph.nodes(data=True)
            if a.get("type") == "function" and a.get("file") and file in a.get("file")
        ]
        if not matches:
            return f"No functions found in file '{file}'."
        return "Functions:\n" + "\n".join(f"- {graph.nodes[m]['display_name']}" for m in matches)

    # --- calls / called by ---
    tokens = q.split()
    if "calls" in tokens:
        func = tokens[0].replace("()", "")
        matches = [n for n, a in graph.nodes(data=True)
                   if a.get("type") == "function" and func in a.get("display_name", "")]
        if not matches:
            return f"No function matching '{func}' found."
        func_node = matches[0]
        callees = [
            dst for _, dst, d in graph.out_edges(func_node, data=True)
            if d.get("label") == "calls"
        ]
        if not callees:
            return f"'{func}' does not call any other function."
        return f"'{func}' calls:\n" + "\n".join(f"- {graph.nodes[c]['display_name']}" for c in callees)

    if "called by" in q:
        func = q.split("called by")[0].strip().replace("()", "")
        matches = [n for n, a in graph.nodes(data=True)
                   if a.get("type") == "function" and func in a.get("display_name", "")]
        if not matches:
            return f"No function matching '{func}' found."
        func_node = matches[0]
        callers = [
            src for src, _, d in graph.in_edges(func_node, data=True)
            if d.get("label") == "calls"
        ]
        if not callers:
            return f"'{func}' is not called by any function."
        return f"'{func}' is called by:\n" + "\n".join(f"- {graph.nodes[c]['display_name']}" for c in callers)

    return "Query not understood. Try: 'show info for foo', 'functions in file.py', 'foo calls', 'foo called by'."


# ------------------------------------------------------------
# Streamlit UI
# ------------------------------------------------------------
def main():
    st.set_page_config(page_title="Codebase Navigator", layout="wide")
    load_dotenv()
    init_db()

    st.title("Codebase Navigator")

    # Sidebar: codebase management
    st.sidebar.header("Codebases")

    # Add / load / delete
    code_input = st.sidebar.text_input("Enter local path or GitHub URL:")
    if st.sidebar.button("Load Codebase"):
        try:
            repo_path = get_local_repo_path(code_input)
            codebase_id, graph, parsed = load_or_parse_graph(repo_path)
            register_codebase(codebase_id, os.path.basename(repo_path), repo_path)
            st.session_state["graph"] = graph
            st.session_state["codebase_id"] = codebase_id
            st.sidebar.success(f"Loaded: {os.path.basename(repo_path)}")
        except Exception as e:
            st.sidebar.error(str(e))

    # List registered codebases
    codebases = list_codebases()
    if codebases:
        selected = st.sidebar.selectbox(
            "Select existing codebase:",
            options=[(cid, name, path) for cid, name, path in codebases],
            format_func=lambda x: x[1],
        )
        if st.sidebar.button("Load Selected"):
            cid, name, path = selected
            _, graph, _ = load_or_parse_graph(path)
            st.session_state["graph"] = graph
            st.session_state["codebase_id"] = cid
            st.sidebar.success(f"Loaded cached: {name}")

        if st.sidebar.button("Delete Selected"):
            cid, name, _ = selected
            delete_codebase(cid)
            st.sidebar.warning(f"Deleted {name}")

    st.sidebar.markdown("---")

    # --------------------------------------------------------
    # Visualization
    # --------------------------------------------------------
    graph = st.session_state.get("graph")
    if graph:
        st.subheader("Visualization Layers")
        layer = st.radio(
            "Select layer view:",
            ["File Layer", "Class/Method Layer", "Full Semantic Layer"],
            horizontal=True,
        )

        with st.spinner("Rendering graph..."):
            if layer == "File Layer":
                html = generate_file_layer(graph)
            elif layer == "Class/Method Layer":
                html = generate_class_method_layer(graph)
            else:
                html = generate_full_semantic_layer(graph)
            components.html(html, height=850, scrolling=True)

    # --------------------------------------------------------
    # Chat / Query Section
    # --------------------------------------------------------
    st.markdown("---")
    st.subheader("Chat / Query")

    if "codebase_id" in st.session_state:
        cid = st.session_state["codebase_id"]
        history = get_chat_history(cid)
        for role, msg, ts in history:
            with st.chat_message(role):
                st.markdown(msg)

        if query := st.chat_input("Ask about this codebase..."):
            # show user message immediately
            with st.chat_message("user"):
                st.markdown(query)
            save_message(cid, "user", query)

            # process + show response
            response = process_query(st.session_state["graph"], query)
            save_message(cid, "assistant", response)
            with st.chat_message("assistant"):
                st.markdown(response)
    else:
        st.info("Load a codebase to start querying.")


if __name__ == "__main__":
    main()
