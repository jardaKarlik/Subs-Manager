-- Railway Database Investigation Queries
-- Run these in: railway connect postgres

-- ============================================================
-- 1. TABLE ROW COUNTS
-- ============================================================
SELECT 'subscriptions' AS table_name, COUNT(*) AS row_count FROM subscriptions
UNION ALL
SELECT 'processed_emails', COUNT(*) FROM processed_emails
UNION ALL
SELECT 'subscription_events', COUNT(*) FROM subscription_events;

-- Expected:
-- subscriptions: 14 (current) → should increase after fix
-- processed_emails: 0 (suspected) → should be 17,510
-- subscription_events: ? (unknown) → should match subscriptions

-- ============================================================
-- 2. TABLE SIZES (STORAGE)
-- ============================================================
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- This shows actual disk usage
-- If processed_emails is 0 bytes → confirms empty table

-- ============================================================
-- 3. INSPECT EXISTING 14 SUBSCRIPTIONS
-- ============================================================
SELECT 
    id,
    service_name,
    cost,
    currency,
    billing_cycle,
    source,
    start_date,
    notes,
    created_at
FROM subscriptions
ORDER BY created_at DESC;

-- Look for:
-- - source column: "manual" vs "gmail" vs "outlook"
-- - created_at: when were they added?
-- - notes: is plan info populated?

-- ============================================================
-- 4. CHECK ProcessedEmail TABLE DETAILS
-- ============================================================
SELECT 
    source,
    COUNT(*) AS count,
    MIN(processed_date) AS first_processed,
    MAX(processed_date) AS last_processed
FROM processed_emails
GROUP BY source;

-- Expected if bug:
-- (no rows returned)

-- Expected if working:
-- gmail    | 7000 | 2026-05-15 | 2026-05-15
-- outlook  | 10510 | 2026-05-15 | 2026-05-15

-- ============================================================
-- 5. CHECK SUBSCRIPTION EVENTS
-- ============================================================
SELECT 
    COUNT(*) AS total_events,
    COUNT(DISTINCT subscription_id) AS unique_subscriptions,
    COUNT(DISTINCT message_id) AS unique_emails,
    MIN(event_date) AS earliest_event,
    MAX(event_date) AS latest_event
FROM subscription_events;

-- This shows:
-- - How many payment events exist
-- - How many unique subscriptions have events
-- - Date range of events

-- ============================================================
-- 6. CHECK FOR ORPHANED EVENTS
-- ============================================================
SELECT 
    se.subscription_id,
    se.service_name,
    se.amount,
    se.currency,
    se.event_date,
    s.id AS sub_exists
FROM subscription_events se
LEFT JOIN subscriptions s ON se.subscription_id = s.id
WHERE s.id IS NULL
LIMIT 10;

-- This finds events that point to non-existent subscriptions
-- Should return 0 rows if data is consistent

-- ============================================================
-- 7. SUBSCRIPTION SOURCES BREAKDOWN
-- ============================================================
SELECT 
    source,
    status,
    COUNT(*) AS count,
    SUM(cost) AS total_cost
FROM subscriptions
GROUP BY source, status
ORDER BY source, status;

-- Shows:
-- - How many subscriptions from each source
-- - Active vs cancelled breakdown
-- - Total cost per source

-- ============================================================
-- 8. CHECK FOR RECENT ACTIVITY
-- ============================================================
SELECT 
    'subscriptions' AS table_name,
    MAX(created_at) AS last_created,
    MAX(updated_at) AS last_updated
FROM subscriptions
UNION ALL
SELECT 
    'processed_emails',
    MAX(processed_date),
    MAX(processed_date)
FROM processed_emails;

-- This shows when data was last touched
-- If processed_emails is NULL → empty table confirmed

-- ============================================================
-- 9. SAMPLE DATA FROM SUBSCRIPTIONS
-- ============================================================
SELECT 
    service_name,
    category,
    cost || ' ' || currency AS price,
    billing_cycle,
    status,
    source
FROM subscriptions
LIMIT 5;

-- Quick look at what's in the database

-- ============================================================
-- 10. CHECK FOR DUPLICATE SERVICE NAMES
-- ============================================================
SELECT 
    service_name,
    COUNT(*) AS count
FROM subscriptions
GROUP BY service_name
HAVING COUNT(*) > 1;

-- Multiple entries for same service might indicate:
-- - Deduplication not working
-- - Multiple plans/variants
-- - Test data

-- ============================================================
-- DIAGNOSTIC SUMMARY QUERY
-- ============================================================
WITH counts AS (
    SELECT 
        (SELECT COUNT(*) FROM subscriptions) AS subs,
        (SELECT COUNT(*) FROM processed_emails) AS emails,
        (SELECT COUNT(*) FROM subscription_events) AS events
)
SELECT 
    subs AS subscriptions,
    emails AS processed_emails,
    events AS events,
    CASE 
        WHEN emails = 0 THEN '🔴 CRITICAL: ProcessedEmail table is empty'
        WHEN emails < 100 THEN '🟡 WARNING: Very few emails processed'
        ELSE '✅ OK: Emails are being tracked'
    END AS processed_emails_status,
    CASE
        WHEN subs = 0 AND events > 0 THEN '🔴 CRITICAL: Orphaned events exist'
        WHEN subs < (events / 10) THEN '🟡 WARNING: More events than expected'
        ELSE '✅ OK: Event count looks normal'
    END AS events_status
FROM counts;

-- ============================================================
-- RECOMMENDED EXECUTION ORDER:
-- ============================================================
-- 1. Run query #1 (table counts) first
-- 2. If processed_emails = 0, run query #8 to confirm
-- 3. Run query #3 to understand the 14 subscriptions
-- 4. Run query #5 to check events
-- 5. Run query #11 (diagnostic summary) for overall health
