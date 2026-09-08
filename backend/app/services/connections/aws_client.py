"""
The connected AWS account: credential resolution and the boto3 session.

Credentials come from the encrypted connection store and nowhere else — the
process environment is not consulted, so a stray AWS_ACCESS_KEY_ID on the host
cannot silently point the tools at a different account than the one the UI
shows as connected.

🛡️ Read-only by construction. The only boto3 calls made anywhere in this app
are the list/get calls in `services/tools/integrations/aws.py`; nothing here
creates, deletes or writes. Keep it that way — the account is reached through a
sentence a user typed into a chat box.
"""

from typing import Any, Dict

from app.store.connections_store import AWS_ID, get_connection

DEFAULT_REGION = "us-east-1"

# A connection test or tool call must fail as data, never hang the stream.
CONNECT_TIMEOUT = 5
READ_TIMEOUT = 15


class AwsNotConnected(Exception):
    """No usable AWS account is connected — callers fall back to demo data."""


def _boto3():
    """Import boto3 lazily so the app still runs without the dependency."""
    try:
        import boto3  # noqa: PLC0415 - optional dependency
    except ImportError as e:  # pragma: no cover - depends on the install
        raise AwsNotConnected(
            "boto3 is not installed. Run: pip install -r backend/requirements.txt"
        ) from e
    return boto3


def stored_credentials() -> Dict[str, Any] | None:
    """The connected account's config, or None when there isn't one.

    A disabled connection counts as not connected, which is what makes the
    "Use demo data instead" switch in the UI work without deleting the keys.
    """
    connection = get_connection(AWS_ID)
    if not connection or not connection["enabled"]:
        return None

    config = connection["config"]
    if not config.get("access_key_id") or not config.get("secret_access_key"):
        return None

    return config


def is_live() -> bool:
    """Whether the AWS tools should call the real account rather than the fixture."""
    return stored_credentials() is not None


def get_client(service: str, region: str | None = None):
    """A boto3 client for the connected account.

    Raises AwsNotConnected when there is no account, so every caller has one
    obvious place to fall back to demo data.
    """
    config = stored_credentials()
    if config is None:
        raise AwsNotConnected("No AWS account is connected.")

    boto3 = _boto3()
    from botocore.config import Config  # noqa: PLC0415 - comes with boto3

    return boto3.client(
        service,
        aws_access_key_id=config["access_key_id"],
        aws_secret_access_key=config["secret_access_key"],
        aws_session_token=config.get("session_token") or None,
        region_name=region or config.get("region") or DEFAULT_REGION,
        config=Config(
            connect_timeout=CONNECT_TIMEOUT,
            read_timeout=READ_TIMEOUT,
            retries={"max_attempts": 2},
        ),
    )


def account_region() -> str:
    config = stored_credentials() or {}
    return config.get("region") or DEFAULT_REGION


def test_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate a credential set with a live STS call.

    `sts:GetCallerIdentity` needs no permissions of its own, so it tells us the
    keys are valid without requiring the user to grant anything first. The
    identity it returns is what the UI shows as "connected as".
    """
    boto3 = _boto3()
    from botocore.config import Config  # noqa: PLC0415
    from botocore.exceptions import BotoCoreError, ClientError  # noqa: PLC0415

    client = boto3.client(
        "sts",
        aws_access_key_id=config.get("access_key_id"),
        aws_secret_access_key=config.get("secret_access_key"),
        aws_session_token=config.get("session_token") or None,
        region_name=config.get("region") or DEFAULT_REGION,
        config=Config(connect_timeout=CONNECT_TIMEOUT, read_timeout=READ_TIMEOUT,
                      retries={"max_attempts": 1}),
    )

    try:
        identity = client.get_caller_identity()
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        message = e.response.get("Error", {}).get("Message", str(e))
        if code in ("InvalidClientTokenId", "SignatureDoesNotMatch", "AuthFailure"):
            message = "Those credentials were rejected by AWS. Check the access key and secret."
        elif code == "ExpiredToken":
            message = "The session token has expired. Paste a fresh one."
        raise ValueError(message) from e
    except BotoCoreError as e:
        raise ValueError(f"Could not reach AWS: {e}") from e

    return {
        "ok": True,
        "account": identity.get("Account", ""),
        "arn": identity.get("Arn", ""),
        "user_id": identity.get("UserId", ""),
        "region": config.get("region") or DEFAULT_REGION,
    }
