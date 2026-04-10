from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.entities.models import Entity, Relationship
from apps.investigations.models import Investigation
from apps.transforms.models import Transform

User = get_user_model()


class Command(BaseCommand):
    help = "Populate database with test data for OSINT platform"

    def handle(self, *args, **options):
        self.stdout.write("Creating test data...")

        # Create admin user
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@osint.com",
                "first_name": "Admin",
                "last_name": "User",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        admin_user.email = "admin@osint.com"
        admin_user.first_name = "Admin"
        admin_user.last_name = "User"
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.is_active = True
        admin_user.set_password("admin123")
        admin_user.save()
        if created:
            self.stdout.write(f"Created admin user: {admin_user.username}")

        # Create test investigations
        investigations_data = [
            {
                "name": "Investigación de Fraude Financiero",
                "description": (
                    "Análisis detallado de transacciones sospechosas en"
                    " cuentas corporativas de la empresa XYZ."
                ),
                "status": "active",
                "tags": ["fraude", "financiero", "corporativo"],
                "metadata": {"target": "Empresa XYZ S.A.", "priority": "high"},
            },
            {
                "name": "Análisis de Red Social",
                "description": (
                    "Mapeo de conexiones y relaciones en redes sociales"
                    " para identificar patrones de comportamiento."
                ),
                "status": "completed",
                "tags": ["social_media", "redes_sociales"],
                "metadata": {"target": "Perfil @suspicious_user", "priority": "medium"},
            },
            {
                "name": "Investigación de Ciberseguridad",
                "description": "Análisis de amenazas y vulnerabilidades en infraestructura digital.",
                "status": "active",
                "tags": ["ciberseguridad", "amenazas", "vulnerabilidades"],
                "metadata": {"target": "Dominio malicioso.com", "priority": "high"},
            },
        ]

        created_investigations = []
        for inv_data in investigations_data:
            investigation, created = Investigation.objects.get_or_create(
                name=inv_data["name"],
                defaults={
                    **inv_data,
                    "created_by": admin_user,
                    "created_at": datetime.now() - timedelta(days=10),
                    "updated_at": datetime.now() - timedelta(days=2),
                },
            )
            if created:
                created_investigations.append(investigation)
                self.stdout.write(f"Created investigation: {investigation.name}")

        # Create entities for the first investigation
        if created_investigations:
            inv = created_investigations[0]

            entities_data = [
                {
                    "entity_type": "person",
                    "value": "Juan Pérez",
                    "description": "CEO de la empresa investigada",
                    "confidence": 0.95,
                },
                {
                    "entity_type": "organization",
                    "value": "Empresa XYZ S.A.",
                    "description": "Empresa bajo investigación por fraude",
                    "confidence": 1.0,
                },
                {
                    "entity_type": "email",
                    "value": "juan.perez@xyzcorp.com",
                    "description": "Email corporativo del CEO",
                    "confidence": 0.9,
                },
                {
                    "entity_type": "phone",
                    "value": "+34-600-123-456",
                    "description": "Teléfono móvil personal",
                    "confidence": 0.8,
                },
                {
                    "entity_type": "bank_account",
                    "value": "ES91 2100 0418 4502 0005 1332",
                    "description": "Cuenta bancaria corporativa",
                    "confidence": 0.95,
                },
            ]

            created_entities = []
            for ent_data in entities_data:
                entity, created = Entity.objects.get_or_create(
                    investigation=inv,
                    entity_type=ent_data["entity_type"],
                    value=ent_data["value"],
                    defaults={
                        "description": ent_data["description"],
                        "confidence_score": ent_data["confidence"],
                    },
                )
                if created:
                    created_entities.append(entity)
                    self.stdout.write(f"Created entity: {entity.value}")

            # Create relationships
            if len(created_entities) >= 3:
                relationships_data = [
                    {
                        "source": created_entities[0],  # Juan Pérez
                        "target": created_entities[1],  # Empresa XYZ
                        "relationship_type": "works_for",
                        "description": "Juan Pérez es CEO de Empresa XYZ S.A.",
                    },
                    {
                        "source": created_entities[0],  # Juan Pérez
                        "target": created_entities[2],  # Email
                        "relationship_type": "owns",
                        "description": "Email corporativo pertenece a Juan Pérez",
                    },
                    {
                        "source": created_entities[1],  # Empresa XYZ
                        "target": created_entities[4],  # Cuenta bancaria
                        "relationship_type": "owns",
                        "description": "Cuenta bancaria corporativa de la empresa",
                    },
                ]

                for rel_data in relationships_data:
                    relationship, created = Relationship.objects.get_or_create(
                        investigation=inv,
                        source_entity=rel_data["source"],
                        target_entity=rel_data["target"],
                        relationship_type=rel_data["relationship_type"],
                        defaults={"description": rel_data["description"]},
                    )
                    if created:
                        self.stdout.write(
                            f"Created relationship: {relationship.relationship_type}"
                        )

        # Create some basic transforms
        transforms_data = [
            {
                "name": "dns_lookup",
                "display_name": "DNS Lookup",
                "description": "Perform DNS lookup on domain names",
                "category": "dns",
                "input_type": "domain",
                "output_types": ["ip"],
                "tool_name": "nslookup",
                "command_template": "nslookup {input}",
                "timeout": 30,
            },
            {
                "name": "whois_lookup",
                "display_name": "WHOIS Lookup",
                "description": "Get WHOIS information for domains",
                "category": "dns",
                "input_type": "domain",
                "output_types": ["organization", "email"],
                "tool_name": "whois",
                "command_template": "whois {input}",
                "timeout": 60,
            },
            {
                "name": "port_scan",
                "display_name": "Port Scanner",
                "description": "Scan for open ports on IP addresses",
                "category": "network",
                "input_type": "ip",
                "output_types": ["mixed"],
                "tool_name": "nmap",
                "command_template": "nmap -p- {input}",
                "timeout": 300,
            },
        ]

        for trans_data in transforms_data:
            transform, created = Transform.objects.get_or_create(
                name=trans_data["name"], defaults={**trans_data, "is_enabled": True}
            )
            if created:
                self.stdout.write(f"Created transform: {transform.name}")

        self.stdout.write(
            self.style.SUCCESS("Successfully populated database with test data!")
        )
