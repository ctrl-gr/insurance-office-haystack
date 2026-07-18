from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


logger = logging.getLogger("insurance.api")


class UpstreamServiceError(RuntimeError):
    def __init__(self, public_message: str):
        super().__init__(public_message)
        self.public_message = public_message


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(UpstreamServiceError)
    async def upstream_error_handler(_request: Request, error: UpstreamServiceError) -> JSONResponse:
        logger.error(
            "Upstream service failure: %s",
            error.public_message,
            exc_info=(type(error.__cause__), error.__cause__, error.__cause__.__traceback__) if error.__cause__ else None,
        )
        return JSONResponse(status_code=502, content={"detail": error.public_message})
