from flask import Blueprint, request, jsonify
from app.database import get_db_connection
from app.middleware.auth_middleware import token_required, role_required
from app.utils.qr_generator import generate_qr_string
from app.utils.helpers import assign_attendant_round_robin, log_action, json_serializer
from datetime import datetime

aarti_bp = Blueprint('aarti', __name__)

@aarti_bp.route('/aarti', methods=['GET'])
@token_required
def get_aarti_slots(current_user):
    date_param = request.args.get('date')
    
    if not date_param:
        date_param = datetime.now().date()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT * FROM aarti WHERE date = %s ORDER BY name
    """, (date_param,))
    
    aarti_slots = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({'aarti_slots': aarti_slots}, default=json_serializer), 200

@aarti_bp.route('/aarti/book', methods=['POST'])
@token_required
@role_required(['TRUSTEE', 'ASSISTANT', 'ADMIN'])
def book_aarti(current_user):
    data = request.json
    
    required_fields = ['aarti_id', 'visitor_name', 'visitor_phone', 'count']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get aarti slot
        cursor.execute("""
            SELECT * FROM aarti WHERE id = %s
        """, (data['aarti_id'],))
        
        aarti = cursor.fetchone()
        
        if not aarti:
            return jsonify({'error': 'Aarti slot not found'}), 404
        
        if aarti['status'] == 'CLOSED':
            return jsonify({'error': 'Aarti slot is closed'}), 400
        
        remaining = aarti['total_capacity'] - aarti['booked_capacity']
        if remaining < data['count']:
            return jsonify({'error': f'Only {remaining} slots available'}), 400
        
        # Get settings
        cursor.execute("SELECT grace_minutes_default FROM settings WHERE id = 1")
        settings = cursor.fetchone()
        grace_minutes = settings['grace_minutes_default'] if settings else 30
        
        # Assign attendant
        attendant = assign_attendant_round_robin(conn)
        if not attendant:
            return jsonify({'error': 'No active attendants available'}), 400
        
        # Generate QR
        qr_string = generate_qr_string()
        
        # Create pass for aarti
        cursor.execute("""
            INSERT INTO passes (
                trustee_id, visitor_name, visitor_phone, visitor_email,
                total_people, darshan_type, date, time, grace_minutes,
                assigned_attendant_id, qr_code_string, status, trustee_note
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            current_user['user_id'],
            data['visitor_name'],
            data['visitor_phone'],
            data.get('visitor_email'),
            data['count'],
            'NORMAL',
            aarti['date'],
            '06:00:00',  # Default time, adjust as needed
            grace_minutes,
            attendant['id'],
            qr_string,
            'NOT_CONTACTED',
            f"Aarti: {aarti['name']}"
        ))
        
        pass_id = cursor.lastrowid
        
        # Update aarti capacity
        cursor.execute("""
            UPDATE aarti SET booked_capacity = booked_capacity + %s
            WHERE id = %s
        """, (data['count'], data['aarti_id']))
        
        conn.commit()
        
        # Log action
        log_action(conn, current_user['user_id'], 'BOOK_AARTI', 'AARTI', data['aarti_id'], data)
        
        return jsonify({
            'message': 'Aarti booked successfully',
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

@aarti_bp.route('/aarti/update-capacity', methods=['POST'])
@token_required
@role_required(['ADMIN', 'TRUSTEE'])
def update_aarti_capacity(current_user):
    data = request.json
    
    required_fields = ['name', 'date', 'total_capacity']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if aarti slot exists
        cursor.execute("""
            SELECT id FROM aarti WHERE name = %s AND date = %s
        """, (data['name'], data['date']))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing
            cursor.execute("""
                UPDATE aarti SET total_capacity = %s, status = %s
                WHERE id = %s
            """, (data['total_capacity'], data.get('status', 'OPEN'), existing['id']))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO aarti (name, date, total_capacity, booked_capacity, status)
                VALUES (%s, %s, %s, 0, %s)
            """, (data['name'], data['date'], data['total_capacity'], data.get('status', 'OPEN')))
        
        conn.commit()
        
        return jsonify({'message': 'Aarti capacity updated'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
