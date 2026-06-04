from typing import Annotated

from fastapi import Depends, Header


def get_device_id_header(
    x_device_id: str | None = Header(default=None, alias="X-Device-ID"),
) -> str | None:
    return x_device_id


DeviceIdHeaderDep = Annotated[str | None, Depends(get_device_id_header)]
