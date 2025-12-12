# src/anon/repository.py
import sqlite3
import os
import logging
import threading
from typing import List, Optional, Tuple

class EntityRepository:
    """
    Handles all database operations for anonymized entities, encapsulating SQL queries.
    This implementation is thread-safe by using thread-local storage for database connections.
    """

    def __init__(self, db_path: str):
        """
        Initializes the repository. A database connection will be created on-demand for each thread.
        
        Args:
            db_path: The path to the SQLite database file (e.g., 'db/entities.db' or ':memory:').
        """
        self.db_path = db_path
        self._local = threading.local()
        logging.info(f"Repository initialized for database at: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        """
        Retrieves or creates a database connection for the current thread.
        """
        if not hasattr(self._local, "connection"):
            logging.debug(f"Thread {threading.get_ident()}: Creating new SQLite connection to {self.db_path}")
            # Add a timeout to handle locked databases gracefully
            self._local.connection = sqlite3.connect(self.db_path, timeout=10)
        return self._local.connection

    def initialize_schema(self, synchronous: str = "NORMAL", journal_mode: str = "WAL"):
        """
        Creates the necessary tables and indexes if they don't exist.
        Sets the PRAGMA settings for the new connection.
        """
        conn = self._get_connection()
        logging.info(f"Setting PRAGMA synchronous={synchronous}, journal_mode={journal_mode} for new connection.")
        conn.execute(f"PRAGMA synchronous={synchronous};")
        conn.execute(f"PRAGMA journal_mode={journal_mode};")
        conn.execute("PRAGMA cache_size=-10000;")
        conn.execute("PRAGMA temp_store=MEMORY;")
        
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
        
        with conn:
            conn.execute(create_table_sql)
            conn.execute(create_index_sql)
        logging.info("Database schema initialized successfully for thread.")

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
        conn = self._get_connection()
        try:
            with conn:
                conn.executemany(insert_sql, entity_list)
            logging.info("%d entities written to database.", len(entity_list))
        except sqlite3.Error as e:
            logging.error(f"Repository failed to save batch: {e}", exc_info=True)
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
        conn = self._get_connection()
        try:
            cursor = conn.execute(query_sql, (display_hash,))
            return cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Repository failed to find by slug '{display_hash}': {e}", exc_info=True)
            return None

    def get_all_entities(self) -> List[Tuple]:
        """
        Retrieves all entities from the database.

        Returns:
            A list of tuples, where each tuple is a record.
        """
        query_sql = "SELECT id, entity_type, original_name, slug_name, full_hash, first_seen, last_seen FROM entities"
        conn = self._get_connection()
        try:
            cursor = conn.execute(query_sql)
            return cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Repository failed to get all entities: {e}", exc_info=True)
            return []

    def clear_all_entities(self):
        """
        Deletes all records from the entities table.
        """
        delete_sql = "DELETE FROM entities"
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(delete_sql)
            logging.info("All entities have been deleted from the database.")
        except sqlite3.Error as e:
            logging.error(f"Repository failed to clear all entities: {e}", exc_info=True)
            raise

    def close_thread_connection(self):
        """Closes the database connection for the current thread, if it exists."""
        if hasattr(self._local, "connection"):
            self._local.connection.close()
            del self._local.connection
            logging.info(f"Repository connection for thread {threading.get_ident()} closed.")

