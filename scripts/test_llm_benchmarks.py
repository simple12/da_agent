#!/usr/bin/env python3
"""Run Phase 1 benchmarks against the API in live LLM (OpenAI) mode."""

import json
import os
import sys
import time
import urllib.error
import urllib.request

API_URL = os.environ.get("API_URL", "http://localhost:8000")

BENCHMARKS = [
    {
        "name": "Test 1 — PMPM Alameda",
        "question": "What is PMPM for Alameda County?",
        "sql_contains": ["alameda", "paid_amount", "member_months"],
    },
    {
        "name": "Test 2 — PMPM by county",
        "question": "Show PMPM by county.",
        "sql_contains": ["group by", "county"],
    },
    {
        "name": "Test 3 — PMPM by age group",
        "question": "Show PMPM by age group.",
        "sql_contains": ["group by", "age_group"],
    },
    {
        "name": "Test 4 — Outstanding by provider",
        "question": "Outstanding claims by provider.",
        "sql_contains": ["provider", "outstanding"],
    },
    {
        "name": "Test 5 — Pending claims",
        "question": "Pending claims count.",
        "sql_contains": ["pending"],
    },
    {
        "name": "Deliverable — Alameda PMPM by age",
        "question": "What is PMPM for Alameda County and stratify by age group?",
        "sql_contains": ["alameda", "age_group", "group by"],
    },
]


def ask(question: str) -> tuple[dict, float]:
    body = json.dumps({"question": question}).encode()
    req = urllib.request.Request(
        f"{API_URL}/ask",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    return data, time.perf_counter() - start


def main() -> int:
    print(f"Testing API at {API_URL} (server must have LLM_PROVIDER=openai)\n")

    passed = executed = 0
    times: list[float] = []

    for bench in BENCHMARKS:
        print(f"{bench['name']}")
        print(f"  Q: {bench['question']}")
        try:
            data, elapsed = ask(bench["question"])
            times.append(elapsed)
            executed += 1
            sql_lower = data["sql"].lower()
            ok = all(token.lower() in sql_lower for token in bench["sql_contains"])
            if not data.get("results"):
                print("  WARN: empty results")
            if ok:
                passed += 1
                print(f"  PASS ({elapsed:.2f}s, {len(data['results'])} rows)")
            else:
                missing = [t for t in bench["sql_contains"] if t.lower() not in sql_lower]
                print(f"  FAIL: SQL missing {missing}")
            print(f"  SQL: {data['sql'][:140].replace(chr(10), ' ')}...")
        except urllib.error.HTTPError as e:
            print(f"  FAIL: HTTP {e.code} — {e.read().decode()}")
        except Exception as e:
            print(f"  FAIL: {e}")
        print()

    print("--- Summary ---")
    print(f"Passed: {passed}/{len(BENCHMARKS)}")
    print(f"Executed: {executed}/{len(BENCHMARKS)}")
    if times:
        print(f"Max latency: {max(times):.2f}s (target < 10s)")

    accuracy = passed / len(BENCHMARKS) if BENCHMARKS else 0
    exec_rate = executed / len(BENCHMARKS) if BENCHMARKS else 0
    print(f"SQL accuracy (heuristic): {accuracy:.0%} (target ≥ 80%)")
    print(f"Execution rate: {exec_rate:.0%} (target ≥ 95%)")

    return 0 if passed == len(BENCHMARKS) and executed == len(BENCHMARKS) else 1


if __name__ == "__main__":
    sys.exit(main())
