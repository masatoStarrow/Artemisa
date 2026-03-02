"""
Seed script: populate initial users synchronized with the Gateway.
Run with: python -m src.infrastructure.scripts.seed_users
"""

import asyncio
import uuid

from src.infrastructure.database.connection import AsyncSessionLocal, engine, Base
from src.adapters.outbound.persistence.models.user_model import UserModel

# Same users as the Gateway's seed_users command
SEED_USERS = [
    {
        "email": "admin@crm.com",
        "full_name": "Administrador CRM",
        "role": "admin",
    },
    {
        "email": "soporte@crm.com",
        "full_name": "Agente Soporte",
        "role": "soporte",
    },
    {
        "email": "comercial@crm.com",
        "full_name": "Agente Comercial",
        "role": "comercial",
    },
]


async def seed():
    from sqlalchemy import select

    async with AsyncSessionLocal() as session:
        for user_data in SEED_USERS:
            stmt = select(UserModel).where(UserModel.email == user_data["email"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                print(f"User already exists: {user_data['email']}")
                continue

            model = UserModel(
                id=uuid.uuid4(),
                email=user_data["email"],
                full_name=user_data["full_name"],
                role=user_data["role"],
            )
            session.add(model)
            print(f"Created user: {user_data['email']} ({user_data['role']})")

        await session.commit()
    print("Seed completed!")


def main():
    asyncio.run(seed())


if __name__ == "__main__":
    main()
