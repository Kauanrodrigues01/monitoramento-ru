from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.settings import settings

DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{settings.DB_USER}:"
    f"{settings.DB_PASSWORD}@"
    f"{settings.DB_HOST}:"
    f"{settings.DB_PORT}/"
    f"{settings.DB_NAME}"
)

TEST_DATABASE_URL = (
    f"postgresql+asyncpg://"
    f"{settings.DB_USER}:"
    f"{settings.DB_PASSWORD}@"
    f"{settings.DB_HOST}:"
    f"{settings.DB_PORT}/"
    f"{settings.TEST_DB_NAME}"
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Desativa o log de SQL para evitar poluição do console
    pool_size=20,  # Tamanho do pool de conexões
    max_overflow=10,
    pool_pre_ping=True,  # Verifica a conexão antes de usá-la, útil para conexões de longa duração
    pool_recycle=3600,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Evita que os objetos sejam expurgados após o commit, permitindo que sejam usados após a transação
)
