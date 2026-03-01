import json
import logging
import re
import subprocess
from typing import Any, Dict, List

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("celery")


@shared_task(bind=True, max_retries=3)
def execute_transform(
    self,
    execution_id: str,
    transform_name: str,
    input_value: str,
    parameters: Dict[str, Any] = None,
):
    """
    Execute a transform on an entity

    Args:
        execution_id: UUID of the TransformExecution record
        transform_name: Name of the transform to execute
        input_value: Input value for the transform
        parameters: Additional parameters for the transform

    Returns:
        Dict containing execution results
    """
    from apps.investigations.models import TransformExecution
    from apps.transforms.models import Transform

    try:
        # Get the execution record
        execution = TransformExecution.objects.get(id=execution_id)
        execution.celery_task_id = self.request.id
        execution.start_execution()

        logger.info(
            f"Starting transform execution {execution_id}: {transform_name} on {input_value}"
        )

        # Get the transform definition
        try:
            transform = Transform.objects.get(name=transform_name, is_enabled=True)
        except Transform.DoesNotExist:
            raise Exception(f"Transform '{transform_name}' not found or disabled")

        # Validate transform availability
        is_valid, message = transform.validate_input(execution.input_entity)
        if not is_valid:
            raise Exception(f"Transform validation failed: {message}")

        # Prepare parameters
        exec_parameters = parameters or {}

        # Execute the transform
        results = _execute_osint_tool(
            transform=transform,
            input_entity=execution.input_entity,
            input_value=input_value,
            parameters=exec_parameters,
        )

        # Process results and create entities/relationships
        processed_results = _process_transform_results(
            execution=execution, transform=transform, raw_results=results
        )

        # Complete the execution
        execution.complete_execution(processed_results)

        logger.info(f"Transform execution {execution_id} completed successfully")

        return {
            "status": "completed",
            "execution_id": execution_id,
            "results": processed_results,
            "entities_created": processed_results.get("entities_created", 0),
            "relationships_created": processed_results.get("relationships_created", 0),
        }

    except Exception as exc:
        logger.error(f"Transform execution {execution_id} failed: {str(exc)}")

        try:
            execution = TransformExecution.objects.get(id=execution_id)
            execution.fail_execution(str(exc))
        except Exception as e:
            logger.error(f"Failed to update execution status: {str(e)}")

        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(
                f"Retrying transform execution {execution_id} (attempt {self.request.retries + 1})"
            )
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=exc)

        return {"status": "failed", "execution_id": execution_id, "error": str(exc)}


