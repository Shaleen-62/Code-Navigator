from pyvis.network import Network
from io import StringIO

def get_callers(graph, func_node):
    return list(graph.predecessors(func_node))

def get_callees(graph, func_node):
    return list(graph.successors(func_node))

def generate_graph_html(graph):
    net = Network(height="800px", width="100%", directed=True)

    for node, attrs in graph.nodes(data=True):
        title = f"{node}\nLOC: {attrs.get('loc','?')}\nParams: {attrs.get('params','[]')}\nDoc: {attrs.get('doc','')[:100]}"
        label = attrs.get("display_name", node)
        net.add_node(node, label=label, title=title, color="#FFD700" if attrs.get("type") == "file" else "#7BE0AD")
        if attrs.get("type") == "file":
            net.add_node(node, label=node, color="#FFD700", shape="box")
        else:
            net.add_node(node, label=node, color="#7BE0AD", shape="ellipse")

    for src, dst, attrs in graph.edges(data=True):
        label = attrs.get("label", "")
        color = "black"
        dashes = False
        if label == "calls":
            color = "#1f77b4"
            dashes = True
        elif label == "defined_in":
            color = "#ff7f0e"

        net.add_edge(src, dst, title=label, color=color, dashes=dashes)

    net.repulsion()
    html = net.generate_html()
    legend_html = """
    <div style='font-size:14px; margin-top:10px;'>
        <b>Legend:</b><br>
        <span style='color:#FFD700;'>■ File Node</span><br>
        <span style='color:#7BE0AD;'>● Function Node</span><br>
        <span style='color:#ff7f0e;'>→ defined_in</span><br>
        <span style='color:#1f77b4;'>⇢ calls</span>
    </div>
    """
    return html + legend_html
