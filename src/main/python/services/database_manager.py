import psycopg2
import psycopg2.pool
import logging
from typing import Optional, Any, List, Tuple, Union, Dict
from contextlib import contextmanager
from threading import Lock

from src.main.python.core.config import DatabaseConfig
from src.main.python.core.exceptions import (
    DatabaseError, DatabaseConnectionError, DatabaseQueryError,
    handle_database_errors
)

log = logging.getLogger(__name__)


class DatabaseManager:
    """
    管理 PostgreSQL 數據庫連接和查詢執行
    
    特性：
    - 連接池管理
    - 事務支持
    - 錯誤處理和重試
    - 類型安全的查詢執行
    """
    
    def __init__(self, config: DatabaseConfig, pool_size: int = 5, max_connections: int = 20):
        """初始化數據庫管理器"""
        self.config = config
        self.pool_size = pool_size
        self.max_connections = max_connections
        self._pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        self._pool_lock = Lock()
        self._initialize_connection_pool()

    @handle_database_errors
    def _initialize_connection_pool(self):
        """初始化連接池"""
        try:
            log.info(f"Initializing database connection pool to {self.config.host}:{self.config.port}/{self.config.name}")
            
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=self.max_connections,
                host=self.config.host,
                port=self.config.port,
                database=self.config.name,
                user=self.config.user,
                password=self.config.password,
                # 連接池配置
                connection_factory=None,
                cursor_factory=None
            )
            
            # 測試連接
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    if result[0] != 1:
                        raise DatabaseConnectionError("Database connection test failed")
            
            log.info("Database connection pool initialized successfully")
            
        except psycopg2.OperationalError as e:
            log.error(f"Failed to initialize database connection pool: {e}")
            raise DatabaseConnectionError(f"Could not connect to database: {e}") from e
        except Exception as e:
            log.error(f"Unexpected error during database initialization: {e}")
            raise DatabaseError(f"Database initialization failed: {e}") from e

    @contextmanager
    def get_connection(self):
        """獲取數據庫連接（上下文管理器）"""
        if not self._pool:
            raise DatabaseConnectionError("Connection pool not initialized")
        
        conn = None
        try:
            with self._pool_lock:
                conn = self._pool.getconn()
            
            if conn is None:
                raise DatabaseConnectionError("Failed to get connection from pool")
            
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                with self._pool_lock:
                    self._pool.putconn(conn)

    @contextmanager
    def get_transaction(self):
        """獲取事務上下文"""
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as e:
                conn.rollback()
                log.error(f"Transaction rolled back due to error: {e}")
                raise

    @handle_database_errors
    def execute_query(
        self, 
        query: str, 
        params: Optional[Union[Tuple, Dict]] = None, 
        fetch: Optional[str] = None
    ) -> Optional[Union[List[Tuple], Tuple, Any]]:
        """
        執行 SQL 查詢
        
        Args:
            query: SQL 查詢語句
            params: 查詢參數
            fetch: 'one', 'all', 或 None
        
        Returns:
            查詢結果或 None
        """
        if not query.strip():
            raise DatabaseQueryError("Empty query provided")
        
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(query, params)
                    
                    if fetch == 'one':
                        result = cur.fetchone()
                    elif fetch == 'all':
                        result = cur.fetchall()
                    else:
                        result = None  # For INSERT, UPDATE, DELETE
                    
                    conn.commit()
                    return result
                    
                except psycopg2.Error as e:
                    conn.rollback()
                    log.error(f"Database query failed: {e}")
                    log.debug(f"Failed query: {query}")
                    log.debug(f"Query params: {params}")
                    raise DatabaseQueryError(f"Query execution failed: {e}") from e

    @handle_database_errors
    def execute_many(self, query: str, params_list: List[Union[Tuple, Dict]]) -> None:
        """
        批量執行 SQL 查詢
        
        Args:
            query: SQL 查詢語句
            params_list: 參數列表
        """
        if not query.strip():
            raise DatabaseQueryError("Empty query provided")
        
        if not params_list:
            log.warning("Empty parameters list provided for batch execution")
            return
        
        with self.get_transaction() as conn:
            with conn.cursor() as cur:
                try:
                    cur.executemany(query, params_list)
                    log.debug(f"Batch executed {len(params_list)} operations")
                    
                except psycopg2.Error as e:
                    log.error(f"Batch query execution failed: {e}")
                    log.debug(f"Failed query: {query}")
                    raise DatabaseQueryError(f"Batch execution failed: {e}") from e

    def check_connection(self) -> bool:
        """檢查數據庫連接狀態"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    result = cur.fetchone()
                    return result[0] == 1
        except Exception as e:
            log.warning(f"Database connection check failed: {e}")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """獲取連接信息"""
        if not self._pool:
            return {"status": "not_initialized"}
        
        return {
            "status": "active",
            "host": self.config.host,
            "port": self.config.port,
            "database": self.config.name,
            "pool_size": self.pool_size,
            "max_connections": self.max_connections,
            "available_connections": len(self._pool._pool) if hasattr(self._pool, '_pool') else "unknown"
        }

    def close(self):
        """關閉連接池"""
        if self._pool:
            try:
                with self._pool_lock:
                    self._pool.closeall()
                    self._pool = None
                log.info("Database connection pool closed")
            except Exception as e:
                log.error(f"Error closing database connection pool: {e}")

    def __enter__(self):
        """上下文管理器入口"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()
