import logging
from datetime import timedelta

from django.core.cache import cache
from django.db.models import Avg, Count, Max, Min, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from apps.authentication.permissions import HasAPIAccess, IsOwnerOrReadOnly
from apps.investigations.models import Investigation

from .models import Entity, Relationship
from .serializers import (
    BulkEntityCreateSerializer,
    EntityCreateSerializer,
    EntityDetailSerializer,
    EntityListSerializer,
    RelationshipCreateSerializer,
    RelationshipListSerializer,
)

logger = logging.getLogger(__name__)


class StandardResultsSetPagination(PageNumberPagination):
    """Standard pagination for API views"""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class EntityListCreateView(generics.ListCreateAPIView):
    """List all entities or create a new entity"""

    permission_classes = [permissions.IsAuthenticated, HasAPIAccess]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return EntityCreateSerializer
        return EntityListSerializer

    def get_queryset(self):
        """Filter entities by investigation and user"""
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        queryset = Entity.objects.filter(investigation=investigation)

        # Search functionality
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(display_name__icontains=search)
                | Q(value__icontains=search)
                | Q(description__icontains=search)
            )

        # Filter by entity type
        entity_type = self.request.query_params.get("entity_type")
        if entity_type:
            queryset = queryset.filter(entity_type=entity_type)

        # Filter by confidence score range
        min_confidence = self.request.query_params.get("min_confidence")
        max_confidence = self.request.query_params.get("max_confidence")

        if min_confidence:
            try:
                min_conf = float(min_confidence)
                queryset = queryset.filter(confidence_score__gte=min_conf)
            except ValueError:
                pass

        if max_confidence:
            try:
                max_conf = float(max_confidence)
                queryset = queryset.filter(confidence_score__lte=max_conf)
            except ValueError:
                pass

        # Filter by verification status
        verified = self.request.query_params.get("verified")
        if verified is not None:
            is_verified = verified.lower() in ["true", "1", "yes"]
            queryset = queryset.filter(properties__verified=is_verified)

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
            "value",
            "-value",
            "display_name",
            "-display_name",
            "entity_type",
            "-entity_type",
            "confidence_score",
            "-confidence_score",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        ]

        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset.select_related("investigation")

    def create(self, request, *args, **kwargs):
        """Create a new entity or update existing one (deduplication)"""
        investigation_id = self.kwargs.get("investigation_id")
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        entity_type = serializer.validated_data.get("entity_type")
        value = serializer.validated_data.get("value")

        # Check for existing entity
        existing_entity = Entity.objects.filter(
            investigation=investigation, entity_type=entity_type, value=value
        ).first()

        if existing_entity:
            # Merge properties
            new_properties = serializer.validated_data.get("properties", {})
            if new_properties:
                existing_entity.properties.update(new_properties)
                existing_entity.save()
            
            # Serialize the existing entity
            response_serializer = EntityListSerializer(existing_entity)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        """Set the investigation for the entity"""
        investigation_id = self.kwargs.get("investigation_id")
        
        # We fetch investigation again here or could pass it if we refactored, 
        # but for safety let's just get it (cached by DB query usually)
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        entity = serializer.save(investigation=investigation)

        logger.info(
            f"Entity '{entity.display_name or entity.value}' created in investigation {investigation.name}"
        )

        # Clear investigation cache
        cache_key = f"investigation_entities_{investigation_id}"
        cache.delete(cache_key)


class EntityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an entity"""

    permission_classes = [permissions.IsAuthenticated, HasAPIAccess, IsOwnerOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return EntityCreateSerializer
        return EntityDetailSerializer

    def get_queryset(self):
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        return (
            Entity.objects.filter(investigation=investigation)
            .select_related("investigation")
            .prefetch_related(
                "source_relationships__target_entity",
                "target_relationships__source_entity",
            )
        )

    def perform_update(self, serializer):
        """Log entity updates"""
        entity = serializer.save()

        logger.info(
            f"Entity '{entity.display_name or entity.value}' updated in investigation {entity.investigation.name}"
        )

        # Clear caches
        cache_key = f"entity_{entity.id}"
        cache.delete(cache_key)
        cache_key = f"investigation_entities_{entity.investigation.id}"
        cache.delete(cache_key)

    def perform_destroy(self, instance):
        """Log entity deletion"""
        logger.info(
            f"Entity '{instance.display_name or instance.value}' deleted from investigation {instance.investigation.name}"
        )

        # Clear caches
        cache_key = f"entity_{instance.id}"
        cache.delete(cache_key)
        cache_key = f"investigation_entities_{instance.investigation.id}"
        cache.delete(cache_key)

        instance.delete()


class RelationshipListCreateView(generics.ListCreateAPIView):
    """List all relationships or create a new relationship"""

    permission_classes = [permissions.IsAuthenticated, HasAPIAccess]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RelationshipCreateSerializer
        return RelationshipListSerializer

    def get_queryset(self):
        """Filter relationships by investigation and user"""
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        queryset = Relationship.objects.filter(investigation=investigation)

        # Search functionality
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(relationship_type__icontains=search)
                | Q(description__icontains=search)
                | Q(source_entity__display_name__icontains=search)
                | Q(source_entity__value__icontains=search)
                | Q(target_entity__display_name__icontains=search)
                | Q(target_entity__value__icontains=search)
            )

        # Filter by relationship type
        relationship_type = self.request.query_params.get("relationship_type")
        if relationship_type:
            queryset = queryset.filter(relationship_type=relationship_type)

        # Filter by confidence score range
        min_confidence = self.request.query_params.get("min_confidence")
        max_confidence = self.request.query_params.get("max_confidence")

        if min_confidence:
            try:
                min_conf = float(min_confidence)
                queryset = queryset.filter(confidence_score__gte=min_conf)
            except ValueError:
                pass

        if max_confidence:
            try:
                max_conf = float(max_confidence)
                queryset = queryset.filter(confidence_score__lte=max_conf)
            except ValueError:
                pass

        # Filter by verification status
        verified = self.request.query_params.get("verified")
        if verified is not None:
            is_verified = verified.lower() in ["true", "1", "yes"]
            queryset = queryset.filter(properties__verified=is_verified)

        # Filter by source or target entity
        source_entity = self.request.query_params.get("source_entity")
        target_entity = self.request.query_params.get("target_entity")

        if source_entity:
            queryset = queryset.filter(source_entity_id=source_entity)

        if target_entity:
            queryset = queryset.filter(target_entity_id=target_entity)

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
            "relationship_type",
            "-relationship_type",
            "confidence_score",
            "-confidence_score",
            "created_at",
            "-created_at",
            "updated_at",
            "-updated_at",
        ]

        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset.select_related(
            "investigation", "source_entity", "target_entity"
        )

    def perform_create(self, serializer):
        """Set the investigation for the relationship"""
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        relationship = serializer.save(investigation=investigation)

        logger.info(
            f"Relationship '{relationship.relationship_type}' created between "
            f"'{relationship.source_entity.display_name or relationship.source_entity.value}' "
            f"and '{relationship.target_entity.display_name or relationship.target_entity.value}' "
            f"in investigation {investigation.name}"
        )

        # Clear investigation cache
        cache_key = f"investigation_relationships_{investigation_id}"
        cache.delete(cache_key)


class RelationshipDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a relationship"""

    permission_classes = [permissions.IsAuthenticated, HasAPIAccess, IsOwnerOrReadOnly]

    def get_queryset(self):
        investigation_id = self.kwargs.get("investigation_id")

        # Verify user owns the investigation
        investigation = get_object_or_404(
            Investigation, id=investigation_id, created_by=self.request.user
        )

        return Relationship.objects.filter(investigation=investigation).select_related(
            "investigation", "source_entity", "target_entity"
        )

    def perform_update(self, serializer):
        """Log relationship updates"""
        relationship = serializer.save()

        logger.info(
            f"Relationship '{relationship.relationship_type}' updated in investigation {relationship.investigation.name}"
        )

        # Clear caches
        cache_key = f"relationship_{relationship.id}"
        cache.delete(cache_key)
        cache_key = f"investigation_relationships_{relationship.investigation.id}"
        cache.delete(cache_key)

    def perform_destroy(self, instance):
        """Log relationship deletion"""
        logger.info(
            f"Relationship '{instance.relationship_type}' deleted from investigation {instance.investigation.name}"
        )

        # Clear caches
        cache_key = f"relationship_{instance.id}"
        cache.delete(cache_key)
        cache_key = f"investigation_relationships_{instance.investigation.id}"
        cache.delete(cache_key)

        instance.delete()


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def entity_stats(request, investigation_id):
    """Get entity statistics for an investigation"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    # Check cache first
    cache_key = f"entity_stats_{investigation_id}"
    cached_stats = cache.get(cache_key)
    if cached_stats:
        return Response(cached_stats)

    entities = Entity.objects.filter(investigation=investigation)
    relationships = Relationship.objects.filter(investigation=investigation)

    total_entities = entities.count()
    verified_entities = entities.filter(properties__verified=True).count()
    total_relationships = relationships.count()
    verified_relationships = relationships.filter(properties__verified=True).count()

    stats = {
        "entities": {
            "total": total_entities,
            "by_type": dict(
                entities.values("entity_type")
                .annotate(count=Count("id"))
                .values_list("entity_type", "count")
            ),
            "verified": verified_entities,
            "unverified": max(total_entities - verified_entities, 0),
            "confidence_stats": entities.aggregate(
                avg_confidence=Avg("confidence_score"),
                max_confidence=Max("confidence_score"),
                min_confidence=Min("confidence_score"),
            ),
            "recent": entities.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
        },
        "relationships": {
            "total": total_relationships,
            "by_type": dict(
                relationships.values("relationship_type")
                .annotate(count=Count("id"))
                .values_list("relationship_type", "count")
            ),
            "verified": verified_relationships,
            "unverified": max(total_relationships - verified_relationships, 0),
            "confidence_stats": relationships.aggregate(
                avg_confidence=Avg("confidence_score"),
                max_confidence=Max("confidence_score"),
                min_confidence=Min("confidence_score"),
            ),
            "recent": relationships.filter(
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count(),
        },
        "network": {
            "nodes": total_entities,
            "edges": total_relationships,
            "density": (
                total_relationships
                / max((total_entities * (total_entities - 1)) / 2, 1)
            )
            if total_entities > 1
            else 0,
            "most_connected_entities": list(
                entities.annotate(
                    connection_count=Count("source_relationships")
                    + Count("target_relationships")
                )
                .order_by("-connection_count")[:5]
                .values("id", "display_name", "value", "entity_type", "connection_count")
            ),
        },
    }

    # Cache for 5 minutes
    cache.set(cache_key, stats, 300)

    return Response(stats)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def geo_events(request):
    limit_param = request.query_params.get("limit")
    try:
        limit = int(limit_param) if limit_param is not None else 200
    except ValueError:
        limit = 200
    limit = max(1, min(limit, 500))

    entities = Entity.objects.filter(investigation__created_by=request.user).order_by(
        "-created_at"
    )
    events = []

    def extract_lat_lng(entity):
        props = entity.properties or {}
        lat = props.get("lat", props.get("latitude"))
        lng = props.get("lng", props.get("lon", props.get("longitude")))
        if lat is None or lng is None:
            if entity.entity_type == "geolocation" and isinstance(entity.value, str):
                parts = [p.strip() for p in entity.value.split(",") if p.strip()]
                if len(parts) >= 2:
                    lat = parts[0]
                    lng = parts[1]
        try:
            if lat is None or lng is None:
                return None, None
            return float(lat), float(lng)
        except (TypeError, ValueError):
            return None, None

    for entity in entities:
        lat, lng = extract_lat_lng(entity)
        if lat is None or lng is None:
            continue

        props = entity.properties or {}
        title = entity.display_name or entity.value or "Evento"
        kind = props.get("kind") or props.get("type") or entity.entity_type or "ioc"
        severity = props.get("severity") or "low"
        timestamp = entity.updated_at or entity.created_at
        events.append(
            {
                "id": str(entity.id),
                "title": title,
                "kind": kind,
                "severity": severity,
                "lat": lat,
                "lng": lng,
                "timestamp": timestamp.isoformat() if timestamp else None,
                "source": props.get("source") or entity.source,
            }
        )
        if len(events) >= limit:
            break

    return Response(events)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def bulk_create_entities(request, investigation_id):
    """Create multiple entities in bulk"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    serializer = BulkEntityCreateSerializer(data=request.data)
    if serializer.is_valid():
        entities_data = serializer.validated_data["entities"]

        # Create entities
        entities = []
        for entity_data in entities_data:
            entity = Entity.objects.create(investigation=investigation, **entity_data)
            entities.append(entity)

        logger.info(
            f"Bulk created {len(entities)} entities in investigation {investigation.name}"
        )

        # Clear cache
        cache_key = f"investigation_entities_{investigation_id}"
        cache.delete(cache_key)

        # Serialize created entities
        entity_serializer = EntityListSerializer(entities, many=True)

        return Response(
            {
                "message": f"{len(entities)} entities created successfully",
                "entities": entity_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def entity_relationships(request, investigation_id, entity_id):
    """Get all relationships for a specific entity"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    entity = get_object_or_404(Entity, id=entity_id, investigation=investigation)

    # Get relationships where entity is source or target
    source_relationships = Relationship.objects.filter(
        source_entity=entity
    ).select_related("target_entity")

    target_relationships = Relationship.objects.filter(
        target_entity=entity
    ).select_related("source_entity")

    # Serialize relationships
    source_data = RelationshipListSerializer(source_relationships, many=True).data
    target_data = RelationshipListSerializer(target_relationships, many=True).data

    return Response(
        {
            "entity": EntityDetailSerializer(entity).data,
            "outgoing_relationships": source_data,
            "incoming_relationships": target_data,
            "total_relationships": len(source_data) + len(target_data),
        }
    )


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def merge_entities(request, investigation_id):
    """Merge multiple entities into one"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    entity_ids = request.data.get("entity_ids", [])
    target_entity_id = request.data.get("target_entity_id")

    if len(entity_ids) < 2:
        return Response(
            {"error": "At least 2 entities are required for merging"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not target_entity_id:
        return Response(
            {"error": "Target entity ID is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verify all entities exist and belong to the investigation
    entities = Entity.objects.filter(id__in=entity_ids, investigation=investigation)

    if len(entities) != len(entity_ids):
        return Response(
            {"error": "One or more entities not found"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    target_entity = get_object_or_404(
        Entity, id=target_entity_id, investigation=investigation
    )

    if target_entity.id not in entity_ids:
        return Response(
            {"error": "Target entity must be one of the entities to merge"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Merge entities
    entities_to_merge = entities.exclude(id=target_entity_id)

    # Update relationships to point to target entity
    for entity in entities_to_merge:
        # Update source relationships
        Relationship.objects.filter(source_entity=entity).update(
            source_entity=target_entity
        )

        # Update target relationships
        Relationship.objects.filter(target_entity=entity).update(
            target_entity=target_entity
        )

    # Merge metadata and properties
    merged_metadata = target_entity.metadata or {}
    merged_properties = target_entity.properties or {}

    for entity in entities_to_merge:
        if entity.metadata:
            merged_metadata.update(entity.metadata)
        if entity.properties:
            merged_properties.update(entity.properties)

    target_entity.metadata = merged_metadata
    target_entity.properties = merged_properties
    target_entity.save()

    # Delete merged entities
    merged_count = entities_to_merge.count()
    entities_to_merge.delete()

    logger.info(
        f"Merged {merged_count} entities into entity "
        f"'{target_entity.display_name or target_entity.value}' "
        f"in investigation {investigation.name}"
    )

    # Clear caches
    cache_key = f"investigation_entities_{investigation_id}"
    cache.delete(cache_key)
    cache_key = f"investigation_relationships_{investigation_id}"
    cache.delete(cache_key)

    return Response(
        {
            "message": f"Successfully merged {merged_count} entities",
            "target_entity": EntityDetailSerializer(target_entity).data,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def entity_graph(request, investigation_id):
    """Get graph data for visualization"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    # Get limit from query params
    try:
        limit = int(request.query_params.get("limit", 500))  # Default to 500 nodes to prevent saturation
    except ValueError:
        limit = 500

    # Check cache first (include limit in key)
    cache_key = f"entity_graph_{investigation_id}_{limit}"
    cached_graph = cache.get(cache_key)
    if cached_graph:
        return Response(cached_graph)

    # Get entities, prioritize by connectivity (degree centrality)
    entities_qs = Entity.objects.filter(investigation=investigation).annotate(
        degree=Count("source_relationships") + Count("target_relationships")
    ).order_by("-degree", "-created_at")

    if limit > 0:
        entities_qs = entities_qs[:limit]

    # Fetch entities
    entities = list(entities_qs)
    entity_ids = {e.id for e in entities}

    # Get relationships only between selected entities
    relationships = Relationship.objects.filter(
        investigation=investigation,
        source_entity__id__in=entity_ids,
        target_entity__id__in=entity_ids
    ).select_related("source_entity", "target_entity")

    # Build graph data
    nodes = []
    for entity in entities:
        nodes.append(
            {
                "id": str(entity.id),
                "name": entity.display_name or entity.value,
                "value": entity.value,
                "display_name": entity.display_name,
                "type": entity.entity_type,
                "confidence": entity.confidence_score,
                "verified": bool((entity.properties or {}).get("verified")),
                "properties": entity.properties or {},
                "degree": getattr(entity, 'degree', 0)
            }
        )

    edges = []
    for relationship in relationships:
        edges.append(
            {
                "id": str(relationship.id),
                "source": str(relationship.source_entity.id),
                "target": str(relationship.target_entity.id),
                "type": relationship.relationship_type,
                "confidence": relationship.confidence_score,
                "verified": bool((relationship.properties or {}).get("verified")),
                "properties": relationship.properties or {},
            }
        )

    graph_data = {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "node_types": list(set(node["type"] for node in nodes)),
            "edge_types": list(set(edge["type"] for edge in edges)),
            "total_nodes_available": Entity.objects.filter(investigation=investigation).count(),
        },
    }

    # Cache for 60 seconds
    cache.set(cache_key, graph_data, 60)

    return Response(graph_data)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def validate_entities(request, investigation_id):
    """Validate entities in an investigation"""
    # Verify user owns the investigation
    investigation = get_object_or_404(
        Investigation, id=investigation_id, created_by=request.user
    )

    entities = Entity.objects.filter(investigation=investigation)

    validation_results = []

    for entity in entities:
        issues = []

        # Check for empty or invalid values
        if not entity.value or entity.value.strip() == "":
            issues.append("Empty or invalid value")

        # Check confidence score
        if entity.confidence_score < 0.3:
            issues.append("Low confidence score")

        # Check for duplicates
        duplicates = Entity.objects.filter(
            investigation=investigation,
            entity_type=entity.entity_type,
            value=entity.value,
        ).exclude(id=entity.id)

        if duplicates.exists():
            issues.append(f"Duplicate entities found: {[d.id for d in duplicates]}")

        # Type-specific validation
        if entity.entity_type == "email":
            import re

            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, entity.value):
                issues.append("Invalid email format")

        elif entity.entity_type == "ip":
            import ipaddress

            try:
                ipaddress.ip_address(entity.value)
            except ValueError:
                issues.append("Invalid IP address format")

        elif entity.entity_type == "domain":
            import re

            domain_pattern = (
                r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.[a-zA-Z]{2,}$"
            )
            if not re.match(domain_pattern, entity.value):
                issues.append("Invalid domain format")

        validation_results.append(
            {
                "entity_id": entity.id,
                "entity_name": entity.display_name or entity.value,
                "entity_type": entity.entity_type,
                "is_valid": len(issues) == 0,
                "issues": issues,
            }
        )

    # Summary
    total_entities = len(validation_results)
    valid_entities = sum(1 for r in validation_results if r["is_valid"])
    invalid_entities = total_entities - valid_entities

    return Response(
        {
            "summary": {
                "total_entities": total_entities,
                "valid_entities": valid_entities,
                "invalid_entities": invalid_entities,
                "validation_rate": (valid_entities / max(total_entities, 1)) * 100,
            },
            "results": validation_results,
        }
    )


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def entity_types(request):
    return Response([choice[0] for choice in Entity.ENTITY_TYPE_CHOICES])


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated, HasAPIAccess])
def all_entities(request):
    """Get all entities across all user's investigations"""
    # Get all investigations owned by the user
    user_investigations = Investigation.objects.filter(created_by=request.user)

    # Get all entities from user's investigations
    entities = (
        Entity.objects.filter(investigation__in=user_investigations)
        .select_related("investigation")
        .order_by("-created_at")
    )

    # Apply pagination
    paginator = StandardResultsSetPagination()
    page = paginator.paginate_queryset(entities, request)

    if page is not None:
        serializer = EntityListSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    serializer = EntityListSerializer(entities, many=True)
    return Response(serializer.data)
