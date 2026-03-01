import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


def percentile(values, pct):
    if not values:
        return None
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (pct / 100.0)
    f = int(k)
    c = min(f + 1, len(values_sorted) - 1)
    if f == c:
        return values_sorted[f]
    d = k - f
    return values_sorted[f] + (values_sorted[c] - values_sorted[f]) * d


def auth(base_url, username, password):
    response = requests.post(
        f"{base_url}/auth/token/",
        data={"username": username, "password": password},
        timeout=30,
    )
    response.raise_for_status()
    token = response.json().get("access")
    if not token:
        raise RuntimeError("No access token")
    return {"Authorization": f"Bearer {token}"}


def create_investigation(base_url, headers, name):
    response = requests.post(
        f"{base_url}/investigations/",
        headers=headers,
        json={"name": name, "description": "Concurrency test", "status": "active"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def create_entity(base_url, headers, inv_id, entity_type, value):
    response = requests.post(
        f"{base_url}/investigations/{inv_id}/entities/",
        headers=headers,
        json={
            "entity_type": entity_type,
            "value": value,
            "source": "concurrency_test",
            "confidence_score": 0.7,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def get_graph(base_url, headers, inv_id, limit):
    start = time.perf_counter()
    response = requests.get(
        f"{base_url}/investigations/{inv_id}/entities/graph/?limit={limit}",
        headers=headers,
        timeout=60,
    )
    latency = time.perf_counter() - start
    response.raise_for_status()
    return latency


def get_transforms(base_url, headers):
    start = time.perf_counter()
    response = requests.get(
        f"{base_url}/transforms/",
        headers=headers,
        timeout=60,
    )
    latency = time.perf_counter() - start
    response.raise_for_status()
    return latency


def get_investigations(base_url, headers):
    start = time.perf_counter()
    response = requests.get(
        f"{base_url}/investigations/",
        headers=headers,
        timeout=60,
    )
    latency = time.perf_counter() - start
    response.raise_for_status()
    return latency


def get_tools_status(base_url, headers):
    start = time.perf_counter()
    response = requests.get(
        f"{base_url}/tools/status/",
        headers=headers,
        timeout=60,
    )
    latency = time.perf_counter() - start
    response.raise_for_status()
    return latency


def user_flow(base_url, headers, inv_id, graph_limit):
    latencies = {
        "investigations": [],
        "transforms": [],
        "tools_status": [],
        "graph": [],
        "errors": [],
    }
    try:
        latencies["investigations"].append(get_investigations(base_url, headers))
    except Exception as exc:
        latencies["errors"].append(f"investigations: {exc}")
    try:
        latencies["transforms"].append(get_transforms(base_url, headers))
    except Exception as exc:
        latencies["errors"].append(f"transforms: {exc}")
    try:
        latencies["tools_status"].append(get_tools_status(base_url, headers))
    except Exception as exc:
        latencies["errors"].append(f"tools_status: {exc}")
    try:
        latencies["graph"].append(get_graph(base_url, headers, inv_id, graph_limit))
    except Exception as exc:
        latencies["errors"].append(f"graph: {exc}")
    return latencies


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://localhost:8000/api"))
    parser.add_argument("--username", default=os.environ.get("USERNAME", "admin"))
    parser.add_argument("--password", default=os.environ.get("PASSWORD", "admin_password"))
    parser.add_argument("--users", type=int, default=20)
    parser.add_argument("--graph-limit", type=int, default=500)
    parser.add_argument("--output", default=os.path.join("docs", "reports", "performance_concurrency.json"))
    args = parser.parse_args()

    headers = auth(args.base_url, args.username, args.password)
    inv = create_investigation(args.base_url, headers, f"Concurrency {int(time.time())}")
    inv_id = inv["id"]
    for i in range(25):
        create_entity(args.base_url, headers, inv_id, "domain", f"example{i}.com")

    buckets = {
        "investigations": [],
        "transforms": [],
        "tools_status": [],
        "graph": [],
    }
    errors = []

    with ThreadPoolExecutor(max_workers=max(args.users, 1)) as executor:
        futures = [
            executor.submit(user_flow, args.base_url, headers, inv_id, args.graph_limit)
            for _ in range(args.users)
        ]
        for future in as_completed(futures):
            result = future.result()
            for key in buckets:
                buckets[key].extend(result[key])
            errors.extend(result.get("errors", []))

    stats = {}
    for key, values in buckets.items():
        stats[key] = {
            "count": len(values),
            "p50": round(percentile(values, 50), 3),
            "p95": round(percentile(values, 95), 3),
            "p99": round(percentile(values, 99), 3),
            "max": round(max(values), 3),
        }

    payload = {"users": args.users, "stats": stats, "errors": errors}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
