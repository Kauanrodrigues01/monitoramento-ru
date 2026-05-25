import hashlib
import hmac
import time
from decimal import Decimal

from app.core.logging import get_logger
from app.core.settings import settings
from app.exceptions.geo_signature_exceptions import (
    ExpiredGeoSignatureException,
    InvalidGeoSignatureException,
)

logger = get_logger(__name__)


class GeoSignatureService:
    # valor padrão usado quando accuracy_m não for informado
    # evita "magic string" espalhada pelo código
    NULL_ACCURACY_VALUE = "null"

    @staticmethod
    def build_payload(
        lat: Decimal,
        lng: Decimal,
        accuracy_m: Decimal | None,
        geo_timestamp: int,
    ) -> str:
        """
        Monta a string canônica (payload) que será assinada.

        Essa string precisa ser EXATAMENTE igual no app mobile e no backend.
        Qualquer diferença de formato (casas decimais, separadores, ordem)
        invalida a assinatura.

        Exemplo:
        -4.225123|-38.730456|5.3|1716620000

        Se accuracy_m vier como None, usamos "null" explicitamente,
        evitando ambiguidade com 0.0.
        """

        # Se accuracy_m existir:
        # Decimal("5.37") -> "5.4"
        #
        # Se for None:
        # usa a constante "null"
        accuracy_value = (
            f"{accuracy_m:.1f}"
            if accuracy_m is not None
            else GeoSignatureService.NULL_ACCURACY_VALUE
        )

        # padronizamos:
        # lat/lng com 6 casas
        # accuracy com 1 casa
        # timestamp inteiro
        return f"{lat:.6f}|{lng:.6f}|{accuracy_value}|{geo_timestamp}"

    @staticmethod
    def generate_signature(payload: str) -> str:
        """
        Gera o HMAC-SHA256 da string.

        Fórmula:
        signature = HMAC(secret, payload)

        Isso garante:
        - integridade (ninguém alterou os dados)
        - autenticidade (quem enviou conhece a secret)
        """

        return hmac.new(
            # chave secreta compartilhada entre app e backend
            key=settings.APP_GEO_SECRET.encode(),
            # payload convertido para bytes
            msg=payload.encode(),
            # algoritmo de hash
            digestmod=hashlib.sha256,
        ).hexdigest()

    @classmethod
    def validate(
        cls,
        lat: Decimal,
        lng: Decimal,
        accuracy_m: Decimal | None,
        geo_timestamp: int,
        received_signature: str,
    ) -> None:
        """
        Valida toda a assinatura recebida do cliente.

        Fluxo:
        1. valida timestamp (proteção contra replay attack)
        2. recria payload
        3. gera assinatura esperada
        4. compara com a enviada pelo cliente
        """

        # 1 - impede reuso de requests antigas
        cls._validate_timestamp(geo_timestamp)

        # 2 - recria exatamente o payload
        payload = cls.build_payload(
            lat=lat,
            lng=lng,
            accuracy_m=accuracy_m,
            geo_timestamp=geo_timestamp,
        )

        # 3 - gera a assinatura esperada
        expected_signature = cls.generate_signature(payload)

        # 4 - comparação em tempo constante
        #
        # compare_digest evita timing attack:
        # atacante não consegue descobrir a assinatura
        # medindo tempo de resposta
        if not hmac.compare_digest(
            expected_signature,
            received_signature,
        ):
            logger.warning(
                "Assinatura geo inválida: geo_timestamp=%d, payload=%s",
                geo_timestamp,
                payload,
            )
            raise InvalidGeoSignatureException()

        logger.debug("Assinatura geo válida: geo_timestamp=%d", geo_timestamp)

    @staticmethod
    def _validate_timestamp(geo_timestamp: int) -> None:
        """
        Valida se o timestamp está dentro da janela permitida.

        Exemplo:
        agora = 1716620100
        cliente = 1716620045
        diferença = 55 segundos -> válido

        Se passar de 60s (configurável),
        rejeitamos a requisição.
        """

        # pega timestamp atual do servidor (Unix timestamp)
        now = int(time.time())

        # abs() = valor absoluto
        #
        # Ex:
        # abs(10 - 20) = 10
        # abs(20 - 10) = 10
        #
        # isso permite aceitar tanto:
        # - relógio do cliente atrasado
        # - relógio do cliente adiantado
        #
        # sem precisar saber quem está "na frente"
        time_difference = abs(now - geo_timestamp)

        # se passou da janela máxima permitida,
        # bloqueia por possível replay attack
        max_skew = (
            settings.GEO_SIGNATURE_MAX_SKEW_SECONDS if not settings.DEBUG else 86400
        )
        if time_difference > max_skew:
            logger.warning(
                "Assinatura geo expirada: geo_timestamp=%d, skew=%ds, max_skew=%ds",
                geo_timestamp,
                time_difference,
                max_skew,
            )
            raise ExpiredGeoSignatureException()
