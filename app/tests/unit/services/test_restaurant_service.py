from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.restaurant_exceptions import (
    RestaurantAlreadyExistsError,
    RestaurantNotFoundError,
)
from app.models.queue_snapshot import SnapshotStatusEnum
from app.models.restaurant import CampusEnum, MealPeriodEnum
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.restaurant_service import RestaurantService
from app.tests.factories.restaurant_model_factory import RestaurantFactory
from app.tests.factories.restaurant_schema_factory import (
    build_restaurant_create_schema,
    build_restaurant_update_schema,
)


@pytest.fixture
def mock_repository():
    """Cria um mock do repositório"""
    mock = AsyncMock(spec=RestaurantRepository)
    mock.db_session = AsyncMock()
    return mock


@pytest.fixture
def mock_snapshot_repo():
    return AsyncMock(spec=QueueSnapshotRepository)


@pytest.fixture
def service(mock_repository, mock_snapshot_repo):
    """Cria a service com repositórios mockados"""
    return RestaurantService(repo=mock_repository, snapshot_repo=mock_snapshot_repo)


# ===== CREATE RESTAURANT =====
class TestCreateRestaurant:
    @pytest.mark.asyncio
    async def test_should_create_restaurant_successfully(
        self, service, mock_repository
    ):
        """Deve criar um restaurante com sucesso"""
        restaurant_data = build_restaurant_create_schema()
        created_restaurant = RestaurantFactory.build(name=restaurant_data.name)

        mock_repository.get_by_name.return_value = None
        mock_repository.create.return_value = created_restaurant
        mock_repository.db_session.commit = AsyncMock()

        # Simula que o refresh atualiza o objeto
        async def mock_refresh(obj):
            pass

        mock_repository.db_session.refresh = mock_refresh

        result = await service.create_restaurant(restaurant_data)

        assert result.name == restaurant_data.name
        assert result.campus == restaurant_data.campus
        mock_repository.get_by_name.assert_called_once_with(restaurant_data.name)
        mock_repository.create.assert_called_once()
        mock_repository.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_raise_error_when_restaurant_already_exists(
        self, service, mock_repository
    ):
        """Deve lançar erro quando restaurante já existe"""
        restaurant_data = build_restaurant_create_schema()
        existing_restaurant = RestaurantFactory.build(name=restaurant_data.name)

        mock_repository.get_by_name.return_value = existing_restaurant

        with pytest.raises(RestaurantAlreadyExistsError):
            await service.create_restaurant(restaurant_data)

        mock_repository.get_by_name.assert_called_once_with(restaurant_data.name)
        mock_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_rollback_on_integrity_error(self, service, mock_repository):
        """Deve fazer rollback em caso de IntegrityError"""
        restaurant_data = build_restaurant_create_schema()

        mock_repository.get_by_name.return_value = None
        mock_repository.create.side_effect = IntegrityError("", "", "")
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RestaurantAlreadyExistsError):
            await service.create_restaurant(restaurant_data)

        mock_repository.db_session.rollback.assert_called_once()
        mock_repository.db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_rollback_and_reraise_unexpected_error(
        self, service, mock_repository
    ):
        """Deve fazer rollback e relançar erros inesperados"""
        restaurant_data = build_restaurant_create_schema()

        mock_repository.get_by_name.return_value = None
        mock_repository.create.side_effect = ValueError("Erro inesperado")
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.rollback = AsyncMock()

        with pytest.raises(ValueError):
            await service.create_restaurant(restaurant_data)

        mock_repository.db_session.rollback.assert_called_once()


