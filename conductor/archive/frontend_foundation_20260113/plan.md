# Track Plan: Frontend Foundation

## Phase 1: Data Verification
- [x] Task: Confirm database connectivity and data existence. [verified_count_1]
    - **Action:** Run a script to count rows in `Listing` table.
    - **Action:** If count is 0, run `python engine/run_seed.py`.

## Phase 2: Application Plumbing
- [x] Task: Configure Prisma Client Singleton. [implemented]
    - **Action:** Create `web/lib/prisma.ts` to handle the `PrismaClient` instance (preventing connection limits in HMR).
    - **Reference:** Standard Next.js + Prisma best practice.

## Phase 3: "Hello World" Display
- [x] Task: Connect Home Page to Database. [implemented]
    - **Action:** Modify `web/app/page.tsx` to be an `async` Server Component.
    - **Action:** Fetch `prisma.listing.findMany({ take: 5 })`.
    - **Action:** Render a simple `<ul>` of listing names.
    - **Goal:** Verify end-to-end data flow (DB -> Prisma -> Next.js -> Browser).

## Phase 4: Verification
- [x] Task: User Manual Verification. [verified]
    - **Check:** User opens `http://localhost:3000` and sees listing names.
