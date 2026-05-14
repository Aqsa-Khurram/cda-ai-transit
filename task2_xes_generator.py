import csv
import os
from datetime import datetime
from xml.etree.ElementTree import Element, SubElement, ElementTree, indent

INPUT_CSV = "data/routes.csv"
OUTPUT_XES = "data/cda_event_log.xes"

BASE_DATE = "2026-04-23"


def _str(p, k, v):
    e = SubElement(p, "string")
    e.set("key", k)
    e.set("value", str(v))


def _int(p, k, v):
    e = SubElement(p, "int")
    e.set("key", k)
    e.set("value", str(v))


def _date(p, k, v):
    e = SubElement(p, "date")
    e.set("key", k)
    e.set("value", str(v))


def load_routes(csv_path):
    routes = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            route_id = row["route_id"]
            routes.setdefault(route_id, []).append(row)

    # sort by stop sequence
    for r in routes:
        routes[r].sort(key=lambda x: int(x["stop_sequence"]))

    return routes


def build_xes(routes):

    log = Element("log")
    log.set("xes.version", "1.0")
    log.set("xes.features", "nested-attributes")
    log.set("xmlns", "http://www.xes-standard.org/")

    _str(log, "concept:name", "CDA Bus Event Log")
    _str(log, "lifecycle:model", "standard")

    case_id = 1

    for route_id, rows in routes.items():

        direction = rows[0]["direction"]

        trace = SubElement(log, "trace")

        _str(trace, "concept:name", f"{route_id}_{direction}")
        _str(trace, "route:id", route_id)
        _str(trace, "direction", direction)
        _int(trace, "case:id", case_id)

        for row in rows:

            event = SubElement(trace, "event")

            _str(event, "concept:name", row["stop_name"])
            _str(event, "route:id", route_id)
            _str(event, "direction", direction)

            _int(event, "stop:sequence", int(row["stop_sequence"]))

            _str(event, "lifecycle:transition", "complete")

            # REAL timestamps (no modification)
            _date(event, "time:timestamp", f"{BASE_DATE}T{row['arrival_time']}+05:00")
            _date(event, "time:departure", f"{BASE_DATE}T{row['departure_time']}+05:00")

            _str(event, "org:resource", f"Bus_{route_id}")

        case_id += 1

    return log


def main():

    print("Loading CSV...")
    routes = load_routes(INPUT_CSV)

    print(f"Routes loaded: {len(routes)}")

    log = build_xes(routes)

    indent(log, space="  ")

    tree = ElementTree(log)

    os.makedirs(os.path.dirname(OUTPUT_XES), exist_ok=True)

    tree.write(OUTPUT_XES, encoding="utf-8", xml_declaration=True)

    print(f"\nXES generated → {OUTPUT_XES}")
    print("Using REAL timestamps from dataset ✔")


if __name__ == "__main__":
    main()