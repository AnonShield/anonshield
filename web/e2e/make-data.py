"""Synthetic files for the end-to-end test (no real data). Usage: python3 make-data.py DIR"""
import json
import sys
import zipfile
from pathlib import Path

out = Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
(out / "tickets.txt").write_text(
    "Contato: Maria Souza (maria.souza@example.com), servidor 192.168.10.45. Ticket TICKET-1234.\n")

records = []
for i in range(30):
    record = {
        "output": f"Host 10.0.0.{i} reachable; owner joao{i}@example.com",
        "id": i,
        "asset": {"host_name": f"srvfiles{i:02d}", "name": f"srvfiles{i:02d}", "ipv4_addresses": [f"10.0.0.{i}"]},
        "definition": {"name": "OpenSSH check", "description": "Public plugin text that cites 203.0.113.7 as an example.",
                       "output": f"Host 10.0.0.{i} reachable"},
        "scan": {"target": f"10.0.0.{i}"},
    }
    if i == 25:  # fields that only a late record has
        record["asset"]["netbios_name"] = "SRVNB25"
        record["notes"] = "late field: contact ana.late@example.com from 10.9.9.9"
    records.append(record)
(out / "scan.json").write_text(json.dumps(records, indent=2))
(out / "other.json").write_text(json.dumps([{"a": 1, "b": {"c": "x@example.com"}}]))
(out / "invalid.json").write_text('{"email": "a@example.com", broken}')
(out / "dados.tsv").write_text("id\tmail\n1\ta@example.com\n")
with zipfile.ZipFile(out / "mixed.zip", "w") as archive:
    archive.writestr("tickets/one.txt", "Contato maria@example.com 10.0.0.5")
    archive.writestr("tickets/notes.md", "x@example.com")

# A profile saved before 2026-10: an allow-list of the first record's fields.
first = [f"{k}.{s}" if isinstance(v, dict) else k for k, v in records[0].items()
         for s in (v if isinstance(v, dict) else [None])]
(out / "old-profile.yaml").write_text(
    "strategy: regex\nlang: en\nslug_length: 8\nanonymization_config:\n  force_anonymize: {}\n  fields_to_anonymize:\n"
    + "".join(f"    - {f}\n" for f in first if f != "id") + "  fields_to_exclude:\n    - id\n")
(out / "ip-only-profile.yaml").write_text("strategy: regex\nlang: en\nslug_length: 8\nentities:\n  - IP_ADDRESS\n")
(out / "big.txt").write_text("".join(
    f"Line {i}: Maria Souza works at Acme Corp in Porto Alegre with John Smith.\n" for i in range(6000)))
# Over the 1 MB limit of the limited instance (URL_LIMITED in e2e.mjs).
(out / "large.txt").write_text("".join(f"Line {i}: contact maria{i}@example.com\n" for i in range(50000)))
