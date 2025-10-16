#!/usr/bin/env python3
"""
Database Connection Monitor
Monitors PostgreSQL connections and helps diagnose connection issues
"""

import os
import psycopg2
import time
from datetime import datetime
import sys

def get_db_connection():
    """Get database connection from environment"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return None
    
    try:
        conn = psycopg2.connect(database_url)
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None

def check_connections():
    """Check current database connections"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Get connection count
        cursor.execute("SELECT count(*) FROM pg_stat_activity;")
        total_connections = cursor.fetchone()[0]
        
        # Get connections by user
        cursor.execute("""
            SELECT usename, count(*) as conn_count, 
                   array_agg(DISTINCT COALESCE(state, 'unknown')) as states
            FROM pg_stat_activity 
            GROUP BY usename 
            ORDER BY conn_count DESC;
        """)
        user_connections = cursor.fetchall()
        
        # Get max connections setting
        cursor.execute("SHOW max_connections;")
        max_connections = int(cursor.fetchone()[0])
        
        print(f"\n📊 Database Connection Status - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🔗 Total connections: {total_connections}/{max_connections}")
        print(f"📈 Usage: {(total_connections/max_connections)*100:.1f}%")
        
        if total_connections > max_connections * 0.8:
            print("⚠️  WARNING: High connection usage!")
        
        print("\n👥 Connections by user:")
        for user, count, states in user_connections:
            print(f"  {user}: {count} connections (states: {', '.join(states)})")
        
        # Check for idle connections
        cursor.execute("""
            SELECT count(*) FROM pg_stat_activity 
            WHERE state = 'idle' AND query_start < now() - interval '5 minutes';
        """)
        idle_connections = cursor.fetchone()[0]
        
        if idle_connections > 0:
            print(f"\n💤 Idle connections (>5min): {idle_connections}")
            print("💡 Consider cleaning up idle connections")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error checking connections: {e}")
        return False

def cleanup_idle_connections():
    """Clean up idle connections"""
    conn = get_db_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Find idle connections older than 1 hour
        cursor.execute("""
            SELECT pid, usename, query_start, state 
            FROM pg_stat_activity 
            WHERE state = 'idle' 
            AND query_start < now() - interval '1 hour'
            AND usename != 'postgres';
        """)
        
        idle_connections = cursor.fetchall()
        
        if not idle_connections:
            print("✅ No idle connections to clean up")
            return True
        
        print(f"🧹 Found {len(idle_connections)} idle connections to clean up:")
        
        terminated_count = 0
        for pid, user, query_start, state in idle_connections:
            try:
                cursor.execute(f"SELECT pg_terminate_backend({pid});")
                terminated_count += 1
                print(f"  ✅ Terminated connection {pid} (user: {user}, idle since: {query_start})")
            except Exception as e:
                print(f"  ❌ Failed to terminate connection {pid}: {e}")
        
        print(f"\n🎯 Successfully terminated {terminated_count} idle connections")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error cleaning up connections: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == 'cleanup':
        print("🧹 Starting connection cleanup...")
        cleanup_idle_connections()
    else:
        print("📊 Monitoring database connections...")
        check_connections()
        
        print("\n💡 Usage:")
        print("  python monitor_db_connections.py        # Check connections")
        print("  python monitor_db_connections.py cleanup  # Clean up idle connections")

if __name__ == "__main__":
    main()
