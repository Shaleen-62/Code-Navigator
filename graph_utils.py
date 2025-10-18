from pyvis.network import Network
from io import StringIO

def get_callers(graph, func_node):
    return list(graph.predecessors(func_node))

def get_callees(graph, func_node):
    return list(graph.successors(func_node))

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