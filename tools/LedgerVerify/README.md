# LedgerVerify

Independent C# (.NET 8) verifier for the SIGNAL hash-chained ledger
(`execution/ledger.py`). It re-implements verification from scratch — no
Python code is shared — so a bug or tampering in the Python side cannot
silently validate itself.

## What it checks

1. **Chain integrity**: every record's `prev_hash` links to the previous
   record's `hash`, and each `hash` equals SHA-256 over the canonical JSON
   of the record (keys sorted recursively, no whitespace — byte-identical
   to the Python canonicalization).
2. **Hard trading constraints**, re-derived from the fill sequence:
   - long-only: positions never go negative
   - no shorting: a SELL may never exceed the held quantity
   - penny-stock floor: no BUY below $5
   - concentration: no position above 25% of equity
   - exposure: gross long exposure never above 95% of equity
   - capital: starts from exactly $100

## Usage

```bash
cd tools/LedgerVerify
dotnet run -- /path/to/ledger.jsonl
```

Exit code 0 = chain intact and all constraints hold; exit code 1 = violations
listed; exit code 2 = ledger file not found.

Export a ledger with the Python side (offline, synthetic — no experiment run):

```bash
cd ../..
.venv/bin/python dashboard/scripts/generate_fixtures.py  # writes a ledger to /tmp
dotnet run -- /tmp/signal-fixture-ledger.jsonl
```

## Build status

**Not compiled locally.** This project was written on a machine where the
.NET SDK (`dotnet`) was not installed, so it has not been built or run here.
The `Program.cs` is a single self-contained file using only the .NET 8 base
class libraries (`System.Text.Json`, `System.Security.Cryptography`) — no
NuGet packages required. CI does not build it for the same reason; verify on
any machine with .NET 8 SDK installed.
