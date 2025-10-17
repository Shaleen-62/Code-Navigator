import os
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from code_parser import CodeParser
from graph_utils import generate_graph_html, get_callers, get_callees
from chat_manager import init_db, save_message, get_chat_history, register_codebase, list_codebases, delete_codebase
import hashlib
import pickle
import tempfile
import subprocess

# --- Utilities ---
def hash_codebase(repo_path):
    sha = hashlib.sha256()
    for root, _, files in os.walk(repo_path):
        for f in sorted(files):
            file_path = os.path.join(root, f)
            try:
                with open(file_path, "rb") as file:
                    while True:
                        chunk = file.read(4096)
                        if not chunk:
                            break
                        sha.update(chunk)
            except Exception:
                # skip unreadable files (binaries, permissions, etc.)
                pass
    return sha.hexdigest()


def get_local_repo_path(path_or_url):
    """
    If the input is a GitHub URL, clone it to a temporary dir and return that path.
    Otherwise, return absolute local path.
    """
    if not path_or_url:
        raise ValueError("Empty path provided.")

    path_or_url = path_or_url.strip()
    if path_or_url.startswith(("http://", "https://")):
        if "github.com" not in path_or_url:
            raise ValueError("Only GitHub URLs are supported at the moment.")
        tmp_dir = tempfile.mkdtemp(prefix="repo_")
        with st.spinner("Cloning GitHub repository..."):
            try:
                subprocess.run(["git", "clone", path_or_url, tmp_dir], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                # remove temp dir if clone failed
                try:
                    if os.path.exists(tmp_dir):
                        import shutil
                        shutil.rmtree(tmp_dir)
                except Exception:
                    pass
                raise ValueError("Failed to clone repository. Ensure the URL is public and git is installed.") from e
        return tmp_dir
    # local path
    if not os.path.exists(path_or_url):
        raise ValueError(f"Local path does not exist: {path_or_url}")
    return os.path.abspath(path_or_url)


def load_or_parse_graph(repo_path):
    """
    Return (codebase_id, graph, parsed_flag).
    parsed_flag is True if parsing occurred now; False if loaded from cache.
    """
    if not os.path.exists(repo_path):
        raise ValueError(f"Repo path not found: {repo_path}")

    codebase_id = hash_codebase(repo_path)
    os.makedirs("cache", exist_ok=True)
    cache_file = os.path.join("cache", f"{codebase_id}.pkl")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, "rb") as f:
                graph = pickle.load(f)
            parsed = False
        except Exception:
            # cache corrupted; reparse and overwrite
            parser = CodeParser(repo_path)
            graph = parser.parse()
            with open(cache_file, "wb") as f:
                pickle.dump(graph, f)
            parsed = True
    else:
        parser = CodeParser(repo_path)
        graph = parser.parse()
        with open(cache_file, "wb") as f:
            pickle.dump(graph, f)
        parsed = True

    return codebase_id, graph, parsed


