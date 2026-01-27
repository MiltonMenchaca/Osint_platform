import logging
import re

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import Entity, Relationship

logger = logging.getLogger("entities")


@receiver(pre_save, sender=Entity)
def entity_pre_save(sender, instance, **kwargs):
    """
    Handle pre-save actions for Entity model
    """
    # Normalize entity value based on type
    if instance.entity_type == "domain":
        # Normalize domain names to lowercase
        instance.value = instance.value.lower().strip()

        # Remove protocol if present
        instance.value = re.sub(r"^https?://", "", instance.value)

        # Remove trailing slash
        instance.value = instance.value.rstrip("/")

    elif instance.entity_type == "email":
        # Normalize email to lowercase
        instance.value = instance.value.lower().strip()

    elif instance.entity_type == "ip":
        # Validate and normalize IP address
        instance.value = instance.value.strip()

        # Basic IP validation
        ip_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        if not re.match(ip_pattern, instance.value):
            logger.warning(f"Invalid IP address format: {instance.value}")

    elif instance.entity_type == "url":
        # Normalize URL
        instance.value = instance.value.strip()

        # Add protocol if missing
        if not instance.value.startswith(("http://", "https://")):
            instance.value = "http://" + instance.value

    # Auto-detect entity type if not set or if value doesn't match type
    if not instance.entity_type or not _validate_entity_type(
        instance.value, instance.entity_type
    ):
        detected_type = _detect_entity_type(instance.value)
        if detected_type:
            instance.entity_type = detected_type
            logger.info(
                f"Auto-detected entity type '{detected_type}' for value '{instance.value}'"
            )


