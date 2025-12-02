import qrcode
import io
import base64
import uuid

def generate_qr_string():
    """Generate unique QR code string"""
    return f"SV-{uuid.uuid4().hex[:12].upper()}"

def generate_qr_image(qr_string):
    """Generate QR code image as base64"""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_string)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode()
