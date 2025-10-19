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
        self._add_class_nodes_and_edges()
        self._resolve_function_calls()
        
        self.crossrefs = {
        "calls": self._group_edges_by_label("calls"),
        "inherits": self._group_edges_by_label("inherits"),
        "defines_var": self._group_edges_by_label("defines_var"),
        "uses_var": self._group_edges_by_label("uses_var"),
        }
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
                            
    def _add_class_nodes_and_edges(self):
        """Add class nodes, their methods, and inheritance relationships."""
        for rel in self.repo_files:
            with open(os.path.join(self.repo_path, rel), "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=rel)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    class_uid = f"{rel}::{class_name}"
                    doc = ast.get_docstring(node) or ""
                    start = getattr(node, "lineno", 0)
                    end = getattr(node, "end_lineno", start)
                    loc = end - start + 1
                    bases = [getattr(b, "id", getattr(b, "attr", "")) for b in node.bases]

                    # --- Add class node ---
                    self.graph.add_node(
                        class_uid,
                        type="class",
                        display_name=class_name,
                        file=rel,
                        loc=loc,
                        bases=bases,
                        doc=doc,
                    )

                    # --- Link: file → class ---
                    self.graph.add_edge(rel, class_uid, label="defined_in")

                    # --- Link: subclass → baseclass (if base exists) ---
                    for base in bases:
                        # Find if base class exists in same repo
                        for existing_node, attrs in self.graph.nodes(data=True):
                            if attrs.get("type") == "class" and attrs.get("display_name") == base:
                                self.graph.add_edge(class_uid, existing_node, label="inherits")
                                
                    # --- Add method nodes and edges: class → method ---
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            func_uid = f"{rel}::{class_name}::{child.name}"
                            display = f"{child.name}()"
                            start = getattr(child, "lineno", 0)
                            end = getattr(child, "end_lineno", start)
                            loc = end - start + 1
                            params = [a.arg for a in child.args.args]
                            doc = ast.get_docstring(child) or ""

                            # --- Add method node ---
                            self.graph.add_node(
                                func_uid,
                                type="function",
                                display_name=display,
                                file=rel,
                                class_name=class_name,
                                loc=loc,
                                params=params,
                                doc=doc,
                            )
                            
                            # --- Edge: class → method ---
                            self.graph.add_edge(class_uid, func_uid, label="has_method")

                            self._track_variables(child, rel)
                            self._track_types(child, func_uid)
                            self._track_method_calls(child, class_uid, func_uid)
                        '''# --- Link: class → its methods ---
                        for child in node.body:
                            if isinstance(child, ast.FunctionDef):
                                func_uid = f"{rel}::{child.name}"
                                if func_uid in self.graph.nodes:
                                    self.graph.add_edge(class_uid, func_uid, label="has_method")'''


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
                
                self._track_variables(fnode, rel)
                self._track_types(fnode, uid)

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
                caller_uid = f"{rel}::{fname}"  # top-level functions

                for node in ast.walk(fnode):
                    if not isinstance(node, ast.Call):
                        continue

                    callee_uid = self._resolve_callee(node, rel, caller_uid)
                    if callee_uid and self.graph.has_node(callee_uid):
                        self.graph.add_edge(caller_uid, callee_uid, label="calls")

        # --- Also handle class methods ---
        for rel in self.repo_files:
            with open(os.path.join(self.repo_path, rel), "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=rel)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_name = node.name
                    for child in node.body:
                        if isinstance(child, ast.FunctionDef):
                            caller_uid = f"{rel}::{class_name}::{child.name}"
                            for n in ast.walk(child):
                                if isinstance(n, ast.Call):
                                    callee_uid = self._resolve_callee(n, rel, caller_uid, class_name)
                                    if callee_uid and self.graph.has_node(callee_uid):
                                        self.graph.add_edge(caller_uid, callee_uid, label="calls")

    # ----------------------------------------------------------
    def _resolve_callee(self, node, rel, caller_uid = None, current_class = None):
        """Try to resolve a call node to an existing function UID in the repo."""
        # Case 1: foo()F
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in self.builtin_names:
                return None
            # same file top-level function
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
            # imported module?
            mapped_mod = self.imports_by_file.get(rel, {}).get(owner)
            if mapped_mod:
                matched = self._match_module_to_file(mapped_mod)
                if matched:
                    return f"{matched}::{attr}"

        # Case 3: self.method() or super().method()
        elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            val = node.func.value.id
            attr = node.func.attr
            if val == "self" and current_class:
                candidate = f"{rel}::{current_class}::{attr}"
                if self.graph.has_node(candidate):
                    return candidate
            elif val == "super" and current_class:
                # find base class
                bases = [
                    a.get("display_name")
                    for n, a in self.graph.nodes(data=True)
                    if n == f"{rel}::{current_class}"
                ]
                if bases:
                    base_class_name = bases[0]  # assume single inheritance
                    candidate = f"{rel}::{base_class_name}::{attr}"
                    if self.graph.has_node(candidate):
                        return candidate
        return None
    # ----------------------------------------------------------
    def _match_module_to_file(self, module_name):
        """Find the repo file corresponding to a module name."""
        candidate = module_name + ".py"
        for f in self.repo_files:
            if os.path.basename(f) == candidate:
                return f
        return None
    #------------------------------------------------------------
    '''def _track_variables(self, node, file_rel):
        """Add variable definition, usage, and mutation edges."""
        for child in ast.walk(node):
            # Definitions
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        var_uid = f"{file_rel}::{target.id}"
                        self.graph.add_node(
                            var_uid,
                            type="variable",
                            display_name=target.id,
                            defined_in=file_rel,
                        )
                        self.graph.add_edge(file_rel, var_uid, label="defines_var")

            # Mutations (augmented assignments)
            elif isinstance(child, ast.AugAssign):
                if isinstance(child.target, ast.Name):
                    var_uid = f"{file_rel}::{child.target.id}"
                    if var_uid in self.graph.nodes:
                        self.graph.add_edge(var_uid, file_rel, label="mutated_in")

            # Usage
            elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                var_uid = f"{file_rel}::{child.id}"
                if var_uid in self.graph.nodes:
                    self.graph.add_edge(file_rel, var_uid, label="uses_var")

    def _track_types(self, func_node, func_uid):
        """Capture argument and return types if annotated."""
        if hasattr(func_node, "returns") and func_node.returns:
            self.graph.nodes[func_uid]["return_type"] = ast.unparse(func_node.returns)
        for arg in func_node.args.args:
            if arg.annotation:
                self.graph.nodes[func_uid].setdefault("arg_types", {})[arg.arg] = ast.unparse(arg.annotation)

    def _track_method_calls(self, node, current_class_uid, current_func_uid):
        """Detect self.method() or super().method() calls."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                # self.method()
                if isinstance(child.func, ast.Attribute):
                    if isinstance(child.func.value, ast.Name) and child.func.value.id in {"self", "super"}:
                        callee_name = child.func.attr
                        callee_uid = f"{current_class_uid}::{callee_name}"
                        if callee_uid in self.graph.nodes:
                            self.graph.add_edge(current_func_uid, callee_uid, label="calls_method")'''
                            
    def _track_variables(self, node, context_uid):
        for subnode in ast.walk(node):
            # --- Definitions ---
            if isinstance(subnode, ast.Assign):
                for target in subnode.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        var_uid = f"{context_uid}::{var_name}"
                        self.graph.add_node(var_uid, type="variable", display_name=var_name)
                        self.graph.add_edge(context_uid, var_uid, label="defines_var")

            # --- Mutations (+=, -=, etc.) ---
            elif isinstance(subnode, ast.AugAssign):
                if isinstance(subnode.target, ast.Name):
                    var_name = subnode.target.id
                    var_uid = f"{context_uid}::{var_name}"
                    self.graph.add_node(var_uid, type="variable", display_name=var_name)
                    self.graph.add_edge(context_uid, var_uid, label="mutates_var")

            # --- Usages ---
            elif isinstance(subnode, ast.Name):
                if isinstance(subnode.ctx, ast.Load):
                    var_name = subnode.id
                    var_uid = f"{context_uid}::{var_name}"
                    if self.graph.has_node(var_uid):
                        self.graph.add_edge(var_uid, context_uid, label="uses_var")


    def _track_types(self, node, func_uid):
        if not isinstance(node, ast.FunctionDef):
            return

        # Parameter types
        for arg in node.args.args:
            if arg.annotation:
                type_name = self._get_type_name(arg.annotation)
                self.graph.add_node(type_name, type="type", display_name=type_name)
                self.graph.add_edge(func_uid, type_name, label="param_type")

        # Return type
        if node.returns:
            type_name = self._get_type_name(node.returns)
            self.graph.add_node(type_name, type="type", display_name=type_name)
            self.graph.add_edge(func_uid, type_name, label="return_type")

    def _get_type_name(self, ann):
        if isinstance(ann, ast.Name):
            return ann.id
        elif isinstance(ann, ast.Subscript):
            base = self._get_type_name(ann.value)
            sub = self._get_type_name(ann.slice)
            return f"{base}[{sub}]"
        elif isinstance(ann, ast.Attribute):
            return f"{ann.value.id}.{ann.attr}" if isinstance(ann.value, ast.Name) else ann.attr
        else:
            return ast.unparse(ann) if hasattr(ast, "unparse") else str(ann)


    def _track_method_calls(self, node, class_uid, func_uid):
        for subnode in ast.walk(node):
            if isinstance(subnode, ast.Call) and isinstance(subnode.func, ast.Attribute):
                if isinstance(subnode.func.value, ast.Name) and subnode.func.value.id in {"self", "super"}:
                    called_name = subnode.func.attr
                    called_uid = f"{class_uid}::{called_name}"
                    if self.graph.has_node(called_uid):
                        self.graph.add_edge(func_uid, called_uid, label="calls")

    def _group_edges_by_label(self, label):
        edges = {}
        for u, v, d in self.graph.edges(data=True):
            if d.get("label") == label:
                edges.setdefault(u, []).append(v)
        return edges
    
    def find_variable_updates(self, var_name):
        """Find where a variable is defined or mutated."""
        results = []
        for u, v, d in self.graph.edges(data=True):
            if d.get("label") in {"defines_var", "mutated_in"} and var_name in v:
                results.append((u, v, d["label"]))
        return results

    def find_call_chain(self, func_uid, depth=3):
        """Find downstream call chain up to given depth."""
        chain = []
        def dfs(node, level):
            if level > depth:
                return
            for _, callee, d in self.graph.out_edges(node, data=True):
                if d.get("label") == "calls":
                    chain.append((node, callee))
                    dfs(callee, level + 1)
        dfs(func_uid, 1)
        return chain