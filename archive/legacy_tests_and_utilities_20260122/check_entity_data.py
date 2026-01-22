#!/usr/bin/env python3
"""Check Entity table data"""
import asyncio
from prisma import Prisma

async def main():
    db = Prisma()
    await db.connect()

    count = await db.entity.count()
    print(f'Total Entity records: {count}')

    if count > 0:
        # Count by entity_class
        entities = await db.entity.find_many(take=5)
        print('\nSample entities:')
        for e in entities:
            print(f'  {e.entity_name} (class: {e.entity_class}, roles: {e.canonical_roles})')

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
