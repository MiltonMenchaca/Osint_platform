import logging
import requests
import time
from typing import Any, Dict, List

# ID único de la fuente para el sistema
SOURCE_ID = "crtsh_public"

# Configuración de logger
logger = logging.getLogger(__name__)

def run(target: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Consulta crt.sh para obtener certificados y subdominios de un dominio objetivo.
    Esta es una fuente PASIVA y LEGAL.
    """
    findings = []
    
    # Validar que el target sea un dominio u organización compatible
    target_value = target.get("value")
    target_type = target.get("type")
    
    if not target_value:
        return []
        
    # Si es organización, intentamos usar el nombre tal cual, aunque crt.sh funciona mejor con dominios (%.domain.com)
    # Para este ejemplo real, asumiremos que el usuario provee un dominio base (ej. "santander.com")
    query = f"%.{target_value}"
    
    print(f"[crtsh_public] Consultando certificados para: {query}")
    
    # Retry mechanism simple
    max_retries = 3
    for attempt in range(max_retries):
        try:
            url = "https://crt.sh/"
            params = {
                "q": query,
                "output": "json"
            }
            # Timeout prudente para evitar bloqueos
            response = requests.get(url, params=params, timeout=20)
            
            if response.status_code == 200:
                try:
                    data = response.json()
                except Exception:
                    # A veces devuelve JSON malformado si hay demasiados resultados
                    print("[crtsh_public] Error parseando JSON de crt.sh")
                    return []

                # Limitar resultados para no saturar el reporte
                # En un entorno real Data-Driven, esto iría a un Data Lake
                preview_data = data[:15] 
                
                for entry in preview_data:
                    common_name = entry.get("common_name")
                    name_value = entry.get("name_value")
                    
                    # Normalización básica
                    domains = set()
                    if common_name:
                        domains.add(common_name.lower())
                    if name_value:
                        # name_value puede tener múltiples líneas
                        for d in name_value.split("\n"):
                            domains.add(d.lower())
                    
                    for domain in domains:
                        findings.append({
                            "type": "domain",
                            "value": domain,
                            "metadata": {
                                "source": "crt.sh",
                                "issuer": entry.get("issuer_name"),
                                "entry_timestamp": entry.get("entry_timestamp")
                            }
                        })
                
                print(f"[crtsh_public] Encontrados {len(findings)} registros (limitado).")
                return findings
                
            elif response.status_code == 503:
                print(f"[crtsh_public] Servicio no disponible (503). Reintentando {attempt+1}/{max_retries}...")
                time.sleep(2 * (attempt + 1)) # Backoff
            else:
                print(f"[crtsh_public] Error HTTP {response.status_code}")
                break
                
        except Exception as e:
            print(f"[crtsh_public] Error de conexión: {str(e)}")
            time.sleep(1)
            
    return findings
