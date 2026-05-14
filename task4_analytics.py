from collections import defaultdict
import pandas as pd

# ─────────────────────────────────────────────
# 4a — Throughput Time per Trip
# ─────────────────────────────────────────────

def compute_throughput_times(df):

    results = []

    for case, group in df.groupby("case"):

        group = group.sort_values("timestamp")

        start_time = group.iloc[0]["timestamp"]
        end_time = group.iloc[-1]["timestamp"]

        duration = (end_time - start_time).total_seconds() / 60  # minutes

        results.append(duration)

    return {
        "min": min(results),
        "max": max(results),
        "avg": sum(results) / len(results)
    }


# ─────────────────────────────────────────────
# 4b — Transition Time Computation
# ─────────────────────────────────────────────

def compute_transition_times(df):

    transitions = defaultdict(list)

    df = df.sort_values(["case", "timestamp"])

    for case, group in df.groupby("case"):

        rows = list(group.itertuples())

        for i in range(len(rows) - 1):

            src = rows[i].activity
            dst = rows[i + 1].activity

            t1 = rows[i].timestamp
            t2 = rows[i + 1].timestamp

            duration = (t2 - t1).total_seconds() / 60  # minutes

            transitions[(src, dst)].append(duration)

    avg_transitions = {
        k: sum(v) / len(v)
        for k, v in transitions.items()
    }

    return avg_transitions


# ─────────────────────────────────────────────
# Bottleneck Detection
# ─────────────────────────────────────────────

def detect_bottlenecks(transitions, threshold):

    bottlenecks = {
        k: v for k, v in transitions.items()
        if v > threshold
    }

    # Top 3 slowest
    top3 = sorted(
        transitions.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    return bottlenecks, top3


# ─────────────────────────────────────────────
# Helper for GUI display
# ─────────────────────────────────────────────

def build_performance_table(transitions):

    return pd.DataFrame([
        {
            "From": k[0],
            "To": k[1],
            "Avg Time (min)": round(v, 2)
        }
        for k, v in transitions.items()
    ])