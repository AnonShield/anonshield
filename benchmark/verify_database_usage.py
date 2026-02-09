#!/usr/bin/env python3
"""
Verifica se todos os hashes da database estão presentes no arquivo de saída.
Reporta hashes não utilizados (que existem na DB mas não no arquivo).
"""

import sqlite3
import sys
import re
from pathlib import Path
from typing import Set, Dict, List, Tuple


def extract_hashes_from_db(db_path: str) -> Tuple[Dict[str, Tuple[str, str]], Dict[str, Tuple[str, str]]]:
    """
    Extrai todos os hashes da database (tanto slug_name quanto full_hash).

    Returns:
        Tuple of (slug_hashes, full_hashes)
        - slug_hashes: Dict mapping slug_name (10 chars) -> (entity_type, original_name)
        - full_hashes: Dict mapping full_hash (64 chars) -> (entity_type, original_name)
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT slug_name, full_hash, entity_type, original_name FROM entities")

    slug_hashes = {}
    full_hashes = {}
    for row in cursor.fetchall():
        slug_name, full_hash, entity_type, original_name = row
        if slug_name:
            slug_hashes[slug_name] = (entity_type, original_name)
        if full_hash:
            full_hashes[full_hash] = (entity_type, original_name)

    conn.close()
    return slug_hashes, full_hashes


def find_hashes_in_file(file_path: str) -> Tuple[Set[str], Set[str]]:
    """
    Encontra todos os hashes no arquivo (tanto 10 chars quanto 64 chars).

    Extrai hashes do formato [ENTITY_TYPE_hash] onde hash pode ser 10 ou 64 caracteres.

    Returns:
        Tuple of (short_hashes, long_hashes)
        - short_hashes: Set de hashes de 10 caracteres (v1.0 format)
        - long_hashes: Set de hashes de 64 caracteres (v2.0+ format)
    """
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Formato: [ENTITY_TYPE_hash] onde hash é de 10 ou 64 caracteres hex
    # Exemplo v1.0: [IP_ADDRESS_3a5e707752]
    # Exemplo v2.0: [IP_ADDRESS_5b02f3792c70c0fc3838c96d652634a8203ee8af723b27dd8599bd638e89aa55]

    # Busca por hashes de 10 caracteres no formato [TYPE_hash10]
    short_pattern = re.compile(r'\[[A-Z_]+_([0-9a-f]{10})\]')
    short_hashes = set(short_pattern.findall(content))

    # Busca por hashes de 64 caracteres no formato [TYPE_hash64]
    long_pattern = re.compile(r'\[[A-Z_]+_([0-9a-f]{64})\]')
    long_hashes = set(long_pattern.findall(content))

    return short_hashes, long_hashes


def verify_database_usage(db_path: str, output_file: str) -> None:
    """
    Verifica se todos os hashes da database estão no arquivo de saída.
    """
    print("=" * 80)
    print("DATABASE USAGE VERIFICATION")
    print("=" * 80)
    print(f"\nDatabase: {db_path}")
    print(f"Output file: {output_file}")
    print()

    # Extrai hashes da database
    print("[1/3] Extracting hashes from database...")
    db_slug_hashes, db_full_hashes = extract_hashes_from_db(db_path)
    print(f"      Found {len(db_slug_hashes)} entities (short format)")
    print(f"      Found {len(db_full_hashes)} entities (long format)")

    # Encontra hashes no arquivo de saída
    print("[2/3] Searching for hashes in output file...")
    file_short_hashes, file_long_hashes = find_hashes_in_file(output_file)
    print(f"      Found {len(file_short_hashes)} short hashes (10 chars)")
    print(f"      Found {len(file_long_hashes)} long hashes (64 chars)")

    # Determina qual formato usar baseado no que foi encontrado
    print("[3/3] Comparing...")

    if file_long_hashes and len(file_long_hashes) > len(file_short_hashes):
        print("      Detected v2.0+ format (64-char hashes)")
        db_hashes = db_full_hashes
        file_hashes = file_long_hashes
        hash_format = "SHA256 (64 chars)"
    else:
        print("      Detected v1.0 format (10-char hashes)")
        db_hashes = db_slug_hashes
        file_hashes = file_short_hashes
        hash_format = "slug (10 chars)"

    db_hash_set = set(db_hashes.keys())
    unused_hashes = db_hash_set - file_hashes
    extra_hashes = file_hashes - db_hash_set
    used_hashes = db_hash_set & file_hashes

    print()
    print("=" * 80)
    print("RESULTS")
    print("=" * 80)
    print(f"\nHash format: {hash_format}")
    print(f"Total entities in database:     {len(db_hashes)}")
    print(f"Hashes found in output file:    {len(file_hashes)}")
    print(f"Database hashes used in output: {len(used_hashes)} ({len(used_hashes)/len(db_hashes)*100:.1f}%)")
    print(f"Database hashes NOT in output:  {len(unused_hashes)} ({len(unused_hashes)/len(db_hashes)*100:.1f}%)")
    print(f"Output hashes NOT in database:  {len(extra_hashes)}")

    if unused_hashes:
        print("\n" + "=" * 80)
        print("⚠️  UNUSED HASHES (in database but NOT in output file)")
        print("=" * 80)

        # Agrupa por tipo
        by_type: Dict[str, List[Tuple[str, str, str]]] = {}
        for hash_val in sorted(unused_hashes):
            entity_type, original = db_hashes[hash_val]
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append((hash_val, entity_type, original))

        for entity_type in sorted(by_type.keys()):
            entries = by_type[entity_type]
            print(f"\n{entity_type}: {len(entries)} unused")
            for hash_val, _, original in entries[:10]:  # Mostra até 10 por tipo
                print(f"  - {hash_val} <- {original}")
            if len(entries) > 10:
                print(f"  ... and {len(entries) - 10} more")

    if extra_hashes:
        print("\n" + "=" * 80)
        print("⚠️  EXTRA HASHES (in output file but NOT in database)")
        print("=" * 80)
        print(f"\nFound {len(extra_hashes)} hashes in output that don't exist in database:")
        for hash_val in sorted(list(extra_hashes)[:20]):
            print(f"  - {hash_val}")
        if len(extra_hashes) > 20:
            print(f"  ... and {len(extra_hashes) - 20} more")
        print("\nNote: These might be:")
        print("  - False positives (random 10-char hex strings)")
        print("  - Hashes from a different database")
        print("  - Artifacts from the anonymization process")

    if not unused_hashes and not extra_hashes:
        print("\n✅ PERFECT MATCH! All database hashes are in the output file.")
        print("   The database contains only entities used in this file.")
    elif not unused_hashes:
        print("\n✅ All database hashes are used in the output file.")
        print("   (There are some extra hashes in output, but database is clean)")

    print("\n" + "=" * 80)


def main():
    if len(sys.argv) != 3:
        print("Usage: python verify_database_usage.py <database.db> <output_file.csv>")
        print("\nExample:")
        print("  python verify_database_usage.py anonlfi_1.0/db/entities.db anonlfi_1.0/output/anon_file.csv")
        sys.exit(1)

    db_path = sys.argv[1]
    output_file = sys.argv[2]

    # Verifica se arquivos existem
    if not Path(db_path).exists():
        print(f"❌ Error: Database not found: {db_path}")
        sys.exit(1)

    if not Path(output_file).exists():
        print(f"❌ Error: Output file not found: {output_file}")
        sys.exit(1)

    verify_database_usage(db_path, output_file)


if __name__ == "__main__":
    main()
