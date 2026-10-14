# Webhook Relay Lab

Signed event processing with a durable queue, bounded retries and dead-letter handling.

![Project overview](cover.png)

**Portfolio demonstration by Usman Saleem Bhatti.** Newly built with AI assistance and synthetic sample data; not represented as past client work.

## Workflow

`HMAC validation → timestamp check → durable queue → retry policy → delivered/dead letter`

## Features

HMAC verification, replay-window checking, event-ID deduplication, SQLite persistence, exponential backoff, synthetic failure simulation.

## Quick start

Python 3.11 or newer. No third-party dependencies.

```sh
python app.py --demo --output runs
python -m unittest discover -v
```

Open `runs/report.html` in a browser. `runs/result.json` contains structured output. Demo reruns reuse their local ledger where applicable; use a fresh output folder to repeat the first-run scenario.

## Custom input

```sh
python app.py --demo --output runs
```

## What is tested

The unit tests cover the business rules, malformed inputs and important failure paths. The generated `demo-report.html` is a checked-in sample report for quick inspection. Runtime output and databases are ignored by Git.

## Daily checks

The included `checks.yml` is a GitHub Actions workflow template. To activate it, place it at `.github/workflows/checks.yml`. It runs tests and the demo daily and on pushes, retaining run logs and a report artifact. The local portfolio bundle also includes `run_daily_checks.py` for background checks.

## Scope and limitations

A single-worker integration core, not a production HTTP service. Delivery is simulated. Real adapters must forward idempotency keys; delivery is at-least-once across crashes. Concurrency, TLS, rate limits and deployment monitoring are future work.

## Contact

[Usman on Upwork](https://www.upwork.com/freelancers/~017ac7683856df4451) · [GitHub](https://github.com/Usb01)