def _execute_osint_tool(
    transform: Any, input_entity: Any, input_value: str, parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute the actual OSINT tool

    Args:
        transform: Transform model instance
        input_value: Input value for the tool
        parameters: Additional parameters

    Returns:
        Dict containing raw tool output
    """
    try:
        try:
            from apps.transforms.wrappers import (
                OSINTToolError,
                ToolNotFoundError,
                get_wrapper,
            )

            wrapper_cls = get_wrapper(transform.tool_name)
            wrapper = wrapper_cls()
            input_type = (
                transform.input_type
                if transform.input_type != "any"
                else getattr(input_entity, "entity_type", "domain")
            )

            wrapper_kwargs = dict(parameters or {})
            if "timeout" not in wrapper_kwargs:
                wrapper_kwargs["timeout"] = transform.timeout

            print(f"DEBUG: Executing wrapper for {transform.tool_name} with value {input_value}")
            wrapper_result = wrapper.execute(
                {"type": input_type, "value": input_value},
                **wrapper_kwargs,
            )
            print(f"DEBUG: Wrapper result: {json.dumps(wrapper_result)[:100]}...")

            metadata = wrapper_result.get("metadata") or {}

            return {
                "command": metadata.get("command") or transform.get_command(
                    input_value, **(parameters or {})
                ),
                "return_code": 0,
                "stdout": json.dumps(wrapper_result, ensure_ascii=False),
                "stderr": "",
                "parsed_output": wrapper_result.get("results", []) or [],
                "wrapper_output": wrapper_result,
            }

        except (ValueError, ToolNotFoundError) as e:
            logger.warning(f"Wrapper not found for {transform.tool_name}: {e}")
            pass
        except OSINTToolError:
            raise
        except Exception as e:
            logger.warning(f"Wrapper execution failed: {e}. Falling back to command line.")
            import traceback
            logger.warning(traceback.format_exc())
            pass

        # Get the command to execute
        command = transform.get_command(input_value, **parameters)

        logger.info(f"Executing command: {command}")
        
        import tempfile
        cwd = getattr(settings, "OSINT_TOOLS_DIR", tempfile.gettempdir())

        # Execute the command
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=transform.timeout,
            cwd=cwd,
        )

        if result.returncode != 0:
            error_msg = (
                f"Command failed with return code {result.returncode}: {result.stderr}"
            )
            logger.error(error_msg)
            raise Exception(error_msg)

        # Parse output based on transform type
        parsed_output = _parse_tool_output(transform.tool_name, result.stdout)

        return {
            "command": command,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "parsed_output": parsed_output,
        }

    except subprocess.TimeoutExpired:
        error_msg = f"Command timed out after {transform.timeout} seconds"
        logger.error(error_msg)
        raise Exception(error_msg)
    except Exception as e:
        logger.error(f"Error executing OSINT tool: {str(e)}")
        raise


def _parse_tool_output(tool_name: str, output: str) -> List[Dict[str, Any]]:
    """
    Parse tool output based on the tool type

    Args:
        tool_name: Name of the OSINT tool
        output: Raw output from the tool

    Returns:
        List of parsed entities
    """
    parsed_entities = []

    try:
        if tool_name == "assetfinder":
            # Assetfinder returns one domain per line
            for line in output.strip().split("\n"):
                if line.strip():
                    parsed_entities.append(
                        {
                            "type": "domain",
                            "value": line.strip(),
                            "source": "assetfinder",
                        }
                    )

        elif tool_name == "amass":
            # Amass enum returns domains, parse JSON if available
            for line in output.strip().split("\n"):
                if line.strip():
                    try:
                        # Try to parse as JSON first
                        data = json.loads(line)
                        parsed_entities.append(
                            {
                                "type": "domain",
                                "value": data.get("name", ""),
                                "source": "amass",
                                "properties": data,
                            }
                        )
                    except json.JSONDecodeError:
                        # Fallback to plain text
                        parsed_entities.append(
                            {"type": "domain", "value": line.strip(), "source": "amass"}
                        )

        elif tool_name == "nmap":
            # Parse nmap output for open ports and services
            lines = output.strip().split("\n")
            current_host = None

            for line in lines:
                if "Nmap scan report for" in line:
                    # Extract host
                    parts = line.split()
                    if len(parts) >= 5:
                        current_host = parts[4]
                elif "/tcp" in line or "/udp" in line and current_host:
                    # Parse port information
                    parts = line.split()
                    if len(parts) >= 3:
                        port_info = parts[0]
                        state = parts[1]
                        service = parts[2] if len(parts) > 2 else "unknown"

                        if state == "open":
                            parsed_entities.append(
                                {
                                    "type": "ip",
                                    "value": current_host,
                                    "source": "nmap",
                                    "properties": {
                                        "port": port_info,
                                        "state": state,
                                        "service": service,
                                    },
                                }
                            )

        elif tool_name == "shodan":
            try:
                data = json.loads(output)
                if isinstance(data, dict):
                    if "matches" in data and isinstance(data["matches"], list):
                        for match in data["matches"]:
                            parsed_entities.append(
                                {
                                    "type": "ip",
                                    "value": str(match.get("ip_str", "") or "").strip(),
                                    "source": "shodan",
                                    "properties": {
                                        "port": match.get("port"),
                                        "org": match.get("org"),
                                        "hostnames": match.get("hostnames", []),
                                        "location": match.get("location", {}),
                                        "data": match.get("data", ""),
                                    },
                                }
                            )
                    else:
                        ip_val = str(data.get("ip_str", "") or data.get("ip", "") or "").strip()
                        if ip_val:
                            props = {
                                "port": data.get("port"),
                                "org": data.get("org"),
                                "hostnames": data.get("hostnames", []),
                                "location": data.get("location", {}),
                                "data": data.get("data", ""),
                            }
                            parsed_entities.append({"type": "ip", "value": ip_val, "source": "shodan", "properties": props})
            except json.JSONDecodeError:
                import re
                lines = (output or "").splitlines()
                ip_regex = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
                ports = []
                org = None
                hostnames = []
                ip_val = None
                for raw in lines:
                    line = raw.strip()
                    if not line:
                        continue
                    if not ip_val:
                        m = re.search(ip_regex, line)
                        if m:
                            ip_val = m.group(0)
                    if "Org" in line or "Organization" in line:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            org = parts[1].strip()
                    if "Hostnames" in line or "Hostname" in line:
                        parts = line.split(":")
                        if len(parts) >= 2:
                            hostnames = [h.strip() for h in parts[1].split(",") if h.strip()]
                    m_port = re.findall(r"\b(?:port|ports)\b[:\\s]*([0-9, ]+)", line, flags=re.IGNORECASE)
                    if m_port:
                        for grp in m_port:
                            for p in grp.split(","):
                                p = p.strip()
                                if p.isdigit():
                                    ports.append(int(p))
                    m_inline = re.findall(r"\b([0-9]{1,5})/(?:tcp|udp)\b", line, flags=re.IGNORECASE)
                    for p in m_inline:
                        if p.isdigit():
                            ports.append(int(p))
                if ip_val:
                    props = {}
                    if ports:
                        props["ports"] = sorted(list(set(ports)))
                    if org:
                        props["org"] = org
                    if hostnames:
                        props["hostnames"] = hostnames
                    parsed_entities.append({"type": "ip", "value": ip_val, "source": "shodan", "properties": props})

        elif tool_name == "subfinder":
            for line in output.strip().split("\n"):
                value = line.strip()
                if not value:
                    continue
                parsed_entities.append(
                    {
                        "type": "domain",
                        "value": value,
                        "source": "subfinder",
                    }
                )

        elif tool_name == "sherlock":
            for raw_line in (output or "").splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if "http://" not in line and "https://" not in line:
                    continue
                cleaned = line.replace("[+]", "").replace("[*]", "").strip()
                platform = None
                url = None
                if ": " in cleaned:
                    left, right = cleaned.split(": ", 1)
                    platform = left.strip() or None
                    url = right.strip() or None
                else:
                    for part in cleaned.split():
                        if part.startswith("http://") or part.startswith("https://"):
                            url = part.strip()
                            break
                if not url:
                    continue
                entity = {"type": "social_media", "value": url, "source": "sherlock"}
                if platform:
                    entity["properties"] = {"platform": platform}
                parsed_entities.append(entity)

        else:
            # Generic parser - try to extract domains, IPs, emails
            import re

            # Domain pattern
            domain_pattern = (
                r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+"
                r"[a-zA-Z]{2,}\b"
            )
            domains = re.findall(domain_pattern, output)

            # IP pattern
            ip_pattern = r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"
            ips = re.findall(ip_pattern, output)

            # Email pattern
            email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            emails = re.findall(email_pattern, output)

            for domain in set(domains):
                parsed_entities.append(
                    {"type": "domain", "value": domain, "source": tool_name}
                )

            for ip in set(ips):
                parsed_entities.append({"type": "ip", "value": ip, "source": tool_name})

            for email in set(emails):
                parsed_entities.append(
                    {"type": "email", "value": email, "source": tool_name}
                )

    except Exception as e:
        logger.error(f"Error parsing {tool_name} output: {str(e)}")

    return parsed_entities


def _process_transform_results(
    execution: Any, transform: Any, raw_results: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process transform results and create entities/relationships

    Args:
        execution: TransformExecution instance
        transform: Transform instance
        raw_results: Raw results from tool execution

    Returns:
        Dict containing processed results
    """
    from apps.entities.models import Entity, Relationship

    entities_created = 0
    relationships_created = 0
    created_entities = []

    try:
        parsed_output = raw_results.get("parsed_output", [])
        allowed_entity_types = {t[0] for t in Entity.ENTITY_TYPE_CHOICES}
        
        # Track processed entities in this batch to avoid duplicates
        processed_in_batch = set()

        for entity_data in parsed_output:
            raw_type = (entity_data.get("type") or "other").strip().lower()
            raw_value = entity_data.get("value")
            value = str(raw_value or "").strip()
            if not value:
                continue

            entity_type = raw_type
            if entity_type in {"subdomain", "hostname"}:
                entity_type = "domain"
            elif entity_type == "host":
                entity_type = (
                    "ip"
                    if re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", value)
                    else "domain"
                )
            elif entity_type.startswith("hash_"):
                entity_type = "hash"

            if entity_type not in allowed_entity_types:
                entity_type = "other"

            # Skip duplicates in the same batch
            entity_key = (entity_type, value)
            if entity_key in processed_in_batch:
                continue
            processed_in_batch.add(entity_key)

            # Create or get entity
            try:
                entity, created = Entity.objects.get_or_create(
                    investigation=execution.investigation,
                    entity_type=entity_type,
                    value=value,
                    defaults={
                        "source": entity_data.get("source", transform.tool_name),
                        "properties": entity_data.get("properties", {}),
                        "confidence_score": 0.8,
                    },
                )
            except Exception as e:
                # Handle race condition or integrity error explicitly
                logger.warning(f"Error creating entity {entity_type}:{value} - {e}. Trying to get existing.")
                try:
                    entity = Entity.objects.get(
                        investigation=execution.investigation,
                        entity_type=entity_type,
                        value=value
                    )
                    created = False
                except Entity.DoesNotExist:
                     logger.error(f"Failed to create or retrieve entity {entity_type}:{value}: {e}")
                     continue

            if created:
                entities_created += 1
                created_entities.append(
                    {
                        "id": str(entity.id),
                        "type": entity.entity_type,
                        "value": entity.value,
                    }
                )

            # Create relationship between input entity and discovered entity
            if entity != execution.input_entity:
                relationship_type = _determine_relationship_type(
                    execution.input_entity.entity_type,
                    entity.entity_type,
                    transform.name,
                )

                relationship, created = Relationship.objects.get_or_create(
                    investigation=execution.investigation,
                    source_entity=execution.input_entity,
                    target_entity=entity,
                    relationship_type=relationship_type,
                    defaults={"source": transform.tool_name, "confidence_score": 0.8},
                )

                if created:
                    relationships_created += 1

    except Exception as e:
        logger.error(f"Error processing transform results: {str(e)}")
        raise

    return {
        "entities_created": entities_created,
        "relationships_created": relationships_created,
        "created_entities": created_entities,
        "raw_output": raw_results.get("stdout", ""),
        "command_executed": raw_results.get("command", ""),
        "execution_time": timezone.now().isoformat(),
    }


def _determine_relationship_type(
    source_type: str, target_type: str, transform_name: str
) -> str:
    """
    Determine the appropriate relationship type based on entity types and transform

    Args:
        source_type: Type of source entity
        target_type: Type of target entity
        transform_name: Name of the transform

    Returns:
        Relationship type string
    """
    # Define relationship mappings
    relationship_mappings = {
        ("domain", "domain"): "subdomain_of",
        ("domain", "ip"): "resolves_to",
        ("ip", "domain"): "hosted_on",
        ("domain", "email"): "associated_with",
        ("ip", "ip"): "communicates_with",
    }

    # Check for specific transform-based relationships
    if "dns" in transform_name.lower():
        if source_type == "domain" and target_type == "ip":
            return "resolves_to"
        elif source_type == "domain" and target_type == "domain":
            return "subdomain_of"

    # Use mapping or default
    return relationship_mappings.get((source_type, target_type), "associated_with")


@shared_task
def cleanup_old_executions():
    """
    Cleanup old transform executions
    """
    from datetime import timedelta

    from apps.investigations.models import TransformExecution

    try:
        cutoff_date = timezone.now() - timedelta(days=30)
        old_executions = TransformExecution.objects.filter(
            created_at__lt=cutoff_date, status__in=["completed", "failed", "cancelled"]
        )

        count = old_executions.count()
        old_executions.delete()

        logger.info(f"Cleaned up {count} old transform executions")
        return {"cleaned_up": count}

    except Exception as e:
        logger.error(f"Error cleaning up old executions: {str(e)}")
        raise


@shared_task
def health_check():
    """
    Celery health check task
    """
    return {
        "status": "healthy",
        "timestamp": timezone.now().isoformat(),
        "worker_id": health_check.request.id,
    }
