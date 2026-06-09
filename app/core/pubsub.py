import asyncio

from app.core.logging import get_logger
from app.core.redis import get_redis
from app.core.websocket_manager import manager

logger = get_logger(__name__)

_PUBSUB_CHANNEL = "snapshots"
_RECONNECT_DELAY_SECONDS = 5


async def start_pubsub_listener() -> None:
    """
    Inicia um listener Pub/Sub persistente no canal 'snapshots'.
    Usa um cliente Redis dedicado para evitar interferência do pool de conexões
    de operações de publicação/obtenção/definição que compartilham o mesmo cliente.

    Reconecta automaticamente em caso de erros inesperados.
    """
    while True:
        try:
            await _run_listener()
        except asyncio.CancelledError:
            logger.warning("Listener cancelado (shutdown da aplicação).")
            raise
        except Exception:
            logger.exception(
                "Listener caiu inesperadamente. Reconectando em %ds...",
                _RECONNECT_DELAY_SECONDS,
            )
            await asyncio.sleep(_RECONNECT_DELAY_SECONDS)


async def _run_listener() -> None:
    """Single lifecycle of the Pub/Sub listener connection."""
    redis = await get_redis()

    pubsub = redis.pubsub()
    await pubsub.subscribe(_PUBSUB_CHANNEL)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            payload: str = message["data"]

            await manager.broadcast(room=_PUBSUB_CHANNEL, payload=payload)
    finally:
        # Sempre cancela a inscrição e limpa o objeto pubsub ao sair.
        try:
            await pubsub.unsubscribe(_PUBSUB_CHANNEL)
            await pubsub.aclose()
        except Exception:
            logger.debug("Erro ao fechar pubsub durante cleanup.", exc_info=True)
