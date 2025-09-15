"""
Sandbox Database System for SQL Learning Platform
================================================
This module provides dynamic database creation, data population,
resource management, and cleanup for user sandbox environments.
"""

import os
import asyncio
import uuid
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from contextlib import asynccontextmanager
import psycopg2
from psycopg2 import sql
import asyncpg
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.engine.url import make_url

from .database import DATABASE_URL, SessionLocal
from .models import UserSandbox, TestCase, ProblemSchema, SandboxStatus, ExecutionStatus
from .schemas import UserSandboxCreate, ExecutionResultCreate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SandboxConnectionPool:
    """Manages database connections for sandbox environments"""
    
    def __init__(self, max_connections: int = 50):
        self.max_connections = max_connections
        self.connection_pools: Dict[str, asyncpg.Pool] = {}
        self._cleanup_lock = asyncio.Lock()
    
    async def get_pool(self, connection_string: str) -> asyncpg.Pool:
        """Get or create a connection pool for a sandbox database"""
        if connection_string not in self.connection_pools:
            try:
                pool = await asyncpg.create_pool(
                    connection_string,
                    min_size=1,
                    max_size=5,
                    command_timeout=30,
                    server_settings={
                        'statement_timeout': '30000',  # 30 seconds
                        'lock_timeout': '10000',       # 10 seconds
                        'idle_in_transaction_session_timeout': '30000'  # 30 seconds
                    }
                )
                self.connection_pools[connection_string] = pool
                logger.info(f"Created connection pool for sandbox database")
            except Exception as e:
                logger.error(f"Failed to create connection pool: {e}")
                raise
        
        return self.connection_pools[connection_string]
    
    async def close_pool(self, connection_string: str):
        """Close and remove a connection pool"""
        if connection_string in self.connection_pools:
            pool = self.connection_pools.pop(connection_string)
            await pool.close()
            logger.info(f"Closed connection pool for sandbox database")
    
    async def cleanup_all(self):
        """Close all connection pools"""
        async with self._cleanup_lock:
            for connection_string, pool in self.connection_pools.items():
                await pool.close()
            self.connection_pools.clear()
            logger.info("Closed all sandbox connection pools")

# Global connection pool manager
sandbox_pool_manager = SandboxConnectionPool()

