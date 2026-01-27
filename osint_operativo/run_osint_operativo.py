import argparse
import datetime as dt
import json
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List
import importlib.util


BASE_DIR = Path(__file__).resolve().parent
SOURCES_DIR = BASE_DIR / "sources"
DEFAULT_CONFIG = BASE_DIR / "config.example.json"
REPORTS_DIR = BASE_DIR / "reportes"


def load_config(path: Path) -> Dict[str, Any]:
    data = path.read_text(encoding="utf-8")
    return json.loads(data)


def validate_config(config: Dict[str, Any]) -> List[str]:
    errors = []
    if not isinstance(config, dict):
        return ["El archivo de configuración debe ser un objeto JSON."]
    campaign = config.get("campaign")
    if not isinstance(campaign, dict):
        errors.append("El campo 'campaign' es obligatorio y debe ser un objeto.")
    else:
        if not campaign.get("name"):
            errors.append("El campo 'campaign.name' es obligatorio.")
    targets = config.get("targets")
    if not isinstance(targets, list) or not targets:
        errors.append("El campo 'targets' debe ser una lista no vacía.")
    else:
        for i, target in enumerate(targets):
            if not isinstance(target, dict):
                errors.append(f"targets[{i}] debe ser un objeto.")
                continue
            if not target.get("type") or not target.get("value"):
                errors.append(f"targets[{i}] requiere 'type' y 'value'.")
    sources = config.get("sources")
    if not isinstance(sources, list) or not sources:
        errors.append("El campo 'sources' debe ser una lista no vacía.")
    else:
        for i, source in enumerate(sources):
            if not isinstance(source, dict):
                errors.append(f"sources[{i}] debe ser un objeto.")
                continue
            if not source.get("id"):
                errors.append(f"sources[{i}] requiere 'id'.")
    organization = config.get("organization")
    if organization is not None and not isinstance(organization, dict):
        errors.append("El campo 'organization' debe ser un objeto si se proporciona.")
    if isinstance(organization, dict):
        if not organization.get("name"):
            errors.append("El campo 'organization.name' es obligatorio.")
        data_driven = organization.get("data_driven")
        if data_driven is not None and not isinstance(data_driven, dict):
            errors.append("El campo 'organization.data_driven' debe ser un objeto.")
        if isinstance(data_driven, dict):
            required_fields = [
                "data_generated",
                "data_sources",
                "decisions_improved",
                "problems_if_unreliable",
                "data_engineer_role",
                "intuition_only_impact",
            ]
            for field in required_fields:
                if field not in data_driven:
                    errors.append(
                        f"El campo 'organization.data_driven.{field}' es obligatorio."
                    )
    return errors


def discover_sources() -> Dict[str, Any]:
    sources: Dict[str, Any] = {}
    if not SOURCES_DIR.exists():
        return sources
    for path in SOURCES_DIR.glob("*.py"):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        source_id = getattr(module, "SOURCE_ID", path.stem)
        run_fn = getattr(module, "run", None)
        if callable(run_fn):
            sources[source_id] = run_fn
    return sources


def execute_campaign(config: Dict[str, Any]) -> Dict[str, Any]:
    sources = discover_sources()
    enabled_sources = {
        src["id"]: src for src in config["sources"] if src.get("enabled", True)
    }
    findings = []
    runs = []
    for target in config["targets"]:
        for source_id, source_cfg in enabled_sources.items():
            run_fn = sources.get(source_id)
            if not run_fn:
                runs.append(
                    {
                        "source": source_id,
                        "target": target,
                        "status": "skipped",
                        "reason": "source_not_found",
                    }
                )
                continue
            context = {
                "campaign": config.get("campaign", {}),
                "options": source_cfg.get("options", {}),
            }
            result = run_fn(target, context)
            run_findings = result if isinstance(result, list) else []
            for item in run_findings:
                if isinstance(item, dict):
                    item.setdefault("source", source_id)
            findings.extend(run_findings)
            runs.append(
                {
                    "source": source_id,
                    "target": target,
                    "status": "completed",
                    "count": len(run_findings),
                }
            )
    return {
        "id": str(uuid.uuid4()),
        "campaign": config.get("campaign", {}),
        "organization": config.get("organization", {}),
        "generated_at": dt.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "targets": config.get("targets", []),
        "runs": runs,
        "findings": findings,
        "summary": {
            "targets": len(config.get("targets", [])),
            "sources": len(enabled_sources),
            "findings": len(findings),
        },
    }


