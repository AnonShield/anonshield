
import os
import csv
import logging
import sqlite3
import argparse # Added argparse

# --- Configuration ---
# The script is in "scripts/", so the project root is one level up.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "db", "entities.db")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "output")
CSV_FILENAME = "entities_export.csv"
# ---

def main():
    """
    Exports all entities from the database to a CSV file and then
    optionally clears the entities table.
    """
    parser = argparse.ArgumentParser(description="Export entities to CSV and optionally clear the database.")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all entities from the database after exporting to CSV."
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    output_path = os.path.join(OUTPUT_DIR, CSV_FILENAME)

    if not os.path.exists(DB_PATH):
        logging.error(f"Database file not found at '{DB_PATH}'. Make sure the database exists.")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    conn = None
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        logging.info(f"Successfully connected to database at '{DB_PATH}'.")

        # 1. Fetch all entities
        logging.info("Fetching all entities from the database...")
        cursor.execute("SELECT id, entity_type, original_name, slug_name, full_hash, first_seen, last_seen FROM entities")
        entities = cursor.fetchall()

        if not entities:
            logging.info("No entities found in the database. Nothing to export.")
        else:
            # 2. Write to CSV
            logging.info(f"Exporting {len(entities)} entities to '{output_path}'...")
            header = ["id", "entity_type", "original_name", "slug_name", "full_hash", "first_seen", "last_seen"]
            with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header)
                writer.writerows(entities)
            logging.info(f"Export completed successfully. Data saved to {output_path}")

        # 3. Conditionally clear the database
        if args.clear:
            logging.info("Clearing all entities from the database as --clear flag was provided...")
            cursor.execute("DELETE FROM entities")
            conn.commit()
            # To reset the autoincrement counter, we can also delete from sqlite_sequence
            try:
                cursor.execute("DELETE FROM sqlite_sequence WHERE name='entities'")
                conn.commit()
                logging.info("Auto-increment counter for 'entities' table has been reset.")
            except sqlite3.OperationalError:
                # This will happen if the table has never had any data deleted before
                logging.info("No sequence to reset for 'entities' table (this is normal).")
                
            logging.info(f"Database cleared successfully. {cursor.rowcount} rows deleted.")
        else:
            logging.info("Database clear skipped. To clear the database, run the script with the --clear flag.")

    except sqlite3.Error as e:
        logging.error(f"A database error occurred: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()
            logging.info("Database connection closed.")


if __name__ == "__main__":
    main()
