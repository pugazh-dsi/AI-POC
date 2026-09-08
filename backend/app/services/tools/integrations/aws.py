"""AWS integration: S3 storage and CloudWatch metrics.

Demo data today. To go live, swap each function body for the boto3 call named
in its docstring and read credentials from the connector store — nothing else
in the tool path changes.
"""

from datetime import datetime, timedelta, timezone

DEMO_NOTE = (
    "This is DEMO data from a simulated AWS account, not the user's real "
    "infrastructure. Say so when reporting these figures."
)

# One fictional account, shared by both tools so the bucket a user lists is the
# same bucket CloudWatch reports on.
_BUCKETS = [
    {
        "name": "acme-prod-data-lake",
        "region": "us-east-1",
        "created": "2023-02-14",
        "object_count": 1_284_902,
        "size_gb": 4831.7,
        "storage_class": "STANDARD",
        "versioning": "Enabled",
        "public_access_blocked": True,
    },
    {
        "name": "acme-analytics-exports",
        "region": "us-east-1",
        "created": "2023-06-01",
        "object_count": 42_118,
        "size_gb": 312.4,
        "storage_class": "INTELLIGENT_TIERING",
        "versioning": "Enabled",
        "public_access_blocked": True,
    },
    {
        "name": "acme-app-backups",
        "region": "eu-west-1",
        "created": "2022-11-09",
        "object_count": 9_431,
        "size_gb": 1907.2,
        "storage_class": "GLACIER_IR",
        "versioning": "Enabled",
        "public_access_blocked": True,
    },
    {
        "name": "acme-static-assets",
        "region": "ap-south-1",
        "created": "2024-01-22",
        "object_count": 68_240,
        "size_gb": 74.9,
        "storage_class": "STANDARD",
        "versioning": "Suspended",
        "public_access_blocked": False,
    },
]

_OBJECTS = {
    "acme-prod-data-lake": [
        ("raw/events/2026/09/07/part-00000.parquet", 268_435_456, "2026-09-07T23:58:11Z"),
        ("raw/events/2026/09/07/part-00001.parquet", 264_112_003, "2026-09-07T23:58:44Z"),
        ("raw/orders/2026/09/07/orders.snappy.parquet", 91_204_772, "2026-09-08T00:12:07Z"),
        ("curated/customer_360/snapshot.parquet", 1_204_882_311, "2026-09-08T01:30:19Z"),
        ("manifests/_SUCCESS", 0, "2026-09-08T01:31:02Z"),
    ],
    "acme-analytics-exports": [
        ("reports/weekly_revenue_2026-W36.csv", 4_182_004, "2026-09-07T06:00:11Z"),
        ("reports/churn_scores_2026-09.csv", 12_884_910, "2026-09-01T06:00:08Z"),
        ("reports/pipeline_snapshot.json", 882_311, "2026-09-08T06:00:04Z"),
    ],
    "acme-app-backups": [
        ("postgres/2026-09-08/full.dump.gz", 18_884_920_113, "2026-09-08T02:00:00Z"),
        ("postgres/2026-09-07/full.dump.gz", 18_712_004_882, "2026-09-07T02:00:00Z"),
        ("redis/2026-09-08/dump.rdb", 2_004_118_930, "2026-09-08T02:14:00Z"),
    ],
    "acme-static-assets": [
        ("img/hero-desktop.webp", 184_002, "2026-08-19T14:22:10Z"),
        ("img/logo.svg", 6_118, "2026-08-19T14:22:10Z"),
        ("js/app.9f2c1b.js", 1_204_882, "2026-09-05T09:41:55Z"),
    ],
}

# Baseline value + swing per supported CloudWatch metric, used to synthesize a
# plausible series rather than a flat line.
_METRICS = {
    "CPUUtilization": {"namespace": "AWS/EC2", "unit": "Percent", "base": 34.0, "swing": 22.0},
    "MemoryUtilization": {"namespace": "CWAgent", "unit": "Percent", "base": 61.0, "swing": 12.0},
    "NetworkIn": {"namespace": "AWS/EC2", "unit": "Bytes", "base": 84_000_000.0, "swing": 40_000_000.0},
    "Invocations": {"namespace": "AWS/Lambda", "unit": "Count", "base": 1420.0, "swing": 900.0},
    "Errors": {"namespace": "AWS/Lambda", "unit": "Count", "base": 3.0, "swing": 6.0},
    "EstimatedCharges": {"namespace": "AWS/Billing", "unit": "USD", "base": 8412.0, "swing": 260.0},
}


def list_s3_buckets(region: str | None = None) -> dict:
    """S3 buckets in the account. Live equivalent: boto3 s3.list_buckets()."""
    region = (region or "").strip().lower()
    buckets = [b for b in _BUCKETS if not region or b["region"] == region]

    if region and not buckets:
        return {
            "error": f"No buckets found in region '{region}'.",
            "known_regions": sorted({b['region'] for b in _BUCKETS}),
            "demo_data": True,
        }

    return {
        "count": len(buckets),
        "region_filter": region or "all",
        "buckets": buckets,
        "total_size_gb": round(sum(b["size_gb"] for b in buckets), 1),
        "demo_data": True,
        "note": DEMO_NOTE,
    }


