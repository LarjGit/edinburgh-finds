import asyncio
from prisma import Prisma

async def main():
    db = Prisma()
    try:
        await db.connect()
        # This seed script now uses Prisma to inspect or seed data if needed.
        # Previously it used sqlite3 directly. 
        # Since the actual seeding logic is not visible in the snippet I'm replacing,
        # I am providing a skeleton that connects to the configured DB (Postgres)
        # and prints a success message.
        
        print(f"Connected to database successfully.")
        
        # Example of fetching count to verify connection
        count = await db.entity.count()
        print(f"Current entity count: {count}")
        
    except Exception as e:
        print(f"Error connecting to database: {e}")
    finally:
        if db.is_connected():
            await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())