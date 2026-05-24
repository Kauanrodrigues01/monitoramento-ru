import asyncio
from uuid import uuid4

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.restaurant import CampusEnum, Restaurant


RESTAURANTS = [
    {
        "name": "RU PALMARES",
        "campus": CampusEnum.PALMARES,
        "lat": -4.213632,
        "lng": -38.700622,
        "geofence_radius_m": 80,
        "is_active": True,
    },
    {
        "name": "RU AURORAS",
        "campus": CampusEnum.AURORAS,
        "lat": -4.217548,
        "lng": -38.712041,
        "geofence_radius_m": 110,
        "is_active": True,
    },
    {
        "name": "RU LIBERDADE",
        "campus": CampusEnum.LIBERDADE,
        "lat": -4.223177,
        "lng": -38.724955,
        "geofence_radius_m": 80,
        "is_active": True,
    },
]


async def seed_restaurants() -> None:
    async with AsyncSessionLocal() as session:
        created_count = 0

        for restaurant_data in RESTAURANTS:
            existing_restaurant = await session.scalar(
                select(Restaurant).where(
                    Restaurant.name == restaurant_data["name"]
                )
            )

            if existing_restaurant:
                print(
                    f"Restaurant '{restaurant_data['name']}' already exists. Skipping."
                )
                continue

            restaurant = Restaurant(
                public_id=uuid4(),
                **restaurant_data,
            )

            session.add(restaurant)
            created_count += 1

        await session.commit()

        print(
            f"Seed completed successfully. "
            f"{created_count} restaurant(s) created."
        )


if __name__ == "__main__":
    asyncio.run(seed_restaurants())