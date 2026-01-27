import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["POST"])
def holehe_search(request):
    """
    Endpoint para ejecutar búsquedas con Holehe
    """
    try:
        data = json.loads(request.body)
        email = data.get("email")

        if not email:
            return JsonResponse({"error": "Email is required"}, status=400)

        # Por ahora retornamos datos mock hasta que se instale holehe
        # TODO: Implementar la llamada real a holehe cuando esté instalado
        mock_results = {
            "email": email,
            "found_accounts": [
                {
                    "platform": "Twitter",
                    "url": f'https://twitter.com/{email.split("@")[0]}',
                    "status": "found",
                    "confidence": "high",
                },
                {
                    "platform": "Instagram",
                    "url": f'https://instagram.com/{email.split("@")[0]}',
                    "status": "found",
                    "confidence": "medium",
                },
                {
                    "platform": "Facebook",
                    "url": "https://facebook.com",
                    "status": "possible",
                    "confidence": "low",
                },
                {
                    "platform": "LinkedIn",
                    "url": "https://linkedin.com",
                    "status": "not_found",
                    "confidence": "high",
                },
            ],
            "total_found": 2,
            "total_possible": 1,
            "execution_time": "2.3s",
        }

        return JsonResponse({"success": True, "data": mock_results})

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON data"}, status=400)
    except Exception as e:
        return JsonResponse(
            {"error": f"Internal server error: {str(e)}"},
            status=500,
        )


@csrf_exempt
@require_http_methods(["GET"])
def holehe_status(request):
    """
    Endpoint para verificar el estado de Holehe
    """
    try:
        # Verificar si holehe está instalado
        # Por ahora retornamos que está disponible como mock
        return JsonResponse(
            {
                "success": True,
                "data": {"installed": True, "version": "1.60.0", "status": "ready"},
            }
        )
    except Exception as e:
        return JsonResponse(
            {"error": f"Error checking Holehe status: {str(e)}"}, status=500
        )


def _execute_holehe(email):
    """
    Función privada para ejecutar holehe (implementación futura)
    """
    # TODO: Implementar la ejecución real de holehe
    # comando = ['holehe', email, '--only-used']
    # result = subprocess.run(comando, capture_output=True, text=True)
    # return result
    pass
