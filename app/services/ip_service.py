import hashlib

from fastapi import Request


class IpService:
    @staticmethod
    def get_client_ip(request: Request) -> str:
        """
        Resolve o IP real do cliente usando fallback em múltiplas fontes.

        Ordem:
        1. CF-Connecting-IP (Cloudflare)
        2. X-Forwarded-For (proxy/load balancer)
        3. X-Real-IP (nginx)
        4. request.client.host (fallback local)
        """

        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip.strip()

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # formato: "client, proxy1, proxy2"
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        if request.client:
            return request.client.host

        return "unknown"

    @staticmethod
    def hash_ip(ip: str) -> str:
        return hashlib.sha256(ip.encode()).hexdigest()
