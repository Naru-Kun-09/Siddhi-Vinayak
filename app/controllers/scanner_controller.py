from flask import Blueprint, request, jsonify
from app.database import get_db_connection
from app.middleware.auth_middleware import token_required, role_required
from app.utils.helpers import log_action, json_serializer
from datetime import datetime

scanner_bp = Blueprint('scanner', __name__)

@scanner_bp.route('/scanner/scan-qr', methods=['POST'])
@token_required
@role_required(['SCANNER', 'ADMIN'])
def scan_qr(current_user):
    data = request.json
    qr_code_string = data.get('qr_code_string')
    
    if not qr_code_string:
        return jsonify({'error': 'qr_code_string is required'}), 400
    
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
        WHERE p.qr_code_string = %s
    """, (qr_code_string,))
    
    pass_data = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if not pass_data:
        return jsonify({'error': 'Invalid QR code'}), 404
    
    # Check if pass is valid
    if pass_data['status'] in ['CANCELLED', 'EXPIRED']:
        return jsonify({
            'error': f'Pass is {pass_data["status"]}',
            'pass': pass_data
        }, default=json_serializer), 400
    
    if pass_data['status'] == 'COMPLETED':
        return jsonify({
            'error': 'Pass already completed',
            'pass': pass_data
        }, default=json_serializer), 400
    
    return jsonify({
        'message': 'Valid pass',
        'pass': pass_data
    }, default=json_serializer), 200

@scanner_bp.route('/scanner/update-status', methods=['POST'])
@token_required
@role_required(['SCANNER', 'ADMIN'])
def update_pass_status(current_user):
    data = request.json
    pass_id = data.get('pass_id')
    stage = data.get('stage')
    
    valid_stages = ['ARRIVED', 'AT_GATE', 'COMPLETED']
    
    if not pass_id or not stage:
        return jsonify({'error': 'pass_id and stage are required'}), 400
    
    if stage not in valid_stages:
        return jsonify({'error': 'Invalid stage'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Update pass status
        status_map = {'ARRIVED': 'REACHED', 'AT_GATE': 'AT_GATE', 'COMPLETED': 'COMPLETED'}
        
        cursor.execute("""
            UPDATE passes SET status = %s, updated_at = NOW()
            WHERE id = %s
        """, (status_map[stage], pass_id))
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Pass not found'}), 404
        
        # Insert scan record
        cursor.execute("""
            INSERT INTO scans (pass_id, stage, source, created_at)
            VALUES (%s, %s, 'SCANNER', NOW())
        """, (pass_id, stage))
        
        conn.commit()
        
        # Log action
        log_action(conn, current_user['user_id'], 'SCANNER_UPDATE', 'PASS', pass_id, {'stage': stage})
        
        return jsonify({'message': f'Pass updated to {stage}'}), 200
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()

@scanner_bp.route('/scanner/issue', methods=['POST'])
@token_required
@role_required(['SCANNER', 'ADMIN'])
def report_issue(current_user):
    data = request.json
    pass_id = data.get('pass_id')
    issue_type = data.get('issue_type')
    description = data.get('description', '')
    
    valid_types = ['LATE', 'DUPLICATE_QR', 'NO_SHOW', 'OTHER']
    
    if not pass_id or not issue_type:
        return jsonify({'error': 'pass_id and issue_type are required'}), 400
    
    if issue_type not in valid_types:
        return jsonify({'error': 'Invalid issue_type'}), 400
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Insert issue
        cursor.execute("""
            INSERT INTO issues (pass_id, reported_by_user_id, issue_type, description, status)
            VALUES (%s, %s, %s, %s, 'OPEN')
        """, (pass_id, current_user['user_id'], issue_type, description))
        
        # Update pass status
        cursor.execute("""
            UPDATE passes SET status = 'ISSUE', updated_at = NOW()
            WHERE id = %s
        """, (pass_id,))
        
        conn.commit()
        
        return jsonify({'message': 'Issue reported successfully'}), 201
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()
