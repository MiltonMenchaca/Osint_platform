import logging
import re
from datetime import timedelta
from urllib.parse import urlparse

from django.core.cache import cache
from django.db import IntegrityError
from django.db.models import Avg, Count, Max, Min, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.authentication.permissions import HasAPIAccess, IsOwnerOrReadOnly
from apps.entities.models import Entity, Relationship
from apps.transforms.models import Transform

from .models import Investigation, TransformExecution
from .serializers import (
    InvestigationCreateSerializer,
    InvestigationDetailSerializer,
    InvestigationListSerializer,
    TransformExecutionCreateSerializer,
    TransformExecutionDetailSerializer,
    TransformExecutionListSerializer,
)
from .tasks import execute_transform
from .services import AutoReconService, OsintCatalogService

class AutoReconView(generics.GenericAPIView):
    """
    Endpoint to trigger automated reconnaissance
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        target = request.data.get('target')
        investigation_id = request.data.get("investigation_id")
        if not target:
            return Response(
                {"error": "Target URL/Domain is required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            service = AutoReconService()
            results = service.run_scan(target)
            if investigation_id:
                investigation = get_object_or_404(
                    Investigation, id=investigation_id, created_by=request.user
                )
                metadata = investigation.metadata or {}
                metadata["auto_recon"] = results
                metadata["auto_recon_updated_at"] = timezone.now().isoformat()
                investigation.metadata = metadata
                investigation.save(update_fields=["metadata", "updated_at"])

                cleaned_target = str(results.get("target") or target).strip().strip("`")
                parsed = urlparse(cleaned_target if "://" in cleaned_target else f"http://{cleaned_target}")
                domain = parsed.hostname or cleaned_target.split("/")[0]
                is_ip = bool(re.match(r"^(?:\d{1,3}\.){3}\d{1,3}$", domain))
                seed_type = "ip" if is_ip else "domain"
                seed_entity, _ = Entity.objects.get_or_create(
                    investigation=investigation,
                    entity_type=seed_type,
                    value=domain,
                    defaults={"source": "auto_recon", "confidence_score": 0.8, "is_seed": True},
                )
                url_entity = None
                if cleaned_target.startswith(("http://", "https://")) and cleaned_target != domain:
                    url_entity, _ = Entity.objects.get_or_create(
                        investigation=investigation,
                        entity_type="url",
                        value=cleaned_target,
                        defaults={"source": "auto_recon", "confidence_score": 0.7},
                    )
                    if url_entity.id != seed_entity.id:
                        Relationship.objects.get_or_create(
                            investigation=investigation,
                            source_entity=seed_entity,
                            target_entity=url_entity,
                            relationship_type="associated_with",
                            defaults={
                                "confidence_score": 0.7,
                                "properties": {"source": "auto_recon", "tool": "target"},
                            },
                        )

                existing = {
                    (e.entity_type, e.value): e
                    for e in Entity.objects.filter(investigation=investigation)
                }

                tools = results.get("tools") or {}
                aggregate_technologies = set()
                aggregate_ports = {}
                aggregate_services = []
                aggregate_dns = []
                aggregate_whois = None
                for tool_name, tool_data in tools.items():
                    items = tool_data.get("results") if isinstance(tool_data, dict) else None
                    if not isinstance(items, list):
                        continue
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        raw_value = item.get("value")
                        if not raw_value:
                            continue
                        value = str(raw_value).strip()
                        raw_type = str(item.get("type") or "other").lower()
                        if raw_type == "service" and value.startswith(("http://", "https://")):
                            entity_type = "url"
                        elif raw_type == "port":
                            entity_type = "port"
                        elif raw_type == "service":
                            entity_type = "service"
                        elif raw_type in {
                            "domain",
                            "ip",
                            "email",
                            "person",
                            "organization",
                            "phone",
                            "url",
                            "port",
                            "service",
                            "hash",
                            "file",
                            "cryptocurrency",
                            "social_media",
                            "geolocation",
                            "other",
                        }:
                            entity_type = raw_type
                        else:
                            entity_type = "other"

                        key = (entity_type, value)
                        entity = existing.get(key)
                        if not entity:
                            properties = {
                                "tool": tool_name,
                                "raw_type": raw_type,
                                **(item.get("properties") or {}),
                            }
                            try:
                                entity, _ = Entity.objects.get_or_create(
                                    investigation=investigation,
                                    entity_type=entity_type,
                                    value=value,
                                    defaults={
                                        "source": tool_name,
                                        "confidence_score": float(item.get("confidence") or 0.6),
                                        "properties": properties,
                                    },
                                )
                            except IntegrityError:
                                entity = Entity.objects.filter(
                                    investigation=investigation,
                                    entity_type=entity_type,
                                    value=value,
                                ).first()
                            if entity:
                                existing[key] = entity
                        else:
                            props = entity.properties or {}
                            new_props = item.get("properties") or {}
                            if props != {**props, **new_props}:
                                props.update(new_props)
                                props["tool"] = props.get("tool") or tool_name
                                props["raw_type"] = props.get("raw_type") or raw_type
                                entity.properties = props
                                if not entity.source:
                                    entity.source = tool_name
                                entity.save(update_fields=["properties", "source", "updated_at"])

                        if seed_entity.id != entity.id:
                            Relationship.objects.get_or_create(
                                investigation=investigation,
                                source_entity=seed_entity,
                                target_entity=entity,
                                relationship_type="associated_with",
                                defaults={
                                    "confidence_score": float(item.get("confidence") or 0.6),
                                    "properties": {"source": "auto_recon", "tool": tool_name},
                                },
                            )

                        if tool_name == "wappalyzer":
                            if raw_type in {"technology", "other"}:
                                aggregate_technologies.add(value)
                        if tool_name == "nmap":
                            port = item.get("properties", {}).get("port")
                            service_name = item.get("properties", {}).get("service_name")
                            ip_value = item.get("properties", {}).get("ip")
                            if port:
                                aggregate_ports.setdefault(str(port), {"port": port, "services": set(), "ips": set()})
                                if service_name:
                                    aggregate_ports[str(port)]["services"].add(str(service_name))
                                if ip_value:
                                    aggregate_ports[str(port)]["ips"].add(str(ip_value))
                            if raw_type == "service":
                                aggregate_services.append(
                                    {
                                        "value": value,
                                        "service_name": service_name,
                                        "port": port,
                                        "ip": ip_value,
                                    }
                                )
                        if tool_name == "dns":
                            dns_a = item.get("properties", {}).get("dns_a")
                            dns_mx = item.get("properties", {}).get("dns_mx")
                            dns_ns = item.get("properties", {}).get("dns_ns")
                            aggregate_dns.append(
                                {
                                    "domain": value,
                                    "dns_a": dns_a,
                                    "dns_mx": dns_mx,
                                    "dns_ns": dns_ns,
                                    "fuzzer": item.get("properties", {}).get("fuzzer"),
                                }
                            )
                        if tool_name == "whois" and not aggregate_whois:
                            aggregate_whois = item.get("properties", {}).get("raw")

                seed_props = seed_entity.properties or {}
                if aggregate_technologies:
                    seed_props["technologies"] = sorted(aggregate_technologies)
                if aggregate_ports:
                    formatted_ports = []
                    for port_key, data in aggregate_ports.items():
                        formatted_ports.append(
                            {
                                "port": data["port"],
                                "services": sorted(list(data["services"])) if data["services"] else [],
                                "ips": sorted(list(data["ips"])) if data["ips"] else [],
                            }
                        )
                    seed_props["open_ports"] = sorted(formatted_ports, key=lambda p: p["port"])
                if aggregate_services:
                    seed_props["services"] = aggregate_services[:200]
                if aggregate_dns:
                    seed_props["dns_records"] = aggregate_dns[:200]
                if aggregate_whois:
                    seed_props["whois_raw"] = aggregate_whois
                if seed_props != (seed_entity.properties or {}):
                    seed_entity.properties = seed_props
                    seed_entity.save(update_fields=["properties", "updated_at"])

                if url_entity:
                    url_props = url_entity.properties or {}
                    if aggregate_technologies:
                        url_props["technologies"] = sorted(aggregate_technologies)
                    if aggregate_ports:
                        formatted_ports = []
                        for port_key, data in aggregate_ports.items():
                            formatted_ports.append(
                                {
                                    "port": data["port"],
                                    "services": sorted(list(data["services"])) if data["services"] else [],
                                    "ips": sorted(list(data["ips"])) if data["ips"] else [],
                                }
                            )
                        url_props["open_ports"] = sorted(formatted_ports, key=lambda p: p["port"])
                    if aggregate_services:
                        url_props["services"] = aggregate_services[:200]
                    if aggregate_dns:
                        url_props["dns_records"] = aggregate_dns[:200]
                    if aggregate_whois:
                        url_props["whois_raw"] = aggregate_whois
                    if url_props != (url_entity.properties or {}):
                        url_entity.properties = url_props
                        url_entity.save(update_fields=["properties", "updated_at"])

                if aggregate_technologies:
                    for tech in aggregate_technologies:
                        tech_value = f"tech:{tech}"
                        key = ("other", tech_value)
                        tech_entity = existing.get(key)
                        if not tech_entity:
                            tech_entity = Entity.objects.create(
                                investigation=investigation,
                                entity_type="other",
                                value=tech_value,
                                source="wappalyzer",
                                confidence_score=0.8,
                                properties={"category": "technology", "label": tech},
                            )
                            existing[key] = tech_entity
                        Relationship.objects.get_or_create(
                            investigation=investigation,
                            source_entity=seed_entity,
                            target_entity=tech_entity,
                            relationship_type="uses",
                            defaults={
                                "confidence_score": 0.8,
                                "properties": {"source": "auto_recon", "tool": "wappalyzer"},
                            },
                        )

                if aggregate_ports:
                    for port_item in aggregate_ports.values():
                        port_number = str(port_item.get("port"))
                        port_value = f"port:{port_number}"
                        key = ("port", port_value)
                        port_entity = existing.get(key)
                        if not port_entity:
                            port_entity = Entity.objects.create(
                                investigation=investigation,
                                entity_type="port",
                                value=port_value,
                                source="nmap",
                                confidence_score=0.8,
                                properties={
                                    "category": "port",
                                    "port": port_item.get("port"),
                                    "services": sorted(list(port_item.get("services") or [])),
                                    "ips": sorted(list(port_item.get("ips") or [])),
                                },
                            )
                            existing[key] = port_entity
                        Relationship.objects.get_or_create(
                            investigation=investigation,
                            source_entity=seed_entity,
                            target_entity=port_entity,
                            relationship_type="exposes",
                            defaults={
                                "confidence_score": 0.8,
                                "properties": {"source": "auto_recon", "tool": "nmap"},
                            },
                        )

                cache.delete(f"investigation_entities_{investigation.id}")
                cache.delete(f"entity_stats_{investigation.id}")
                for graph_limit in (100, 200, 500, 1000):
                    cache.delete(f"entity_graph_{investigation.id}_{graph_limit}")

            return Response(results, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Auto recon failed: {e}")
            return Response(
                {"error": str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def osint_catalog(request):
    target = request.query_params.get("target")
    service = OsintCatalogService()
    data = service.build_catalog(target=target)
    return Response(data, status=status.HTTP_200_OK)



# Create temporary serializers for missing ones
class BulkExecutionSerializer(serializers.Serializer):
    transform_names = serializers.ListField(child=serializers.CharField())
    input = serializers.JSONField()
    parameters = serializers.JSONField(required=False)


class ExecutionControlSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["cancel", "retry"])


logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API views"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class InvestigationListCreateView(generics.ListCreateAPIView):
    """List all investigations or create a new investigation"""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return InvestigationCreateSerializer
        return InvestigationListSerializer

    def get_queryset(self):
        """Filter investigations by user and search parameters"""
        queryset = Investigation.objects.filter(created_by=self.request.user)

        # Search functionality
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(description__icontains=search)
                | Q(metadata__target__icontains=search)
                | Q(metadata__case_number__icontains=search)
            )

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority_filter = self.request.query_params.get("priority")
        if priority_filter:
            queryset = queryset.filter(metadata__priority=priority_filter)

        # Date range filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            try:
                from datetime import datetime

                date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                queryset = queryset.filter(created_at__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                from datetime import datetime

                date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                queryset = queryset.filter(created_at__lte=date_to)
            except ValueError:
                pass

        # Ordering
        ordering = self.request.query_params.get("ordering", "-created_at")
        valid_orderings = [
            "name",
            "-name",
            "status",
            "-status",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        ]

        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset.select_related("created_by").prefetch_related(
            "entities", "relationships", "transform_executions"
        )

    def perform_create(self, serializer):
        """Set the investigation creator"""
        investigation = serializer.save(created_by=self.request.user)

        logger.info(f"Investigation '{investigation.name}' created")

        # Clear user's investigation cache
        cache_key = f"user_investigations_{self.request.user.id}"
        cache.delete(cache_key)


class ExecuteDorksView(generics.GenericAPIView):
    """
    Endpoint to execute Google Dorks
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, investigation_id, *args, **kwargs):
        dorks = request.data.get('dorks', [])
        if not dorks:
            return Response(
                {"error": "No dorks provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        investigation = get_object_or_404(Investigation, id=investigation_id, created_by=request.user)
        
        # Ensure Google Search transform exists
        transform, _ = Transform.objects.get_or_create(
            name="google_search",
            defaults={
                "display_name": "Google Search",
                "description": "Execute Google Search queries (Dorks)",
                "category": "search",
                "input_type": "any",
                "output_types": ["url"],
                "tool_name": "google_search",
                "command_template": "google_search {value}",
                "is_enabled": True
            }
        )
        
        # Find a suitable input entity (e.g. the seed domain)
        input_entity = investigation.entities.filter(is_seed=True).first()
        if not input_entity:
            # Fallback: create a dummy entity representing the target
             input_entity, _ = Entity.objects.get_or_create(
                investigation=investigation,
                entity_type="domain",
                value=request.data.get("target_domain", "unknown_target"),
                defaults={"is_seed": True}
             )

        execution_ids = []
        for dork in dorks:
            query = dork.get("query", dork) if isinstance(dork, dict) else dork
            
            # Create execution record
            execution = TransformExecution.objects.create(
                investigation=investigation,
                transform_name=transform.name,
                input_entity=input_entity,
                status="pending",
                parameters={"query": query}
            )
            
            # Queue task
            execute_transform.delay(
                execution_id=str(execution.id),
                transform_name=transform.name,
                input_value=query
            )
            execution_ids.append(execution.id)
            
        return Response({
            "message": f"Queued {len(execution_ids)} dork searches",
            "execution_ids": execution_ids
        }, status=status.HTTP_202_ACCEPTED)


class InvestigationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an investigation"""

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return InvestigationDetailSerializer  # Using DetailSerializer temporarily
        return InvestigationDetailSerializer

    def get_queryset(self):
        return (
            Investigation.objects.filter(created_by=self.request.user)
            .select_related("created_by")
            .prefetch_related(
                "entities",
                "relationships",
                "transform_executions",
                "transform_executions__input_entity",
            )
        )

    def perform_update(self, serializer):
        """Log investigation updates"""
        investigation = serializer.save()

        logger.info(
            f"Investigation '{investigation.name}' updated by user {self.request.user.username}"
        )

        # Clear caches
        cache_key = f"investigation_{investigation.id}"
        cache.delete(cache_key)
        cache_key = f"user_investigations_{self.request.user.id}"
        cache.delete(cache_key)

    def perform_destroy(self, instance):
        """Log investigation deletion"""
        logger.info(
            f"Investigation '{instance.name}' deleted by user {self.request.user.username}"
        )

        # Clear caches
        cache_key = f"investigation_{instance.id}"
        cache.delete(cache_key)
        cache_key = f"user_investigations_{self.request.user.id}"
        cache.delete(cache_key)

        instance.delete()


class TransformExecutionListCreateView(generics.ListCreateAPIView):
    """List transform executions or create a new execution"""

    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return TransformExecutionCreateSerializer
        return TransformExecutionListSerializer

    def get_queryset(self):
        """Filter executions by investigation and user"""
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        queryset = TransformExecution.objects.filter(investigation=investigation)

        # Filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by transform
        transform_filter = self.request.query_params.get("transform")
        if transform_filter:
            queryset = queryset.filter(transform_name=transform_filter)

        # Date range filtering
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            try:
                from datetime import datetime

                date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                queryset = queryset.filter(created_at__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                from datetime import datetime

                date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                queryset = queryset.filter(created_at__lte=date_to)
            except ValueError:
                pass

        # Ordering
        ordering = self.request.query_params.get("ordering", "-created_at")
        valid_orderings = [
            "status",
            "-status",
            "created_at",
            "-created_at",
            "started_at",
            "-started_at",
            "completed_at",
            "-completed_at",
        ]

        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset.select_related("investigation", "input_entity")

    def perform_create(self, serializer):
        """Create and execute transform"""
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        execution = serializer.save(
            investigation=investigation
        )

        # Execute transform asynchronously
        task = execute_transform.delay(
            str(execution.id),
            execution.transform_name,
            execution.input_entity.value,
            execution.parameters,
        )
        execution.celery_task_id = task.id
        execution.save(update_fields=["celery_task_id", "updated_at"])

        logger.info(
            f"Transform execution {execution.id} created and queued for investigation {investigation.name}"
        )


class TransformExecutionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a transform execution"""

    permission_classes = [permissions.IsAuthenticated, HasAPIAccess, IsOwnerOrReadOnly]
    serializer_class = TransformExecutionDetailSerializer

    def get_queryset(self):
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        return TransformExecution.objects.filter(investigation=investigation).select_related(
            "investigation", "input_entity"
        )

    def update(self, request, *args, **kwargs):
        """Only allow status updates"""
        instance = self.get_object()

        # Only allow certain status transitions
        new_status = request.data.get("status")
        if new_status and new_status != instance.status:
            if instance.status == "completed" and new_status != "completed":
                return Response(
                    {"error": "Cannot change status of completed execution"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if instance.status == "failed" and new_status not in [
                "pending",
                "cancelled",
            ]:
                return Response(
                    {
                        "error": "Failed executions can only be reset to pending or cancelled"
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return super().update(request, *args, **kwargs)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def investigation_stats(request, investigation_id):
    """Get investigation statistics"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    # Check cache first
    cache_key = f"investigation_stats_{investigation_id}"
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return Response(cached_stats)

    # Calculate statistics
    executions = TransformExecution.objects.filter(investigation=investigation)
    entities = Entity.objects.filter(investigation=investigation)
    relationships = Relationship.objects.filter(investigation=investigation)

    stats = {
        "investigation": {
            "id": investigation.id,
            "name": investigation.name,
            "status": investigation.status,
            "created_at": investigation.created_at,
            "updated_at": investigation.updated_at,
        },
        "executions": {
            "total": executions.count(),
            "by_status": dict(
                executions.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "recent": executions.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            "avg_duration": None,
        },
        "entities": {
            "total": entities.count(),
            "by_type": dict(
                entities.values("entity_type")
                .annotate(count=Count("id"))
                .values_list("entity_type", "count")
            ),
            "confidence_stats": entities.aggregate(
                avg_confidence=Avg("confidence_score"),
                max_confidence=Max("confidence_score"),
                min_confidence=Min("confidence_score"),
            ),
        },
        "relationships": {
            "total": relationships.count(),
            "by_type": dict(
                relationships.values("relationship_type")
                .annotate(count=Count("id"))
                .values_list("relationship_type", "count")
            ),
            "confidence_stats": relationships.aggregate(
                avg_confidence=Avg("confidence_score"),
                max_confidence=Max("confidence_score"),
                min_confidence=Min("confidence_score"),
            ),
        },
    }

    duration_rows = executions.filter(
        status="completed", started_at__isnull=False, completed_at__isnull=False
    ).values_list("started_at", "completed_at")
    total_seconds = 0.0
    duration_count = 0
    for started_at, completed_at in duration_rows:
        if started_at and completed_at:
            delta = completed_at - started_at
            total_seconds += delta.total_seconds()
            duration_count += 1
    stats["executions"]["avg_duration"] = (
        total_seconds / duration_count if duration_count > 0 else 0
    )

    # Cache for 5 minutes
    cache.set(cache_key, stats, 300)

    return Response(stats)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def bulk_execute_transforms(request, investigation_id):
    """Execute multiple transforms in bulk"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    serializer = BulkExecutionSerializer(data=request.data)
    if serializer.is_valid():
        transform_names = serializer.validated_data["transform_names"]
        input_payload = serializer.validated_data["input"]
        parameters = serializer.validated_data.get("parameters") or {}

        input_entity_id = input_payload.get("input_entity_id")
        input_entity = None
        if input_entity_id:
            input_entity = get_object_or_404(
                Entity, id=input_entity_id, investigation=investigation
            )
        else:
            entity_type = input_payload.get("entity_type")
            value = input_payload.get("value")
            if not entity_type or not value:
                return Response(
                    {"error": "input must include input_entity_id or entity_type and value"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            input_entity, _ = Entity.objects.get_or_create(
                investigation=investigation,
                entity_type=entity_type,
                value=value,
                defaults={"source": "bulk_execution", "confidence_score": 1.0},
            )

        # Create execution records
        executions = []
        for transform_name in transform_names:
            transform = get_object_or_404(Transform, name=transform_name, is_enabled=True)
            execution = TransformExecution.objects.create(
                investigation=investigation,
                transform_name=transform.name,
                input_entity=input_entity,
                parameters=parameters,
            )
            executions.append(execution)

        # Execute transforms asynchronously
        execution_ids = []
        for execution in executions:
            task = execute_transform.delay(
                str(execution.id),
                execution.transform_name,
                execution.input_entity.value,
                execution.parameters,
            )
            execution.celery_task_id = task.id
            execution.save(update_fields=["celery_task_id", "updated_at"])
            execution_ids.append(execution.id)

        logger.info(
            f"Bulk execution of {len(executions)} transforms queued for investigation {investigation.name}"
        )

        return Response(
            {
                "message": f"{len(executions)} transforms queued for execution",
                "execution_ids": execution_ids,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def control_execution(request, investigation_id, execution_id):
    """Control transform execution (pause, resume, cancel)"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    execution = get_object_or_404(
        TransformExecution, id=execution_id, investigation=investigation
    )

    serializer = ExecutionControlSerializer(data=request.data)
    if serializer.is_valid():
        action = serializer.validated_data["action"]

        if action == "cancel":
            if execution.status in ["pending", "running"]:
                execution.status = "cancelled"
                execution.error_message = "Cancelled by user"
                execution.completed_at = timezone.now()
                execution.save()

                if execution.celery_task_id:
                    try:
                        from celery import current_app

                        current_app.control.revoke(
                            execution.celery_task_id, terminate=True
                        )
                    except Exception as exc:
                        logger.error(
                            f"Failed to revoke Celery task {execution.celery_task_id}: {str(exc)}"
                        )

                logger.info(
                    f"Execution {execution_id} cancelled by user {request.user.username}"
                )

                return Response({"message": "Execution cancelled"})
            else:
                return Response(
                    {"error": "Cannot cancel execution in current status"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        elif action == "retry":
            if execution.status in ["failed", "cancelled"]:
                execution.status = "pending"
                execution.error_message = None
                execution.started_at = None
                execution.completed_at = None
                execution.results = {}
                execution.save()

                # Re-queue the task
                task = execute_transform.delay(
                    str(execution.id),
                    execution.transform_name,
                    execution.input_entity.value,
                    execution.parameters,
                )
                execution.celery_task_id = task.id
                execution.save(update_fields=["celery_task_id", "updated_at"])

                logger.info(
                    f"Execution {execution_id} retried by user {request.user.username}"
                )

                return Response({"message": "Execution queued for retry"})
            else:
                return Response(
                    {"error": "Cannot retry execution in current status"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        else:
            return Response(
                {"error": "Invalid action"}, status=status.HTTP_400_BAD_REQUEST
            )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def user_investigations_stats(request):
    """Get user's investigation statistics"""
    # Check cache first
    cache_key = f"user_investigations_stats_{request.user.id}"
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return Response(cached_stats)

    investigations = Investigation.objects.filter(created_by=request.user)
    executions = TransformExecution.objects.filter(
        investigation__created_by=request.user
    )
    entities = Entity.objects.filter(investigation__created_by=request.user)
    relationships = Relationship.objects.filter(investigation__created_by=request.user)

    stats = {
        "investigations": {
            "total": investigations.count(),
            "by_status": dict(
                investigations.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "recent": investigations.filter(
                created_at__gte=timezone.now() - timedelta(days=30)
            ).count(),
        },
        "executions": {
            "total": executions.count(),
            "by_status": dict(
                executions.values("status")
                .annotate(count=Count("id"))
                .values_list("status", "count")
            ),
            "recent": executions.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
            "success_rate": (
                executions.filter(status="completed").count()
                / max(executions.count(), 1)
            )
            * 100,
        },
        "entities": {
            "total": entities.count(),
            "by_type": dict(
                entities.values("entity_type")
                .annotate(count=Count("id"))
                .values_list("entity_type", "count")
            ),
            "avg_confidence": entities.aggregate(
                avg_confidence=Avg("confidence_score")
            )["avg_confidence"],
        },
        "relationships": {
            "total": relationships.count(),
            "by_type": dict(
                relationships.values("relationship_type")
                .annotate(count=Count("id"))
                .values_list("relationship_type", "count")
            ),
            "avg_confidence": relationships.aggregate(
                avg_confidence=Avg("confidence_score")
            )["avg_confidence"],
        },
    }

    # Cache for 10 minutes
    cache.set(cache_key, stats, 600)

    return Response(stats)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def investigation_export(request, investigation_id):
    """Export investigation data"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    # Get all related data
    executions = TransformExecution.objects.filter(
        investigation=investigation
    ).select_related("transform", "created_by")

    entities = Entity.objects.filter(investigation=investigation)

    relationships = Relationship.objects.filter(
        investigation=investigation
    ).select_related("source_entity", "target_entity")

    # Serialize data
    investigation_data = InvestigationDetailSerializer(investigation).data
    execution_data = TransformExecutionDetailSerializer(executions, many=True).data

    from apps.entities.serializers import (
        EntityDetailSerializer,
        RelationshipDetailSerializer,
    )

    entity_data = EntityDetailSerializer(entities, many=True).data
    relationship_data = RelationshipDetailSerializer(relationships, many=True).data

    export_data = {
        "investigation": investigation_data,
        "executions": execution_data,
        "entities": entity_data,
        "relationships": relationship_data,
        "exported_at": timezone.now().isoformat(),
        "exported_by": request.user.username,
    }

    logger.info(
        f"Investigation {investigation.name} exported by user {request.user.username}"
    )

    return Response(export_data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def execution_logs(request, investigation_id, execution_id):
    """Get execution logs and output"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    execution = get_object_or_404(
        TransformExecution, id=execution_id, investigation=investigation
    )

    logs_data = {
        "execution_id": execution.id,
        "status": execution.status,
        "transform_name": execution.transform_name,
        "input_entity": {
            "id": str(execution.input_entity.id),
            "type": execution.input_entity.entity_type,
            "value": execution.input_entity.value,
        },
        "parameters": execution.parameters,
        "results": execution.results,
        "error_message": execution.error_message,
        "created_at": execution.created_at,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
        "duration": None,
    }

    # Calculate duration if available
    if execution.started_at and execution.completed_at:
        duration = execution.completed_at - execution.started_at
        logs_data["duration"] = duration.total_seconds()

    return Response(logs_data)
