# Architecture

This document describes the architecture of the Snowflake Diff tool.

## Overview

Snowflake Diff is a CLI tool that compares two Snowflake environments (left vs right) using SnowCLI (`snow sql`). It generates unified diffs, a clickable summary, and raw snapshots for audit purposes.

## System Diagram

<details>
<summary>Click to expand system architecture diagram</summary>

```mermaid
graph TB
    subgraph User
        CLI[CLI / Makefile]
        CONFIG[config.yml]
        ENV[Environment Variables]
    end

    subgraph "snowdiff.py (Orchestrator)"
        PARSE[Parse Config & Args]
        BUILD[Build SnowTargets]
        RUN[Run Collectors]
        DIFF[Generate Diffs]
        REPORT[Generate Report]
    end

    subgraph "collectors.py"
        TABLES[Table List]
        DDL[Table DDLs]
        DATA[Data Fingerprints]
        PROCS[Procedure DDLs]
        COMMENTS[Comments/Metadata]
    end

    subgraph "auth.py"
        SNOWCLI[SnowCLI Runner]
    end

    subgraph "External"
        LEFT[(Left Snowflake)]
        RIGHT[(Right Snowflake)]
    end

    subgraph "Output"
        DIFFS[out/diffs/]
        SNAPS[out/snapshots/]
        SUMMARY[out/SUMMARY.md]
    end

    CLI --> PARSE
    CONFIG --> PARSE
    ENV --> PARSE
    PARSE --> BUILD
    BUILD --> RUN
    RUN --> TABLES
    RUN --> DDL
    RUN --> DATA
    RUN --> PROCS
    RUN --> COMMENTS
    TABLES --> SNOWCLI
    DDL --> SNOWCLI
    DATA --> SNOWCLI
    PROCS --> SNOWCLI
    COMMENTS --> SNOWCLI
    SNOWCLI --> LEFT
    SNOWCLI --> RIGHT
    RUN --> DIFF
    DIFF --> DIFFS
    DIFF --> SNAPS
    DIFF --> REPORT
    REPORT --> SUMMARY
```

</details>

## Data Flow

<details>
<summary>Click to expand data flow diagram</summary>

```mermaid
sequenceDiagram
    participant User
    participant CLI as snowdiff.py
    participant Config as config.yml
    participant Collectors as collectors.py
    participant Auth as auth.py
    participant Left as Left Snowflake
    participant Right as Right Snowflake
    participant Output as out/

    User->>CLI: make diff
    CLI->>Config: Load configuration
    CLI->>CLI: Parse CLI args
    CLI->>CLI: Check env vars
    CLI->>Auth: Build SnowTargets

    loop For each collector
        CLI->>Collectors: Collect snapshots
        Collectors->>Auth: run_sql(left, query)
        Auth->>Left: snow sql --query
        Left-->>Auth: TSV output
        Collectors->>Auth: run_sql(right, query)
        Auth->>Right: snow sql --query
        Right-->>Auth: TSV output
        Collectors->>Output: Write snapshots
    end

    CLI->>CLI: Generate unified diffs
    CLI->>Output: Write diffs
    CLI->>Output: Write SUMMARY.md
    CLI-->>User: Done. See out/SUMMARY.md
```

</details>

## Module Responsibilities

<details>
<summary>Click to expand module details</summary>

### `scripts/snowdiff.py` - CLI Orchestrator

The main entry point that:
- Parses config.yml and CLI arguments
- Reads environment variables
- Builds SnowTarget objects for left/right
- Coordinates collectors
- Generates diffs and reports

### `scripts/auth.py` - SnowCLI Integration

Handles all Snowflake communication:
- `SnowTarget` dataclass with connection details
- `run_sql()` executes queries via `snow sql` with timeout protection
- `ensure_snowcli()` validates SnowCLI is available
- `connection_test()` for connectivity validation

### `scripts/collectors.py` - Snapshot Collection

Contains all query templates and collection logic:
- Table list collection
- DDL extraction (tables and procedures)
- Data fingerprinting (COUNT + HASH_AGG)
- Comment/metadata collection
- Table filtering with pattern matching

### `scripts/diffing.py` - Diff Generation

Pure functions for diff operations:
- `unified_diff()` generates standard unified diffs
- `write_diff_file()` writes diffs only when content differs
- `rel_link()` and `md_anchor()` for Markdown formatting

### `scripts/reporting.py` - Report Generation

Generates the summary report:
- `generate_summary_md()` creates the clickable SUMMARY.md
- Links to individual diff files
- Organizes by section (DDL, data, comments, etc.)

### `scripts/utils.py` - Utilities

Small helper functions:
- `safe_name()` sanitizes filenames for cross-platform compatibility

</details>

## Configuration Priority

<details>
<summary>Click to expand configuration priority diagram</summary>

```mermaid
flowchart TD
    A[Need config value] --> B{Env var set?}
    B -->|Yes| C[Use SNOWDIFF_*]
    B -->|No| D{CLI arg provided?}
    D -->|Yes| E[Use --left-role etc]
    D -->|No| F{In config.yml?}
    F -->|Yes| G[Use config value]
    F -->|No| H[Error with helpful message]

    style C fill:#90EE90
    style E fill:#90EE90
    style G fill:#90EE90
    style H fill:#FFB6C1
```

</details>

## Error Handling

<details>
<summary>Click to expand error handling strategy</summary>

### Graceful Degradation

- **Missing SnowCLI**: `ensure_snowcli()` fails fast with clear message
- **Query errors**: Returns `__ERROR__` sentinel, doesn't crash
- **Timeouts**: Returns `__ERROR__ TIMEOUT` after configurable timeout (default 300s)
- **Missing config**: Error message suggests env var, CLI flag, or config file

### Error Sentinel Pattern

```
__ERROR__<TAB>exit_code<TAB>error_message
```

Example: `__ERROR__\t1\tSQL compilation error: invalid identifier`

This allows:
- Snapshots to be written even with partial failures
- Diffs to show which side had errors
- Reports to indicate issues without crashing

</details>

## Test Architecture

<details>
<summary>Click to expand test architecture</summary>

```mermaid
graph TB
    subgraph "Unit Tests (Mocked)"
        T1[test_auth.py]
        T2[test_collectors.py]
        T3[test_config.py]
        T4[test_diffing.py]
        T5[test_reporting.py]
        T6[test_utils.py]
    end

    subgraph "Coverage Strategy"
        COV1[Functions excluded via .coveragerc patterns]
        COV2["collect_* functions - require live Snowflake"]
        COV3["cmd_diff, cmd_connect_test - integration only"]
    end

    T1 --> |mocks subprocess.run| AUTH
    T2 --> |tests query generation| COLLECT
    T3 --> |tests config parsing| CONFIG

    style T1 fill:#90EE90
    style T2 fill:#90EE90
    style T3 fill:#90EE90
    style T4 fill:#90EE90
    style T5 fill:#90EE90
    style T6 fill:#90EE90
```

**Coverage Target**: 80% minimum (actual: 92%)
**Test Count**: 71 tests

</details>
