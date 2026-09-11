from sqlalchemy.ext.asyncio import AsyncSession
from database.database import init_db
from database.seed import seed_database
from sqlalchemy import select
from models.flight import Flight
import asyncio

async def run_initialization():
    print("--- Initializing Database ---")
    await init_db()

    print("--- Seeding Database ---")
    # We need an async session for seeding
    from database.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        counts = await seed_database(session)
        print(f"Seeded: {counts}")

    print("--- Verifying Data ---")
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Flight).limit(5))
        flights = result.scalars().all()
        for f in flights:
            print(f"Flight: {f.flight_number} | {f.origin} -> {f.destination} | {f.airline}")

if __name__ == "__main__":
    asyncio.run(run_initialization())
