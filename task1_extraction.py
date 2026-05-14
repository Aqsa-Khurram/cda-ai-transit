"""
Task 1: PDF Route Extraction → Structured routes.csv
CDA Bus Route Analysis - Process Mining Project

Reads multiple route PDFs and converts them into a clean CSV
usable by Task 2 (XES event log generator).
"""

import os
import re
import pdfplumber
import pandas as pd

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
PDF_FOLDER = "data/pdf_routes"
OUTPUT_CSV = "data/routes.csv"


# ─────────────────────────────────────────────
# PDF TEXT EXTRACTION
# ─────────────────────────────────────────────
def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


# ─────────────────────────────────────────────
# METADATA PARSER
# ─────────────────────────────────────────────
def parse_route_metadata(text):
    def find(pattern):
        match = re.search(pattern, text)
        return match.group(1).strip() if match else None

    route_id = find(r"Route ID\s+(\d+)")
    short_name = find(r"Short Name\s+([A-Za-z0-9\-]+)")
    long_name = find(r"Long Name\s+(.+)")
    direction = find(r"Direction\s+(\w+)")
    headway = find(r"Average Headway.*?(\d+)")

    return {
        "route_id": route_id,
        "short_name": short_name,
        "long_name": long_name,
        "direction": direction,
        "headway": int(headway) if headway else None
    }


# ─────────────────────────────────────────────
# STOP PARSER (CORE FIX)
# ─────────────────────────────────────────────
def parse_stops(text):
    stops = []

    # This regex handles messy spacing like:
    # "PIMS 05:45:00 05:45:00"
    pattern = r"([A-Za-z0-9 \-\(\)\/]+?)\s+(\d{2}:\d{2}:\d{2})\s+(\d{2}:\d{2}:\d{2})"

    matches = re.findall(pattern, text)

    sequence = 1
    for name, arrival, departure in matches:
        name = name.strip()

        # filter out junk matches (important)
        if len(name) < 2:
            continue
        if "Trip ID" in name:
            continue

        stops.append({
            "stop_sequence": sequence,
            "stop_name": name,
            "arrival_time": arrival,
            "departure_time": departure
        })

        sequence += 1

    return stops


# ─────────────────────────────────────────────
# PROCESS SINGLE PDF
# ─────────────────────────────────────────────
def process_pdf(pdf_path):
    text = extract_text(pdf_path)

    metadata = parse_route_metadata(text)
    stops = parse_stops(text)

    rows = []

    for stop in stops:
        row = {
            **metadata,
            **stop
        }
        rows.append(row)

    return rows


# ─────────────────────────────────────────────
# PROCESS ALL PDFs
# ─────────────────────────────────────────────
def process_all_pdfs(folder):
    all_rows = []

    for file in sorted(os.listdir(folder)):
        if file.endswith(".pdf"):
            print("Processing:", file)

            pdf_path = os.path.join(folder, file)
            rows = process_pdf(pdf_path)

            if rows:
                all_rows.extend(rows)
            else:
                print(f"WARNING: No data extracted from {file}")

    return pd.DataFrame(all_rows)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    print("Starting PDF extraction pipeline...\n")

    df = process_all_pdfs(PDF_FOLDER)

    print("\nColumns found:")
    print(list(df.columns))

    print("\nTotal extracted rows:", len(df))

    if len(df) == 0:
        print("\nERROR: No rows extracted. Check PDF structure or regex.")
        return

    # Save CSV
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)

    print(f"\nroutes.csv created → {OUTPUT_CSV}")
    print("\nSample data:")
    print(df.head())


if __name__ == "__main__":
    main()