def process_query(graph, query):
    """
    Very small natural-language-ish processor that supports:
    - show info for <func>
    - details of <func>
    - functions in <file>
    - <func> called by ...
    - <func> calls ...
    """
    if not graph:
        return "No codebase graph loaded."

    q = (query or "").lower().strip()

    # metadata queries
    if q.startswith("show info for") or q.startswith("details of"):
        # assume last token is function name (like foo or foo())
        func = query.split()[-1].strip()
        # match by display name or by raw node id substring
        matches = [n for n, a in graph.nodes(data=True) if a.get("type") == "function" and (a.get("display_name") == func or func in a.get("display_name", "") or func in n)]
        if not matches:
            return f"No function matching '{func}' found."
        func_node = matches[0]
        attrs = graph.nodes[func_node]
        info = f"Function: {attrs.get('display_name', func_node)}\n"
        info += f"File: {attrs.get('file','?')}\n"
        info += f"Docstring: {attrs.get('doc','(none)')}\n"
        info += f"LOC: {attrs.get('loc','?')}\n"
        info += f"Params: {attrs.get('params','[]')}\n"
        return info

    # functions in a file
    if "functions in" in q or "defined in" in q:
        # take text after 'in'
        parts = query.lower().split("in")
        if len(parts) < 2:
            return "Please say: 'functions in <filename>'"
        file_name = parts[-1].strip()
        matches = [a.get("display_name", n) for n, a in graph.nodes(data=True) if a.get("type") == "function" and os.path.basename(a.get("file", "")) == file_name]
        return "\n".join(matches) if matches else f"No functions found in `{file_name}`."

    # call relationships
    if "called by" in q:
        func = query.split("called by")[-1].strip()
        # find matching node by display_name
        matches = [n for n, a in graph.nodes(data=True) if a.get("type") == "function" and (a.get("display_name") == func or func in a.get("display_name",""))]
        if not matches:
            return f"Function `{func}` not found."
        func_node = matches[0]
        callers = get_callers(graph, func_node)
        # display caller display_names where available
        readable = [graph.nodes[c].get("display_name", str(c)) for c in callers]
        return "\n".join(readable) if readable else f"No callers found for `{func}`."

    if "calls" in q or "callees" in q:
        func = query.split("calls")[-1].strip()
        matches = [n for n, a in graph.nodes(data=True) if a.get("type") == "function" and (a.get("display_name") == func or func in a.get("display_name",""))]
        if not matches:
            return f"Function `{func}` not found."
        func_node = matches[0]
        callees = get_callees(graph, func_node)
        readable = [graph.nodes[c].get("display_name", str(c)) for c in callees]
        return "\n".join(readable) if readable else f"No callees found for `{func}`."

    return "Query not recognized. Try: 'show info for foo', 'functions in file.py', 'foo called by', or 'foo calls'."


# --- Main App ---
def main():
    load_dotenv()
    st.set_page_config(page_title="Code Navigator", layout="wide")
    init_db()
    st.title("Code Navigator")

    # --- Sidebar: codebase management ---
    st.sidebar.header("Codebases")
    codebases = list_codebases()  # returns list of (id, name, path)
    options = [f"{name} ({path})" for _, name, path in codebases]
    id_map = {f"{name} ({path})": cid for cid, name, path in codebases}

    # Add new codebase
    st.sidebar.subheader("Add New Codebase")
    new_path = st.sidebar.text_input("Enter local folder path or GitHub URL:")
    if st.sidebar.button("Add Codebase"):
        if new_path and new_path.strip():
            try:
                real_path = get_local_repo_path(new_path.strip())
                codebase_id, graph, parsed = load_or_parse_graph(real_path)
                register_codebase(codebase_id, os.path.basename(real_path), real_path)
                st.sidebar.success(f"Added: {os.path.basename(real_path)}")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Failed to add codebase: {e}")
        else:
            st.sidebar.warning("Please enter a valid path or GitHub URL.")

    st.sidebar.divider()

    # If there are no codebases yet
    if not options:
        st.sidebar.info("No codebases yet. Add one above to get started.")
        return

    # Select an existing codebase
    selected = st.sidebar.selectbox("Select codebase", options)
    codebase_id = id_map[selected]
    repo_path = [p for (cid, n, p) in codebases if cid == codebase_id][0]

    # Delete button for selected
    if st.sidebar.button("Delete this codebase"):
        delete_codebase(codebase_id)
        cache_file = os.path.join("cache", f"{codebase_id}.pkl")
        if os.path.exists(cache_file):
            try:
                os.remove(cache_file)
            except Exception:
                pass
        st.sidebar.success("Codebase deleted. Please reload.")
        st.stop()

    # Load cached graph (or parse if missing)
    try:
        codebase_id, graph, parsed = load_or_parse_graph(repo_path)
    except Exception as e:
        st.error(f"Failed to load codebase: {e}")
        return

    # Layout: two equal columns
    col1, col2 = st.columns([1, 1])

    # Left column: chat
    with col1:
        st.header("Chat with Codebase")
        history = get_chat_history(codebase_id)
        for role, msg, _ in history:
            st.chat_message(role).write(msg)

        if user_query := st.chat_input("Ask a question about the codebase..."):
            st.chat_message("user").write(user_query)
            response = process_query(graph, user_query)
            st.chat_message("assistant").write(response)
            save_message(codebase_id, "user", user_query)
            save_message(codebase_id, "assistant", response)

    # Right column: graph
    with col2:
        st.header("Code Dependency Graph")
        html = generate_graph_html(graph)
        components.html(html, height=800, scrolling=True)


if __name__ == "__main__":
    main()
