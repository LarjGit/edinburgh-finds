#!/usr/bin/env python3
"""Check available raw ingestion data for testing"""
import asyncio
from prisma import Prisma

async def main():
    db = Prisma()
    await db.connect()

    count = await db.rawingestion.count()
    print(f'Total RawIngestion records: {count}')

    if count > 0:
        sources = await db.rawingestion.group_by(['source'], _count=True)
        print('\nBy source:')
        for s in sources:
            print(f'  {s["source"]}: {s["_count"]}')

        # Get one sample record
        sample = await db.rawingestion.find_first()
        if sample:
            print(f'\nSample record ID: {sample.id}')
            print(f'  Source: {sample.source}')
            print(f'  Extracted: {sample.extracted}')

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
