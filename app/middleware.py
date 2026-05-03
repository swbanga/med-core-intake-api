import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.logger import logger

class FBIFeedbackLoopMiddleware(BaseHTTPMiddleware):
    """
    Global interceptor. Ingests all requests, measures performance, 
    and forces structured JSON output for every response.
    """
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract network vectors
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        try:
            # Pass the request down into the FastAPI application
            response = await call_next(request)
            
            # Measure Celeron execution time
            process_time_ms = round((time.time() - start_time) * 1000, 2)
            
            # Construct the exact telemetry payload
            log_payload = {
                "event": "http_request",
                "client_ip": client_ip,
                "method": method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": process_time_ms
            }

            # Brutal categorization of events
            if response.status_code in [401, 403]:
                log_payload["event"] = "security_breach_attempt"
                logger.warning("Authorization Failure", extra=log_payload)
            elif response.status_code >= 500:
                log_payload["event"] = "system_panic"
                logger.error("Internal Server Error", extra=log_payload)
            else:
                logger.info("Request Processed", extra=log_payload)
                
            return response
            
        except Exception as e:
            # If the server violently crashes, we log the exact reason before dying.
            process_time_ms = round((time.time() - start_time) * 1000, 2)
            logger.critical("Unhandled Exception", extra={
                "event": "catastrophic_failure",
                "client_ip": client_ip,
                "method": method,
                "path": path,
                "error": str(e),
                "duration_ms": process_time_ms
            })
            raise