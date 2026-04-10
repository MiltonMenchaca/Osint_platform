from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import Entity, Relationship


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = [
        "value",
        "entity_type",
        "investigation_link",
        "source",
        "confidence_score",
        "relationships_count",
        "created_at",
    ]
    list_filter = [
        "entity_type",
        "source",
        "confidence_score",
        "created_at",
        "investigation__status",
    ]
    search_fields = ["value", "investigation__name", "source", "properties"]
    readonly_fields = ["id", "created_at", "updated_at", "relationships_count"]

    fieldsets = (
        (
            "Entity Information",
            {"fields": ("id", "investigation", "entity_type", "value")},
        ),
        ("Metadata", {"fields": ("source", "confidence_score", "properties")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def investigation_link(self, obj):
        """Display investigation as a link"""
        url = reverse("admin:investigations_investigation_change", args=[obj.investigation.id])
        return format_html('<a href="{}">{}</a>', url, obj.investigation.name)

    investigation_link.short_description = "Investigation"

    def relationships_count(self, obj):
        """Display count of relationships for this entity"""
        count = obj.source_relationships.count() + obj.target_relationships.count()
        if count > 0:
            return format_html('<span style="color: #0066cc; font-weight: bold;">{}</span>', count)
        return "0"

    relationships_count.short_description = "Relationships"

    def get_queryset(self, request):
        """Optimize queryset with select_related and annotations"""
        return (
            super()
            .get_queryset(request)
            .select_related("investigation")
            .annotate(rel_count=Count("source_relationships") + Count("target_relationships"))
        )

    actions = ["merge_duplicate_entities", "update_confidence_scores"]

    def merge_duplicate_entities(self, request, queryset):
        """Merge duplicate entities (same type and value)"""
        from django.db.models import Count

        # Group entities by type and value
        duplicates = (
            queryset.values("entity_type", "value", "investigation").annotate(count=Count("id")).filter(count__gt=1)
        )

        merged_count = 0

        for duplicate_group in duplicates:
            entities = queryset.filter(
                entity_type=duplicate_group["entity_type"],
                value=duplicate_group["value"],
                investigation_id=duplicate_group["investigation"],
            ).order_by("created_at")

            if entities.count() > 1:
                # Keep the first entity, merge others into it
                primary_entity = entities.first()
                entities_to_merge = entities[1:]

                for entity in entities_to_merge:
                    # Update relationships to point to primary entity
                    entity.source_relationships.update(source_entity=primary_entity)
                    entity.target_relationships.update(target_entity=primary_entity)

                    # Merge properties
                    if entity.properties:
                        if not primary_entity.properties:
                            primary_entity.properties = {}
                        primary_entity.properties.update(entity.properties)

                    # Update confidence score to highest
                    if entity.confidence_score > primary_entity.confidence_score:
                        primary_entity.confidence_score = entity.confidence_score

                    # Delete the duplicate
                    entity.delete()
                    merged_count += 1

                primary_entity.save()

        if merged_count > 0:
            self.message_user(request, f"Successfully merged {merged_count} duplicate entities.")
        else:
            self.message_user(request, "No duplicate entities found to merge.")

    merge_duplicate_entities.short_description = "Merge duplicate entities"

    def update_confidence_scores(self, request, queryset):
        """Update confidence scores based on source and relationships"""
        updated_count = 0

        for entity in queryset:
            old_score = entity.confidence_score

            # Calculate new confidence score based on various factors
            # Source-based scoring
            source_scores = {
                "manual": 1.0,
                "shodan": 0.9,
                "nmap": 0.8,
                "amass": 0.8,
                "assetfinder": 0.7,
                "unknown": 0.5,
            }

            source_score = source_scores.get(entity.source.lower(), 0.5)

            # Relationship-based scoring (more relationships = higher confidence)
            relationship_count = entity.source_relationships.count() + entity.target_relationships.count()
            relationship_bonus = min(relationship_count * 0.1, 0.3)

            # Calculate final score
            new_score = min(source_score + relationship_bonus, 1.0)

            if abs(new_score - old_score) > 0.05:  # Only update if significant change
                entity.confidence_score = new_score
                entity.save()
                updated_count += 1

        if updated_count > 0:
            self.message_user(request, f"Updated confidence scores for {updated_count} entities.")
        else:
            self.message_user(request, "No entities required confidence score updates.")

    update_confidence_scores.short_description = "Update confidence scores"


@admin.register(Relationship)
class RelationshipAdmin(admin.ModelAdmin):
    list_display = [
        "source_entity_display",
        "relationship_type",
        "target_entity_display",
        "investigation_link",
        "source",
        "confidence_score",
        "created_at",
    ]
    list_filter = [
        "relationship_type",
        "source",
        "confidence_score",
        "created_at",
        "investigation__status",
    ]
    search_fields = [
        "source_entity__value",
        "target_entity__value",
        "investigation__name",
        "relationship_type",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (
            "Relationship",
            {
                "fields": (
                    "id",
                    "investigation",
                    "source_entity",
                    "relationship_type",
                    "target_entity",
                )
            },
        ),
        ("Metadata", {"fields": ("source", "confidence_score", "properties")}),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def source_entity_display(self, obj):
        """Display source entity with type"""
        return format_html(
            '<span style="color: #0066cc;">{}</span>: {}',
            obj.source_entity.entity_type,
            obj.source_entity.value[:50] + ("..." if len(obj.source_entity.value) > 50 else ""),
        )

    source_entity_display.short_description = "Source Entity"

    def target_entity_display(self, obj):
        """Display target entity with type"""
        return format_html(
            '<span style="color: #cc6600;">{}</span>: {}',
            obj.target_entity.entity_type,
            obj.target_entity.value[:50] + ("..." if len(obj.target_entity.value) > 50 else ""),
        )

    target_entity_display.short_description = "Target Entity"

    def investigation_link(self, obj):
        """Display investigation as a link"""
        url = reverse("admin:investigations_investigation_change", args=[obj.investigation.id])
        return format_html('<a href="{}">{}</a>', url, obj.investigation.name)

    investigation_link.short_description = "Investigation"

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        return super().get_queryset(request).select_related("investigation", "source_entity", "target_entity")

    actions = ["remove_duplicate_relationships", "update_relationship_confidence"]

    def remove_duplicate_relationships(self, request, queryset):
        """Remove duplicate relationships"""
        from django.db.models import Count

        # Find duplicates
        duplicates = (
            queryset.values("investigation", "source_entity", "target_entity", "relationship_type")
            .annotate(count=Count("id"))
            .filter(count__gt=1)
        )

        removed_count = 0

        for duplicate_group in duplicates:
            relationships = queryset.filter(
                investigation_id=duplicate_group["investigation"],
                source_entity_id=duplicate_group["source_entity"],
                target_entity_id=duplicate_group["target_entity"],
                relationship_type=duplicate_group["relationship_type"],
            ).order_by("created_at")

            if relationships.count() > 1:
                # Keep the first relationship, remove others
                relationships_to_remove = relationships[1:]
                for rel in relationships_to_remove:
                    rel.delete()
                    removed_count += 1

        if removed_count > 0:
            self.message_user(request, f"Removed {removed_count} duplicate relationships.")
        else:
            self.message_user(request, "No duplicate relationships found.")

    remove_duplicate_relationships.short_description = "Remove duplicate relationships"

    def update_relationship_confidence(self, request, queryset):
        """Update relationship confidence scores"""
        updated_count = 0

        for relationship in queryset:
            old_score = relationship.confidence_score

            # Base confidence on source reliability
            source_scores = {
                "manual": 1.0,
                "shodan": 0.9,
                "nmap": 0.8,
                "amass": 0.8,
                "assetfinder": 0.7,
                "dns": 0.9,
                "whois": 0.8,
                "unknown": 0.5,
            }

            new_score = source_scores.get(relationship.source.lower(), 0.5)

            # Adjust based on entity confidence scores
            entity_avg_confidence = (
                relationship.source_entity.confidence_score + relationship.target_entity.confidence_score
            ) / 2

            # Weight the relationship confidence with entity confidence
            final_score = (new_score * 0.7) + (entity_avg_confidence * 0.3)

            if abs(final_score - old_score) > 0.05:
                relationship.confidence_score = final_score
                relationship.save()
                updated_count += 1

        if updated_count > 0:
            self.message_user(request, f"Updated confidence scores for {updated_count} relationships.")
        else:
            self.message_user(request, "No relationships required confidence score updates.")

    update_relationship_confidence.short_description = "Update relationship confidence"