# ===== CREATE RESTAURANT — SNAPSHOTS =====
class TestCreateRestaurantSnapshots:
    @pytest.mark.asyncio
    async def test_should_create_snapshot_for_each_meal_period(
        self, service, mock_repository, mock_snapshot_repo
    ):
        """Deve criar um snapshot para LUNCH e outro para DINNER"""
        restaurant_data = build_restaurant_create_schema()

        mock_repository.get_by_name.return_value = None

        async def _set_id(restaurant):
            restaurant.id = 1

        mock_repository.create.side_effect = _set_id
        mock_repository.db_session.commit = AsyncMock()

        await service.create_restaurant(restaurant_data)

        assert mock_snapshot_repo.create.call_count == 2
        snapshots = [call.args[0] for call in mock_snapshot_repo.create.call_args_list]
        periods = {s.meal_period for s in snapshots}
        assert periods == {MealPeriodEnum.LUNCH, MealPeriodEnum.DINNER}

    @pytest.mark.asyncio
    async def test_should_create_snapshots_with_no_data_status(
        self, service, mock_repository, mock_snapshot_repo
    ):
        """Deve criar snapshots com status NO_DATA"""
        restaurant_data = build_restaurant_create_schema()

        mock_repository.get_by_name.return_value = None

        async def _set_id(restaurant):
            restaurant.id = 1

        mock_repository.create.side_effect = _set_id
        mock_repository.db_session.commit = AsyncMock()

        await service.create_restaurant(restaurant_data)

        snapshots = [call.args[0] for call in mock_snapshot_repo.create.call_args_list]
        assert all(s.current_status == SnapshotStatusEnum.NO_DATA for s in snapshots)

    @pytest.mark.asyncio
    async def test_should_create_snapshots_with_correct_ru_id(
        self, service, mock_repository, mock_snapshot_repo
    ):
        """Deve criar snapshots com o ru_id do restaurante recém-criado"""
        restaurant_data = build_restaurant_create_schema()

        mock_repository.get_by_name.return_value = None

        async def _set_id(restaurant):
            restaurant.id = 42

        mock_repository.create.side_effect = _set_id
        mock_repository.db_session.commit = AsyncMock()

        await service.create_restaurant(restaurant_data)

        snapshots = [call.args[0] for call in mock_snapshot_repo.create.call_args_list]
        assert all(s.ru_id == 42 for s in snapshots)

    @pytest.mark.asyncio
    async def test_should_not_create_snapshots_when_restaurant_already_exists(
        self, service, mock_repository, mock_snapshot_repo
    ):
        """Não deve criar snapshots quando o restaurante já existe"""
        restaurant_data = build_restaurant_create_schema()
        mock_repository.get_by_name.return_value = RestaurantFactory.build(
            name=restaurant_data.name
        )

        with pytest.raises(RestaurantAlreadyExistsError):
            await service.create_restaurant(restaurant_data)

        mock_snapshot_repo.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_rollback_when_snapshot_creation_fails(
        self, service, mock_repository, mock_snapshot_repo
    ):
        """Deve fazer rollback quando a criação de snapshot falhar"""
        restaurant_data = build_restaurant_create_schema()

        mock_repository.get_by_name.return_value = None

        async def _set_id(restaurant):
            restaurant.id = 1

        mock_repository.create.side_effect = _set_id
        mock_snapshot_repo.create.side_effect = RuntimeError("Falha ao criar snapshot")
        mock_repository.db_session.rollback = AsyncMock()
        mock_repository.db_session.commit = AsyncMock()

        with pytest.raises(RuntimeError):
            await service.create_restaurant(restaurant_data)

        mock_repository.db_session.rollback.assert_called_once()
        mock_repository.db_session.commit.assert_not_called()


# ===== LIST RESTAURANTS =====
class TestListRestaurants:
    @pytest.mark.asyncio
    async def test_should_list_all_restaurants(self, service, mock_repository):
        """Deve listar todos os restaurantes"""
        restaurants = [
            RestaurantFactory.build(name="RU Pálmares", campus=CampusEnum.PALMARES),
            RestaurantFactory.build(name="RU Auroras", campus=CampusEnum.AURORAS),
            RestaurantFactory.build(name="RU Liberdade", campus=CampusEnum.LIBERDADE),
        ]

        mock_repository.get_all.return_value = restaurants

        result = await service.list_restaurants()

        assert len(result) == 3
        assert result[0].name == "RU Pálmares"
        assert result[1].name == "RU Auroras"
        assert result[2].name == "RU Liberdade"
        mock_repository.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_restaurants(
        self, service, mock_repository
    ):
        """Deve retornar lista vazia quando não há restaurantes"""
        mock_repository.get_all.return_value = []

        result = await service.list_restaurants()

        assert result == []
        mock_repository.get_all.assert_called_once()


