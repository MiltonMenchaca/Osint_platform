import shutil
from typing import Dict, Any, Optional

from apps.transforms.models import Transform
from apps.transforms.wrappers import list_available_tools


class OsintCatalogService:
    def __init__(self) -> None:
        # Google Dorks indices (Removed by request)
        self.google_indices = []

        self.google_dorks = [
            {
                "category": "Acceso y paneles",
                "name": "Paneles de acceso",
                "query": "site:{target} (login OR admin OR panel OR acceso OR dashboard)",
                "intent": "Detectar paneles de autenticación y administración.",
                "risk": "Exposición de acceso administrativo.",
            },
            {
                "category": "Acceso y paneles",
                "name": "Paneles con ruta común",
                "query": "site:{target} (inurl:admin OR inurl:dashboard OR inurl:cpanel OR inurl:signin)",
                "intent": "Localizar rutas típicas de paneles.",
                "risk": "Enumeración de superficies de login.",
            },
            {
                "category": "Directorios y listados",
                "name": "Directorios listados",
                "query": "site:{target} intitle:\"index of\"",
                "intent": "Encontrar listados de directorios públicos.",
                "risk": "Exposición de archivos internos.",
            },
            {
                "category": "Directorios y listados",
                "name": "Listados con extensiones sensibles",
                "query": "site:{target} intitle:\"index of\" (sql OR env OR bak OR zip OR tar OR gz OR 7z)",
                "intent": "Priorizar listados con archivos potencialmente sensibles.",
                "risk": "Filtración de backups o configuraciones.",
            },
            {
                "category": "Backups y dumps",
                "name": "Backups expuestos",
                "query": "site:{target} (backup OR respaldo OR copia) (zip OR rar OR 7z OR sql OR bak OR tar)",
                "intent": "Detectar copias de seguridad accesibles.",
                "risk": "Exfiltración de datos.",
            },
            {
                "category": "Backups y dumps",
                "name": "Dumps de base de datos",
                "query": "site:{target} (dump OR database OR db) (sql OR sqlite OR mdb)",
                "intent": "Localizar volcados de bases de datos.",
                "risk": "Exposición completa de registros.",
            },
            {
                "category": "Configuración y secretos",
                "name": "Archivos de configuración",
                "query": (
                    "site:{target} (config OR settings OR secrets OR credentials)"
                    " (json OR yml OR yaml OR env OR ini)"
                ),
                "intent": "Ubicar archivos de configuración con credenciales.",
                "risk": "Filtración de secretos.",
            },
            {
                "category": "Configuración y secretos",
                "name": "Variables de entorno",
                "query": "site:{target} (\".env\" OR \"dotenv\")",
                "intent": "Detectar archivos .env expuestos.",
                "risk": "Exposición de claves.",
            },
            {
                "category": "Configuración y secretos",
                "name": "Credenciales en texto",
                "query": (
                    "site:{target} (password OR passwd OR token OR secret"
                    " OR api_key OR \"access key\")"
                ),
                "intent": "Identificar páginas con credenciales visibles.",
                "risk": "Acceso no autorizado.",
            },
            {
                "category": "Documentos sensibles",
                "name": "Documentos internos",
                "query": (
                    "site:{target} (confidencial OR interno OR \"uso interno\")"
                    " (pdf OR doc OR docx OR xls OR xlsx OR ppt OR pptx)"
                ),
                "intent": "Detectar documentos internos expuestos.",
                "risk": "Divulgación de información.",
            },
            {
                "category": "Documentos sensibles",
                "name": "Documentación técnica",
                "query": (
                    "site:{target} (manual OR arquitectura OR \"guía\" OR \"política\")"
                    " (pdf OR doc OR docx OR ppt OR pptx)"
                ),
                "intent": "Localizar documentación técnica.",
                "risk": "Información útil para ataque.",
            },
            {
                "category": "Documentos sensibles",
                "name": "Documentos ofimáticos",
                "query": ("site:{target} (filetype:pdf OR filetype:doc OR filetype:docx"
                          " OR filetype:rtf OR filetype:odt)"),
                "intent": "Encontrar documentos de texto expuestos.",
                "risk": "Divulgación de contenido interno.",
            },
            {
                "category": "Documentos sensibles",
                "name": "Hojas de cálculo",
                "query": "site:{target} (filetype:xls OR filetype:xlsx OR filetype:csv OR filetype:ods)",
                "intent": "Detectar hojas de cálculo con datos sensibles.",
                "risk": "Exposición de registros y listas.",
            },
            {
                "category": "Documentos sensibles",
                "name": "Presentaciones",
                "query": "site:{target} (filetype:ppt OR filetype:pptx OR filetype:odp)",
                "intent": "Ubicar presentaciones internas.",
                "risk": "Divulgación de estrategias o métricas.",
            },
            {
                "category": "Documentos sensibles",
                "name": "Texto plano y reportes",
                "query": "site:{target} (filetype:txt OR filetype:log OR filetype:md)",
                "intent": "Localizar reportes y notas en texto.",
                "risk": "Exposición de datos operativos.",
            },
            {
                "category": "Documentos sensibles",
                "name": "Datos estructurados",
                "query": "site:{target} (filetype:json OR filetype:xml OR filetype:yml OR filetype:yaml)",
                "intent": "Encontrar archivos de datos publicados.",
                "risk": "Exposición de información estructurada.",
            },
            {
                "category": "Documentos sensibles",
                "name": "Plantillas y formularios",
                "query": (
                    "site:{target} (filetype:docm OR filetype:xlt OR filetype:xltx"
                    " OR filetype:dot OR filetype:dotx)"
                ),
                "intent": "Identificar plantillas usadas internamente.",
                "risk": "Divulgación de formatos internos.",
            },
            {
                "category": "APIs y servicios",
                "name": "Endpoints API",
                "query": "site:{target} (api OR graphql OR swagger OR openapi OR postman)",
                "intent": "Enumerar endpoints y documentación de APIs.",
                "risk": "Exposición de superficie API.",
            },
            {
                "category": "APIs y servicios",
                "name": "Documentación Swagger",
                "query": "site:{target} (swagger OR \"swagger-ui\" OR \"swagger.json\" OR \"openapi.json\")",
                "intent": "Encontrar documentación de API.",
                "risk": "Exposición de rutas y esquemas.",
            },
            {
                "category": "Errores y debug",
                "name": "Errores y trazas",
                "query": "site:{target} (stacktrace OR exception OR \"traceback\" OR \"fatal error\")",
                "intent": "Descubrir errores con información sensible.",
                "risk": "Filtración de rutas y credenciales.",
            },
            {
                "category": "Errores y debug",
                "name": "Logs expuestos",
                "query": "site:{target} (log OR logs OR errorlog) (txt OR log)",
                "intent": "Detectar archivos de logs accesibles.",
                "risk": "Exposición de información operativa.",
            },
            {
                "category": "Repositorios y código",
                "name": "Repositorios públicos",
                "query": "site:{target} (git OR github OR bitbucket OR gitlab)",
                "intent": "Localizar repositorios vinculados al dominio.",
                "risk": "Exposición de código y secretos.",
            },
            {
                "category": "Repositorios y código",
                "name": "Repositorios expuestos",
                "query": "site:{target} (\".git\" OR \"git/config\")",
                "intent": "Detectar repositorios expuestos.",
                "risk": "Exposición completa del código.",
            },
            {
                "category": "Cloud y storage",
                "name": "Buckets y storage",
                "query": "site:{target} (s3.amazonaws.com OR storage.googleapis.com OR blob.core.windows.net)",
                "intent": "Identificar buckets o storage asociados.",
                "risk": "Acceso público a almacenamiento.",
            },
            {
                "category": "Cloud y storage",
                "name": "Backups en cloud",
                "query": "site:{target} (backup OR dump) (s3 OR storage OR blob)",
                "intent": "Buscar respaldos en cloud.",
                "risk": "Exposición de datos críticos.",
            },
            {
                "category": "Entornos y subdominios",
                "name": "Ambientes expuestos",
                "query": "site:{target} (dev OR staging OR test OR qa OR uat)",
                "intent": "Detectar entornos no productivos.",
                "risk": "Servicios menos protegidos.",
            },
            {
                "category": "Entornos y subdominios",
                "name": "Subdominios administrativos",
                "query": "site:{target} (admin OR vpn OR intranet OR portal)",
                "intent": "Enumerar subdominios críticos.",
                "risk": "Acceso a servicios internos.",
            },
            {
                "category": "Archivos y media",
                "name": "Archivos multimedia internos",
                "query": "site:{target} (mp4 OR mov OR wav OR mp3) (internal OR privado)",
                "intent": "Localizar archivos internos publicados.",
                "risk": "Exposición de contenido sensible.",
            },
            {
                "category": "Pagos y finanzas",
                "name": "Pasarelas y pagos",
                "query": "site:{target} (payment OR checkout OR pasarela OR \"tarjeta\")",
                "intent": "Detectar flujos de pago expuestos.",
                "risk": "Ataques a rutas críticas.",
            },
            {
                "category": "DevOps y CI/CD",
                "name": "CI/CD expuesto",
                "query": "site:{target} (jenkins OR gitlab OR circleci OR github actions OR bamboo)",
                "intent": "Localizar herramientas de automatización.",
                "risk": "Compromiso de pipelines.",
            },
            {
                "category": "DevOps y CI/CD",
                "name": "Artefactos",
                "query": "site:{target} (artifacts OR build OR release) (zip OR tar OR jar)",
                "intent": "Detectar artefactos de build expuestos.",
                "risk": "Distribución de binarios no controlados.",
            },
            {
                "category": "Login externo",
                "name": "SSO y proveedores",
                "query": "site:{target} (sso OR saml OR oidc OR okta OR azuread)",
                "intent": "Ubicar integración de SSO.",
                "risk": "Superficie de autenticación externa.",
            },
            {
                "category": "Acuerdos y legales",
                "name": "Políticas internas",
                "query": "site:{target} (\"política\" OR \"normativa\" OR \"acuerdo\") (pdf OR doc)",
                "intent": "Encontrar documentos legales internos.",
                "risk": "Divulgación de controles internos.",
            },
            {
                "category": "Contacto y soporte",
                "name": "Correos y formularios",
                "query": "site:{target} (\"@\" OR correo OR email OR soporte OR contacto)",
                "intent": "Recolectar puntos de contacto.",
                "risk": "Ataques de phishing dirigidos.",
            },
            {
                "category": "Metadatos",
                "name": "Documentos con metadatos",
                "query": (
                    "site:{target} (filetype:pdf OR filetype:doc OR filetype:docx"
                    " OR filetype:xls OR filetype:xlsx OR filetype:ppt OR filetype:pptx"
                    " OR filetype:odt OR filetype:ods OR filetype:odp)"
                ),
                "intent": "Identificar documentos para análisis de metadatos.",
                "risk": "Filtración de autores y rutas.",
            },
            {
                "category": "Histórico",
                "name": "Resultados recientes",
                "query": "site:{target} after:2024-01-01",
                "intent": "Priorizar contenido reciente.",
                "risk": "Cambios recientes con errores.",
            },
        ]

        self.google_endpoints = [
            {
                "name": "Google Search",
                "url_template": "https://www.google.com/search?q={query}&num=50",
            },
            {
                "name": "Google Advanced",
                "url_template": "https://www.google.com/search?q={query}&num=100&filter=0",
            },
            {
                "name": "Google Images",
                "url_template": "https://www.google.com/search?q={query}&tbm=isch",
            },
            {
                "name": "Google News",
                "url_template": "https://www.google.com/search?q={query}&tbm=nws",
            },
            {
                "name": "Google Videos",
                "url_template": "https://www.google.com/search?q={query}&tbm=vid",
            },
        ]

        self.binary_aliases = {
            "httpx": ["httpx-pd", "httpx"],
            "nuclei": ["nuclei"],
            "waybackurls": ["waybackurls"],
            "assetfinder": ["assetfinder"],
            "amass": ["amass"],
            "subfinder": ["subfinder"],
            "gobuster": ["gobuster"],
            "dirb": ["dirb"],
            "nikto": ["nikto", "perl"],
            "nmap": ["nmap"],
            "masscan": ["masscan"],
            "zmap": ["zmap"],
            "traceroute": ["traceroute"],
            "ping": ["ping"],
            "whatweb": ["whatweb"],
            "dnstwist": ["dnstwist"],
            "exiftool": ["exiftool"],
            "recon-ng": ["recon-ng"],
            "spiderfoot": ["sf.py"],
            "theharvester": ["theHarvester"],
            "dmitry": ["dmitry"],
        }

    def _resolve_binary(self, tool_name: str) -> Dict[str, Any]:
        candidates = self.binary_aliases.get(tool_name, [tool_name])
        for candidate in candidates:
            path = shutil.which(candidate)
            if path:
                return {
                    "tool": tool_name,
                    "binary": candidate,
                    "path": path,
                    "installed": True,
                }
        return {
            "tool": tool_name,
            "binary": candidates[0] if candidates else tool_name,
            "path": None,
            "installed": False,
        }

    def _expand_google_dorks(self, target: Optional[str]) -> Dict[str, Any]:
        dorks = []
        queries = []
        urls = []
        for dork in self.google_dorks:
            query = dork["query"].format(target=target or "{target}")
            dorks.append({**dork, "query": query})
            if target:
                queries.append(query)
                for endpoint in self.google_endpoints:
                    url = endpoint["url_template"].format(query=query)
                    urls.append({"endpoint": endpoint["name"], "url": url})
        return {
            "dorks": dorks,
            "queries": queries,
            "search_urls": urls,
        }

    def build_catalog(self, target: Optional[str] = None) -> Dict[str, Any]:
        transforms = Transform.objects.filter(is_enabled=True).order_by(
            "category", "display_name"
        )
        tools = [
            {
                "name": t.name,
                "display_name": t.display_name,
                "description": t.description,
                "category": t.category,
                "input_type": t.input_type,
                "output_types": t.output_types,
                "tool_name": t.tool_name,
                "timeout": t.timeout,
                "requires_api_key": t.requires_api_key,
                "api_key_name": t.api_key_name,
            }
            for t in transforms
        ]

        wrapper_tools = sorted(set(list_available_tools()))
        binaries = [self._resolve_binary(tool) for tool in wrapper_tools]
        google = self._expand_google_dorks(target)

        plan = {
            "scope": {
                "steps": [
                    "Definir objetivo y alcance permitido",
                    "Normalizar dominio raíz y subdominios permitidos",
                    "Configurar exclusiones y palabras negativas",
                ],
                "inputs": ["target", "subdomains", "exclusions", "time_window"],
            },
            "query_building": {
                "steps": [
                    "Generar combinaciones por categoría",
                    "Crear variantes con operadores inurl/intitle/intext",
                    "Expandir por extensiones y tipos de archivo",
                ],
                "outputs": ["queries"],
            },
            "execution": {
                "steps": [
                    "Ejecutar consultas por lotes pequeños",
                    "Aplicar rotación de endpoints de búsqueda",
                    "Registrar resultados con metadatos",
                ],
                "rate_limits": {
                    "min_delay_seconds": 5,
                    "max_results_per_query": 50,
                },
            },
            "triage": {
                "steps": [
                    "Deduplicar por URL y host",
                    "Priorizar por riesgo y categoría",
                    "Enriquecer con httpx/nuclei/whatweb",
                ],
                "outputs": ["prioritized_urls", "evidence"],
            },
            "validation": {
                "steps": [
                    "Validar accesibilidad (HTTP 200/403/401)",
                    "Revisar falsos positivos",
                    "Registrar hallazgos en investigación",
                ],
            },
        }

        return {
            "tools": tools,
            "indices": self.google_indices,
            "dorks": google["dorks"],
            "google": {
                "endpoints": self.google_endpoints,
                "queries": google["queries"],
                "search_urls": google["search_urls"],
            },
            "dorking_plan": plan,
            "binaries": binaries,
        }
