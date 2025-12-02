from flask import Blueprint, request, jsonify
from app.database import get_db_connection
from app.middleware.auth_middleware import token_required, role_required
from app.utils.helpers import log_action, json_serializer
import json
from datetime import datetime, date

attendant_bp = Blueprint('attendant', __name__)

@attendant_bp.route('/attendant/assigned', methods=['GET'])
@token_required
@role_required(['ATTENDANT'])
def get_assigned_passes(current_user):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = date.today()
    
    query = """
    SELECT p.*, u.name as trustee_name
    FROM passes p
    LEFT JOIN users u ON p.trustee_id = u.id
    WHERE p.assigned_attendant_id = %s AND DATE(p.date) = %s
    ORDER BY p.time ASC
    """
    
    cursor.execute(query, (current_user['user_id'], today))
    passes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({'passes': passes}, default=json_serializer), 200

@attendant_bp.route('/attendant/upcoming', methods=['GET'])
@token_required
@role_required(['ATTENDANT'])
def get_upcoming_passes(current_user):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = date.today()
    
    query = """
    SELECT p.*, u.name as trustee_name
    FROM passes p
    LEFT JOIN users u ON p.trustee_id = u.id
    WHERE p.assigned_attendant_id = %s AND DATE(p.date) > %s
    ORDER BY p.date ASC, p.time ASC
    LIMIT 20
    """
    
    cursor.execute(query, (current_user['user_id'], today))
    passes = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({'passes': passes}, default=json_serializer), 200

@attendant_bp.route('/attendant/mark-contacted', methods=['POST'])
@token_required
@role_required(['ATTENDANT'])
def mark_contacted(current_user):
    data = request.json
    pass_id = data.get('pass_id')
    
    if not pass_id:
        return jsonify({'error': 'pass_id is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Update pass status
        cursor.execute("""
            UPDATE passes SET status = 'CONTACTED', updated_at = NOW()
            WHERE id = %s AND assigned_attendant_id = %s
        """, (pass_id, current_user['user_id']))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Pass not found or not assigned to you'}), 404
        
        conn.commit()
        
        # Log action
        log_action(conn, current_user['user_id'], 'MARK_CONTACTED', 'PASS', pass_id, {})
        
        return jsonify({'message': 'Pass marked as contacted'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@attendant_bp.route('/attendant/update-status', methods=['POST'])
@token_required
@role_required(['ATTENDANT'])
def update_status(current_user):
    data = request.json
    pass_id = data.get('pass_id')
    status = data.get('status')
    
    valid_statuses = ['REACHED', 'AT_GATE', 'COMPLETED', 'ISSUE']
    
    if not pass_id or not status:
        return jsonify({'error': 'pass_id and status are required'}), 400
    
    if status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if pass exists and is assigned to this attendant
        cursor.execute("""
            SELECT status FROM passes 
            WHERE id = %s AND assigned_attendant_id = %s
        """, (pass_id, current_user['user_id']))
        
        pass_data = cursor.fetchone()
        if not pass_data:
            return jsonify({'error': 'Pass not found or not assigned to you'}), 404
        
        # Update pass status
        cursor.execute("""
            UPDATE passes SET status = %s, updated_at = NOW()
            WHERE id = %s
        """, (status, pass_id))
        
        # Insert scan record for tracking
        if status in ['REACHED', 'AT_GATE', 'COMPLETED']:
            stage_map = {'REACHED': 'ARRIVED', 'AT_GATE': 'AT_GATE', 'COMPLETED': 'COMPLETED'}
            cursor.execute("""
                INSERT INTO scans (pass_id, stage, source, created_at)
                VALUES (%s, %s, 'ATTENDANT', NOW())
            """, (pass_id, stage_map[status]))
        
        conn.commit()
        
        # Log action
        log_action(conn, current_user['user_id'], 'UPDATE_STATUS', 'PASS', pass_id, {'status': status})
        
        return jsonify({'message': f'Pass status updated to {status}'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@attendant_bp.route('/attendant/add-note', methods=['POST'])
@token_required
@role_required(['ATTENDANT'])
def add_note(current_user):
    data = request.json
    pass_id = data.get('pass_id')
    note = data.get('note', '').strip()
    
    if not pass_id or not note:
        return jsonify({'error': 'pass_id and note are required'}), 400
    
    if len(note) > 100:
        return jsonify({'error': 'Note must be 100 characters or less'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get current notes
        cursor.execute("""
            SELECT attendant_notes FROM passes 
            WHERE id = %s AND assigned_attendant_id = %s
        """, (pass_id, current_user['user_id']))
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'Pass not found or not assigned to you'}), 404
        
        # Append new note
        current_notes = json.loads(result['attendant_notes']) if result['attendant_notes'] else []
        current_notes.append({
            'user_id': current_user['user_id'],
            'note': note,
            'timestamp': datetime.now().isoformat()
        })
        
        # Update pass
        cursor.execute("""
            UPDATE passes SET attendant_notes = %s, updated_at = NOW()
            WHERE id = %s
        """, (json.dumps(current_notes), pass_id))
        
        conn.commit()
        
        return jsonify({'message': 'Note added successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@attendant_bp.route('/attendant/attendance/in', methods=['POST'])
@token_required
@role_required(['ATTENDANT'])
def mark_attendance_in(current_user):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = date.today()
    
    try:
        # Check if already marked in
        cursor.execute("""
            SELECT id, time_in FROM attendant_attendance
            WHERE attendant_id = %s AND date = %s
        """, (current_user['user_id'], today))
        
        existing = cursor.fetchone()
        
        if existing and existing['time_in']:
            return jsonify({'error': 'Already marked in for today'}), 400
        
        if existing:
            # Update existing record
            cursor.execute("""
                UPDATE attendant_attendance 
                SET time_in = NOW()
                WHERE id = %s
            """, (existing['id'],))
        else:
            # Insert new record
            cursor.execute("""
                INSERT INTO attendant_attendance (attendant_id, date, time_in)
                VALUES (%s, %s, NOW())
            """, (current_user['user_id'], today))
        
        conn.commit()
        
        return jsonify({'message': 'Attendance marked IN'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@attendant_bp.route('/attendant/attendance/out', methods=['POST'])
@token_required
@role_required(['ATTENDANT'])
def mark_attendance_out(current_user):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = date.today()
    
    try:
        # Get today's attendance record
        cursor.execute("""
            SELECT id, time_in FROM attendant_attendance
            WHERE attendant_id = %s AND date = %s
        """, (current_user['user_id'], today))
        
        record = cursor.fetchone()
        
        if not record:
            return jsonify({'error': 'Please mark attendance IN first'}), 400
        
        if not record['time_in']:
            return jsonify({'error': 'Please mark attendance IN first'}), 400
        
        # Calculate total hours and mark out
        cursor.execute("""
            UPDATE attendant_attendance 
            SET time_out = NOW(),
                total_hours = TIMESTAMPDIFF(SECOND, time_in, NOW()) / 3600
            WHERE id = %s
        """, (record['id'],))
        
        conn.commit()
        
        return jsonify({'message': 'Attendance marked OUT'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
