from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Union, Dict, Any
import logging
import structlog
import traceback
from datetime import datetime

# Configure structured logging
logger = structlog.get_logger()
logging.basicConfig(level=logging.INFO)

class ErrorHandler:
    async def __call__(self, request: Request, call_next):
        try:
            return await call_next(request)
        except HTTPException as exc:
            logger.warning("http_exception",
                error_type="HTTPException",
                status_code=exc.status_code,
                detail=exc.detail,
                path=request.url.path,
                method=request.method
            )
            return JSONResponse(
                status_code=exc.status_code,
                content={"detail": exc.detail}
            )
        except Exception as exc:
            logger.error("unhandled_exception",
                error_type=type(exc).__name__,
                error_details=str(exc),
                traceback=traceback.format_exc(),
                path=request.url.path,
                method=request.method,
                timestamp=datetime.utcnow().isoformat()
            )
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "Internal server error",
                    "error_type": type(exc).__name__
                }
            ) 