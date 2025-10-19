from pyvis.network import Network
from io import StringIO

def get_callers(graph, func_node):
    return list(graph.predecessors(func_node))

def get_callees(graph, func_node):
    return list(graph.successors(func_node))

def generate_file_layer(graph, node_types=None, edge_labels=None):
    net = Network(height="600px", width="100%", directed=True)
    for node, attrs in graph.nodes(data=True):
        if attrs.get("type") != "file":
            continue
        net.add_node(node, label=attrs.get("display_name", node), color="#FFD700", shape="box")
    
    for src, dst, attrs in graph.edges(data=True):
        if attrs.get("label") == "file_import":
            net.add_edge(src, dst, color="black", title="file_import")
    net.barnes_hut(gravity=-8000, central_gravity=0.3, spring_length=250, spring_strength=0.001, damping=0.5)
    return net.generate_html()

from pyvis.network import Network
import streamlit.components.v1 as components

from pyvis.network import Network

def generate_class_method_layer(graph, node_types=None, edge_labels=None):
    """
    Generates a PyVis HTML graph for classes and methods.
    Only includes nodes of type 'class' or 'function'.
    Only includes edges where both nodes exist in the layer.
    """

    net = Network(height="800px", width="100%", directed=True)

    # -----------------
    # Add only class and function nodes
    # -----------------
    layer_nodes = set()
    for node, attrs in graph.nodes(data=True):
        if attrs.get("type") not in ["class", "function"]:
            continue

        label = attrs.get("display_name", node)
        color = "#87CEEB" if attrs.get("type") == "class" else "#7BE0AD"
        shape = "box" if attrs.get("type") == "class" else "ellipse"
        title = (
            f"{node}\n"
            f"LOC: {attrs.get('loc','?')}\n"
            f"Params: {attrs.get('params','[]')}\n"
            f"Doc: {attrs.get('doc','')[:100]}"
        )

        net.add_node(node, label=label, color=color, shape=shape, title=title)
        layer_nodes.add(node)

    # -----------------
    # Add only edges connecting existing nodes in this layer
    # -----------------
    for src, dst, attrs in graph.edges(data=True):
        if attrs.get("label") not in ["defined_in", "calls", "has_method", "inherits"]:
            continue

        # Skip edges where either node is not in the layer
        if src not in layer_nodes or dst not in layer_nodes:
            continue

        color = {
            "calls": "#1f77b4",
            "defined_in": "#ff7f0e",
            "has_method": "#228B22",
            "inherits": "#6a0dad"
        }.get(attrs.get("label"), "black")

        dashes = attrs.get("label") in ["calls", "inherits"]
        net.add_edge(src, dst, color=color, dashes=dashes, title=attrs.get("label"))

    # -----------------
    # Layout/physics
    # -----------------
    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=200,
        spring_strength=0.002,
        damping=0.5
    )

    # -----------------
    # Legend
    # -----------------
    legend_html = """
    <div style='font-size:14px; margin-top:10px; padding:10px; border-top:1px solid #ccc;'>
        <b>Legend:</b><br>
        <span style='color:#FFD700;'>■ File Node</span><br>
        <span style='color:#87CEEB;'>■ Class Node</span><br>
        <span style='color:#7BE0AD;'>● Function Node</span><br>
        <span style='color:#ff7f0e;'>→ defined_in</span><br>
        <span style='color:#228B22;'>→ has_method</span><br>
        <span style='color:#1f77b4;'>⇢ calls</span><br>
        <span style='color:#6a0dad;'>⇢ inherits</span>
    </div>
    """

    html = net.generate_html()
    if "</body>" in html:
        html = html.replace("</body>", legend_html + "\n</body>")
    else:
        html += legend_html

    return html



def generate_graph_html(graph):
    net = Network(height="800px", width="100%", directed=True)

    # --- Add nodes ---
    for node, attrs in graph.nodes(data=True):
        node_type = attrs.get("type", "function")
        label = attrs.get("display_name", node)
        title = (
            f"{node}\n"
            f"LOC: {attrs.get('loc', '?')}\n"
            f"Params: {attrs.get('params', '[]')}\n"
            f"Doc: {attrs.get('doc', '')[:100]}"
        )

        if node_type == "file":
            color = "#FFD700"
            shape = "box"
            
        elif node_type == "class":
            color = "#87CEEB"  # light blue
            shape = "box"
            
        else:
            color = "#7BE0AD"
            shape = "ellipse"

        net.add_node(node, label=label, title=title, color=color, shape=shape)

    # --- Add edges ---
    for src, dst, attrs in graph.edges(data=True):
        label = attrs.get("label", "")
        if label == "calls":
            color = "#1f77b4"
            dashes = True
        elif label == "defined_in":
            color = "#ff7f0e"
            dashes = False
        else:
            color = "black"
            dashes = False

        net.add_edge(src, dst, title=label, color=color, dashes=dashes)

    # --- Layout ---
    net.repulsion()

    # --- Generate base HTML ---
    html = net.generate_html()

    # --- Add legend below graph ---
    legend_html = """
    <div style='font-size:14px; margin-top:10px; padding:10px; border-top:1px solid #ccc;'>
        <b>Legend:</b><br>
        <span style='color:#FFD700;'>■ File Node</span><br>
        <span style='color:#87CEEB;'>■ Class Node</span><br>
        <span style='color:#7BE0AD;'>● Function Node</span><br>
        <span style='color:#ff7f0e;'>→ defined_in</span><br>
        <span style='color:#1f77b4;'>⇢ calls</span>
    </div>
    """

    # Append legend just before </body>
    if "</body>" in html:
        html = html.replace("</body>", legend_html + "\n</body>")
    else:
        html += legend_html

    return html

def generate_full_semantic_layer(graph):
    net = Network(height="800px", width="100%", directed=True)

    # --- Nodes ---
    for node, attrs in graph.nodes(data=True):
        ntype = attrs.get("type")
        label = attrs.get("display_name", node)

        color, shape = {
            "file": ("#FFD700", "box"),
            "class": ("#87CEEB", "box"),
            "function": ("#7BE0AD", "ellipse"),
            "variable": ("#FFA07A", "dot"),
        }.get(ntype, ("#D3D3D3", "ellipse"))

        net.add_node(node, label=label, color=color, shape=shape)

    # --- Edges ---
    for src, dst, attrs in graph.edges(data=True):
        label = attrs.get("label", "")
        color = {
            "defined_in": "#ff7f0e",
            "has_method": "#228B22",
            "calls": "#1f77b4",
            "inherits": "#6a0dad",
            "defines_var": "#FF6347",
            "uses_var": "#32CD32",
            "mutates_var": "#DC143C",
            "param_type": "#20B2AA",
            "return_type": "#9370DB",
        }.get(label, "gray")

        dashes = label in ["calls", "inherits", "uses_var"]
        net.add_edge(src, dst, color=color, dashes=dashes, title=label)

    net.barnes_hut(
        gravity=-8000,
        central_gravity=0.3,
        spring_length=180,
        spring_strength=0.002,
        damping=0.5,
    )
    return net.generate_html()
