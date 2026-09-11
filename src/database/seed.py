import asyncio

from sqlalchemy import select

from database.models.accounts import UserGroup, UserGroupEnum
from database.session import AsyncSessionLocal


async def seed_user_groups() -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(UserGroup.name))
        existing = {row[0] for row in result.all()}

        missing = [
            UserGroup(name=g.value) for g in UserGroupEnum if g.value not in existing
        ]

        if not missing:
            print("User groups already seeded, nothing to do.")
            return

        session.add_all(missing)
        await session.commit()
        print(f"Seeded {len(missing)} user group(s): {[g.name for g in missing]}")


if __name__ == "__main__":
    asyncio.run(seed_user_groups())
