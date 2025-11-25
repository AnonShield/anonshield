# /deanonymize.py
import argparse
import os
import sys
import logging

from src.anon.config import SECRET_KEY
from src.anon.repository import EntityRepository

def find_original_text(slug: str, db_dir: str) -> str:
    """Queries the database via the repository to find the original text for a given slug."""
    
    db_path = os.path.join(db_dir, "entities.db")
    if not os.path.exists(db_path):
        return f"Database file not found at '{db_path}'. Please run the anonymizer first to create the database."

    repo = EntityRepository(db_path)

    try:
        # The slug is in the format [ENTITY_TYPE_display_hash]
        parts = slug.strip('[]').split('_')
        if len(parts) < 2:
            return "Invalid slug format. Expected format: [ENTITY_TYPE_display_hash]."
        
        display_hash = parts[-1]
        if not display_hash:
             return "Invalid slug format. Display hash not found."

    except (IndexError, AttributeError):
        return "Invalid slug format. Expected format: [ENTITY_TYPE_display_hash]."

    try:
        result = repo.find_by_slug(display_hash)
        repo.close_thread_connection()

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

    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
        return "An unexpected error occurred during database lookup."


def main():
    """Main function to run the de-anonymizer tool."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    parser = argparse.ArgumentParser(
        description="De-anonymize a slug to find its original text. Requires ANON_SECRET_KEY."
    )
    parser.add_argument("slug", help="The anonymized slug to look up (e.g., '[PERSON_...hash...]').")
    parser.add_argument("--db-dir", default="db", help="Directory where the database file is located. Defaults to 'db'.")
    args = parser.parse_args()

    if not SECRET_KEY:
        print("[!] Error: ANON_SECRET_KEY environment variable must be set to run this tool.", file=sys.stderr)
        sys.exit(1)

    result = find_original_text(args.slug, args.db_dir)
    print(result)

if __name__ == "__main__":
    main()