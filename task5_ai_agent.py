"""
Task 5: Agentic AI Trip Planner — RouteAIAgent
CDA Bus Route Analysis - Process Mining Project
FAST National University - SE4009
"""

import json
import re
import urllib.request


SYSTEM_PROMPT = """You are a transit assistant for the CDA (Capital Development Authority) bus network in Islamabad, Pakistan.

Your job is to parse the user's natural-language query and extract structured intent.

ALWAYS respond with ONLY a valid JSON object (no markdown, no explanation) in one of these formats:

1. Route query (travel from A to B, find route, options, connect, what are my options):
{"intent": "route", "source": "<stop name>", "destination": "<stop name>"}

2. Stop-through query (which route goes through / passes / stops at X):
{"intent": "routes_through", "stop": "<stop name>"}

3. Travel time query (how long, how much time, duration):
{"intent": "travel_time", "source": "<stop name>", "destination": "<stop name>"}

4. Last bus / schedule query (last bus, last departure, what time does the last bus leave):
{"intent": "last_bus", "stop": "<stop name>"}

5. Unknown / general:
{"intent": "unknown"}

Extract stop names exactly as the user wrote them (preserve case, do not normalize).
Common CDA stops: Khanna Pul, NUST, Faizabad, G-9 Markaz, F-10 Markaz, PIMS Hospital,
Sohan, I-8, I-8 Markaz, G-9/4 park, Police Foundation, FAST Uni, Zero Point, H-8.
"""


class RouteAIAgent:

    def __init__(self, planner, analytics=None):
        self.planner = planner
        self.analytics = analytics
        self._api_available = True

    def ask(self, query: str) -> str:
        if not query.strip():
            return "Please enter a question."

        intent_data = self._parse_intent_via_api(query)
        if intent_data is None:
            intent_data = self._parse_intent_regex(query)

        return self._dispatch(intent_data, query)

    # ------------------------------------------------------------------
    # Claude API intent parser
    # ------------------------------------------------------------------
    def _parse_intent_via_api(self, query: str) -> dict | None:
        if not self._api_available:
            return None

        payload = json.dumps({
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 200,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": query}],
        }).encode("utf-8")

        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                text = data["content"][0]["text"].strip()
                text = re.sub(r"```json|```", "", text).strip()
                return json.loads(text)
        except Exception:
            self._api_available = False
            return None

    # ------------------------------------------------------------------
    # Regex fallback
    # ------------------------------------------------------------------
    def _parse_intent_regex(self, query: str) -> dict:
        q = query.lower()

        # FROM … TO …
        m = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\?|$)", q)
        if m:
            src = re.split(r"\s*[—–]\s*", m.group(1))[0].strip(" ?.!")
            dst = re.split(r"\s*[—–]\s*", m.group(2))[0]
            dst = re.split(r"\s+(?:what|which|how|please|can you|tell)\b", dst)[0].strip(" ?.!-–—")
            if any(w in q for w in ("how long", "time", "duration")):
                return {"intent": "travel_time", "source": src, "destination": dst}
            return {"intent": "route", "source": src, "destination": dst}

        # THROUGH / PASSES / STOPS AT
        m2 = re.search(r"(?:goes?\s+through|passes?\s+through|pass\s+through|stop(?:s)?\s+at|via|which routes?\s+(?:go\s+through|pass\s+through|stop\s+at)?)\s+(.+?)(?:\?|$)", q)
        if m2:
            return {"intent": "routes_through", "stop": m2.group(1).strip(" ?.!")}

        # LAST BUS — grab the LAST from/at/leaving match to avoid preamble
        if "last bus" in q or "last departure" in q:
            all_m = list(re.finditer(r"\b(?:from|at|in|leaving)\s+(\S[^?]*?)(?:\?|$)", q))
            if all_m:
                raw_stop = all_m[-1].group(1).strip(" ?.!")
                return {"intent": "last_bus", "stop": raw_stop}

        # HOW LONG
        if any(w in q for w in ("how long", "travel time", "how much time")):
            m4 = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\?|$)", q)
            if m4:
                return {"intent": "travel_time",
                        "source": m4.group(1).strip(" ?.!"),
                        "destination": m4.group(2).strip(" ?.!")}

        # CONNECT / OPTIONS
        if any(w in q for w in ("connect", "any route", "do any", "options")):
            m5 = re.search(r"\bfrom\s+(.+?)\s+to\s+(.+?)(?:\?|$)", q)
            if not m5:
                m5 = re.search(r"([\w][\w\s\-/]+?)\s+(?:to|and)\s+([\w][\w\s\-/]+?)(?:\?|$)", q)
            if m5:
                return {"intent": "route",
                        "source": m5.group(1).strip(" ?.!"),
                        "destination": m5.group(2).strip(" ?.!")}

        return {"intent": "unknown"}

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def _dispatch(self, intent_data: dict, original_query: str) -> str:
        intent = intent_data.get("intent", "unknown")

        if intent == "route":
            return self.planner._answer_route(
                str(intent_data.get("source", "")),
                str(intent_data.get("destination", ""))
            )

        elif intent == "routes_through":
            return self.planner._answer_routes_through(
                str(intent_data.get("stop", ""))
            )
        elif intent == "travel_time":
            return self.planner._answer_travel_time(
                intent_data.get("source", ""),
                intent_data.get("destination", ""))

        elif intent == "last_bus":
            return self.planner._answer_last_bus(intent_data.get("stop", ""))

        else:
            answer = self.planner.answer_query(original_query)
            if "I can help with" not in answer:
                return answer
            return (
                "I couldn't understand that query.\n\n"
                "Try asking:\n"
                "  •  Travel from Khanna Pul to NUST\n"
                "  •  Which route goes through Faizabad?\n"
                "  •  Last bus from Sohan?\n"
                "  •  How long from I-8 to NUST?\n"
                "  •  Do any routes connect G-9 Markaz to F-10 Markaz?"
            )