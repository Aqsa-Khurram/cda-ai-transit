import streamlit as st
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt

from pm4py.objects.log.importer.xes import importer as xes_importer

from task4_analytics import (
    compute_throughput_times,
    compute_transition_times,
    detect_bottlenecks
)

# ─────────────────────────────────────────────
# CORE FUNCTIONS (safe to import anywhere)
# ─────────────────────────────────────────────

def load_log(path):
    return xes_importer.apply(path)


def log_to_df(log):
    data = []

    for trace in log:
        route_id = trace.attributes.get("route:id", None)
        case_id = trace.attributes["concept:name"]

        for e in trace:
            data.append({
                "case": case_id,
                "route_id": route_id,
                "activity": e["concept:name"],
                "timestamp": e["time:timestamp"]
            })

    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def build_graph(df, transitions, bottlenecks, route_filter=None):

    if route_filter != "All":
        df = df[df["route_id"] == route_filter]

    df = df.sort_values(["case", "timestamp"])

    edges = {}

    for _, group in df.groupby("case"):
        rows = list(group.itertuples())

        for i in range(len(rows) - 1):

            src = rows[i].activity
            dst = rows[i + 1].activity

            duration = (rows[i + 1].timestamp - rows[i].timestamp).total_seconds() / 60

            key = (src, dst)

            if key not in edges:
                edges[key] = {"count": 0, "durations": []}

            edges[key]["count"] += 1
            edges[key]["durations"].append(duration)

    graph_edges = {}

    for (src, dst), val in edges.items():

        avg = sum(val["durations"]) / len(val["durations"])
        is_bottleneck = (src, dst) in bottlenecks

        graph_edges[(src, dst)] = {
            "label": f"{avg:.1f} min | {val['count']} trips",
            "avg": avg,
            "count": val["count"],
            "bottleneck": is_bottleneck
        }

    return graph_edges


def draw_graph(edges):

    G = nx.DiGraph()
    edge_colors = []

    for (src, dst), val in edges.items():
        G.add_edge(src, dst, label=val["label"])
        edge_colors.append("red" if val["bottleneck"] else "black")

    pos = nx.spring_layout(G, seed=42)

    plt.figure(figsize=(12, 7))

    nx.draw(
        G,
        pos,
        with_labels=True,
        node_size=2500,
        node_color="lightblue",
        edge_color=edge_colors,
        arrows=True
    )

    edge_labels = {(u, v): d["label"] for u, v, d in G.edges(data=True)}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

    st.pyplot(plt)


# ─────────────────────────────────────────────
# STREAMLIT APP (NOW PROPERLY WRAPPED)
# ─────────────────────────────────────────────

def run_dashboard():

    st.title("🚍 CDA Process Mining Dashboard (Task 3 + 4)")

    log = load_log("data/cda_event_log.xes")
    df = log_to_df(log)

    routes = ["All"] + sorted(df["route_id"].dropna().unique().tolist())
    selected_route = st.selectbox("Select Route", routes)

    filtered_df = df if selected_route == "All" else df[df["route_id"] == selected_route]

    # Analytics
    perf = compute_throughput_times(filtered_df)

    st.subheader("📊 Trip Performance (Throughput)")
    st.write(f"Average: {perf['avg']:.2f} min")
    st.write(f"Min: {perf['min']:.2f} min")
    st.write(f"Max: {perf['max']:.2f} min")

    transitions = compute_transition_times(filtered_df)
    bottlenecks, top3 = detect_bottlenecks(transitions, threshold=3.0)

    st.subheader("🚨 Top 3 Bottlenecks")
    st.write(top3)

    # Graph
    st.subheader("Process Map")

    edges = build_graph(df, transitions, bottlenecks, selected_route)
    draw_graph(edges)

    # Table
    st.subheader("Edge Statistics")

    table = [
        {
            "From": src,
            "To": dst,
            "Avg Duration (min)": round(val["avg"], 2),
            "Trips": val["count"],
            "Bottleneck": val["bottleneck"]
        }
        for (src, dst), val in edges.items()
    ]

    st.dataframe(pd.DataFrame(table))

def discover_process_map(log):
    return None
# ─────────────────────────────────────────────
# SAFE ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    run_dashboard()