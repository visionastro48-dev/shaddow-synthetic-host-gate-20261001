#!/usr/bin/env python3
import hashlib, json, pathlib, sys

order_path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "round1_order.json")
root = order_path.parent
order = json.loads(order_path.read_text(encoding="utf-8"))
manifest = json.loads((root / "input_manifest.json").read_text(encoding="utf-8"))
allowed = order["allowed_inputs"]

if sorted(manifest["files"].keys()) != sorted(allowed):
    raise SystemExit("input set mismatch")

results = {}
ok = True
for name in allowed:
    p = root / "snapshot" / name
    data = p.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    size = len(data)
    utf8 = True
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        utf8 = False
        text = ""
    checks = {"nonempty": size > 0, "utf8": utf8}
    if name.endswith(".html"):
        low = text.lower()
        checks["html_document"] = "<html" in low or "<!doctype html" in low
    elif name.endswith(".css"):
        checks["css_shape"] = "{" in text and "}" in text
    elif name.endswith(".js"):
        checks["js_shape"] = len(text.strip()) >= 20
    item_ok = all(checks.values()) and size >= int(order["minimum_bytes"].get(name, 1))
    ok = ok and item_ok
    results[name] = {"sha256": sha, "size_bytes": size, "checks": checks, "ok": item_ok}

out = {
    "format": "SHADDOW_FIELD_RESULT_V1",
    "mission_id": order["mission_id"],
    "objective": order["objective"],
    "input_manifest_sha256": hashlib.sha256((root / "input_manifest.json").read_bytes()).hexdigest(),
    "files": results,
    "status": "PASS" if ok else "FAIL",
    "worker_claims": {
        "network_required": False,
        "private_context_required": False,
        "external_effect_requested": False
    }
}
print(json.dumps(out, sort_keys=True, separators=(",", ":")))
