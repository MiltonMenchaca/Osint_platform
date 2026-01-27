import hashlib


SOURCE_ID = "example_source"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def run(target, context):
    target_type = target.get("type")
    value = str(target.get("value", "")).strip()
    if not value:
        return []
    findings = []
    if target_type == "domain":
        findings.append(
            {
                "type": "url",
                "value": f"https://{value}",
                "confidence": 0.6,
                "evidence": f"seed:{_hash(value)}",
            }
        )
        findings.append(
            {
                "type": "subdomain",
                "value": f"www.{value}",
                "confidence": 0.4,
                "evidence": f"seed:{_hash(value)}",
            }
        )
    if target_type == "email" and "@" in value:
        domain = value.split("@", 1)[1]
        findings.append(
            {
                "type": "domain",
                "value": domain,
                "confidence": 0.5,
                "evidence": f"seed:{_hash(value)}",
            }
        )
    return findings