class SandboxManager:
    """Manages sandbox database lifecycle and operations"""
    
    def __init__(self):
        self.base_db_url = DATABASE_URL
        self._parse_database_url()
    
    def _parse_database_url(self):
        """Parse the main database URL to extract connection details using sqlalchemy"""
        try:
            url = make_url(self.base_db_url)
            self.db_user = url.username or 'postgres'
            self.db_password = url.password or ''
            self.db_host = url.host or 'localhost'
            self.db_port = url.port or 5432
            self.db_name = url.database or 'postgres'
        except Exception as e:
            logger.error(f"Failed to parse DATABASE_URL: {e}")
            # Fallback to defaults
            self.db_user = 'postgres'
            self.db_password = ''
            self.db_host = 'localhost'
            self.db_port = 5432
            self.db_name = 'postgres'
    
    def _generate_sandbox_name(self, user_id: str, problem_id: str) -> str:
        """Generate a unique sandbox database name"""
        # Create a safe database name with timestamp
        timestamp = int(time.time())
        short_user_id = user_id[:8]
        short_problem_id = problem_id[:8]
        return f"sandbox_{short_user_id}_{short_problem_id}_{timestamp}"
    
    def _build_connection_string(self, database_name: str) -> str:
        """Build connection string for a sandbox database"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{database_name}"
    
    async def create_sandbox(self, user_id: str, problem_id: str, expires_in_hours: int = 2) -> UserSandbox:
        """Create a new sandbox database for a user and problem"""
        db = SessionLocal()
        
        try:
            # Check if user already has an active sandbox for this problem
            existing_sandbox = db.query(UserSandbox).filter(
                UserSandbox.user_id == user_id,
                UserSandbox.problem_id == problem_id,
                UserSandbox.status == SandboxStatus.ACTIVE.value
            ).first()
            
            if existing_sandbox:
                # Extend expiry of existing sandbox
                existing_sandbox.expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
                existing_sandbox.last_accessed_at = datetime.utcnow()
                db.commit()
                return existing_sandbox
            
            # Generate unique database name
            sandbox_db_name = self._generate_sandbox_name(user_id, problem_id)
            connection_string = self._build_connection_string(sandbox_db_name)
            
            # Create the sandbox database
            await self._create_database(sandbox_db_name)
            
            # Create UserSandbox record
            sandbox = UserSandbox(
                user_id=user_id,
                problem_id=problem_id,
                database_name=sandbox_db_name,
                status=SandboxStatus.ACTIVE.value,
                expires_at=datetime.utcnow() + timedelta(hours=expires_in_hours),
                last_accessed_at=datetime.utcnow()
            )
            
            db.add(sandbox)
            db.commit()
            db.refresh(sandbox)
            
            # Populate sandbox with test data
            await self._populate_sandbox_data(sandbox_db_name, problem_id, db)
            
            logger.info(f"Created sandbox {sandbox_db_name} for user {user_id}, problem {problem_id}")
            return sandbox
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create sandbox: {e}")
            raise
        finally:
            db.close()
    
    async def _create_database(self, database_name: str):
        """Create a new PostgreSQL database"""
        # Connect to the main database to create new one
        admin_connection_string = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/postgres"
        
        try:
            conn = await asyncpg.connect(admin_connection_string)
            
            # Create the database
            await conn.execute(f'CREATE DATABASE "{database_name}"')
            
            await conn.close()
            
            logger.info(f"Created database: {database_name}")
            
        except asyncpg.DuplicateDatabaseError:
            logger.warning(f"Database {database_name} already exists")
        except Exception as e:
            logger.error(f"Failed to create database {database_name}: {e}")
            raise
    
    async def _populate_sandbox_data(self, sandbox_db_name: str, problem_id: str, db):
        """Populate sandbox database with problem schema and test data"""
        connection_string = self._build_connection_string(sandbox_db_name)
        
        try:
            # Get problem schemas and test cases
            problem_schemas = db.query(ProblemSchema).filter(
                ProblemSchema.problem_id == problem_id
            ).all()
            
            test_cases = db.query(TestCase).filter(
                TestCase.problem_id == problem_id
            ).all()
            
            pool = await sandbox_pool_manager.get_pool(connection_string)
            
            async with pool.acquire() as conn:
                # Create tables from problem schemas
                for schema in problem_schemas:
                    await self._create_table_from_schema(conn, schema.table_name, schema.schema_definition)
                    
                    # Insert sample data
                    if schema.sample_data:
                        await self._insert_sample_data(conn, schema.table_name, schema.sample_data)
                
                # Create indexes and constraints
                for schema in problem_schemas:
                    if schema.indexes:
                        await self._create_indexes(conn, schema.table_name, schema.indexes)
                    
                    if schema.constraints:
                        await self._create_constraints(conn, schema.table_name, schema.constraints)
            
            logger.info(f"Populated sandbox {sandbox_db_name} with {len(problem_schemas)} tables")
            
        except Exception as e:
            logger.error(f"Failed to populate sandbox {sandbox_db_name}: {e}")
            raise
    
    async def _create_table_from_schema(self, conn: asyncpg.Connection, table_name: str, schema_definition: Dict[str, Any]):
        """Create a table from schema definition"""
        try:
            # Build CREATE TABLE statement
            columns = []
            for col_name, col_def in schema_definition.get('columns', {}).items():
                col_type = col_def.get('type', 'TEXT')
                nullable = 'NULL' if col_def.get('nullable', True) else 'NOT NULL'
                default = f"DEFAULT {col_def['default']}" if 'default' in col_def else ''
                primary_key = 'PRIMARY KEY' if col_def.get('primary_key', False) else ''
                
                column_def = f'"{col_name}" {col_type} {nullable} {default} {primary_key}'.strip()
                columns.append(column_def)
            
            if columns:
                create_table_sql = f'CREATE TABLE "{table_name}" ({", ".join(columns)})'
                await conn.execute(create_table_sql)
                logger.info(f"Created table: {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            raise
    
    async def _insert_sample_data(self, conn: asyncpg.Connection, table_name: str, sample_data: List[Dict[str, Any]]):
        """Insert sample data into a table"""
        if not sample_data:
            return
        
        try:
            for row in sample_data:
                if row:  # Skip empty rows
                    columns = list(row.keys())
                    values = list(row.values())
                    placeholders = [f'${i+1}' for i in range(len(values))]
                    
                    quoted_columns = [f'"{col}"' for col in columns]
                    insert_sql = f'INSERT INTO "{table_name}" ({", ".join(quoted_columns)}) VALUES ({", ".join(placeholders)})'
                    await conn.execute(insert_sql, *values)
            
            logger.info(f"Inserted {len(sample_data)} rows into {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to insert sample data into {table_name}: {e}")
            raise
    
    async def _create_indexes(self, conn: asyncpg.Connection, table_name: str, indexes: List[Dict[str, Any]]):
        """Create indexes for a table"""
        for index in indexes:
            try:
                index_name = index.get('name', f"idx_{table_name}_{index['columns'][0]}")
                columns = index.get('columns', [])
                unique = 'UNIQUE' if index.get('unique', False) else ''
                
                if columns:
                    quoted_columns = [f'"{col}"' for col in columns]
                    create_index_sql = f'CREATE {unique} INDEX "{index_name}" ON "{table_name}" ({", ".join(quoted_columns)})'
                    await conn.execute(create_index_sql)
                    logger.info(f"Created index: {index_name}")
            
            except Exception as e:
                logger.error(f"Failed to create index on {table_name}: {e}")
    
    async def _create_constraints(self, conn: asyncpg.Connection, table_name: str, constraints: List[Dict[str, Any]]):
        """Create constraints for a table"""
        for constraint in constraints:
            try:
                constraint_type = constraint.get('type')
                constraint_name = constraint.get('name', f"con_{table_name}_{constraint_type}")
                
                if constraint_type == 'foreign_key':
                    column = constraint['column']
                    ref_table = constraint['references']['table']
                    ref_column = constraint['references']['column']
                    
                    alter_sql = f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{constraint_name}" FOREIGN KEY ("{column}") REFERENCES "{ref_table}" ("{ref_column}")'
                    await conn.execute(alter_sql)
                    logger.info(f"Created foreign key constraint: {constraint_name}")
                
                elif constraint_type == 'check':
                    check_condition = constraint['condition']
                    alter_sql = f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{constraint_name}" CHECK ({check_condition})'
                    await conn.execute(alter_sql)
                    logger.info(f"Created check constraint: {constraint_name}")
            
            except Exception as e:
                logger.error(f"Failed to create constraint on {table_name}: {e}")
    
    async def execute_query(self, sandbox_id: str, query: str, timeout_seconds: int = 30) -> Tuple[Dict[str, Any], ExecutionStatus]:
        """Execute a SQL query in a sandbox environment with resource limits"""
        db = SessionLocal()
        
        try:
            # Get sandbox details
            sandbox = db.query(UserSandbox).filter(UserSandbox.id == sandbox_id).first()
            if not sandbox:
                raise ValueError(f"Sandbox {sandbox_id} not found")
            
            if sandbox.status != SandboxStatus.ACTIVE.value:
                raise ValueError(f"Sandbox {sandbox_id} is not active")
            
            # Update last accessed time
            sandbox.last_accessed_at = datetime.utcnow()
            db.commit()
            
            connection_string = self._build_connection_string(sandbox.database_name)
            pool = await sandbox_pool_manager.get_pool(connection_string)
            
            start_time = time.time()
            
            async with pool.acquire() as conn:
                # Set resource limits
                await conn.execute(f"SET statement_timeout = '{timeout_seconds}s'")
                await conn.execute("SET lock_timeout = '10s'")
                
                try:
                    # Execute the query
                    result = await conn.fetch(query)
                    
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    # Convert result to JSON-serializable format
                    result_data = []
                    if result:
                        columns = list(result[0].keys())
                        for row in result:
                            row_dict = {}
                            for col in columns:
                                value = row[col]
                                # Handle non-serializable types
                                if hasattr(value, 'isoformat'):  # datetime objects
                                    value = value.isoformat()
                                elif isinstance(value, (bytes, bytearray)):
                                    value = str(value)
                                row_dict[col] = value
                            result_data.append(row_dict)
                    
                    return {
                        'status': ExecutionStatus.SUCCESS,
                        'execution_time_ms': execution_time_ms,
                        'result': result_data,
                        'rows_affected': len(result_data),
                        'columns': list(result[0].keys()) if result else []
                    }, ExecutionStatus.SUCCESS
                
                except asyncpg.QueryCanceledError:
                    return {
                        'status': ExecutionStatus.TIMEOUT,
                        'error': f'Query execution timed out after {timeout_seconds} seconds',
                        'execution_time_ms': timeout_seconds * 1000
                    }, ExecutionStatus.TIMEOUT
                
                except asyncpg.PostgresError as e:
                    return {
                        'status': ExecutionStatus.ERROR,
                        'error': str(e),
                        'error_code': e.sqlstate,
                        'execution_time_ms': int((time.time() - start_time) * 1000)
                    }, ExecutionStatus.ERROR
        
        except Exception as e:
            logger.error(f"Failed to execute query in sandbox {sandbox_id}: {e}")
            return {
                'status': ExecutionStatus.ERROR,
                'error': str(e),
                'execution_time_ms': 0
            }, ExecutionStatus.ERROR
        
        finally:
            db.close()
    
    async def cleanup_expired_sandboxes(self):
        """Clean up expired sandbox databases"""
        db = SessionLocal()
        
        try:
            # Find expired sandboxes
            expired_sandboxes = db.query(UserSandbox).filter(
                UserSandbox.status == SandboxStatus.ACTIVE.value,
                UserSandbox.expires_at < datetime.utcnow()
            ).all()
            
            logger.info(f"Found {len(expired_sandboxes)} expired sandboxes to cleanup")
            
            for sandbox in expired_sandboxes:
                try:
                    # Mark as cleanup pending
                    sandbox.status = SandboxStatus.CLEANUP_PENDING.value
                    sandbox.cleanup_scheduled_at = datetime.utcnow()
                    db.commit()
                    
                    # Close connection pool
                    connection_string = self._build_connection_string(sandbox.database_name)
                    await sandbox_pool_manager.close_pool(connection_string)
                    
                    # Drop the database
                    await self._drop_database(sandbox.database_name)
                    
                    # Mark as expired
                    sandbox.status = SandboxStatus.EXPIRED.value
                    db.commit()
                    
                    logger.info(f"Cleaned up sandbox: {sandbox.database_name}")
                
                except Exception as e:
                    logger.error(f"Failed to cleanup sandbox {sandbox.database_name}: {e}")
                    # Continue with other sandboxes
                    continue
        
        except Exception as e:
            logger.error(f"Failed to cleanup expired sandboxes: {e}")
        
        finally:
            db.close()
    
    async def _drop_database(self, database_name: str):
        """Drop a sandbox database"""
        admin_connection_string = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/postgres"
        
        try:
            conn = await asyncpg.connect(admin_connection_string)
            
            # Terminate active connections to the database
            await conn.execute(f"""
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = '{database_name}' AND pid <> pg_backend_pid()
            """)
            
            # Drop the database
            await conn.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
            
            await conn.close()
            
            logger.info(f"Dropped database: {database_name}")
            
        except Exception as e:
            logger.error(f"Failed to drop database {database_name}: {e}")
            raise

# Global sandbox manager instance
sandbox_manager = SandboxManager()

# Background cleanup task
async def start_cleanup_scheduler():
    """Start the background cleanup scheduler"""
    while True:
        try:
            await sandbox_manager.cleanup_expired_sandboxes()
            # Run cleanup every 30 minutes
            await asyncio.sleep(30 * 60)
        except Exception as e:
            logger.error(f"Cleanup scheduler error: {e}")
            # Wait 5 minutes before retrying on error
            await asyncio.sleep(5 * 60)

# Utility functions for API integration
async def create_user_sandbox(user_id: str, problem_id: str) -> UserSandbox:
    """Create a sandbox for a user and problem"""
    return await sandbox_manager.create_sandbox(user_id, problem_id)

async def execute_sandbox_query(sandbox_id: str, query: str, timeout_seconds: int = 30) -> Tuple[Dict[str, Any], ExecutionStatus]:
    """Execute a query in a sandbox"""
    return await sandbox_manager.execute_query(sandbox_id, query, timeout_seconds)

async def cleanup_sandbox_resources():
    """Cleanup all sandbox resources (for shutdown)"""
    await sandbox_pool_manager.cleanup_all()