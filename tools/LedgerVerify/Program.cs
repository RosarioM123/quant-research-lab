// LedgerVerify — independent C# verifier for the SIGNAL ledger.
//
// Reads an exported ledger JSONL file (see execution/ledger.py) and
// independently verifies, WITHOUT any Python code:
//
//   1. Chain integrity: every record's prev_hash links to the previous
//      record's hash, and every record's hash matches SHA-256 over the
//      canonical JSON of the record (keys sorted, separators "," and ":",
//      exactly as the Python side canonicalizes).
//   2. Hard trading constraints, re-derived from the fill sequence:
//        - long-only: positions never go negative
//        - no shorting: a SELL may never exceed the held quantity
//        - penny-stock floor: no BUY below $5
//        - concentration: no position above 25% of equity
//        - exposure: gross long exposure never above 95% of equity
//
// Usage:
//   dotnet run -- /path/to/ledger.jsonl
//
// NOTE: this project was written on a machine without the .NET SDK, so it
// has NOT been compiled locally. See README.md.
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

var path = args.Length > 0 ? args[0] : "ledger.jsonl";
if (!File.Exists(path))
{
    Console.Error.WriteLine($"Ledger file not found: {path}");
    return 2;
}

string Canonical(JsonNode? node)
{
    // Canonical JSON: object keys sorted recursively, no whitespace.
    // Matches Python: json.dumps(obj, sort_keys=True, separators=(",", ":")).
    return node switch
    {
        JsonObject o => "{" + string.Join(",",
            o.OrderBy(kv => kv.Key, StringComparer.Ordinal)
             .Select(kv => JsonSerializer.Serialize(kv.Key) + ":" + Canonical(kv.Value))) + "}",
        JsonArray a => "[" + string.Join(",", a.Select(Canonical)) + "]",
        _ => node?.ToJsonString() ?? "null",
    };
}

string Sha256Hex(string s)
{
    var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(s));
    return Convert.ToHexString(bytes).ToLowerInvariant();
}

var errors = new List<string>();
var prevHash = new string('0', 64);
int seq = 0;

// Reconstructed portfolio state from the fill sequence.
var positions = new Dictionary<string, double>();
double cash = 100.0;   // simulated capital is exactly $100
const double MaxPositionPct = 0.25;
const double MaxGrossPct = 0.95;
const double MinPrice = 5.0;
var prices = new Dictionary<string, double>();

foreach (var line in File.ReadLines(path))
{
    if (string.IsNullOrWhiteSpace(line)) continue;
    seq++;
    JsonObject? rec;
    try { rec = JsonNode.Parse(line)?.AsObject(); }
    catch { errors.Add($"seq {seq}: not valid JSON"); continue; }
    if (rec is null) { errors.Add($"seq {seq}: not a JSON object"); continue; }

    // --- Chain integrity -------------------------------------------------
    var hash = rec["hash"]?.GetValue<string>();
    var ph = rec["prev_hash"]?.GetValue<string>();
    if (ph != prevHash)
        errors.Add($"seq {seq}: prev_hash mismatch (chain broken)");
    var body = new JsonObject();
    foreach (var kv in rec.Where(kv => kv.Key != "hash"))
        body[kv.Key] = kv.Value?.DeepClone();
    var recomputed = Sha256Hex(Canonical(body));
    if (hash != recomputed)
        errors.Add($"seq {seq}: hash mismatch (record tampered)");
    prevHash = hash ?? prevHash;

    // --- Constraint checks on fills --------------------------------------
    if (rec["type"]?.GetValue<string>() == "fill")
    {
        var data = rec["data"]?.AsObject();
        if (data is null) continue;
        var symbol = data["symbol"]?.GetValue<string>() ?? "?";
        var side = data["side"]?.GetValue<string>() ?? "?";
        var qty = data["qty"]?.GetValue<double>() ?? 0;
        var price = data["fill_price"]?.GetValue<double>() ?? 0;
        prices[symbol] = price;
        positions.TryGetValue(symbol, out var held);

        if (side == "BUY")
        {
            if (price < MinPrice)
                errors.Add($"seq {seq}: penny-stock violation: {symbol} @ ${price}");
            positions[symbol] = held + qty;
            cash -= qty * price;
        }
        else if (side == "SELL")
        {
            if (held <= 0)
                errors.Add($"seq {seq}: SHORT attempt: SELL {symbol} with no long position");
            else if (qty > held + 1e-9)
                errors.Add($"seq {seq}: OVERSELL: SELL {qty} > held {held} ({symbol})");
            positions[symbol] = Math.Max(0, held - qty);
            cash += qty * price;
        }

        var equity = cash + positions.Sum(kv =>
            kv.Value * (prices.TryGetValue(kv.Key, out var p) ? p : 0));
        if (equity <= 0) { errors.Add($"seq {seq}: non-positive equity"); continue; }

        foreach (var kv in positions)
        {
            var val = kv.Value * (prices.TryGetValue(kv.Key, out var pp) ? pp : 0);
            if (val > MaxPositionPct * equity + 1e-9)
                errors.Add($"seq {seq}: over-concentration: {kv.Key} = {val / equity:P1} of equity");
        }
        var gross = positions.Sum(kv =>
            kv.Value * (prices.TryGetValue(kv.Key, out var p2) ? p2 : 0));
        if (gross > MaxGrossPct * equity + 1e-9)
            errors.Add($"seq {seq}: over-exposure: gross {gross / equity:P1} of equity");
    }
}

Console.WriteLine($"Verified {seq} records.");
if (errors.Count == 0)
{
    Console.WriteLine("OK: chain intact, all hard constraints hold.");
    return 0;
}
Console.WriteLine($"FAILED: {errors.Count} violation(s):");
foreach (var e in errors) Console.WriteLine("  - " + e);
return 1;
