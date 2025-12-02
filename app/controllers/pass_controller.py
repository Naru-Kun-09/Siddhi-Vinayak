from flask import Blueprint, request, jsonify
from app.database import get_db_connection
from app.middleware.auth_middleware import token_required, role_required
from app.utils.qr_generator import generate_qr_string
from app.utils.helpers import assign_attendant_round_robin, log_action, json_serializer
import json
from datetime import datetime

pass_bp = Blueprint('pass', __name__)

@pass_bp.route('/passes', methods=['POST'])
@token_required
@role_required(['TRUSTEE', 'ASSISTANT', 'ADMIN'])
def create_pass(current_user):
    data = request.json
    
    # Validate required fields
    required_fields = ['visitor_name', 'visitor_phone', 'total_people', 'darshan_type', 'date', 'time']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get grace minutes from settings
        cursor.execute("SELECT grace_minutes_default FROM settings WHERE id = 1")
        settings = cursor.fetchone()
        grace_minutes = settings['grace_minutes_default'] if settings else 30
        
        # Assign attendant using round-robin
        attendant = assign_attendant_round_robin(conn)
        if not attendant:
            return jsonify({'error': 'No active attendants available'}), 400
        
        # Generate QR code
        qr_string = generate_qr_string()
        
        # Prepare vastra data
        vastra_names = json.dumps(data.get('vastra_names', [])) if data.get('vastra_names') else None
        
        # Insert pass
        query = """
        INSERT INTO passes (
            trustee_id, assistant_id, visitor_name, visitor_phone, visitor_email,
            total_people, darshan_type, vastra_count, vastra_names, date, time,
            grace_minutes, assigned_attendant_id, trustee_note, qr_code_string, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            current_user['user_id'],
            data.get('assistant_id'),
            data['visitor_name'],
            data['visitor_phone'],
            data.get('visitor_email'),
            data['total_people'],
            data['darshan_type'],
            data.get('vastra_count'),
            vastra_names,
            data['date'],
            data['time'],
            grace_minutes,
            attendant['id'],
            data.get('trustee_note'),
            qr_string,
            'NOT_CONTACTED'
        ))
        
        pass_id = cursor.lastrowid
        conn.commit()
        
        # Log action
        log_action(conn, current_user['user_id'], 'CREATE_PASS', 'PASS', pass_id, data)
        
        return jsonify({
            'message': 'Pass created successfully',
            'pass_id': pass_id,
            'qr_code': qr_string,
            'attendant': {
                'name': attendant['name'],
                'phone': attendant['phone']
            }
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@pass_bp.route('/passes/today', methods=['GET'])
@token_required
def get_today_passes(current_user):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.now().date()
    
    # Role-based filtering
    if current_user['role'] == 'TRUSTEE':
        query = """
        SELECT p.*, u.name as attendant_name, u.phone as attendant_phone
        FROM passes p
        LEFT JOIN users u ON p.assigned_attendant_id = u.id
        WHERE p.trustee_id = %s AND DATE(p.date) = %s
        ORDER BY p.time ASC
        """
        cursor.execute(query, (current_user['user_id'], today))
        
    elif current_user['role'] == 'ATTENDANT':
        query = """
        SELECT p.*, u.name as trustee_name
        FROM passes p
        LEFT JOIN users u ON p.trustee_id = u.id
        WHERE p.assigned_attendant_id = %s AND DATE(p.date) = %s
        ORDER BY p.time ASC
        """
        cursor.execute(query, (current_user['user_id'], today))
        
    else:  # ADMIN
        query = """
        SELECT p.*, 
               t.name as trustee_name,
               a.name as attendant_name,
               a.phone as attendant_phone
        FROM passes p
        LEFT JOIN users t ON p.trustee_id = t.id
        LEFT JOIN users a ON p.assigned_attendant_id = a.id
        WHERE DATE(p.date) = %s
        ORDER BY p.time ASC
        """
        cursor.execute(query, (today,))
    
    passes = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify({'passes': passes}, default=json_serializer), 200

@pass_bp.route('/passes/<int:pass_id>', methods=['GET'])
@token_required
def get_pass_details(current_user, pass_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get pass details
    cursor.execute("""
        SELECT p.*, 
               t.name as trustee_name,
               a.name as attendant_name,
               a.phone as attendant_phone
        FROM passes p
        LEFT JOIN users t ON p.trustee_id = t.id
        LEFT JOIN users a ON p.assigned_attendant_id = a.id
        WHERE p.id = %s
    """, (pass_id,))
    
    pass_data = cursor.fetchone()
    
    if not pass_data:
        cursor.close()
        conn.close()
        return jsonify({'error': 'Pass not found'}), 404
    
    # Get timeline (scans)
    cursor.execute("""
        SELECT * FROM scans WHERE pass_id = %s ORDER BY created_at ASC
    """, (pass_id,))
    
    timeline = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({
        'pass': pass_data,
        'timeline': timeline
    }, default=json_serializer), 200
