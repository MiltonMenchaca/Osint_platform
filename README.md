# OSINT Platform

Plataforma de Inteligencia de Fuentes Abiertas (OSINT) diseñada para centralizar, automatizar y visualizar investigaciones de ciberseguridad.

## 📋 Descripción

![Dashboard OSINT Platform](osintplatform.png)

Esta plataforma permite a investigadores y analistas de seguridad realizar búsquedas OSINT, gestionar investigaciones, ejecutar transformaciones de datos y visualizar relaciones entre entidades (dominios, IPs, correos, personas) en un entorno gráfico interactivo.

El sistema está construido con una arquitectura moderna separando el frontend (React) del backend (Django REST Framework), permitiendo escalabilidad y flexibilidad.

## 🚀 Características Principales

- **Gestión de Investigaciones**: Crear, organizar y seguir casos de investigación.
- **Entidades y Relaciones**: Modelado flexible de datos (Persona, Organización, Dominio, IP, Email, Puertos, Servicios, etc.).
- **Visualización de Grafos**: Interfaz interactiva basada en Cytoscape.js para explorar conexiones.
- **Herramientas OSINT Integradas**:
  - **Holehe**: Verificación de cuentas de correo en más de 120 sitios.
  - **Assetfinder**: Descubrimiento de subdominios.
  - **Amass**: Enumeración exhaustiva de subdominios.
  - **Nmap**: Escaneo de puertos y servicios.
  - **Shodan**: Búsqueda de dispositivos conectados (requiere API Key).
  - **crt.sh**: Búsqueda en logs de transparencia de certificados.
  - **Auto Recon**: Suite rápida de reconocimiento (ping, whois, dns, wappalyzer, nmap).
- **Arquitectura Data-Driven**: Enfoque en la calidad, normalización y accionabilidad de los datos.

## 🛠️ Tecnologías

### Backend
- **Python 3.12+**
- **Django 4.2** & **Django REST Framework**
- **Celery** & **Redis** (para tareas asíncronas y colas)
- **PostgreSQL** (recomendado para producción) / SQLite (desarrollo)

### Frontend
- **React 19**
- **TypeScript**
- **Vite**
- **Cytoscape.js** (visualización de grafos)
- **Bootstrap 5** & **React-Bootstrap**

## 🗂️ Estructura del repositorio

- `apps/` Backend (Django apps)
- `frontend/` Frontend (React/Vite)
- `docs/` Documentación y figuras
- `data/` Datos (raw/processed/external)
- `outputs/` Resultados generados
- `archives/` Archivos históricos y entregables

```text
osint/
├─ apps/
├─ config/
├─ core/
├─ data/
│  ├─ raw/
│  ├─ processed/
│  └─ external/
├─ docs/
│  ├─ figures/
│  └─ reports/
├─ docker/
├─ frontend/
├─ osint_platform/
├─ osint_tools/
├─ outputs/
├─ archives/
├─ requirements/
├─ scripts/
├─ tests/
├─ .env.example
├─ .gitignore
├─ README.md
├─ manage.py
└─ pytest.ini
```

## 📦 Instalación y Despliegue

### Requisitos Previos
- Python 3.12 o superior
- Node.js 18 o superior
- Redis (para Celery)
- Herramientas OSINT instaladas en el sistema:
  - ping (iputils)
  - whois
  - nmap
  - dnstwist
  - httpx
  - wappalyzer (python-Wappalyzer)
  - holehe
  - amass
  - assetfinder

### Configuración del Backend

1. **Clonar el repositorio**
   ```bash
   git clone https://github.com/MiltonMenchaca/Osint_platform.git
   cd Osint_platform
   ```

2. **Crear y activar entorno virtual**
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   ```

5. **Configurar base de datos y migraciones**
   ```bash
   python manage.py migrate
   ```

6. **Crear superusuario**
   ```bash
   python manage.py createsuperuser
   ```

7. **Iniciar servidor de desarrollo**
   ```bash
   python manage.py runserver
   ```

### Configuración del Frontend

1. **Ir al directorio frontend**
   ```bash
   cd frontend
   ```

2. **Instalar dependencias**
   ```bash
   npm install
   ```

3. **Iniciar servidor de desarrollo**
   ```bash
   npm run dev
   ```

El frontend estará disponible en `http://localhost:5173` y el backend en `http://localhost:8000`.

### Docker (Dev/Prod)

- Archivos de Docker en `docker/`
- Desarrollo:
  ```bash
  docker compose --env-file .env -f docker/docker-compose.yml up -d --build
  ```
