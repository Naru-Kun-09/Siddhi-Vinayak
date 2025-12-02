from flask import Blueprint, request, jsonify
from app.database import get_db_connection
from app.middleware.auth_middleware import token_required, role_required
from app.utils.helpers import json_serializer
import bcrypt

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/users', methods=['POST'])
@token_required
@role_required(['ADMIN'])
def create_user(current_user):
    data = request.json
    
    required_fields = ['name', 'phone', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'{field} is required'}), 400
    
    valid_roles = ['TRUSTEE', 'ASSISTANT', 'ATTENDANT', 'SCANNER', 'ADMIN']
    if data['role'] not in valid_roles:
        return jsonify({'error': 'Invalid role'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if phone already exists
        cursor.execute("SELECT id FROM users WHERE phone = %s", (data['phone'],))
        if cursor.fetchone():
            return jsonify({'error': 'Phone number already exists'}), 400
        
        # Hash password
        hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
        
        # Insert user
        cursor.execute("""
            INSERT INTO users (name, phone, email, password, role, parent_trustee_id, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data['name'],
            data['phone'],
            data.get('email'),
            hashed_password.decode('utf-8'),
            data['role'],
            data.get('parent_trustee_id'),
            True
        ))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user_id': user_id
        }), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/users/<int:user_id>', methods=['PATCH'])
@token_required
@role_required(['ADMIN'])
def update_user(current_user, user_id):
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Build update query dynamically
        update_fields = []
        values = []
        
        if 'name' in data:
            update_fields.append('name = %s')
            values.append(data['name'])
        
        if 'email' in data:
            update_fields.append('email = %s')
            values.append(data['email'])
        
        if 'is_active' in data:
            update_fields.append('is_active = %s')
            values.append(data['is_active'])
        
        if 'password' in data:
            hashed_password = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())
            update_fields.append('password = %s')
            values.append(hashed_password.decode('utf-8'))
        
        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400
        
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
        
        cursor.execute(query, values)
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'User not found'}), 404
        
        conn.commit()
        
        return jsonify({'message': 'User updated successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@admin_bp.route('/admin/attendance', methods=['GET'])
@token_required
@role_required(['ADMIN'])
def get_attendance(current_user):
    date_param = request.args.get('date')
    attendant_id = request.args.get('attendant_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
    SELECT aa.*, u.name as attendant_name, u.phone as attendant_phone
    FROM attendant_attendance aa
    JOIN users u ON aa.attendant_id = u.id
    WHERE 1=1
    """
    
    params = []
    
    if date_param:
        query += " AND aa.date = %s"
        params.append(date_param)
    
    if attendant_id:
        query += " AND aa.attendant_id = %s"
        params.append(attendant_id)
    
    query += " ORDER BY aa.date DESC, aa.time_in DESC"
    
    cursor.execute(query, params)
    attendance_records = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({'attendance': attendance_records}, default=json_serializer), 200

@admin_bp.route('/admin/performance', methods=['GET'])
@token_required
@role_required(['ADMIN'])
def get_performance(current_user):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get performance metrics per attendant
    cursor.execute("""
        SELECT 
            u.id,
            u.name,
            u.phone,
            COUNT(p.id) as total_passes,
            SUM(CASE WHEN p.status = 'COMPLETED' THEN 1 ELSE 0 END) as completed_passes,
            SUM(CASE WHEN p.status = 'ISSUE' THEN 1 ELSE 0 END) as issue_passes,
            AVG(aa.total_hours) as avg_hours_per_day
        FROM users u
        LEFT JOIN passes p ON p.assigned_attendant_id = u.id
        LEFT JOIN attendant_attendance aa ON aa.attendant_id = u.id
        WHERE u.role = 'ATTENDANT' AND u.is_active = TRUE
        GROUP BY u.id, u.name, u.phone
    """)
    
    performance = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return jsonify({'performance': performance}, default=json_serializer), 200

@admin_bp.route('/admin/settings', methods=['PATCH'])
@token_required
@role_required(['ADMIN'])
def update_settings(current_user):
    data = request.json
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        update_fields = []
        values = []
        
        if 'grace_minutes_default' in data:
            update_fields.append('grace_minutes_default = %s')
            values.append(data['grace_minutes_default'])
        
        if 'max_visitors_per_attendant' in data:
            update_fields.append('max_visitors_per_attendant = %s')
            values.append(data['max_visitors_per_attendant'])
        
        if 'reminder_config' in data:
            update_fields.append('reminder_config = %s')
            values.append(json.dumps(data['reminder_config']))
        
        if not update_fields:
            return jsonify({'error': 'No fields to update'}), 400
        
        query = f"UPDATE settings SET {', '.join(update_fields)} WHERE id = 1"
        
        cursor.execute(query, values)
        conn.commit()
        
        return jsonify({'message': 'Settings updated successfully'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
