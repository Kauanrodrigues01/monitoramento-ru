import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import TEST_DATABASE_URL
from app.dependencies.database import get_db_session
from app.main import app
from app.models.base import Base

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)

TestAsyncSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


# scope="session" - executa 1 vez por execução inteira do pytest. É executado 1 vez a cada comando pytest
# autouse=True - executa essa fixture automaticamente sem precisar chamar
@pytest.fixture(scope="session")
async def prepare_database():
    """
    pytest inicia
    ↓
    prepare_database()
    ↓
    create_all()
    ↓
    roda todos os testes
    ↓
    drop_all()
    ↓
    pytest termina
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_db_session():
    """
    executa uma vez para cada teste

    test_1
    ↓
    abre conexão
    ↓
    BEGIN transaction
    ↓
    entrega a sessão ao teste
    ↓
    teste roda normalmente
      - pode fazer insert
      - pode fazer update
      - pode fazer delete
      - pode até dar commit
    ↓
    fecha sessão
    ↓
    ROLLBACK transaction
    ↓
    tudo que o teste fez é desfeito

    --------------------------

    test_2
    ↓
    começa com banco limpo
    """
    async with test_engine.connect() as connection:
        transaction = await connection.begin()

        db_session = TestAsyncSessionLocal(bind=connection)

        yield db_session

        await db_session.close()

        await transaction.rollback()


@pytest.fixture
async def client(test_db_session):
    """
    executa uma vez para cada teste que pedir "client"

    endpoint normalmente:
        Depends(get_db_session)
            ↓
            usa banco real

    durante o teste:
        sobrescrevemos get_db_session
            ↓
            agora ele usa test_db_session

    resultado:
        nenhum endpoint toca o banco de produção
        todos usam o banco de teste
    """

    async def override_get_db_session():
        yield test_db_session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


"""
pytest
 ↓
prepare_database()
 create tables
 ↓
test_1
  test_db_session()
    BEGIN
  client()
  teste roda
    COMMIT (se houver)
  ROLLBACK
 ↓
test_2
  BEGIN
  banco limpo
  ROLLBACK
 ↓
test_3
 ...
 ↓
prepare_database()
 drop tables
"""