def list_s3_objects(bucket: str, prefix: str = "", limit: int = 10) -> dict:
    """Objects in one bucket. Live equivalent: boto3 s3.list_objects_v2()."""
    bucket = (bucket or "").strip()
    if not bucket:
        return {"error": "No bucket name provided.", "demo_data": True}

    if bucket not in _OBJECTS:
        return {
            "error": f"Bucket '{bucket}' does not exist in this account.",
            "available_buckets": list(_OBJECTS),
            "demo_data": True,
        }

    try:
        limit = max(1, min(int(limit or 10), 50))
    except (TypeError, ValueError):
        limit = 10

    prefix = (prefix or "").strip()
    objects = [
        {"key": key, "size_bytes": size, "last_modified": modified}
        for key, size, modified in _OBJECTS[bucket]
        if not prefix or key.startswith(prefix)
    ][:limit]

    return {
        "bucket": bucket,
        "prefix": prefix or "(none)",
        "count": len(objects),
        "objects": objects,
        "demo_data": True,
        "note": DEMO_NOTE,
    }


def get_cloudwatch_metric(
    metric_name: str, resource_id: str = "", hours: int = 24
) -> dict:
    """A CloudWatch metric series. Live equivalent: boto3 cloudwatch.get_metric_statistics()."""
    metric_name = (metric_name or "").strip()
    if not metric_name:
        return {"error": "No metric name provided.", "available_metrics": list(_METRICS), "demo_data": True}

    # Models are loose about casing on enum-ish strings.
    match = next((m for m in _METRICS if m.lower() == metric_name.lower()), None)
    if match is None:
        return {
            "error": f"Metric '{metric_name}' is not collected in this account.",
            "available_metrics": list(_METRICS),
            "demo_data": True,
        }

    try:
        hours = max(1, min(int(hours or 24), 168))
    except (TypeError, ValueError):
        hours = 24

    spec = _METRICS[match]
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    step = max(1, hours // 12)

    datapoints = []
    for i in range(hours, -1, -step):
        stamp = now - timedelta(hours=i)
        # Deterministic pseudo-variation: a daily sine-ish shape without importing numpy.
        phase = ((stamp.hour * 7 + stamp.day * 3) % 24) / 24
        value = spec["base"] + spec["swing"] * (phase - 0.5) * 2
        datapoints.append({
            "timestamp": stamp.isoformat().replace("+00:00", "Z"),
            "average": round(max(value, 0), 2),
        })

    values = [d["average"] for d in datapoints]

    return {
        "metric": match,
        "namespace": spec["namespace"],
        "unit": spec["unit"],
        "resource_id": resource_id or "i-0a1b2c3d4e5f6a7b8",
        "period_hours": hours,
        "datapoint_count": len(datapoints),
        "minimum": min(values),
        "maximum": max(values),
        "average": round(sum(values) / len(values), 2),
        "datapoints": datapoints,
        "demo_data": True,
        "note": DEMO_NOTE,
    }


LIST_BUCKETS_SCHEMA = {
    "name": "aws_list_s3_buckets",
    "description": (
        "List the Amazon S3 buckets in the connected AWS account with their "
        "region, object count and stored size. Use this for questions about S3 "
        "storage, what buckets exist, or how much data is stored."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "region": {
                "type": "string",
                "description": "Optional AWS region filter, e.g. 'us-east-1'. Omit for all regions.",
            },
        },
        "required": [],
    },
}

LIST_OBJECTS_SCHEMA = {
    "name": "aws_list_s3_objects",
    "description": (
        "List objects inside one S3 bucket, with key, size and last-modified "
        "time. Use after aws_list_s3_buckets when the user asks what is stored "
        "in a specific bucket or folder."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "bucket": {"type": "string", "description": "Bucket name, e.g. 'acme-prod-data-lake'."},
            "prefix": {"type": "string", "description": "Optional key prefix to filter by, e.g. 'raw/events/'."},
            "limit": {"type": "integer", "description": "How many objects to return (1-50). Defaults to 10."},
        },
        "required": ["bucket"],
    },
}

CLOUDWATCH_SCHEMA = {
    "name": "aws_cloudwatch_metric",
    "description": (
        "Read an Amazon CloudWatch metric series (CPUUtilization, "
        "MemoryUtilization, NetworkIn, Invocations, Errors, EstimatedCharges) "
        "with its min, max and average over a time window. Use for questions "
        "about AWS performance, errors, load or estimated spend."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "metric_name": {
                "type": "string",
                "enum": list(_METRICS),
                "description": "Which CloudWatch metric to read.",
            },
            "resource_id": {
                "type": "string",
                "description": "Optional instance or function id the metric belongs to.",
            },
            "hours": {
                "type": "integer",
                "description": "How many hours back to look (1-168). Defaults to 24.",
            },
        },
        "required": ["metric_name"],
    },
}
