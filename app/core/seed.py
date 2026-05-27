import asyncio
from datetime import time
from uuid import uuid4

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.queue_snapshot import QueueSnapshot, SnapshotStatusEnum
from app.models.restaurant import (
    CampusEnum,
    MealPeriodEnum,
    Restaurant,
    RestaurantSchedule,
)

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

WEEKDAYS = [0, 1, 2, 3, 4, 5]

SCHEDULES = [
    {
        "meal_period": MealPeriodEnum.LUNCH,
        "opens_at": time(11, 0),
        "closes_at": time(14, 0),
    },
    {
        "meal_period": MealPeriodEnum.DINNER,
        "opens_at": time(17, 0),
        "closes_at": time(19, 0),
    },
]


async def seed_restaurants() -> None:
    async with AsyncSessionLocal() as session:
        restaurants_created = 0
        schedules_created = 0

        for restaurant_data in RESTAURANTS:
            existing = await session.scalar(
                select(Restaurant).where(Restaurant.name == restaurant_data["name"])
            )

            if existing:
                print(
                    f"Restaurant '{restaurant_data['name']}' already exists. Skipping."
                )
                restaurant = existing
            else:
                restaurant = Restaurant(public_id=uuid4(), **restaurant_data)
                session.add(restaurant)
                await session.flush()
                restaurants_created += 1
                print(f"Restaurant '{restaurant.name}' created.")

            for weekday in WEEKDAYS:
                for schedule_data in SCHEDULES:
                    existing_schedule = await session.scalar(
                        select(RestaurantSchedule).where(
                            RestaurantSchedule.ru_id == restaurant.id,
                            RestaurantSchedule.weekday == weekday,
                            RestaurantSchedule.meal_period
                            == schedule_data["meal_period"],
                        )
                    )

                    if existing_schedule:
                        continue

                    schedule = RestaurantSchedule(
                        ru_id=restaurant.id,
                        weekday=weekday,
                        **schedule_data,
                    )
                    session.add(schedule)
                    schedules_created += 1

        snapshots_created = 0

        for restaurant_data in RESTAURANTS:
            restaurant = await session.scalar(
                select(Restaurant).where(Restaurant.name == restaurant_data["name"])
            )

            if not restaurant:
                continue

            for meal_period in (MealPeriodEnum.LUNCH, MealPeriodEnum.DINNER):
                existing_snapshot = await session.scalar(
                    select(QueueSnapshot).where(
                        QueueSnapshot.ru_id == restaurant.id,
                        QueueSnapshot.meal_period == meal_period,
                    )
                )

                if existing_snapshot:
                    continue

                snapshot = QueueSnapshot(
                    ru_id=restaurant.id,
                    meal_period=meal_period,
                    current_status=SnapshotStatusEnum.NO_DATA,
                )
                session.add(snapshot)
                snapshots_created += 1

        await session.commit()

        print(
            f"Seed completed. "
            f"{restaurants_created} restaurant(s), {schedules_created} schedule(s) "
            f"and {snapshots_created} snapshot(s) created."
        )


if __name__ == "__main__":
    asyncio.run(seed_restaurants())
