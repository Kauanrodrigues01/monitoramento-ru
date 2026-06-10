from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator


def setup_prometheus(app: FastAPI) -> None:
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        # Adiciona label do método no in-progress também
        inprogress_labels=True,
        excluded_handlers=[
            r"^/metrics$",
            r"^/docs$",
            r"^/redoc$",
            r"^/openapi\.json$",
            r"^/health.*",
            r"^.*/debug.*",
            r"^.*/ws.*",
        ],
    )

    instrumentator.instrument(app)
    instrumentator.expose(app, include_in_schema=False)  # esconde do OpenAPI
