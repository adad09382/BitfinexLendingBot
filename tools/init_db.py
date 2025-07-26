import logging
import os
import sys
from decouple import Config, RepositoryEnv
from dotenv import load_dotenv

# Add project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.main.python.services.database_manager import DatabaseManager

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

def create_tables(db_manager):
    """
    Creates all necessary tables in the database.
    """
    log.info("Creating table 'market_logs'...")
    market_log_table_query = """
    CREATE TABLE IF NOT EXISTS market_logs (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        currency VARCHAR(10) NOT NULL,
        rates_data JSONB NOT NULL
    );
    """
    db_manager.execute_query(market_log_table_query)
    log.info("Table 'market_logs' created successfully.")

    # Add other table creation queries here in the future
    # log.info("Creating table 'users'...")
    # ...

def main():
    """
    Main function to initialize the database.
    """
    log.info("--- Database Initialization Script --- ")
    try:
        # Load config from .env file
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        load_dotenv(dotenv_path=os.path.join(project_root, '.env'))
        config = Config(RepositoryEnv(os.path.join(project_root, '.env')))
        
        db_manager = DatabaseManager(config)
        create_tables(db_manager)
        db_manager.close()
        log.info("Database initialization complete.")
    except Exception as e:
        log.critical(f"An error occurred during database initialization: {e}", exc_info=True)

if __name__ == "__main__":
    main()
