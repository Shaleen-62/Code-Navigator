import os
import ast
import networkx as nx
import builtins

class CodeParser:
    """
    Parses a Python repo into a call + import dependency graph.
    Nodes:
        - file (type="file")
        - function (type="function")
    Edges:
        - file_import (file → imported file)
        - defined_in (function → file)
        - calls (function → function)
    """

    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.graph = nx.DiGraph()
        self.repo_files = []                  # list of .py files (rel paths)
        self.functions_by_file = {}           # file -> {func_name: ast.FunctionDef}
        self.imports_by_file = {}             # file -> alias -> module
        self.from_imports_by_file = {}        # file -> name -> module
        self.builtin_names = set(dir(builtins))

    # ----------------------------------------------------------
    def parse(self):
        """Main entry point to build the full graph."""
        self._collect_files()
        self._index_functions_and_imports()
        self._add_function_nodes_and_import_edges()
        self._resolve_function_calls()
        return self.graph

    # ----------------------------------------------------------
    def _collect_files(self):
        """Walk repo and collect all .py files."""
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.repo_path)
                    self.repo_files.append(rel_path)
                    self.graph.add_node(rel_path, type="file", display_name=rel_path)

    # ----------------------------------------------------------
    def _index_functions_and_imports(self):
        """Parse AST for each file, record functions and imports."""
        for rel in self.repo_files:
            full = os.path.join(self.repo_path, rel)
            try:
                with open(full, "r", encoding="utf-8") as f:
                    src = f.read()
                tree = ast.parse(src)
            except Exception as e:
                print(f"Failed to parse {rel}: {e}")
                continue

            self.functions_by_file[rel] = {}
            self.imports_by_file[rel] = {}
            self.from_imports_by_file[rel] = {}

            for node in tree.body:
                # record function definitions
                if isinstance(node, ast.FunctionDef):
                    self.functions_by_file[rel][node.name] = node

                # record `import module as alias`
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split('.')[0]
                        asname = alias.asname or mod
                        self.imports_by_file[rel][asname] = mod

                # record `from module import name as alias`
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod = node.module.split('.')[0]
                        for alias in node.names:
                            asname = alias.asname or alias.name
                            self.from_imports_by_file[rel][asname] = mod

    # ----------------------------------------------------------
    def _add_function_nodes_and_import_edges(self):
        """Create function nodes and file_import edges."""
        for rel in self.repo_files:
            funcs = self.functions_by_file.get(rel, {})

            # Add function nodes and link to file
            # inside _add_function_nodes_and_import_edges()
            for fname, fnode in funcs.items():
                uid = f"{rel}::{fname}"
                display = f"{fname}()"
                start = getattr(fnode, "lineno", 0)
                end = getattr(fnode, "end_lineno", start)
                loc = end - start + 1
                params = [a.arg for a in fnode.args.args]
                doc = ast.get_docstring(fnode) or ""

                self.graph.add_node(uid, type="function", display_name=display,
                                    file=rel, loc=loc, params=params, doc=doc)

                # change direction: file → function
                self.graph.add_edge(rel, uid, label="defined_in")

                # Add edges for imports that match repo files
                for alias, module in self.imports_by_file.get(rel, {}).items():
                    self._add_import_edge(rel, module)

                for name, module in self.from_imports_by_file.get(rel, {}).items():
                    self._add_import_edge(rel, module)

    # ----------------------------------------------------------
    def _add_import_edge(self, src_file, module_name):
        """Link file → file if module_name matches repo file."""
        candidate = module_name + ".py"
        for f in self.repo_files:
            if os.path.basename(f) == candidate:
                self.graph.add_edge(src_file, f, label="file_import")

    # ----------------------------------------------------------
    def _resolve_function_calls(self):
        """Walk all function bodies, add call edges."""
        for rel, funcs in self.functions_by_file.items():
            for fname, fnode in funcs.items():
                caller_uid = f"{rel}::{fname}"

                for node in ast.walk(fnode):
                    if not isinstance(node, ast.Call):
                        continue

                    callee_uid = self._resolve_callee(node, rel)
                    if callee_uid and self.graph.has_node(callee_uid):
                        self.graph.add_edge(caller_uid, callee_uid, label="calls")

    # ----------------------------------------------------------
    def _resolve_callee(self, node, rel):
        """Try to resolve a call node to an existing function UID in the repo."""
        # Case 1: foo()
        if isinstance(node.func, ast.Name):
            name = node.func.id
            # skip builtins
            if name in self.builtin_names:
                return None
            # same file
            if name in self.functions_by_file.get(rel, {}):
                return f"{rel}::{name}"
            # from-imported function
            elif name in self.from_imports_by_file.get(rel, {}):
                mod = self.from_imports_by_file[rel][name]
                matched = self._match_module_to_file(mod)
                if matched:
                    return f"{matched}::{name}"
            return None

        # Case 2: module.func()
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            owner = node.func.value.id
            attr = node.func.attr
            # is the owner an imported module?
            mapped_mod = self.imports_by_file.get(rel, {}).get(owner)
            if mapped_mod:
                matched = self._match_module_to_file(mapped_mod)
                if matched:
                    return f"{matched}::{attr}"
        return None

    # ----------------------------------------------------------
    def _match_module_to_file(self, module_name):
        """Find the repo file corresponding to a module name."""
        candidate = module_name + ".py"
        for f in self.repo_files:
            if os.path.basename(f) == candidate:
                return f
        return None
