from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.core.datetime_utils import to_app_tz, utc_now
from app.core.openapi_responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    RATE_LIMIT_RESPONSE,
    error_response,
)
from app.core.rate_limiter import limiter
from app.core.rate_limits import (
    CREATE_SCHEDULE_EXCEPTION_RATE_LIMIT,
    READ_RATE_LIMIT,
    UPDATE_SCHEDULE_EXCEPTION_RATE_LIMIT,
)
from app.dependencies.auth import require_admin_api_key
from app.dependencies.restaurant_dependencies import (
    RestaurantScheduleExceptionServiceDep,
)
from app.exceptions.auth import InvalidAdminApiKeyError
from app.exceptions.restaurant_exceptions import (
    RestaurantNotFoundError,
    RestaurantScheduleExceptionAlreadyExistsError,
    RestaurantScheduleExceptionInvalidStateError,
    RestaurantScheduleExceptionNotFoundError,
)
from app.schemas.restaurant_schedule_exception_schemas import (
    ActiveScheduleExceptionResponse,
    RestaurantScheduleExceptionCreate,
    RestaurantScheduleExceptionResponse,
    RestaurantScheduleExceptionUpdate,
)

router = APIRouter(prefix="/restaurants", tags=["Restaurant Schedule Exceptions"])


@router.post(
    "/{restaurant_public_id}/schedule-exceptions",
    status_code=201,
    response_model=RestaurantScheduleExceptionResponse,
    dependencies=[Depends(require_admin_api_key)],
    responses=(
        error_response(RestaurantNotFoundError)
        | error_response(RestaurantScheduleExceptionAlreadyExistsError)
        | error_response(InvalidAdminApiKeyError)
        | RATE_LIMIT_RESPONSE
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit(CREATE_SCHEDULE_EXCEPTION_RATE_LIMIT)
async def create_restaurant_schedule_exception(
    restaurant_public_id: UUID,
    request: Request,
    data: RestaurantScheduleExceptionCreate,
    service: RestaurantScheduleExceptionServiceDep,
):
    return await service.create_restaurant_schedule_exception(
        restaurant_public_id, data
    )


@router.get(
    "/{restaurant_public_id}/schedule-exceptions/current",
    summary="Retorna a exceção de horário em vigor no momento atual",
    description=(
        "Verifica se existe uma exceção de horário **em vigor agora** para o restaurante "
        "informado, considerando a data e o período de refeição atuais (calculados no horário "
        "de Brasília no momento da requisição).\n\n"
        "**Atenção:** 'active' aqui significa *em efeito neste instante*, não um campo de "
        "status do registro. O resultado muda conforme o horário do dia.\n\n"
        "**Casos possíveis:**\n"
        '- Retorna `{"exception": null}` quando não há exceção em vigor (comportamento normal '
        "do restaurante).\n"
        '- Retorna `{"exception": {...}}` com `exception_type = CLOSED` quando o restaurante '
        "está fechado por exceção (dia inteiro ou para o período de refeição atual).\n"
        '- Retorna `{"exception": {...}}` com `exception_type = CUSTOM_HOURS` quando o '
        "restaurante opera em horário diferente do padrão para o período atual.\n\n"
        "O endpoint **sempre retorna 200**; nunca retorna 404 quando a exceção não existe — "
        "use `exception: null` para detectar ausência."
    ),
    response_model=ActiveScheduleExceptionResponse,
    responses=(
        error_response(RestaurantNotFoundError)
        | RATE_LIMIT_RESPONSE
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit(READ_RATE_LIMIT)
async def get_current_schedule_exception(
    restaurant_public_id: UUID,
    request: Request,
    service: RestaurantScheduleExceptionServiceDep,
):
    exception = await service.get_active_exception(
        restaurant_public_id, to_app_tz(utc_now())
    )
    return ActiveScheduleExceptionResponse(exception=exception)


@router.get(
    "/{restaurant_public_id}/schedule-exceptions",
    response_model=list[RestaurantScheduleExceptionResponse],
    responses=(
        error_response(RestaurantNotFoundError)
        | RATE_LIMIT_RESPONSE
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit(READ_RATE_LIMIT)
async def list_restaurant_schedule_exceptions(
    restaurant_public_id: UUID,
    request: Request,
    service: RestaurantScheduleExceptionServiceDep,
    exception_date: date | None = None,
):
    return await service.list_restaurant_schedule_exceptions(
        restaurant_public_id, exception_date
    )


@router.patch(
    "/{restaurant_public_id}/schedule-exceptions/{restaurant_schedule_exception_public_id}",
    response_model=RestaurantScheduleExceptionResponse,
    dependencies=[Depends(require_admin_api_key)],
    responses=(
        error_response(RestaurantNotFoundError)
        | error_response(RestaurantScheduleExceptionNotFoundError)
        | error_response(RestaurantScheduleExceptionAlreadyExistsError)
        | error_response(RestaurantScheduleExceptionInvalidStateError)
        | error_response(InvalidAdminApiKeyError)
        | RATE_LIMIT_RESPONSE
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit(UPDATE_SCHEDULE_EXCEPTION_RATE_LIMIT)
async def update_restaurant_schedule_exception(
    restaurant_public_id: UUID,
    restaurant_schedule_exception_public_id: UUID,
    request: Request,
    data: RestaurantScheduleExceptionUpdate,
    service: RestaurantScheduleExceptionServiceDep,
):
    return await service.update_restaurant_schedule_exception(
        restaurant_public_id, restaurant_schedule_exception_public_id, data
    )
