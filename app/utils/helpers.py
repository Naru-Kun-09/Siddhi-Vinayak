import json
from datetime import datetime, date, time

def json_serializer(obj):
    """JSON serializer for objects not serializable by default"""
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def assign_attendant_round_robin(connection):
    """Assign attendant using round-robin with load balancing"""
    cursor = connection.cursor()
    
    # Get today's date
    today = datetime.now().date()
    
    # Find attendant with least assignments today
    query = """
    SELECT u.id, u.name, u.phone, COUNT(p.id) as pass_count
    FROM users u
    LEFT JOIN passes p ON p.assigned_attendant_id = u.id AND DATE(p.date) = %s
    WHERE u.role = 'ATTENDANT' AND u.is_active = TRUE
    GROUP BY u.id
    ORDER BY pass_count ASC
    LIMIT 1
    """
    cursor.execute(query, (today,))
    result = cursor.fetchone()
    cursor.close()
    
    return result

def log_action(connection, user_id, action, entity_type, entity_id=None, payload=None):
    """Log user action"""
    cursor = connection.cursor()
    query = """
    INSERT INTO logs (user_id, action, entity_type, entity_id, payload)
    VALUES (%s, %s, %s, %s, %s)
    """
    cursor.execute(query, (user_id, action, entity_type, entity_id, json.dumps(payload)))
    connection.commit()
    cursor.close()