@receiver(post_save, sender=Entity)
def entity_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save actions for Entity model
    """
    if created:
        logger.info(
            f"New entity created: {instance.entity_type}:{instance.value} "
            f"in investigation {instance.investigation.name}"
        )

        # Auto-create relationships based on entity patterns
        _auto_create_relationships(instance)

        # Update entity metadata
        if not instance.properties:
            instance.properties = {}

        instance.properties.update(
            {
                "created_timestamp": timezone.now().isoformat(),
                "auto_detected_type": getattr(instance, "_auto_detected", False),
            }
        )

        # Save without triggering signals again
        Entity.objects.filter(id=instance.id).update(properties=instance.properties)


@receiver(post_delete, sender=Entity)
def entity_post_delete(sender, instance, **kwargs):
    """
    Handle post-delete actions for Entity model
    """
    logger.info(
        f"Entity deleted: {instance.entity_type}:{instance.value} "
        f"from investigation {instance.investigation.name}"
    )


@receiver(post_save, sender=Relationship)
def relationship_post_save(sender, instance, created, **kwargs):
    """
    Handle post-save actions for Relationship model
    """
    if created:
        logger.info(
            f"New relationship created: {instance.source_entity.value} "
            f"{instance.relationship_type} {instance.target_entity.value}"
        )

        # Update relationship metadata
        if not instance.properties:
            instance.properties = {}

        instance.properties.update(
            {
                "created_timestamp": timezone.now().isoformat(),
                "source_entity_type": instance.source_entity.entity_type,
                "target_entity_type": instance.target_entity.entity_type,
            }
        )

        # Save without triggering signals again
        Relationship.objects.filter(id=instance.id).update(
            properties=instance.properties
        )


def _detect_entity_type(value: str) -> str:
    """
    Auto-detect entity type based on value pattern

    Args:
        value: Entity value to analyze

    Returns:
        Detected entity type or None
    """
    value = value.strip().lower()

    # Email pattern
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if re.match(email_pattern, value):
        return "email"

    # IP address pattern
    ip_pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
    if re.match(ip_pattern, value):
        return "ip"

    # URL pattern
    url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    if re.match(url_pattern, value):
        return "url"

    # Domain pattern (more restrictive than URL)
    domain_pattern = (
        r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+" r"[a-zA-Z]{2,}$"
    )
    if re.match(domain_pattern, value):
        return "domain"

    # Phone number pattern (basic)
    phone_pattern = r"^[+]?[1-9]?[0-9]{7,15}$"
    if re.match(phone_pattern, re.sub(r"[\s\-\(\)]", "", value)):
        return "phone"

    # Hash patterns
    if len(value) == 32 and re.match(r"^[a-f0-9]+$", value):
        return "hash_md5"
    elif len(value) == 40 and re.match(r"^[a-f0-9]+$", value):
        return "hash_sha1"
    elif len(value) == 64 and re.match(r"^[a-f0-9]+$", value):
        return "hash_sha256"

    # Default to 'other' if no pattern matches
    return "other"


def _validate_entity_type(value: str, entity_type: str) -> bool:
    """
    Validate if entity value matches the specified type

    Args:
        value: Entity value
        entity_type: Specified entity type

    Returns:
        True if value matches type, False otherwise
    """
    detected_type = _detect_entity_type(value)
    return detected_type == entity_type


def _auto_create_relationships(entity: Entity):
    """
    Auto-create relationships based on entity patterns and existing entities

    Args:
        entity: Newly created entity
    """
    try:
        investigation = entity.investigation

        # Find potential relationships based on entity type
        if entity.entity_type == "domain":
            _create_domain_relationships(entity, investigation)
        elif entity.entity_type == "ip":
            _create_ip_relationships(entity, investigation)
        elif entity.entity_type == "email":
            _create_email_relationships(entity, investigation)

    except Exception as e:
        logger.error(
            f"Error auto-creating relationships for entity {entity.id}: {str(e)}"
        )


def _create_domain_relationships(domain_entity: Entity, investigation):
    """
    Create relationships for domain entities

    Args:
        domain_entity: Domain entity
        investigation: Investigation instance
    """
    domain_value = domain_entity.value

    # Find parent domain relationships
    domain_parts = domain_value.split(".")
    if len(domain_parts) > 2:
        # This might be a subdomain
        parent_domain = ".".join(domain_parts[1:])

        # Look for parent domain in existing entities
        parent_entities = Entity.objects.filter(
            investigation=investigation, entity_type="domain", value=parent_domain
        )

        for parent_entity in parent_entities:
            # Create subdomain relationship
            Relationship.objects.get_or_create(
                investigation=investigation,
                source_entity=domain_entity,
                target_entity=parent_entity,
                relationship_type="subdomain_of",
                defaults={"source": "auto_detection", "confidence_score": 0.9},
            )
            logger.info(
                f"Auto-created subdomain relationship: {domain_value} -> {parent_domain}"
            )


def _create_ip_relationships(ip_entity: Entity, investigation):
    """
    Create relationships for IP entities

    Args:
        ip_entity: IP entity
        investigation: Investigation instance
    """
    # Look for domains that might resolve to this IP
    # This would typically be handled by DNS resolution transforms
    pass


def _create_email_relationships(email_entity: Entity, investigation):
    """
    Create relationships for email entities

    Args:
        email_entity: Email entity
        investigation: Investigation instance
    """
    email_value = email_entity.value

    # Extract domain from email
    if "@" in email_value:
        domain_part = email_value.split("@")[1]

        # Look for existing domain entity
        domain_entities = Entity.objects.filter(
            investigation=investigation, entity_type="domain", value=domain_part
        )

        for domain_entity in domain_entities:
            # Create email-domain relationship
            Relationship.objects.get_or_create(
                investigation=investigation,
                source_entity=email_entity,
                target_entity=domain_entity,
                relationship_type="associated_with",
                defaults={"source": "auto_detection", "confidence_score": 0.95},
            )
            logger.info(
                f"Auto-created email-domain relationship: {email_value} -> {domain_part}"
            )

        # If domain doesn't exist, create it
        if not domain_entities.exists():
            domain_entity = Entity.objects.create(
                investigation=investigation,
                entity_type="domain",
                value=domain_part,
                source="auto_extraction",
                confidence_score=0.8,
            )

            # Create relationship
            Relationship.objects.create(
                investigation=investigation,
                source_entity=email_entity,
                target_entity=domain_entity,
                relationship_type="associated_with",
                source="auto_extraction",
                confidence_score=0.8,
            )
            logger.info(
                f"Auto-created domain from email and relationship: {email_value} -> {domain_part}"
            )
