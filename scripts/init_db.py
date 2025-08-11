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

    log.info("Creating table 'lending_orders'...")
    lending_orders_table_query = """
    CREATE TABLE IF NOT EXISTS lending_orders (
        id SERIAL PRIMARY KEY,
        order_id BIGINT NOT NULL UNIQUE,
        symbol VARCHAR(10) NOT NULL,
        amount NUMERIC(20, 8) NOT NULL,
        rate NUMERIC(20, 8) NOT NULL,
        period INTEGER NOT NULL,
        status VARCHAR(20) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        executed_at TIMESTAMPTZ,
        cancelled_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        executed_amount NUMERIC(20, 8),
        executed_rate NUMERIC(20, 8),
        strategy_name VARCHAR(50),
        strategy_params JSONB
    );
    """
    db_manager.execute_query(lending_orders_table_query)
    log.info("Table 'lending_orders' created successfully.")

    log.info("Creating table 'interest_payments'...")
    interest_payments_table_query = """
    CREATE TABLE IF NOT EXISTS interest_payments (
        id SERIAL PRIMARY KEY,
        ledger_id BIGINT NOT NULL UNIQUE,
        currency VARCHAR(10) NOT NULL,
        amount NUMERIC(20, 8) NOT NULL,
        paid_at TIMESTAMPTZ NOT NULL,
        description TEXT NOT NULL,
        order_id BIGINT
    );
    """
    db_manager.execute_query(interest_payments_table_query)
    log.info("Table 'interest_payments' created successfully.")

    log.info("Creating table 'daily_profits'...")
    daily_profits_table_query = """
    CREATE TABLE IF NOT EXISTS daily_profits (
        id SERIAL PRIMARY KEY,
        currency VARCHAR(10) NOT NULL,
        interest_income NUMERIC(20, 8) NOT NULL,
        total_loan NUMERIC(20, 8) NOT NULL,
        type VARCHAR(50) NOT NULL,
        date DATE NOT NULL
    );
    """
    db_manager.execute_query(daily_profits_table_query)
    log.info("Table 'daily_profits' created successfully.")

    log.info("Creating table 'portfolio_stats'...")
    portfolio_stats_table_query = """
    CREATE TABLE IF NOT EXISTS portfolio_stats (
        id SERIAL PRIMARY KEY,
        snapshot_date DATE NOT NULL,
        base_currency VARCHAR(10) NOT NULL,
        total_portfolio_value NUMERIC(20, 8),
        total_deployed NUMERIC(20, 8),
        total_available NUMERIC(20, 8),
        total_pending NUMERIC(20, 8),
        overall_utilization NUMERIC(5, 2),
        target_utilization NUMERIC(5, 2),
        utilization_efficiency NUMERIC(5, 2),
        current_daily_rate NUMERIC(20, 8),
        projected_annual_return NUMERIC(20, 8),
        ytd_return NUMERIC(20, 8),
        prev_month_utilization NUMERIC(5, 2),
        prev_month_return NUMERIC(20, 8),
        utilization_trend VARCHAR(20),
        last_updated TIMESTAMPTZ NOT NULL,
        data_sources JSONB,
        calculation_version VARCHAR(10),
        risk_currency_concentration NUMERIC(5, 2),
        risk_period_concentration NUMERIC(5, 2),
        risk_counterparty_concentration NUMERIC(5, 2),
        risk_avg_maturity_days NUMERIC(10, 2),
        risk_liquidity_ratio NUMERIC(5, 2),
        risk_rate_sensitivity NUMERIC(20, 8),
        risk_duration_risk NUMERIC(20, 8),
        risk_portfolio_var NUMERIC(20, 8),
        risk_score NUMERIC(5, 2)
    );
    """
    db_manager.execute_query(portfolio_stats_table_query)
    log.info("Table 'portfolio_stats' created successfully.")

    log.info("Creating table 'portfolio_currency_allocations'...")
    portfolio_currency_allocations_table_query = """
    CREATE TABLE IF NOT EXISTS portfolio_currency_allocations (
        id SERIAL PRIMARY KEY,
        portfolio_stats_id INTEGER NOT NULL REFERENCES portfolio_stats(id),
        currency VARCHAR(10) NOT NULL,
        total_amount NUMERIC(20, 8),
        deployed_amount NUMERIC(20, 8),
        available_amount NUMERIC(20, 8),
        allocation_percentage NUMERIC(5, 2),
        avg_rate NUMERIC(20, 8),
        total_orders INTEGER
    );
    """
    db_manager.execute_query(portfolio_currency_allocations_table_query)
    log.info("Table 'portfolio_currency_allocations' created successfully.")

    log.info("Creating table 'portfolio_period_allocations'...")
    portfolio_period_allocations_table_query = """
    CREATE TABLE IF NOT EXISTS portfolio_period_allocations (
        id SERIAL PRIMARY KEY,
        portfolio_stats_id INTEGER NOT NULL REFERENCES portfolio_stats(id),
        period_days INTEGER NOT NULL,
        total_amount NUMERIC(20, 8),
        allocation_percentage NUMERIC(5, 2),
        avg_rate NUMERIC(20, 8),
        order_count INTEGER,
        expected_return NUMERIC(20, 8)
    );
    """
    db_manager.execute_query(portfolio_period_allocations_table_query)
    log.info("Table 'portfolio_period_allocations' created successfully.")

    log.info("Creating table 'portfolio_strategy_allocations'...")
    portfolio_strategy_allocations_table_query = """
    CREATE TABLE IF NOT EXISTS portfolio_strategy_allocations (
        id SERIAL PRIMARY KEY,
        portfolio_stats_id INTEGER NOT NULL REFERENCES portfolio_stats(id),
        strategy_name VARCHAR(50) NOT NULL,
        total_amount NUMERIC(20, 8),
        allocation_percentage NUMERIC(5, 2),
        order_count INTEGER,
        success_rate NUMERIC(5, 2),
        avg_return NUMERIC(20, 8),
        last_used TIMESTAMPTZ
    );
    """
    db_manager.execute_query(portfolio_strategy_allocations_table_query)
    log.info("Table 'portfolio_strategy_allocations' created successfully.")

    log.info("Creating table 'profit_reports'...")
    profit_reports_table_query = """
    CREATE TABLE IF NOT EXISTS profit_reports (
        id SERIAL PRIMARY KEY,
        currency VARCHAR(10) NOT NULL,
        period_type VARCHAR(20) NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        total_interest NUMERIC(20, 8),
        total_fees NUMERIC(20, 8),
        net_profit NUMERIC(20, 8),
        total_return_rate NUMERIC(20, 8),
        annualized_return NUMERIC(20, 8),
        daily_avg_return NUMERIC(20, 8),
        avg_deployed_amount NUMERIC(20, 8),
        max_deployed_amount NUMERIC(20, 8),
        utilization_rate NUMERIC(5, 2),
        avg_lending_rate NUMERIC(20, 8),
        max_lending_rate NUMERIC(20, 8),
        min_lending_rate NUMERIC(20, 8),
        return_volatility NUMERIC(20, 8),
        sharpe_ratio NUMERIC(20, 8),
        max_drawdown NUMERIC(20, 8),
        total_orders INTEGER,
        successful_orders INTEGER,
        cancelled_orders INTEGER,
        avg_order_size NUMERIC(20, 8),
        benchmark_return NUMERIC(20, 8),
        previous_period_return NUMERIC(20, 8),
        market_avg_rate NUMERIC(20, 8),
        best_performing_strategy VARCHAR(50),
        worst_performing_strategy VARCHAR(50),
        report_generated_at TIMESTAMPTZ NOT NULL,
        data_points_count INTEGER,
        data_completeness NUMERIC(5, 2),
        daily_profits_json JSONB,
        rate_distribution_json JSONB,
        period_distribution_json JSONB,
        strategy_performance_json JSONB
    );
    """
    db_manager.execute_query(profit_reports_table_query)
    log.info("Table 'profit_reports' created successfully.")

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
