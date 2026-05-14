import pandas as pd
import networkx as nx
from difflib import get_close_matches
from datetime import datetime


def norm(x: str) -> str:
    return str(x).strip().lower()


def _time_to_minutes(t: str) -> float:
    """Convert HH:MM:SS string to total minutes as float."""
    try:
        parts = str(t).strip().split(":")
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        return h * 60 + m + s / 60
    except Exception:
        return 0.0


def _minutes_to_hhmm(minutes: float) -> str:
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h:02d}:{m:02d}"


class TripPlanner:

    def __init__(self, log, routes_file: str):
        self.log = log
        self.routes_file = routes_file

        # Directed graph — A→B and B→A can differ
        self.graph = nx.DiGraph()

        self.stop_routes: dict[str, set] = {}        # norm_stop → {route_id, …}
        self.route_stops: dict[str, list] = {}       # route_id  → [norm stop names in order]
        self.route_short_name: dict[str, str] = {}   # route_id  → "FR-01"
        self.stop_fr_names: dict[str, set] = {}      # norm_stop → {"FR-01", …}

        # Full timetable per route:
        # route_id → [ {stop, arr_min, dep_min, arr_str, dep_str}, … ]
        self.route_schedule: dict[str, list] = {}

        self.build_graph()

    # ─────────────────────────────────────────────────────────────
    # BUILD GRAPH
    # ─────────────────────────────────────────────────────────────
    def build_graph(self):
        df = pd.read_csv(self.routes_file)

        # ── KEY FIX: group by (route_id, direction) so that Forward and
        # Backward stop sequences are never interleaved with each other.
        # Without this, stops from both directions get merged under one
        # route_id, sorted by stop_sequence (which resets to 1 for each
        # direction), producing nonsensical consecutive pairs and near-zero
        # edge weights (e.g. Khanna Pul → NUST shown as 0 min).
        group_cols = ["route_id", "direction"] if "direction" in df.columns else ["route_id"]

        for keys, group in df.groupby(group_cols):
            # Build a stable composite key so route_id remains unique per direction
            if isinstance(keys, tuple):
                route_id, direction = str(keys[0]), str(keys[1])
            else:
                route_id, direction = str(keys), ""

            composite_id = f"{route_id}_{direction}" if direction else route_id

            group = group.sort_values("stop_sequence")

            stops     = group["stop_name"].tolist()
            arr_times = group["arrival_time"].tolist()
            dep_times = group["departure_time"].tolist()

            short_name = (
                str(group["short_name"].iloc[0])
                if "short_name" in group.columns
                else route_id
            )
            self.route_short_name[composite_id] = short_name
            self.route_stops[composite_id] = [norm(s) for s in stops]

            # ── Store full schedule with both arrival & departure ──
            schedule = []
            for s, arr, dep in zip(stops, arr_times, dep_times):
                schedule.append({
                    "stop":    norm(s),
                    "arr_min": _time_to_minutes(arr),
                    "dep_min": _time_to_minutes(dep),
                    "arr_str": str(arr),
                    "dep_str": str(dep),
                })
            self.route_schedule[composite_id] = schedule

            for i in range(len(stops) - 1):
                src = norm(stops[i])
                dst = norm(stops[i + 1])

                # ── CORRECT travel time ──
                # In-motion time = arrival at NEXT stop − departure from THIS stop.
                # This correctly excludes dwell time at both stops.
                travel_time = schedule[i + 1]["arr_min"] - schedule[i]["dep_min"]

                # Skip corrupt/negative legs (can happen at direction wrap-around
                # or midnight crossings in the raw data).
                if travel_time <= 0:
                    continue

                # Keep fastest known time for this directed edge
                if self.graph.has_edge(src, dst):
                    if travel_time < self.graph[src][dst]["weight"]:
                        self.graph[src][dst]["weight"] = travel_time
                        self.graph[src][dst]["time"]   = travel_time
                else:
                    self.graph.add_edge(src, dst, weight=travel_time, time=travel_time)

                self.stop_routes.setdefault(src, set()).add(composite_id)
                self.stop_routes.setdefault(dst, set()).add(composite_id)
                self.stop_fr_names.setdefault(src, set()).add(short_name)
                self.stop_fr_names.setdefault(dst, set()).add(short_name)

    # ─────────────────────────────────────────────────────────────
    # STOP RESOLVER
    # ─────────────────────────────────────────────────────────────
    def resolve_stop(self, name: str) -> str | None:
        if not name:
            return None
        name = norm(name)
        if name in self.graph.nodes:
            return name
        candidates = [n for n in self.graph.nodes if name in n or n in name]
        if candidates:
            return max(candidates, key=len)
        matches = get_close_matches(name, list(self.graph.nodes), n=1, cutoff=0.45)
        return matches[0] if matches else None

    def suggest_stops(self, name: str, n: int = 3) -> list[str]:
        name = norm(name)
        return get_close_matches(name, list(self.graph.nodes), n=n, cutoff=0.35)

    def debug_resolve(self, name: str) -> str:
        """
        Diagnostic helper — shows exactly which graph node a stop name resolves to.
        Useful when travel times look wrong.
        Usage:  print(planner.debug_resolve("NUST Metro Station"))
        """
        resolved = self.resolve_stop(name)
        nust_ish = [n for n in sorted(self.graph.nodes) if "nust" in n]
        return (
            f"Input:    '{name}'\n"
            f"Resolved: '{resolved}'\n"
            f"NUST-related nodes in graph: {nust_ish}\n"
            f"Total nodes: {len(self.graph.nodes)}"
        )

    # ─────────────────────────────────────────────────────────────
    # ROUTE QUERIES
    # ─────────────────────────────────────────────────────────────
    def find_route(self, source, destination):
        src = self.resolve_stop(source)
        dst = self.resolve_stop(destination)
        if not src or not dst:
            return None
        try:
            return nx.shortest_path(self.graph, src, dst, weight="weight")
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def _scheduled_segment_time(self, src: str, dst: str) -> float:
        """
        Return the scheduled in-motion time (minutes) from stop src to stop dst.

        For each consecutive pair of stops on the route between src and dst,
        we compute  arrival[k+1] − departure[k]  (pure travel, no dwell).

        Guards:
        - Each individual leg is floored at 0.5 min (never 0 or negative).
          A negative value means the XES/CSV has a corrupt timestamp for that
          stop (e.g. "Nust Metro Station" with 06:00 on a route that starts
          at 07:15); we fall back to the graph edge weight in that case.
        - The total for a multi-stop segment is also floored at 0.5 min.
        - Falls back to the graph edge weight when no schedule covers this pair.
        """
        MIN_LEG = 0.5   # 30-second minimum per leg

        best = None

        common_routes = (
            self.stop_routes.get(src, set()) &
            self.stop_routes.get(dst, set())
        )

        for route_id in common_routes:
            schedule   = self.route_schedule.get(route_id, [])
            stops_norm = [e["stop"] for e in schedule]

            if src not in stops_norm or dst not in stops_norm:
                continue

            idx_src = stops_norm.index(src)
            idx_dst = stops_norm.index(dst)

            if idx_src >= idx_dst:
                continue   # wrong direction on this route

            t = 0.0
            valid = True
            for k in range(idx_src, idx_dst):
                leg = schedule[k + 1]["arr_min"] - schedule[k]["dep_min"]
                if leg <= 0:
                    # Corrupt timestamp in this route's schedule for this leg.
                    # Discard the whole route candidate and try others.
                    valid = False
                    break
                t += leg

            if not valid:
                continue

            t = max(t, MIN_LEG)
            if best is None or t < best:
                best = t

        # Fallback: use the graph edge weight that was set during build_graph
        # (also computed from the schedule, but kept as a pre-built cache)
        if best is None and self.graph.has_edge(src, dst):
            best = max(self.graph[src][dst]["weight"], MIN_LEG)

        return best if best is not None else 3.0

    def travel_time(self, source, destination) -> float | None:
        """
        Total scheduled travel time along the optimal path, in minutes.
        Sums _scheduled_segment_time for each hop in the path.

        Returns None (not 0) if stops can't be resolved, resolve to the same
        node (which would silently give 0 min), or no path exists.
        """
        src = self.resolve_stop(source)
        dst = self.resolve_stop(destination)

        if not src or not dst:
            return None

        # If two different names collapse to the same graph node after fuzzy
        # resolution, the path would be length-1 and travel time would be 0.
        # Treat this as "not found" so the caller gets a clear error instead.
        if src == dst:
            return None

        path = self.find_route(src, dst)
        if not path or len(path) < 2:
            return None

        return sum(
            self._scheduled_segment_time(path[i], path[i + 1])
            for i in range(len(path) - 1)
        )

    # ─────────────────────────────────────────────────────────────
    def routes_through(self, stop: str) -> list:
        s = self.resolve_stop(stop)
        return sorted(list(self.stop_routes.get(s, []))) if s else []

    def fr_names_through(self, stop: str) -> list[str]:
        s = self.resolve_stop(stop)
        return sorted(list(self.stop_fr_names.get(s, []))) if s else []

    def direct_routes(self, source: str, destination: str) -> list:
        src = self.resolve_stop(source)
        dst = self.resolve_stop(destination)
        if not src or not dst:
            return []
        shared = self.stop_routes.get(src, set()) & self.stop_routes.get(dst, set())
        return sorted([str(r) for r in shared])

    # ─────────────────────────────────────────────────────────────
    # SCHEDULE QUERIES
    # ─────────────────────────────────────────────────────────────
    def next_departure(self, stop, after_time=None):
        s = self.resolve_stop(stop)
        if not s:
            return None

        ref = (
            _time_to_minutes(after_time)
            if after_time
            else datetime.now().hour * 60 + datetime.now().minute
        )

        best = None
        for route_id in self.stop_routes.get(s, set()):
            for entry in self.route_schedule.get(route_id, []):
                if entry["stop"] != s:
                    continue
                if entry["dep_min"] >= ref:
                    if not best or entry["dep_min"] < best["minutes"]:
                        best = {
                            "route":   route_id,
                            "fr":      self.route_short_name.get(route_id, route_id),
                            "time":    _minutes_to_hhmm(entry["dep_min"]),
                            "minutes": entry["dep_min"],
                        }
        return best

    def last_bus(self, stop: str):
        s = self.resolve_stop(stop)
        if not s:
            return None

        last = None
        for route_id in self.stop_routes.get(s, set()):
            for entry in self.route_schedule.get(route_id, []):
                if entry["stop"] != s:
                    continue
                latest_min = entry["dep_min"] + (8 - 1) * 60  # 8 daily trips
                if not last or latest_min > last["minutes"]:
                    last = {
                        "route":   route_id,
                        "fr":      self.route_short_name.get(route_id, route_id),
                        "time":    _minutes_to_hhmm(latest_min),
                        "minutes": latest_min,
                    }
        return last

    def personal_route(self, source: str, home_stop: str):
        src = self.resolve_stop(source)
        dst = self.resolve_stop(home_stop)
        if not src or not dst:
            return None
        path = self.find_route(src, dst)
        if not path:
            return None
        return {"path": path, "time": self.travel_time(src, dst)}

    # ─────────────────────────────────────────────────────────────
    # ANSWER HELPERS  (called by AI agent)
    # ─────────────────────────────────────────────────────────────
    def _answer_route(self, raw_src, raw_dst):
        src = self.resolve_stop(raw_src)
        dst = self.resolve_stop(raw_dst)

        if not src:
            sug = self.suggest_stops(raw_src)
            msg = f"⚠️ Source stop not found: '{raw_src}'"
            if sug:
                msg += "\n\nDid you mean:\n" + "\n".join(f"  • {t.title()}" for t in sug)
            return msg

        if not dst:
            sug = self.suggest_stops(raw_dst)
            msg = f"⚠️ Destination stop not found: '{raw_dst}'"
            if sug:
                msg += "\n\nDid you mean:\n" + "\n".join(f"  • {t.title()}" for t in sug)
            return msg

        path = self.find_route(src, dst)
        if not path:
            return f"No route found between {src.title()} and {dst.title()}."

        total_time = self.travel_time(src, dst)
        direct     = self.direct_routes(src, dst)

        path_display = []
        for stop in path:
            frs    = sorted(self.stop_fr_names.get(stop, []))
            fr_str = f" [{', '.join(frs)}]" if frs else ""
            path_display.append(f"{stop.title()}{fr_str}")

        lines = [
            f"🚍 {src.title()} → {dst.title()}",
            f"⏱ Estimated travel time: {total_time:.0f} min  ({len(path)-1} stops)",
            "",
            "📍 Stops:",
            "  →  ".join(path_display),
        ]

        if direct:
            fr_list = [self.route_short_name.get(r, r) for r in direct]
            lines.append(f"\n✅ Direct routes: {', '.join(fr_list)}")
        else:
            lines.append("\n🔄 Transfer required along this path.")

        return "\n".join(lines)

    def _answer_routes_through(self, stop):
        s = self.resolve_stop(stop)
        if not s:
            sug = self.suggest_stops(stop)
            msg = f"⚠️ Stop not found: '{stop}'"
            if sug:
                msg += "\n\nDid you mean:\n" + "\n".join(f"  • {t.title()}" for t in sug)
            return msg

        route_ids = self.routes_through(s)
        if not route_ids:
            return f"No routes found through {s.title()}."

        pairs = [f"{self.route_short_name.get(rid, rid)} (ID {rid})" for rid in route_ids]
        return (
            f"🚏 Routes through {s.title()}:\n"
            + "\n".join(f"  • {p}" for p in pairs)
        )

    def _answer_last_bus(self, raw_stop: str) -> str:
        s = self.resolve_stop(raw_stop)
        if not s:
            sug = self.suggest_stops(raw_stop)
            msg = f"⚠️ Stop not found: '{raw_stop}'"
            if sug:
                msg += "\n\nDid you mean:\n" + "\n".join(f"  • {t.title()}" for t in sug)
            return msg

        lb = self.last_bus(s)
        if not lb:
            return f"No schedule data for {s.title()}."

        note = (
            f"\nℹ️ (matched '{raw_stop}' → '{s.title()}')"
            if norm(raw_stop) != s else ""
        )
        return (
            f"🕒 Last bus from {s.title()}:{note}\n"
            f"    {lb['fr']} (Route {lb['route']}) departs at {lb['time']}"
        )

    def _answer_travel_time(self, a, b):
        src  = self.resolve_stop(a)
        dst  = self.resolve_stop(b)
        if not src or not dst:
            return "One or both stops not found."

        path = self.find_route(src, dst)
        t    = self.travel_time(src, dst)
        if t is None or path is None:
            return f"No route found between {a} and {b}."

        # Show per-hop breakdown so the user can verify
        lines   = [
            f"⏱ Travel time from {src.title()} to {dst.title()}: {t:.0f} min",
            f"📍 Path ({len(path)-1} stops):",
        ]
        running = 0.0
        for i in range(len(path) - 1):
            seg      = self._scheduled_segment_time(path[i], path[i + 1])
            running += seg
            lines.append(
                f"   {path[i].title()}  →  {path[i+1].title()}"
                f"  ({seg:.1f} min,  running total: {running:.0f} min)"
            )
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────
    def answer_query(self, query):
        return "Use AI agent"