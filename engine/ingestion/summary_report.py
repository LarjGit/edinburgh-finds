"""
Ingestion Summary Report Module

This module provides comprehensive summary reports for the data ingestion pipeline.
It aggregates statistics, error analysis, and health status into a single report
suitable for monitoring, debugging, and operational insights.

The report includes:
- Overview: Total records, success rate, date range, source count
- By Source: Per-source statistics and success rates
- Errors: Error analysis with recent failures
- Health: Integration with health check module

Reports can be generated programmatically or displayed via CLI.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from prisma import Prisma

from engine.ingestion.health_check import check_health


def now_utc() -> datetime:
    """Get current time as timezone-aware UTC datetime"""
    return datetime.now(timezone.utc)


async def get_summary_data() -> Dict[str, Any]:
    """
    Get comprehensive summary data from the database.

    This is the core data collection function that gathers all statistics
    needed for the summary report. It queries the RawIngestion table and
    aggregates data across multiple dimensions.

    Returns:
        Dictionary containing:
        - overview: Overall statistics
        - by_source: Per-source breakdown
        - errors: Error analysis
        - health: Health status from health check module

    Example:
        >>> data = await get_summary_data()
        >>> print(f"Total records: {data['overview']['total_records']}")
        >>> print(f"Success rate: {data['overview']['success_rate']:.1f}%")
    """
    db = Prisma()

    try:
        await db.connect()
    except Exception as e:
        # Return empty structure if connection fails
        return {
            'overview': {
                'total_records': 0,
                'success_rate': 0,
                'total_sources': 0,
                'first_ingestion': None,
                'last_ingestion': None
            },
            'by_source': {},
            'errors': {
                'total_errors': 0,
                'recent_errors': [],
                'by_source': {}
            },
            'health': {
                'status': 'critical',
                'failed_ingestions': {},
                'stale_data': {},
                'api_quota': {}
            }
        }

    try:
        # Get all ingestion records
        all_records = await db.rawingestion.find_many(
            order={'ingested_at': 'asc'}
        )

        total_records = len(all_records)

        # Calculate overview statistics
        if total_records > 0:
            first_ingestion = all_records[0].ingested_at
            last_ingestion = all_records[-1].ingested_at

            # Count successes and failures
            success_count = sum(1 for r in all_records if r.status == 'success')
            failed_count = sum(1 for r in all_records if r.status == 'failed')
            success_rate = (success_count / total_records * 100) if total_records > 0 else 0

            # Get unique sources
            sources = set(r.source for r in all_records)
            total_sources = len(sources)
        else:
            first_ingestion = None
            last_ingestion = None
            success_rate = 0
            total_sources = 0
            success_count = 0
            failed_count = 0

        # Build per-source statistics
        by_source = {}
        for record in all_records:
            source = record.source

            if source not in by_source:
                by_source[source] = {
                    'total': 0,
                    'success': 0,
                    'failed': 0,
                    'success_rate': 0,
                    'last_ingestion': None
                }

            by_source[source]['total'] += 1

            if record.status == 'success':
                by_source[source]['success'] += 1
            elif record.status == 'failed':
                by_source[source]['failed'] += 1

            # Track last ingestion time
            if by_source[source]['last_ingestion'] is None or \
               record.ingested_at > by_source[source]['last_ingestion']:
                by_source[source]['last_ingestion'] = record.ingested_at

        # Calculate success rates per source
        for source, data in by_source.items():
            if data['total'] > 0:
                data['success_rate'] = (data['success'] / data['total'] * 100)

        # Gather error information
        failed_records = [r for r in all_records if r.status == 'failed']
        total_errors = len(failed_records)

        # Get recent errors (last 10)
        recent_errors = []
        for record in sorted(failed_records, key=lambda x: x.ingested_at, reverse=True)[:10]:
            recent_errors.append({
                'id': record.id,
                'source': record.source,
                'source_url': record.source_url,
                'ingested_at': record.ingested_at
            })

        # Count errors by source
        errors_by_source = {}
        for record in failed_records:
            if record.source not in errors_by_source:
                errors_by_source[record.source] = 0
            errors_by_source[record.source] += 1

        # Get health status
        health_data = await check_health()

        return {
            'overview': {
                'total_records': total_records,
                'success_rate': success_rate,
                'total_sources': total_sources,
                'first_ingestion': first_ingestion,
                'last_ingestion': last_ingestion,
                'success_count': success_count,
                'failed_count': failed_count
            },
            'by_source': by_source,
            'errors': {
                'total_errors': total_errors,
                'recent_errors': recent_errors,
                'by_source': errors_by_source
            },
            'health': {
                'status': health_data['status'],
                'failed_ingestions': health_data['failed_ingestions'],
                'stale_data': health_data['stale_data'],
                'api_quota': health_data['api_quota']
            }
        }

    finally:
        await db.disconnect()


async def generate_summary_report() -> Dict[str, Any]:
    """
    Generate a complete ingestion summary report.

    This is the main entry point for generating summary reports. It collects
    all data and adds a generation timestamp.

    Returns:
        Dictionary containing:
        - generated_at: When the report was generated
        - overview: Overall statistics
        - by_source: Per-source breakdown
        - errors: Error analysis
        - health: Health status

    Example:
        >>> report = await generate_summary_report()
        >>> print(f"Report generated at: {report['generated_at']}")
        >>> print(f"Overall status: {report['health']['status']}")
    """
    data = await get_summary_data()

    # Add generation timestamp
    report = {
        'generated_at': now_utc(),
        **data
    }

    return report


def format_summary_report(report: Dict[str, Any]) -> str:
    """
    Format a summary report for display.

    Converts the report dictionary into a human-readable string format
    suitable for console output or log files.

    Args:
        report: Report dictionary from generate_summary_report()

    Returns:
        Formatted string representation of the report

    Example:
        >>> report = await generate_summary_report()
        >>> formatted = format_summary_report(report)
        >>> print(formatted)
    """
    lines = []
    lines.append("=" * 80)
    lines.append("INGESTION SUMMARY REPORT")
    lines.append("=" * 80)
    lines.append("")

    # Generation time
    generated_at = report['generated_at'].strftime('%Y-%m-%d %H:%M:%S UTC')
    lines.append(f"Generated: {generated_at}")
    lines.append("")

    # Overview section
    lines.append("OVERVIEW")
    lines.append("-" * 80)
    overview = report['overview']
    lines.append(f"  Total Records:      {overview['total_records']:,}")
    lines.append(f"  Success Rate:       {overview['success_rate']:.1f}%")
    lines.append(f"  Successful:         {overview.get('success_count', 0):,}")
    lines.append(f"  Failed:             {overview.get('failed_count', 0):,}")
    lines.append(f"  Total Sources:      {overview['total_sources']}")

    if overview['first_ingestion']:
        first = overview['first_ingestion'].strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"  First Ingestion:    {first}")
    if overview['last_ingestion']:
        last = overview['last_ingestion'].strftime('%Y-%m-%d %H:%M:%S')
        lines.append(f"  Last Ingestion:     {last}")
    lines.append("")

    # Health status section
    lines.append("HEALTH STATUS")
    lines.append("-" * 80)
    health = report['health']
    status_symbol = {
        'healthy': '✓',
        'warning': '⚠',
        'critical': '✗'
    }.get(health['status'], '?')

    lines.append(f"  Overall Status:     {status_symbol} {health['status'].upper()}")
    lines.append(f"  Failed Ingestions:  {health['failed_ingestions']['status']}")
    lines.append(f"  Stale Data:         {health['stale_data']['status']}")
    lines.append(f"  API Quota:          {health['api_quota']['status']}")
    lines.append("")

    # By source section
    lines.append("BY SOURCE")
    lines.append("-" * 80)
    if report['by_source']:
        # Sort by total count (descending)
        sorted_sources = sorted(
            report['by_source'].items(),
            key=lambda x: x[1]['total'],
            reverse=True
        )

        for source, data in sorted_sources:
            lines.append(f"  {source}")
            lines.append(f"    Total:        {data['total']:,}")
            lines.append(f"    Success:      {data['success']:,} ({data['success_rate']:.1f}%)")
            lines.append(f"    Failed:       {data['failed']:,}")

            if data['last_ingestion']:
                last = data['last_ingestion'].strftime('%Y-%m-%d %H:%M:%S')
                lines.append(f"    Last:         {last}")
            lines.append("")
    else:
        lines.append("  No sources yet")
        lines.append("")

    # Errors section
    lines.append("ERROR ANALYSIS")
    lines.append("-" * 80)
    errors = report['errors']
    lines.append(f"  Total Errors:       {errors['total_errors']:,}")

    if errors['by_source']:
        lines.append("  Errors by Source:")
        sorted_error_sources = sorted(
            errors['by_source'].items(),
            key=lambda x: x[1],
            reverse=True
        )
        for source, count in sorted_error_sources:
            lines.append(f"    {source:20s} {count:,}")
    lines.append("")

    if errors['recent_errors']:
        lines.append("  Recent Errors (Last 10):")
        for error in errors['recent_errors']:
            timestamp = error['ingested_at'].strftime('%Y-%m-%d %H:%M:%S')
            url = error['source_url']
            if len(url) > 50:
                url = url[:47] + '...'
            lines.append(f"    ✗ {timestamp}  {error['source']:15s} {url}")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)
