import time
from decimal import Decimal

from fastapi import APIRouter, Query, Request

from app.services.geo_signature_service import GeoSignatureService
from app.services.ip_service import IpService

router = APIRouter(prefix="/debug", tags=["Debug"])


@router.get("/ip")
async def get_ip(request: Request):
    ip = IpService.get_client_ip(request)
    return {
        "ip": ip,
        "cf_connecting_ip": request.headers.get("CF-Connecting-IP"),
        "x_forwarded_for": request.headers.get("X-Forwarded-For"),
        "x_real_ip": request.headers.get("X-Real-IP"),
        "request_client_host": request.client.host if request.client else None,
    }


@router.get("/geo-signature")
async def generate_geo_signature(
    lat: Decimal = Query(examples=[-3.74736]),
    lng: Decimal = Query(examples=[-38.52306]),
    accuracy_m: Decimal | None = Query(default=None, examples=[12.5]),
):
    geo_timestamp = int(time.time())
    payload = GeoSignatureService.build_payload(
        lat=lat,
        lng=lng,
        accuracy_m=accuracy_m,
        geo_timestamp=geo_timestamp,
    )
    signature = GeoSignatureService.generate_signature(payload)
    return {
        "geo_timestamp": geo_timestamp,
        "geo_signature": signature,
        "payload": payload,
    }
