# /deanonymize.py
import argparse
import os
import sqlite3
import sys

from config import DB_PATH, SECRET_KEY

def find_original_text(slug: str) -> str | None:
    """Queries the database to find the original text for a given anonymized slug."""
    if not os.path.exists(DB_PATH):
        return "Database file not found. Please run the anonymizer first."

    # The slug is in the format [ENTITY_TYPE_hash]
    try:
        # Extract the 64-character hash part from the slug
        full_hash = slug.strip().split('_')[-1].rstrip(']')
        if not full_hash or len(full_hash) != 64:
             return "Invalid slug format. Expected format: [ENTITY_TYPE_hash]."
    except (IndexError, AttributeError):
        return "Invalid slug format. Expected format: [ENTITY_TYPE_hash]."

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT original_name, entity_type, first_seen, last_seen FROM entities WHERE full_hash = ?", (full_hash,))
            result = cur.fetchone()
            
            if result:
                original_name, entity_type, first, last = result
                return (
                    f"Original Text Found:\n"
                    f"  - Text: {original_name}\n"
                    f"  - Entity Type: {entity_type}\n"
                    f"  - First Seen: {first}\n"
                    f"  - Last Seen: {last}"
                )
            else:
                return "Original text not found for the given slug."

    except sqlite3.Error as e:
        return f"Database error: {e}"

def main():
    """Main function to run the de-anonymizer tool."""
    parser = argparse.ArgumentParser(
        description="De-anonymize a slug to find its original text. Requires ANON_SECRET_KEY."
    )
    parser.add_argument("slug", help="The anonymized slug to look up (e.g., '[PERSON_...hash...]').")
    args = parser.parse_args()

    if not SECRET_KEY:
        print("[!] Error: ANON_SECRET_KEY environment variable must be set to run this tool.", file=sys.stderr)
        sys.exit(1)

    result = find_original_text(args.slug)
    print(result)

if __name__ == "__main__":
    main()