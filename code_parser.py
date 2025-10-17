import os
import ast
import networkx as nx
import pickle

class CodeParser:
    def __init__(self, repo_path):
        self.repo_path = repo_path
        self.graph = nx.DiGraph()

    def parse(self):
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, self.repo_path)
                    self.graph.add_node(rel_path, type="file")

                    with open(file_path, "r", encoding="utf-8") as f:
                        try:
                            tree = ast.parse(f.read())
                            self._parse_ast(tree, rel_path)
                        except Exception:
                            continue
        return self.graph
    
    def _parse_ast(self, tree, file_name):
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_name = f"{node.name}()"
                unique_id = f"{file_name}::{node.name}"  # internal unique key
                self.graph.add_node(unique_id, type="function", display_name=func_name, file=file_name)
                
                # --- Extract metadata ---
                doc = ast.get_docstring(node)
                start = getattr(node, "lineno", 0)
                end = getattr(node, "end_lineno", start)
                loc = end - start
                params = [a.arg for a in node.args.args]
                
                # Attach metadata to the node
                nx.set_node_attributes(
                    self.graph,
                    {unique_id: {
                        "doc": doc or "",
                        "loc": loc,
                        "params": params,
                        "file": file_name,
                        "display_name": func_name
                    }}
                )

                # Link: function → its file
                self.graph.add_edge(unique_id, file_name, label="defined_in")

                # Link: function → functions it calls
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        # Handle foo(), self.foo(), module.foo()
                        if isinstance(child.func, ast.Name):
                            called_func = child.func.id
                        elif isinstance(child.func, ast.Attribute):
                            called_func = child.func.attr
                        else:
                            continue

                        called_func_name = f"{file_name}::{called_func}()"
                        self.graph.add_node(called_func_name, type="function")
                        self.graph.add_edge(unique_id, called_func_name, label="calls")

    '''def _build_file_graph(self):
        """
        Build file dependency graph based on import statements.
        Nodes: file names (relative to repo_path)
        Edges: fileA imports fileB
        """
        files = []
        for root, _, filenames in os.walk(self.repo_path):
            for file in filenames:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.repo_path)
                    files.append(rel_path)

        # Add file nodes
        for f in files:
            self.graph.add_node(f, type="file")

        # Parse imports to add edges
        for f in files:
            full_path = os.path.join(self.repo_path, f)
            try:
                with open(full_path, "r", encoding="utf-8") as file:
                    source = file.read()
                tree = ast.parse(source)
            except Exception as e:
                print(f"Failed to parse {f}: {e}")
                continue

            imported_files = self._get_imported_files(tree, files)
            for imp in imported_files:
                # edge: f imports imp
                if imp in files:
                    self.graph.add_edge(f, imp, type="file_import")'''

    def _get_imported_files(self, tree, files):
        """
        Extract relative file names from import statements.
        Only consider files in the repo.
        """
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    mod = alias.name.split('.')[0]
                    # try to match mod to a file
                    matched_file = self._match_module_to_file(mod, files)
                    if matched_file:
                        imported.add(matched_file)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    mod = node.module.split('.')[0]
                    matched_file = self._match_module_to_file(mod, files)
                    if matched_file:
                        imported.add(matched_file)
        return imported

    def _match_module_to_file(self, module_name, files):
        """
        Simple heuristic to match module name to file name.
        e.g. module 'file2' -> 'file2.py' in repo
        """
        candidate = module_name + ".py"
        for f in files:
            if os.path.basename(f) == candidate:
                return f
        return None

    '''def _build_function_graph(self):
        """
        Build function-level dependency graph.
        Nodes: (file, function_name)
        Edges: functionA calls functionB
        Also link functions to files.
        """
        for node in list(self.graph.nodes(data=True)):
            if node[1].get("type") == "file":
                file_node = node[0]
                full_path = os.path.join(self.repo_path, file_node)
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        source = f.read()
                    tree = ast.parse(source)
                except Exception as e:
                    print(f"Failed to parse {file_node} for functions: {e}")
                    continue

                # Find all functions in the file
                funcs = {}
                for item in tree.body:
                    if isinstance(item, ast.FunctionDef):
                        funcs[item.name] = item

                # Add function nodes and edges
                for func_name, func_node in funcs.items():
                    func_id = (file_node, func_name)
                    self.graph.add_node(func_id, type="function", file=file_node)

                    # Link function to file (edge)
                    self.graph.add_edge(file_node, func_id, type="file_contains")

                    # Find function calls inside this function
                    calls = self._find_function_calls(func_node)
                    for call in calls:
                        # Attempt to resolve call to (file, function) if possible
                        target_func_id = self._resolve_function_call(call, file_node)
                        if target_func_id:
                            self.graph.add_edge(func_id, target_func_id, type="function_calls")'''

    def _find_function_calls(self, func_node):
        """
        Return list of function names called inside this function.
        """
        calls = set()
        for node in ast.walk(func_node):
            if isinstance(node, ast.Call):
                # handle calls like foo(), self.foo(), module.foo()
                if isinstance(node.func, ast.Name):
                    calls.add(node.func.id)
                elif isinstance(node.func, ast.Attribute):
                    calls.add(node.func.attr)
        return calls

    def _resolve_function_call(self, call_name, current_file):
        """
        Try to resolve function call to a function node (file, func)
        Simple heuristic:
          - If function defined in current file, return that
          - Else check imported files for that function
          - Else return None
        """
        # Check if function is in current file
        candidate = (current_file, call_name)
        if self.graph.has_node(candidate):
            return candidate

        # Check functions in files imported by current_file
        imported_files = [tgt for src, tgt, data in self.graph.out_edges(current_file, data=True) if data.get("type") == "file_import"]
        for imp_file in imported_files:
            candidate = (imp_file, call_name)
            if self.graph.has_node(candidate):
                return candidate

        return None