# ===== GET RESTAURANT =====
class TestGetRestaurant:
    @pytest.mark.asyncio
    async def test_should_get_restaurant_by_public_id(self, service, mock_repository):
        """Deve obter um restaurante pelo public_id"""
        public_id = uuid4()
        restaurant = RestaurantFactory.build(public_id=public_id, name="RU Pálmares")

        mock_repository.get_by_public_id.return_value = restaurant

        result = await service.get_restaurant(public_id)

        assert result.public_id == public_id
        assert result.name == "RU Pálmares"
        mock_repository.get_by_public_id.assert_called_once_with(public_id)

    @pytest.mark.asyncio
    async def test_should_raise_error_when_restaurant_not_found(
        self, service, mock_repository
    ):
        """Deve lançar erro quando restaurante não existe"""
        public_id = uuid4()

        mock_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.get_restaurant(public_id)

        mock_repository.get_by_public_id.assert_called_once_with(public_id)


# ===== UPDATE RESTAURANT =====
class TestUpdateRestaurant:
    @pytest.mark.asyncio
    async def test_should_update_restaurant_successfully(
        self, service, mock_repository
    ):
        """Deve atualizar um restaurante com sucesso"""
        public_id = uuid4()
        original_restaurant = RestaurantFactory.build(
            public_id=public_id, name="RU Pálmares"
        )
        update_data = build_restaurant_update_schema(
            name="RU Pálmares Renovado", geofence_radius_m=100
        )

        mock_repository.get_by_public_id.return_value = original_restaurant
        mock_repository.get_by_name.return_value = None
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.refresh = AsyncMock()

        result = await service.update_restaurant(public_id, update_data)

        assert result.name == "RU Pálmares Renovado"
        assert result.geofence_radius_m == 100
        mock_repository.get_by_public_id.assert_called_once_with(public_id)
        mock_repository.db_session.commit.assert_called_once()
        mock_repository.db_session.refresh.assert_called_once_with(original_restaurant)

    @pytest.mark.asyncio
    async def test_should_raise_error_when_updating_non_existent_restaurant(
        self, service, mock_repository
    ):
        """Deve lançar erro ao atualizar restaurante que não existe"""
        public_id = uuid4()
        update_data = build_restaurant_update_schema(name="Novo Nome")

        mock_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.update_restaurant(public_id, update_data)

        mock_repository.get_by_public_id.assert_called_once_with(public_id)

    @pytest.mark.asyncio
    async def test_should_raise_error_when_updating_name_to_existing_one(
        self, service, mock_repository
    ):
        """Deve lançar erro ao atualizar nome para um que já existe"""
        public_id = uuid4()
        original_restaurant = RestaurantFactory.build(
            public_id=public_id, name="RU Pálmares"
        )
        existing_restaurant = RestaurantFactory.build(
            name="RU Auroras", campus=CampusEnum.AURORAS
        )
        update_data = build_restaurant_update_schema(name="RU Auroras")

        mock_repository.get_by_public_id.return_value = original_restaurant
        mock_repository.get_by_name.return_value = existing_restaurant

        with pytest.raises(RestaurantAlreadyExistsError):
            await service.update_restaurant(public_id, update_data)

        mock_repository.get_by_name.assert_called_once_with("RU Auroras")

    @pytest.mark.asyncio
    async def test_should_update_restaurant_without_changing_name(
        self, service, mock_repository
    ):
        """Deve atualizar restaurante sem mudar o nome (sem verificar duplicação)"""
        public_id = uuid4()
        original_restaurant = RestaurantFactory.build(
            public_id=public_id, name="RU Pálmares", geofence_radius_m=80
        )
        update_data = build_restaurant_update_schema(geofence_radius_m=120)

        mock_repository.get_by_public_id.return_value = original_restaurant
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.refresh = AsyncMock()

        result = await service.update_restaurant(public_id, update_data)

        assert result.geofence_radius_m == 120
        assert result.name == "RU Pálmares"
        # get_by_name não deve ser chamado pois o nome não foi alterado
        mock_repository.get_by_name.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_rollback_on_integrity_error_during_update(
        self, service, mock_repository
    ):
        """Deve fazer rollback em caso de IntegrityError durante atualização"""
        public_id = uuid4()
        original_restaurant = RestaurantFactory.build(public_id=public_id)
        update_data = build_restaurant_update_schema(name="Novo Nome")

        mock_repository.get_by_public_id.return_value = original_restaurant
        mock_repository.get_by_name.return_value = None
        mock_repository.db_session.commit.side_effect = IntegrityError("", "", "")
        mock_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RestaurantAlreadyExistsError):
            await service.update_restaurant(public_id, update_data)

        mock_repository.db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_rollback_and_reraise_unexpected_error_during_update(
        self, service, mock_repository
    ):
        """Deve fazer rollback e relançar erros inesperados durante atualização"""
        public_id = uuid4()
        original_restaurant = RestaurantFactory.build(public_id=public_id)
        update_data = build_restaurant_update_schema(name="Novo Nome")

        mock_repository.get_by_public_id.return_value = original_restaurant
        mock_repository.get_by_name.return_value = None
        mock_repository.db_session.commit.side_effect = RuntimeError("Erro BD")
        mock_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RuntimeError):
            await service.update_restaurant(public_id, update_data)

        mock_repository.db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_update_only_provided_fields(self, service, mock_repository):
        """Deve atualizar apenas os campos fornecidos (None é ignorado)"""
        public_id = uuid4()
        original_restaurant = RestaurantFactory.build(
            public_id=public_id,
            name="RU Pálmares",
            geofence_radius_m=80,
            is_active=True,
        )
        update_data = build_restaurant_update_schema(
            geofence_radius_m=120, is_active=None
        )

        mock_repository.get_by_public_id.return_value = original_restaurant
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.refresh = AsyncMock()

        result = await service.update_restaurant(public_id, update_data)

        assert result.geofence_radius_m == 120
        assert result.is_active is True  # Não deve ser alterado


