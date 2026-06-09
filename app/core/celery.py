from celery import Celery
from app.core.logging import setup_logging
from app.core.settings import settings

# Configura o Logging antes de criar a instância do Celery para garantir que as mensagens de log do Celery sejam formatadas corretamente.
setup_logging()

celery_app = Celery(
    "monitor_ru",
    broker=settings.CELERY_BROKER_URL,
)

celery_app.conf.update(
    # Serializa os argumentos das tasks em JSON.
    # Mais seguro e interoperável que pickle.
    task_serializer="json",
    # Serializa os resultados das tasks em JSON.
    # Útil caso seja utilizado um result backend futuramente.
    result_serializer="json",
    # Aceita apenas payloads JSON.
    # Evita execução de formatos inseguros como pickle.
    accept_content=["json"],
    # Timezone utilizado por agendamentos do Celery Beat
    # (crontabs, periodic tasks, etc.).
    timezone=settings.APP_TIMEZONE,
    # Converte internamente datas para UTC.
    # Recomendado para evitar inconsistências entre servidores.
    enable_utc=True,
    # A task só envia ACK para o broker após terminar.
    # Se o worker morrer durante a execução,
    # a mensagem poderá ser reenfileirada.
    task_acks_late=True,
    # Caso o worker seja encerrado abruptamente,
    # a task volta para a fila ao invés de ser perdida.
    task_reject_on_worker_lost=True,
    # Cada worker reserva apenas uma task por vez.
    # Evita concentração de tarefas em um único worker
    # e melhora o balanceamento de carga.
    worker_prefetch_multiplier=1,
)

celery_app.conf.imports = ("app.tasks.snapshot_tasks",)