- Producción:
  ```bash
  docker compose --env-file .env -f docker/docker-compose.prod.yml up -d --build
  ```

## 🔧 Uso de OSINT Operativo (Scripts)

El proyecto incluye un módulo `osint_operativo` para ejecutar campañas OSINT automatizadas mediante scripts y configuración JSON, ideal para entornos CI/CD o ejecuciones programadas.

1. **Configurar campaña**
   Editar `osint_operativo/config.example.json` o crear uno nuevo.

2. **Ejecutar campaña**
   ```bash
   python osint_operativo/run_osint_operativo.py --config osint_operativo/config.json
   ```

3. **Revisar reportes**
   Los resultados se guardan en `osint_operativo/reportes/` en formatos JSON, TXT y DOCX.

---

## 🔄 DevOps — CI/CD Pipeline

El proyecto implementa un flujo DevOps completo con Integración Continua y Despliegue Continuo.

### Arquitectura del Pipeline

```
Push/PR → GitHub Actions CI → Tests + Lint + Build Docker → Push a ghcr.io → Helm Deploy a K8s
```

### Integración Continua (CI)

El workflow `.github/workflows/ci.yml` se ejecuta en cada push/PR a `main` y `develop`:

| Job | Descripción |
|-----|------------|
| **backend-tests** | Python 3.11 + PostgreSQL 16 + Redis 7 → flake8, black --check, pytest --cov |
| **frontend-build** | Node 20 → npm ci, eslint, vite build |
| **docker-build** | Build y push de 3 imágenes a GitHub Container Registry (ghcr.io) |

### Despliegue Continuo (CD)

El workflow `.github/workflows/cd.yml` se ejecuta al hacer merge a `main`:

1. Construye imágenes Docker con tag de versión
2. Despliega a Kubernetes con `helm upgrade --install`
3. Verifica rollout de deployments

### Kubernetes

Manifiestos en `k8s/` para despliegue directo:

```bash
# Aplicar todos los manifiestos
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/ -R
```

**Servicios desplegados**: PostgreSQL, Redis, Backend (Django), Frontend (Nginx), Tools Worker (Celery)

### Helm Chart

Chart en `helm/osint-platform/` para administración del despliegue:

```bash
# Desarrollo (minikube/kind)
helm install osint ./helm/osint-platform -f helm/osint-platform/values-dev.yaml

# Producción
helm install osint ./helm/osint-platform -f helm/osint-platform/values-prod.yaml

# Actualizar despliegue
helm upgrade osint ./helm/osint-platform --set backend.image.tag=v1.2.0

# Verificar
helm list
kubectl get pods -n osint-platform
```

### Despliegue Local con Minikube

```bash
# Iniciar minikube
minikube start --driver=docker

# Habilitar ingress
minikube addons enable ingress

# Instalar con Helm
helm install osint ./helm/osint-platform -f helm/osint-platform/values-dev.yaml

# Agregar al /etc/hosts (o C:\Windows\System32\drivers\etc\hosts)
echo "$(minikube ip) osint.local" | sudo tee -a /etc/hosts

# Acceder: http://osint.local
```

### Estructura DevOps

```text
.github/workflows/
├── ci.yml                    # Pipeline CI: tests, lint, Docker build
└── cd.yml                    # Pipeline CD: deploy a Kubernetes

k8s/
├── namespace.yaml
├── ingress.yaml
├── backend/                  # Deployment, Service, ConfigMap, Secret
├── frontend/                 # Deployment, Service
├── postgres/                 # Deployment, Service, PVC
├── redis/                    # Deployment, Service
└── tools-worker/             # Deployment

helm/osint-platform/
├── Chart.yaml
├── values.yaml               # Valores por defecto
├── values-dev.yaml            # Override desarrollo
├── values-prod.yaml           # Override producción
└── templates/                 # Templates parametrizables
```

---

## 🤝 Contribución

1. Fork del repositorio
2. Crear rama de feature (`git checkout -b feature/nueva-herramienta`)
3. Commit de cambios (`git commit -m 'Agrega soporte para X'`)
4. Push a la rama (`git push origin feature/nueva-herramienta`)
5. Crear Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Consulta el archivo `LICENSE` para más detalles.

## ⚠️ Aviso Legal

Esta herramienta está diseñada para uso defensivo, educativo y de investigación autorizada. El usuario es responsable de asegurarse de tener permiso antes de escanear o investigar objetivos. Los desarrolladores no se hacen responsables del mal uso de esta plataforma.
