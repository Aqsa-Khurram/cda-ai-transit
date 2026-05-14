# CDA Bus Route Analysis — Process Mining & AI Trip Planner

A process mining and AI-powered transit analysis system for the CDA bus network in Islamabad & Rawalpindi. The project transforms raw PDF timetables into structured datasets, process mining logs, analytics dashboards, AI trip planning services, and interactive route visualizations.

Developed for the SE4009 — Process Mining and Simulation course at FAST National University.

---

# Features

- PDF timetable extraction
- XES event log generation
- Process mining dashboard
- Bottleneck detection & analytics
- AI-powered trip planner
- Interactive route visualization
- NLP-based route queries
- Graph-based shortest path routing

---

# Technology Stack

| Layer | Technologies |
|---|---|
| Data Extraction | Python, pdfplumber, pandas, regex |
| Process Mining | pm4py, NetworkX, matplotlib |
| Analytics | pandas |
| AI/NLP | Claude API, difflib |
| Visualization | Streamlit, Leaflet.js, OSRM |
| GUI | Tkinter |

---

# Project Structure

```bash
CDA-Bus-Route-Analysis/
│
├── data/
│   ├── pdf_routes/
│   ├── routes.csv
│   └── routes.xes
│
├── task1_extraction.py
├── task2_xes_generation.py
├── task3_dashboard.py
├── task4_analytics.py
├── task5_ai_planner.py
├── task6_personal_routes.py
├── gui.py
├── requirements.txt
└── README.md
```

---

# Tasks Overview

## Task 1 — PDF Route Extraction
Extracts structured route data from CDA timetable PDFs and generates:

```bash
routes.csv
```

## Task 2 — XES Event Log Generation
Converts CSV route data into IEEE-compliant XES event logs:

```bash
routes.xes
```

## Task 3 — Process Mining Dashboard
Interactive Streamlit dashboard for:
- Route visualization
- Process graphs
- Bottleneck inspection
- Performance analytics

## Task 4 — Analytics & Bottleneck Detection
Computes:
- Throughput times
- Transition durations
- Slowest route segments

## Task 5 — AI Trip Planner
Supports natural language transit queries such as:

```text
How do I travel from Khanna Pul to NUST?
Which route goes through Faizabad?
```

Features:
- Claude API integration
- Regex fallback parser
- Fuzzy stop matching
- Dijkstra shortest-path routing

## Task 6 — Personal Route Visualization
Displays:
- Interactive maps
- GPS-based routes
- Route overlays

---

# Installation

## Clone Repository

```bash
git clone https://github.com/your-username/cda-bus-route-analysis.git
cd cda-bus-route-analysis
```

## Create Virtual Environment

```bash
python -m venv venv
```

### Windows
```bash
venv\Scripts\activate
```

### Linux / Mac
```bash
source venv/bin/activate
```

## Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Usage

## Run PDF Extraction

```bash
python task1_extraction.py
```

## Generate XES Logs

```bash
python task2_xes_generation.py
```

## Launch Dashboard

```bash
streamlit run task3_dashboard.py
```

## Run AI Planner

```bash
python task5_ai_planner.py
```

## Launch GUI

```bash
python gui.py
```

---

# Example Queries

```text
Travel from FAST University to PIMS
Which route goes through Faizabad?
Last bus from Sohan?
```

---

# Core Algorithms

- Dijkstra Shortest Path
- A* Search
- Graph Traversal
- Fuzzy String Matching

---

# Future Improvements

- Real-time GPS integration
- Live arrival prediction
- Multi-modal routing
- Accessibility improvements

---

# References

- PM4Py
- NetworkX
- Claude API
- Leaflet.js
- OSRM

---

# License

This project was developed for academic purposes at FAST National University.
