from django.http import HttpResponse
import logging

logger = logging.getLogger('medical_reports')

class CorsOptionsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "OPTIONS":
            response = HttpResponse(status=200)
            response["Access-Control-Allow-Origin"] = "http://localhost:4200"
            response["Access-Control-Allow-Methods"] = "GET,POST,PUT,PATCH,DELETE,OPTIONS"
            response["Access-Control-Allow-Headers"] = "Authorization,Content-Type"
            response["Access-Control-Allow-Credentials"] = "true"
            return response
        return self.get_response(request)

class RawPayloadLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == "POST" and request.path == "/api/patients/":
            try:
                raw_body = request.body.decode('utf-8')
                logger.info(f"Raw POST payload for /api/patients/: {raw_body}")
            except Exception as e:
                logger.error(f"Failed to decode raw payload: {str(e)}")
        response = self.get_response(request)
        return response