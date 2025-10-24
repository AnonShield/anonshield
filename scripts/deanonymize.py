# /deanonymize.py
import argparse
import os
import sqlite3
import sys

from src.anon.config import DB_PATH, SECRET_KEY

def find_original_text(slug: str) -> str | None:
    """Queries the database to find the original text for a given anonymized slug."""
    if not os.path.exists(DB_PATH):
        return "Database file not found. Please run the anonymizer first."

    # The slug is in the format [ENTITY_TYPE_display_hash]
    try:
        # Extract the display_hash part from the slug
        parts = slug.strip().split('_')
        if len(parts) < 2:
            return "Invalid slug format. Expected format: [ENTITY_TYPE_display_hash]."
        
        entity_type_part = parts[0].lstrip('[')
        display_hash = parts[-1].rstrip(']')

        if not display_hash:
             return "Invalid slug format. Display hash not found."
    except (IndexError, AttributeError):
        return "Invalid slug format. Expected format: [ENTITY_TYPE_display_hash]."

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            # Query using slug_name (which stores the display_hash)
            cur.execute("SELECT original_name, entity_type, first_seen, last_seen FROM entities WHERE slug_name = ?", (display_hash,))
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