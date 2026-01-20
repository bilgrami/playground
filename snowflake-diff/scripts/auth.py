"""
auth
====

SnowCLI execution helpers.

This module is responsible for invoking Snowflake CLI (`snow sql`) using a
**connection name** (as defined in your SnowCLI configuration, often stored in
a ``snow.toml`` file).

The rest of the codebase treats Snowflake access as a pure function:

- input: :class:`~scripts.auth.SnowTarget` + SQL
- output: TSV text (or an ``__ERROR__`` sentinel)

This keeps collection logic testable and centralized.

Sphinx
------
You can document this module with Sphinx autodoc. See README for a minimal
``docs/index.rst`` example.

"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class SnowTarget:
    """Snowflake target configuration for SnowCLI.

    Parameters
    ----------
    connection:
        SnowCLI connection name (e.g., "dev", "prod"), configured in SnowCLI.
    role:
        Role to use for the session.
    warehouse:
        Warehouse to use for the session.
    database:
        Database to use for the session.
    schema:
        Schema to use for the session.
    label:
        Human label for logs and reporting (e.g., "left" or "right").
    """

    connection: str
    role: str
    warehouse: str
    database: str
    schema: str
    label: str


def ensure_snowcli() -> None:
    """Ensure the `snow` executable exists on PATH.

    Raises
    ------
    SystemExit
        If SnowCLI (`snow`) is not found.
    """
    if shutil.which("snow") is None:
        raise SystemExit(
            "ERROR: `snow` CLI not found in PATH. Install SnowCLI and ensure `snow sql` works."
        )


DEFAULT_TIMEOUT_SECONDS = 300  # 5 minutes


def run_sql(target: SnowTarget, query: str, timeout: int | None = None) -> str:
    """Run a SQL query via SnowCLI and return TSV output.

    The command is executed with:

    - ``--connection <name>``
    - role/warehouse/database/schema overrides
    - ``--format tsv --header false`` for stable diffs

    Parameters
    ----------
    target:
        The Snowflake target describing connection and namespace.
    query:
        SQL string to execute.
    timeout:
        Maximum time in seconds to wait for the query. Defaults to 300 seconds.
        Set to None for no timeout (not recommended for production).

    Returns
    -------
    str
        TSV output as text with normalized newlines. If the SnowCLI command fails,
        a sentinel string starting with ``__ERROR__`` is returned containing the
        exit code and stderr. If the command times out, an ``__ERROR__`` sentinel
        with ``TIMEOUT`` is returned.

    Notes
    -----
    If your SnowCLI uses a different flag name than ``--connection``, update the
    command list below (single place change).
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT_SECONDS

    cmd = [
        "snow",
        "sql",
        "--connection",
        target.connection,
        "--role",
        target.role,
        "--warehouse",
        target.warehouse,
        "--database",
        target.database,
        "--schema",
        target.schema,
        "--query",
        query,
        "--format",
        "tsv",
        "--header",
        "false",
    ]

    try:
        proc = subprocess.run(
            cmd, check=False, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return f"__ERROR__\tTIMEOUT\tQuery timed out after {timeout} seconds\n"

    if proc.returncode != 0:
        return f"__ERROR__\t{proc.returncode}\t{(proc.stderr or '').strip()}\n"

    return (proc.stdout or "").replace("\r\n", "\n").replace("\r", "\n")


def connection_test(target: SnowTarget) -> tuple[bool, str]:
    """Perform a lightweight connectivity test.

    Parameters
    ----------
    target:
        Target to test.

    Returns
    -------
    tuple[bool, str]
        ``(ok, message)`` where message is TSV output (or the error sentinel).
    """
    out = run_sql(
        target,
        "SELECT CURRENT_ACCOUNT(), CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE(), CURRENT_SCHEMA();",
    )
    if out.startswith("__ERROR__"):
        return False, out.strip()
    return True, out.strip()
