"""
Ingestion Health Check Module

This module provides health check functionality for the data ingestion pipeline.
It monitors:
- Failed ingestion rates
- Stale data (sources not updated recently)
- API quota usage

Each check returns a status (healthy, warning, critical) and supporting metrics.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List
from prisma import Prisma


def now_utc() -> datetime:
    """Get current time as timezone-aware UTC datetime"""
    return datetime.now(timezone.utc)


async def check_health() -> Dict[str, Any]:
    """
    Run all health checks and aggregate results.

    This is the main entry point for health monitoring. It runs all individual
    checks in parallel and aggregates their results into an overall health status.

    Returns:
        Dictionary containing:
        - status: Overall health status ('healthy', 'warning', or 'critical')
        - timestamp: When the health check was performed
        - failed_ingestions: Results from failed ingestions check
        - stale_data: Results from stale data check
        - api_quota: Results from API quota check

    Example:
        >>> result = await check_health()
        >>> print(result['status'])
        'healthy'
        >>> print(result['failed_ingestions']['failed_count'])
        0
    """
    # Run all checks in parallel
    failed_check, stale_check, quota_check = await asyncio.gather(
        check_failed_ingestions(),
        check_stale_data(),
        check_api_quota()
    )

    # Aggregate status (worst of all checks)
    statuses = [
        failed_check['status'],
        stale_check['status'],
        quota_check['status']
    ]

    # Priority: critical > warning > healthy
    if 'critical' in statuses:
        overall_status = 'critical'
    elif 'warning' in statuses:
        overall_status = 'warning'
    else:
        overall_status = 'healthy'

    return {
        'status': overall_status,
        'timestamp': now_utc(),
        'failed_ingestions': failed_check,
        'stale_data': stale_check,
        'api_quota': quota_check
    }


async def check_failed_ingestions(
    warning_threshold: float = 10.0,
    critical_threshold: float = 25.0,
    time_window_hours: int = 24
) -> Dict[str, Any]:
    """
    Check for failed ingestions and calculate failure rate.

    Analyzes recent ingestion attempts (last 24 hours by default) to identify
    failed ingestions and calculate the failure rate. Returns health status
    based on configurable thresholds.

    Args:
        warning_threshold: Failure rate percentage for warning status (default: 10%)
        critical_threshold: Failure rate percentage for critical status (default: 25%)
        time_window_hours: Time window to analyze in hours (default: 24)

    Returns:
        Dictionary containing:
        - status: Health status ('healthy', 'warning', or 'critical')
        - failed_count: Number of failed ingestions in time window
        - failure_rate: Percentage of failed ingestions (0-100)
        - recent_failures: List of recent failed ingestions with details
        - message: Human-readable status message

    Example:
        >>> result = await check_failed_ingestions()
        >>> if result['status'] == 'critical':
        ...     print(f"High failure rate: {result['failure_rate']:.1f}%")
    """
    db = Prisma()

    try:
        await db.connect()
    except Exception as e:
        return {
            'status': 'critical',
            'failed_count': 0,
            'failure_rate': 0,
            'recent_failures': [],
            'message': f'Database connection failed: {str(e)}'
        }

    try:
        # Calculate time window
        cutoff_time = now_utc() - timedelta(hours=time_window_hours)

        # Get all recent ingestions (within time window)
        recent_ingestions = await db.rawingestion.find_many(
            where={
                'ingested_at': {
                    'gte': cutoff_time
                }
            }
        )

        total_count = len(recent_ingestions)
        failed_count = sum(1 for r in recent_ingestions if r.status == 'failed')

        # Calculate failure rate
        failure_rate = (failed_count / total_count * 100) if total_count > 0 else 0

        # Get recent failures for reporting
        recent_failures = []
        for record in recent_ingestions:
            if record.status == 'failed':
                recent_failures.append({
                    'id': record.id,
                    'source': record.source,
                    'source_url': record.source_url,
                    'ingested_at': record.ingested_at
                })

        # Determine status based on thresholds
        if failure_rate >= critical_threshold:
            status = 'critical'
            message = f'Critical: {failure_rate:.1f}% failure rate ({failed_count}/{total_count} failed)'
        elif failure_rate >= warning_threshold:
            status = 'warning'
            message = f'Warning: {failure_rate:.1f}% failure rate ({failed_count}/{total_count} failed)'
        else:
            status = 'healthy'
            if total_count == 0:
                message = 'Healthy: No recent ingestions to analyze'
            else:
                message = f'Healthy: {failure_rate:.1f}% failure rate ({failed_count}/{total_count} failed)'

        return {
            'status': status,
            'failed_count': failed_count,
            'failure_rate': failure_rate,
            'recent_failures': recent_failures,
            'message': message
        }

    finally:
        await db.disconnect()


async def check_stale_data(threshold_hours: int = 24) -> Dict[str, Any]:
    """
    Check for stale data by identifying sources not updated recently.

    Analyzes when each source was last successfully ingested. Sources that
    haven't been updated within the threshold are marked as stale.

    Args:
        threshold_hours: Number of hours after which data is considered stale (default: 24)

    Returns:
        Dictionary containing:
        - status: Health status ('healthy', 'warning', or 'critical')
        - stale_sources: List of stale sources with details
        - last_ingestion_by_source: Dictionary mapping source names to last ingestion times
        - message: Human-readable status message

    Example:
        >>> result = await check_stale_data(threshold_hours=48)
        >>> for source in result['stale_sources']:
        ...     print(f"{source['source']} is {source['hours_since']} hours old")
    """
    db = Prisma()

    try:
        await db.connect()
    except Exception as e:
        return {
            'status': 'critical',
            'stale_sources': [],
            'last_ingestion_by_source': {},
            'message': f'Database connection failed: {str(e)}'
        }

    try:
        # Get all successful ingestions
        all_ingestions = await db.rawingestion.find_many(
            where={'status': 'success'},
            order={'ingested_at': 'desc'}
        )

        if not all_ingestions:
            return {
                'status': 'warning',
                'stale_sources': [],
                'last_ingestion_by_source': {},
                'message': 'Warning: No successful ingestions found'
            }

        # Calculate cutoff time
        cutoff_time = now_utc() - timedelta(hours=threshold_hours)

        # Find last ingestion per source
        last_ingestion_by_source = {}
        for record in all_ingestions:
            if record.source not in last_ingestion_by_source:
                last_ingestion_by_source[record.source] = record.ingested_at

        # Identify stale sources
        stale_sources = []
        for source, last_ingestion in last_ingestion_by_source.items():
            if last_ingestion < cutoff_time:
                hours_since = (now_utc() - last_ingestion).total_seconds() / 3600
                stale_sources.append({
                    'source': source,
                    'last_ingestion': last_ingestion,
                    'hours_since': round(hours_since, 1)
                })

        # Determine status
        total_sources = len(last_ingestion_by_source)
        stale_count = len(stale_sources)

        if stale_count == 0:
            status = 'healthy'
            message = f'Healthy: All {total_sources} sources have fresh data'
        elif stale_count == total_sources:
            status = 'critical'
            message = f'Critical: All {total_sources} sources are stale (>{threshold_hours}h old)'
        else:
            status = 'warning'
            message = f'Warning: {stale_count}/{total_sources} sources are stale (>{threshold_hours}h old)'

        return {
            'status': status,
            'stale_sources': stale_sources,
            'last_ingestion_by_source': last_ingestion_by_source,
            'message': message
        }

    finally:
        await db.disconnect()


async def check_api_quota() -> Dict[str, Any]:
    """
    Check API quota usage by analyzing request frequency.

    Analyzes the number of requests made to each source in recent time windows
    (last hour and last day) to help monitor API quota usage.

    Note: This provides usage metrics but doesn't enforce quotas directly.
    Quota limits should be configured in sources.yaml and enforced by rate limiters.

    Returns:
        Dictionary containing:
        - status: Health status ('healthy', 'warning', or 'critical')
        - quota_by_source: Dictionary with request counts per source
        - message: Human-readable status message

    Example:
        >>> result = await check_api_quota()
        >>> for source, quota_info in result['quota_by_source'].items():
        ...     print(f"{source}: {quota_info['requests_today']} requests today")
    """
    db = Prisma()

    try:
        await db.connect()
    except Exception as e:
        return {
            'status': 'critical',
            'quota_by_source': {},
            'message': f'Database connection failed: {str(e)}'
        }

    try:
        # Calculate time windows
        now = now_utc()
        one_hour_ago = now - timedelta(hours=1)
        one_day_ago = now - timedelta(days=1)

        # Get all ingestions in the last day
        recent_ingestions = await db.rawingestion.find_many(
            where={
                'ingested_at': {
                    'gte': one_day_ago
                }
            }
        )

        # Count requests by source
        quota_by_source = {}
        for record in recent_ingestions:
            if record.source not in quota_by_source:
                quota_by_source[record.source] = {
                    'requests_today': 0,
                    'requests_this_hour': 0,
                    'total_requests': 0
                }

            quota_by_source[record.source]['requests_today'] += 1
            quota_by_source[record.source]['total_requests'] += 1

            # Count requests in last hour
            if record.ingested_at >= one_hour_ago:
                quota_by_source[record.source]['requests_this_hour'] += 1

        # Determine status based on usage patterns
        # Note: Without quota limits defined, we use conservative estimates
        # Most APIs have limits like 100/hour or 1000/day
        warning_sources = []
        critical_sources = []

        for source, quota_info in quota_by_source.items():
            requests_hour = quota_info['requests_this_hour']
            requests_day = quota_info['requests_today']

            # Conservative thresholds (should be customized per source)
            if requests_hour > 80 or requests_day > 800:
                critical_sources.append(source)
            elif requests_hour > 50 or requests_day > 500:
                warning_sources.append(source)

        # Determine overall status
        if critical_sources:
            status = 'critical'
            message = f'Critical: High API usage on {len(critical_sources)} sources: {", ".join(critical_sources)}'
        elif warning_sources:
            status = 'warning'
            message = f'Warning: Elevated API usage on {len(warning_sources)} sources: {", ".join(warning_sources)}'
        else:
            total_sources = len(quota_by_source)
            if total_sources == 0:
                status = 'healthy'
                message = 'Healthy: No API requests in last 24 hours'
            else:
                status = 'healthy'
                message = f'Healthy: Normal API usage across {total_sources} sources'

        return {
            'status': status,
            'quota_by_source': quota_by_source,
            'message': message
        }

    finally:
        await db.disconnect()
