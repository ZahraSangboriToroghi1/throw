from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if isinstance(exc, ValidationError):
            response.data = {
                "statusCode": response.status_code,
                "message": "Validation failed",
                "errors": response.data
            }
        else:
            response.data = {
                "statusCode": response.status_code,
                "message": response.data.get('detail', 'An error occurred'),
                "errors": {}
            }

    return response