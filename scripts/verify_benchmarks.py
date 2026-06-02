#!/usr/bin/env python3
"""Run Phase 1 verification suite against the API."""

import json
import sys
import time
import urllib.error
import urllib.request

API_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"

BENCHMARKS = [
    {
        "name": "Test 1 — PMPM Alameda",
        "question": "What is PMPM for Alameda County?",
        "sql_contains": ["alameda"],
        "sql_must_have": ["select"],
    },
    {
        "name": "Test 2 — PMPM by county",
        "question": "Show PMPM by county.",
        "sql_contains": ["group by", "county"],
        "sql_must_have": [],
    },
    {
        "name": "Test 3 — PMPM by age group",
        "question": "Show PMPM by age group.",
        "sql_contains": ["group by", "age_group"],
        "sql_must_have": [],
    },
    {
        "name": "Test 4 — Outstanding by provider",
        "question": "Outstanding claims by provider.",
        "sql_contains": ["provider", "group by"],
        "sql_must_have": [],
    },
    {
        "name": "Test 5 — Pending claims",
        "question": "Pending claims count.",
        "sql_contains": ["pending"],
        "sql_must_have": [],
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
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    elapsed = time.perf_counter() - start
    return data, elapsed


def main():
    passed = 0
    executed = 0
    times: list[float] = []

    for bench in BENCHMARKS:
        print(f"\n{bench['name']}")
        print(f"  Q: {bench['question']}")
        try:
            data, elapsed = ask(bench["question"])
            times.append(elapsed)
            executed += 1
            sql_lower = data["sql"].lower()
            ok = True
            for token in bench["sql_contains"]:
                if token.lower() not in sql_lower:
                    print(f"  FAIL: SQL missing '{token}'")
                    ok = False
            for token in bench["sql_must_have"]:
                if token.lower() not in sql_lower:
                    print(f"  FAIL: SQL missing '{token}'")
                    ok = False
            if not data.get("results"):
                print("  WARN: empty results (SQL may still be valid)")
            if ok:
                passed += 1
                print(f"  PASS ({elapsed:.2f}s, {len(data['results'])} rows)")
            print(f"  SQL: {data['sql'][:120]}...")
        except urllib.error.HTTPError as e:
            detail = e.read().decode()
            print(f"  FAIL: HTTP {e.code} — {detail}")
        except Exception as e:
            print(f"  FAIL: {e}")

    print("\n--- Summary ---")
    print(f"Benchmark checks passed: {passed}/{len(BENCHMARKS)}")
    print(f"Queries executed: {executed}/{len(BENCHMARKS)}")
    if times:
        print(f"Max latency: {max(times):.2f}s (target < 10s)")
    sys.exit(0 if passed == len(BENCHMARKS) and executed == len(BENCHMARKS) else 1)


if __name__ == "__main__":
    main()
