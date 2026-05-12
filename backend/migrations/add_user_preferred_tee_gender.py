import asyncio, sys, os
sys.path.insert(0, '/app')
from app.database import engine
from sqlalchemy import text

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE users ADD COLUMN preferred_tee_gender VARCHAR(10) NULL"
        ))
    print("Migration complete: users.preferred_tee_gender added")

asyncio.run(migrate())
