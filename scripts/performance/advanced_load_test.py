import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


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
        json={"name": name, "description": "Advanced load test", "status": "active"},
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
            "source": "load_test",
            "confidence_score": 0.7,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def create_relationship(base_url, headers, inv_id, source_id, target_id, relationship_type):
    response = requests.post(
        f"{base_url}/investigations/{inv_id}/relationships/",
        headers=headers,
        json={
            "source_entity_id": source_id,
            "target_entity_id": target_id,
            "relationship_type": relationship_type,
            "confidence_score": 0.6,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def bulk_execute(base_url, headers, inv_id, transform_names, input_payload, parameters):
    response = requests.post(
        f"{base_url}/investigations/{inv_id}/bulk-execute/",
        headers=headers,
        json={
            "transform_names": transform_names,
            "input": input_payload,
            "parameters": parameters,
        },
        timeout=120,
    )
    if response.status_code >= 400:
        return {"fallback": True, "error": response.text}
    response.raise_for_status()
    return response.json()


def execute_single(base_url, headers, inv_id, input_payload, transform_name, parameters):
    response = requests.post(
        f"{base_url}/investigations/{inv_id}/executions/",
        headers=headers,
        json={
            "transform_name": transform_name,
            "input": input_payload,
            "parameters": parameters,
        },
        timeout=120,
    )
    if response.status_code >= 400:
        return {"error": response.text, "status_code": response.status_code}
    return response.json()


def poll_execution(base_url, headers, inv_id, exec_id, timeout_seconds):
    start = time.time()
    while time.time() - start < timeout_seconds:
        response = requests.get(
            f"{base_url}/investigations/{inv_id}/executions/{exec_id}/",
            headers=headers,
            timeout=30,
        )
        if response.status_code == 200:
            data = response.json()
            status = data.get("status")
            if status in {"completed", "failed"}:
                return status, data
        time.sleep(2)
    return "timeout", None


def measure_graph(base_url, headers, inv_id, limit):
    start = time.perf_counter()
    response = requests.get(
        f"{base_url}/investigations/{inv_id}/entities/graph/?limit={limit}",
        headers=headers,
        timeout=60,
    )
    latency = time.perf_counter() - start
    response.raise_for_status()
    data = response.json()
    return round(latency, 2), data.get("stats", {})


def run_scenario(base_url, headers, entity_count, transforms, graph_limit, transform_timeout):
    scenario = {
        "entities": entity_count,
        "relationships": max(entity_count - 1, 0),
        "graph_limit": graph_limit,
        "transforms": [],
        "errors": [],
    }

    t0 = time.perf_counter()
    inv = create_investigation(base_url, headers, f"Advanced {entity_count} {int(time.time())}")
    inv_id = inv["id"]
    scenario["investigation_id"] = inv_id

    entity_ids = []
    for i in range(entity_count):
        entity = create_entity(base_url, headers, inv_id, "domain", f"example{i}.com")
        entity_ids.append(entity["id"])

    for i in range(1, len(entity_ids)):
        create_relationship(base_url, headers, inv_id, entity_ids[i - 1], entity_ids[i], "associated_with")

    scenario["setup_seconds"] = round(time.perf_counter() - t0, 2)

    if transforms:
        transform_inputs = {
            "nmap": {"entity_type": "ip", "value": "8.8.8.8"},
            "spiderfoot": {"entity_type": "domain", "value": "example.com"},
            "dnstwist": {"entity_type": "domain", "value": "example.com"},
        }
        transform_params = {
            "nmap": {"scan_type": "ping", "ports": "top-100"},
            "spiderfoot": {"modules": "passive", "timeout": 300},
            "dnstwist": {"format": "json"},
        }
        bulk_payload = {"entity_type": "domain", "value": "example.com"}
        bulk = bulk_execute(
            base_url,
            headers,
            inv_id,
            transforms,
            bulk_payload,
            {},
        )
        if bulk.get("error"):
            scenario["errors"].append({"bulk_execute": bulk.get("error")})
        execution_ids = bulk.get("execution_ids", [])
        if bulk.get("fallback"):
            for name in transforms:
                execution = execute_single(
                    base_url,
                    headers,
                    inv_id,
                    transform_inputs.get(name, bulk_payload),
                    name,
                    transform_params.get(name, {}),
                )
                if execution.get("error"):
                    scenario["transforms"].append(
                        {
                            "execution_id": None,
                            "status": "create_failed",
                            "error": execution.get("error"),
                        }
                    )
                    continue
                execution_ids.append(execution["id"])
        for exec_id in execution_ids:
            status, payload = poll_execution(base_url, headers, inv_id, exec_id, transform_timeout)
            scenario["transforms"].append(
                {
                    "execution_id": exec_id,
                    "status": status,
                    "error": None if not payload else payload.get("error_message"),
                }
            )

    graph_latency, graph_stats = measure_graph(base_url, headers, inv_id, graph_limit)
    scenario["graph_seconds"] = graph_latency
    scenario["graph_stats"] = graph_stats
    scenario["total_seconds"] = round(time.perf_counter() - t0, 2)
    return scenario


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://localhost:8000/api"))
    parser.add_argument("--username", default=os.environ.get("USERNAME", "admin"))
    parser.add_argument("--password", default=os.environ.get("PASSWORD", "admin_password"))
    parser.add_argument("--entity-counts", default="200,500")
    parser.add_argument("--transforms", default="ping,whois")
    parser.add_argument("--graph-limit", type=int, default=500)
    parser.add_argument("--transform-timeout", type=int, default=300)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--output", default=os.path.join("docs", "reports", "performance_advanced.json"))
    args = parser.parse_args()

    headers = auth(args.base_url, args.username, args.password)
    counts = [int(v.strip()) for v in args.entity_counts.split(",") if v.strip()]
    transforms = [t.strip() for t in args.transforms.split(",") if t.strip()]

    results = []
    with ThreadPoolExecutor(max_workers=max(args.concurrency, 1)) as executor:
        futures = {
            executor.submit(
                run_scenario,
                args.base_url,
                headers,
                count,
                transforms,
                args.graph_limit,
                args.transform_timeout,
            ): count
            for count in counts
        }
        for future in as_completed(futures):
            count = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"entities": count, "error": str(exc)})

    results_sorted = sorted(results, key=lambda r: r.get("entities", 0))
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"base_url": args.base_url, "results": results_sorted}, f, indent=2)

    print(json.dumps({"results": results_sorted}, indent=2))


if __name__ == "__main__":
    main()