# ===== LOGGING VALIDATION =====
class TestLogging:
    @pytest.mark.asyncio
    async def test_should_log_info_when_restaurant_created_successfully(
        self, service, mock_repository
    ):
        """Deve fazer log INFO quando restaurante é criado"""
        restaurant_data = build_restaurant_create_schema()
        created_restaurant = RestaurantFactory.build(name=restaurant_data.name)

        mock_repository.get_by_name.return_value = None
        mock_repository.create.return_value = created_restaurant
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.refresh = AsyncMock()

        with patch("app.services.restaurant_service.logger") as mock_logger:
            await service.create_restaurant(restaurant_data)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0]
            assert "Restaurante criado" in call_args[0]
            assert restaurant_data.name in call_args

    @pytest.mark.asyncio
    async def test_should_log_warning_when_restaurant_not_found(
        self, service, mock_repository
    ):
        """Deve fazer log WARNING quando restaurante não é encontrado"""
        public_id = uuid4()
        mock_repository.get_by_public_id.return_value = None

        with patch("app.services.restaurant_service.logger") as mock_logger:
            with pytest.raises(RestaurantNotFoundError):
                await service.get_restaurant(public_id)

            mock_logger.warning.assert_called_once()
            assert str(public_id) in str(mock_logger.warning.call_args)

    @pytest.mark.asyncio
    async def test_should_log_warning_when_duplicate_restaurant_creation_attempted(
        self, service, mock_repository
    ):
        """Deve fazer log WARNING ao tentar criar restaurante duplicado"""
        restaurant_data = build_restaurant_create_schema()
        existing_restaurant = RestaurantFactory.build(name=restaurant_data.name)

        mock_repository.get_by_name.return_value = existing_restaurant

        with patch("app.services.restaurant_service.logger") as mock_logger:
            with pytest.raises(RestaurantAlreadyExistsError):
                await service.create_restaurant(restaurant_data)

            mock_logger.warning.assert_called_once()
            assert "duplicado" in mock_logger.warning.call_args[0][0]


