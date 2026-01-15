# Product Requirements Document (PRD)

## Goal
Provide a developer-friendly toolkit to flatten JSON data into CSV and ingest it into MongoDB
for demos, testing, and lightweight data movement tasks.

## Users
- Data engineers validating JSON ingestion paths.
- Developers prototyping document-to-tabular pipelines.
- Analysts needing quick CSV exports from nested JSON.

## Core requirements
- Flatten nested JSON structures with configurable list handling.
- Support array explosion into multiple CSV records.
- Provide scenario-based examples from intermediate to advanced complexity.
- Offer a Docker image for CSV ingestion into MongoDB.
- Include unit tests and CI-driven badges.

## Non-goals
- Full ETL orchestration.
- Schema inference beyond simple type casting.
- High-volume streaming ingestion.

## Success metrics
- A single command produces scenario outputs.
- CSV ingestion into MongoDB works in a standard Docker environment.
- Test coverage and unit test counts are visible in the README.
