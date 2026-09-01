"""
db.py — Neon PostgreSQL Database Connection Layer
Handles all CRUD operations for users, active_charters, and charter_reports.
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    """Create and return a new database connection."""
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ─────────────────────────────────────────────
# USER OPERATIONS
# ─────────────────────────────────────────────

def authenticate_user(employee_id, password):
    """Authenticate user by employee_id and plain-text password. Returns user dict or None."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, employee_id, full_name, role, department FROM users WHERE employee_id = %s AND password = %s",
                (employee_id, password)
            )
            user = cur.fetchone()
            return dict(user) if user else None
    finally:
        conn.close()


def get_user_by_id(user_id):
    """Fetch a single user by UUID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, employee_id, full_name, role, department FROM users WHERE id = %s",
                (user_id,)
            )
            user = cur.fetchone()
            return dict(user) if user else None
    finally:
        conn.close()


# ─────────────────────────────────────────────
# ACTIVE CHARTERS OPERATIONS
# ─────────────────────────────────────────────

def get_active_charters(user_id=None):
    """Fetch all active charters, optionally filtered by user_id."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    "SELECT * FROM active_charters WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
            else:
                cur.execute("SELECT * FROM active_charters ORDER BY created_at DESC")
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def create_charter(data):
    """Insert a new active charter record."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO active_charters 
                (user_id, vessel_name, vessel_type, cargo_type, cargo_volume_tons,
                 origin_port, destination_port, strategy_type, contract_rate_per_ton,
                 total_landed_cost, status, estimated_arrival_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                data.get('user_id'),
                data['vessel_name'],
                data['vessel_type'],
                data.get('cargo_type', 'Coking Coal'),
                data['cargo_volume_tons'],
                data['origin_port'],
                data['destination_port'],
                data.get('strategy_type', 'CVC'),
                data['contract_rate_per_ton'],
                data['total_landed_cost'],
                data.get('status', 'En-Route'),
                data['estimated_arrival_date']
            ))
            conn.commit()
            result = cur.fetchone()
            return dict(result) if result else None
    finally:
        conn.close()


def update_charter_status(charter_id, new_status):
    """Update the status of an existing charter."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE active_charters SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s RETURNING *",
                (new_status, charter_id)
            )
            conn.commit()
            result = cur.fetchone()
            return dict(result) if result else None
    finally:
        conn.close()


# ─────────────────────────────────────────────
# CHARTER REPORTS OPERATIONS
# ─────────────────────────────────────────────

def get_reports(user_id=None):
    """Fetch all saved reports, optionally filtered by user_id."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if user_id:
                cur.execute(
                    "SELECT * FROM charter_reports WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,)
                )
            else:
                cur.execute("SELECT * FROM charter_reports ORDER BY created_at DESC")
            rows = cur.fetchall()
            return [dict(r) for r in rows]
    finally:
        conn.close()


def save_report(data):
    """Save a new charter/forecast report."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO charter_reports
                (user_id, report_title, trade_route, destination_port, cargo_volume_tons,
                 recommended_vessel, market_signal, forecasted_rate_per_ton,
                 estimated_total_cost, projected_arbitrage_savings, demurrage_risk_usd,
                 forecast_timeline_data)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                data.get('user_id'),
                data['report_title'],
                data['trade_route'],
                data['destination_port'],
                data['cargo_volume_tons'],
                data['recommended_vessel'],
                data['market_signal'],
                data['forecasted_rate_per_ton'],
                data['estimated_total_cost'],
                data.get('projected_arbitrage_savings', 0),
                data.get('demurrage_risk_usd', 0),
                data.get('forecast_timeline_data')
            ))
            conn.commit()
            result = cur.fetchone()
            return dict(result) if result else None
    finally:
        conn.close()


def delete_report(report_id):
    """Delete a report by ID."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM charter_reports WHERE id = %s", (report_id,))
            conn.commit()
            return cur.rowcount > 0
    finally:
        conn.close()