# ===== REPOSITORY CALL VALIDATION =====
class TestRepositoryInteraction:
    @pytest.mark.asyncio
    async def test_should_create_restaurant_object_with_correct_data(
        self, service, mock_repository
    ):
        """Deve criar objeto Restaurant com dados corretos"""
        restaurant_data = build_restaurant_create_schema()
        created_restaurant = RestaurantFactory.build(name=restaurant_data.name)

        mock_repository.get_by_name.return_value = None
        mock_repository.create.return_value = created_restaurant
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.refresh = AsyncMock()

        await service.create_restaurant(restaurant_data)

        # Valida que create foi chamado com objeto Restaurant
        mock_repository.create.assert_called_once()
        called_restaurant = mock_repository.create.call_args[0][0]

        assert called_restaurant.name == restaurant_data.name
        assert called_restaurant.campus == restaurant_data.campus


# ===== EDGE CASES =====
class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_should_handle_special_characters_in_name(
        self, service, mock_repository
    ):
        """Deve aceitar nomes com caracteres especiais"""
        special_name = "RU Café & Restaurante"
        restaurant_data = build_restaurant_create_schema(name=special_name)
        created_restaurant = RestaurantFactory.build(name=special_name)

        mock_repository.get_by_name.return_value = None
        mock_repository.create.return_value = created_restaurant
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.refresh = AsyncMock()

        result = await service.create_restaurant(restaurant_data)

        assert result.name == special_name

    @pytest.mark.asyncio
    async def test_should_handle_campus_uniqueness_constraint(
        self, service, mock_repository
    ):
        """Deve respeitar constraint único de campus na atualização"""
        public_id = uuid4()
        original = RestaurantFactory.build(
            public_id=public_id, campus=CampusEnum.PALMARES
        )
        update_data = build_restaurant_update_schema(campus=CampusEnum.AURORAS)

        mock_repository.get_by_public_id.return_value = original
        mock_repository.get_by_name.return_value = None
        mock_repository.db_session.commit.side_effect = IntegrityError("", "", "")
        mock_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RestaurantAlreadyExistsError):
            await service.update_restaurant(public_id, update_data)

    @pytest.mark.asyncio
    async def test_should_not_call_get_by_name_when_only_geofence_changes(
        self, service, mock_repository
    ):
        """Não deve validar nome quando só geofence é atualizado"""
        public_id = uuid4()
        original = RestaurantFactory.build(
            public_id=public_id, name="RU Original", geofence_radius_m=80
        )
        update_data = build_restaurant_update_schema(geofence_radius_m=100)

        mock_repository.get_by_public_id.return_value = original
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.refresh = AsyncMock()

        await service.update_restaurant(public_id, update_data)

        # get_by_name não deve ser chamado pois nome não mudou
        mock_repository.get_by_name.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_preserve_existing_fields_during_partial_update(
        self, service, mock_repository
    ):
        """Deve preservar campos não alterados durante update parcial"""
        public_id = uuid4()
        original = RestaurantFactory.build(
            public_id=public_id,
            name="RU Original",
            geofence_radius_m=80,
            is_active=True,
        )
        update_data = build_restaurant_update_schema(geofence_radius_m=120)

        mock_repository.get_by_public_id.return_value = original
        mock_repository.db_session.commit = AsyncMock()
        mock_repository.db_session.refresh = AsyncMock()

        result = await service.update_restaurant(public_id, update_data)

        # Campos não alterados devem ser preservados
        assert result.name == "RU Original"
        assert result.is_active is True
        # Campo alterado deve ser atualizado
        assert result.geofence_radius_m == 120
