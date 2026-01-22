import asyncio
from prisma import Prisma

async def main():
    """
    Check data integrity in the database.
    """
    db = Prisma()
    try:
        await db.connect()
        print("Checking Entity data...")
        
        entities = await db.entity.find_many(take=5)
        for entity in entities:
            print(f"ID: {entity.id}, Name: {entity.entity_name}, Class: {entity.entity_class}")
            
    except Exception as e:
        print(f"Error checking data: {e}")
    finally:
        if db.is_connected():
            await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())