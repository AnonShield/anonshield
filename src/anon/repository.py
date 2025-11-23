# src/anon/repository.py
import sqlite3
import os
import logging
from typing import List, Optional, Tuple

class EntityRepository:
    """
    Handles all database operations for anonymized entities, encapsulating SQL queries.
    """

    def __init__(self, db_path: str):
        """
        Initializes the repository and establishes a database connection.
        
        Args:
            db_path: The path to the SQLite database file (e.g., 'db/entities.db' or ':memory:').
        """
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        logging.info(f"Repository initialized for database at: {db_path}")

    def initialize_schema(self, synchronous: str = "NORMAL", journal_mode: str = "WAL"):
        """
        Creates the necessary tables and indexes if they don't exist.
        Sets the PRAGMA settings for the connection.
        """
        logging.info(f"Setting PRAGMA synchronous={synchronous}, journal_mode={journal_mode}")
        self.connection.execute(f"PRAGMA synchronous={synchronous};")
        self.connection.execute(f"PRAGMA journal_mode={journal_mode};")
        self.connection.execute("PRAGMA cache_size=-10000;")
        self.connection.execute("PRAGMA temp_store=MEMORY;")
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            original_name TEXT NOT NULL,
            slug_name TEXT NOT NULL,
            full_hash TEXT NOT NULL UNIQUE,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        )
        """
        create_index_sql = "CREATE INDEX IF NOT EXISTS idx_full_hash ON entities(full_hash);"
        
        with self.connection:
            self.connection.execute(create_table_sql)
            self.connection.execute(create_index_sql)
        logging.info("Database schema initialized successfully.")

    def save_batch(self, entity_list: List[Tuple]):
        """
        Saves a batch of entities to the database using INSERT OR IGNORE.

        Args:
            entity_list: A list of tuples, where each tuple represents an entity record.
        """
        if not entity_list:
            return
            
        insert_sql = """
        INSERT OR IGNORE INTO entities
        (entity_type, original_name, slug_name, full_hash, first_seen, last_seen)
        VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
        """
        try:
            with self.connection:
                self.connection.executemany(insert_sql, entity_list)
            logging.info("%d entities written to database.", len(entity_list))
        except sqlite3.Error as e:
            logging.error(f"Repository failed to save batch: {e}", exc_info=True)
            # Re-raise the exception to allow the caller to handle it (e.g., for deadlock retry logic)
            raise

    def find_by_slug(self, display_hash: str) -> Optional[Tuple]:
        """
        Finds a single entity record by its display hash (slug_name).

        Args:
            display_hash: The hash part of the anonymized slug.

        Returns:
            A tuple containing the entity data if found, otherwise None.
        """
        query_sql = "SELECT original_name, entity_type, first_seen, last_seen FROM entities WHERE slug_name = ?"
        try:
            with self.connection:
                cursor = self.connection.execute(query_sql, (display_hash,))
                return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Repository failed to find by slug '{display_hash}': {e}", exc_info=True)
            return None

    def close(self):
        """Closes the database connection."""
        if self.connection:
            self.connection.close()
            logging.info(f"Repository connection to {self.db_path} closed.")