def render_report_text(result: Dict[str, Any]) -> str:
    lines = []
    campaign = result.get("campaign", {})
    lines.append(f"Campaña: {campaign.get('name', 'Sin nombre')}")
    if campaign.get("description"):
        lines.append(f"Descripción: {campaign.get('description')}")
    organization = result.get("organization", {})
    if organization:
        lines.append("")
        lines.append("Organización Data-Driven")
        lines.append(f"- Nombre: {organization.get('name', 'Sin nombre')}")
        if organization.get("sector"):
            lines.append(f"- Sector: {organization.get('sector')}")
        if organization.get("description"):
            lines.append(f"- Descripción: {organization.get('description')}")
        data_driven = organization.get("data_driven", {})
        if data_driven:
            lines.append("")
            lines.append("Datos y decisiones")
            lines.append("¿Qué datos genera esta organización?")
            lines.extend(_format_list(data_driven.get("data_generated")))
            lines.append("¿De dónde provienen esos datos?")
            lines.extend(_format_list(data_driven.get("data_sources")))
            lines.append("¿Qué decisiones importantes podrían mejorarse usando datos?")
            lines.extend(_format_list(data_driven.get("decisions_improved")))
            lines.append("¿Qué problemas existirían si los datos no fueran confiables?")
            lines.extend(_format_list(data_driven.get("problems_if_unreliable")))
            lines.append("¿Qué rol tendría un Data Engineer en esta organización?")
            lines.extend(_format_list(data_driven.get("data_engineer_role")))
            lines.append("¿Qué pasaría si la empresa tomara decisiones solo por intuición?")
            lines.extend(_format_list(data_driven.get("intuition_only_impact")))
    lines.append(f"Fecha: {result.get('generated_at')}")
    lines.append("")
    summary = result.get("summary", {})
    lines.append("Resumen")
    lines.append(f"- Objetivos: {summary.get('targets', 0)}")
    lines.append(f"- Fuentes: {summary.get('sources', 0)}")
    lines.append(f"- Hallazgos: {summary.get('findings', 0)}")
    lines.append("")
    lines.append("Ejecuciones")
    for run in result.get("runs", []):
        lines.append(
            f"- {run.get('source')} | {run.get('status')} | {run.get('count', 0)}"
        )
    lines.append("")
    lines.append("Hallazgos")
    for finding in result.get("findings", []):
        lines.append(
            f"- {finding.get('type')} | {finding.get('value')} | {finding.get('source')}"
        )
    return "\n".join(lines)


def _format_list(value: Any) -> List[str]:
    if value is None:
        return ["- (sin datos)"]
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return [f"- {item}" for item in items] if items else ["- (sin datos)"]
    text = str(value).strip()
    return [f"- {text}"] if text else ["- (sin datos)"]


def write_output(result: Dict[str, Any], output_dir: Path) -> Dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    base = f"campaign_{timestamp}"
    json_path = output_dir / f"{base}.json"
    txt_path = output_dir / f"{base}.txt"
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path.write_text(render_report_text(result), encoding="utf-8")
    return {"json": str(json_path), "txt": str(txt_path)}


def list_sources():
    sources = discover_sources()
    if not sources:
        print("No hay fuentes registradas.")
        return
    for source_id in sorted(sources.keys()):
        print(source_id)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--output", default=str(REPORTS_DIR))
    parser.add_argument("--list-sources", action="store_true")
    args = parser.parse_args()

    if args.list_sources:
        list_sources()
        return

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"No existe el archivo de configuración: {config_path}")
        sys.exit(1)

    config = load_config(config_path)
    errors = validate_config(config)
    if errors:
        for error in errors:
            print(error)
        sys.exit(1)

    result = execute_campaign(config)
    output_paths = write_output(result, Path(args.output))
    print(output_paths["json"])
    print(output_paths["txt"])


if __name__ == "__main__":
    main()
