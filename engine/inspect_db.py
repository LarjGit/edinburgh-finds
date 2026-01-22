import asyncio
from prisma import Prisma

async def main():
    """
    Inspect the database schema and table names.
    Replaces legacy sqlite3 inspection.
    """
    db = Prisma()
    try:
        await db.connect()
        print("Connected to PostgreSQL via Prisma.")
        
        # Prisma Client doesn't expose raw table inspection easily without raw queries,
        # but we can check if we can query the main table.
        try:
            count = await db.entity.count()
            print(f"Table 'Entity' is accessible. Row count: {count}")
        except Exception as exc:
            print(f"Could not access 'Entity' table: {exc}")

    except Exception as e:
        print(f"Database connection error: {e}")
    finally:
        if db.is_connected():
            await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())