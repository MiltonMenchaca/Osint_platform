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
        json={"name": name, "description": "Load test", "status": "active"},
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


def trigger_transform(base_url, headers, inv_id, input_payload, transform_name, parameters):
    response = requests.post(
        f"{base_url}/investigations/{inv_id}/executions/",
        headers=headers,
        json={
            "transform_name": transform_name,
            "input": input_payload,
            "parameters": parameters,
        },
        timeout=30,
    )
    response.raise_for_status()
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


def run_volume(base_url, headers, volume, transforms, transform_timeout, transform_input):
    metrics = {
        "entities": 0,
        "relationships": 0,
        "transforms": [],
        "errors": [],
    }
    t0 = time.perf_counter()
    inv = create_investigation(base_url, headers, f"Perf {volume} {int(time.time())}")
    inv_id = inv["id"]

    entity_ids = []
    for i in range(volume):
        entity = create_entity(base_url, headers, inv_id, "domain", f"example{i}.com")
        entity_ids.append(entity["id"])
    metrics["entities"] = len(entity_ids)

    for i in range(1, len(entity_ids)):
        create_relationship(base_url, headers, inv_id, entity_ids[i - 1], entity_ids[i], "associated_with")
    metrics["relationships"] = max(len(entity_ids) - 1, 0)

    for tname in transforms:
        exec_data = trigger_transform(
            base_url,
            headers,
            inv_id,
            transform_input,
            tname,
            {"count": 1, "timeout": 10} if tname == "ping" else {},
        )
        exec_id = exec_data["id"]
        status, payload = poll_execution(base_url, headers, inv_id, exec_id, transform_timeout)
        metrics["transforms"].append(
            {
                "transform": tname,
                "execution_id": exec_id,
                "status": status,
                "error": None if not payload else payload.get("error_message"),
            }
        )

    metrics["total_seconds"] = round(time.perf_counter() - t0, 2)
    metrics["investigation_id"] = inv_id
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("BASE_URL", "http://localhost:8000/api"))
    parser.add_argument("--username", default=os.environ.get("USERNAME", "admin"))
    parser.add_argument("--password", default=os.environ.get("PASSWORD", "admin_password"))
    parser.add_argument("--volumes", default="5,25,100")
    parser.add_argument("--transforms", default="ping")
    parser.add_argument("--transform-timeout", type=int, default=180)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--transform-input-type", default="domain")
    parser.add_argument("--transform-input-value", default="example.com")
    parser.add_argument("--output", default=os.path.join("docs", "reports", "performance_metrics.json"))
    args = parser.parse_args()

    headers = auth(args.base_url, args.username, args.password)
    volumes = [int(v.strip()) for v in args.volumes.split(",") if v.strip()]
    transforms = [t.strip() for t in args.transforms.split(",") if t.strip()]
    transform_input = {"entity_type": args.transform_input_type, "value": args.transform_input_value}

    results = []
    with ThreadPoolExecutor(max_workers=max(args.concurrency, 1)) as executor:
        futures = {
            executor.submit(
                run_volume,
                args.base_url,
                headers,
                volume,
                transforms,
                args.transform_timeout,
                transform_input,
            ): volume
            for volume in volumes
        }
        for future in as_completed(futures):
            volume = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({"volume": volume, "error": str(exc)})

    results_sorted = sorted(results, key=lambda r: r.get("entities", 0))
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"base_url": args.base_url, "results": results_sorted}, f, indent=2)

    print(json.dumps({"results": results_sorted}, indent=2))


if __name__ == "__main__":
    main()
