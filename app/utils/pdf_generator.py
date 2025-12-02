from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from io import BytesIO
import qrcode

def generate_visitor_ticket(pass_data, attendant_name, attendant_phone):
    """Generate PDF ticket for visitor"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(width/2, height - 1*inch, "Siddhivinayak Temple")
    c.drawCentredString(width/2, height - 1.3*inch, "Darshan Pass")
    
    # Visitor Details
    c.setFont("Helvetica-Bold", 14)
    c.drawString(1*inch, height - 2*inch, f"Visitor: {pass_data['visitor_name']}")
    c.setFont("Helvetica", 11)
    c.drawString(1*inch, height - 2.3*inch, f"Phone: {pass_data['visitor_phone']}")
    c.drawString(1*inch, height - 2.6*inch, f"Email: {pass_data.get('visitor_email', 'N/A')}")
    c.drawString(1*inch, height - 2.9*inch, f"Date: {pass_data['date']}")
    c.drawString(1*inch, height - 3.2*inch, f"Time: {pass_data['time']}")
    c.drawString(1*inch, height - 3.5*inch, f"Total People: {pass_data['total_people']}")
    c.drawString(1*inch, height - 3.8*inch, f"Valid for {pass_data['grace_minutes']} minutes after slot")
    
    # Vastra Details
    if pass_data.get('vastra_count'):
        c.drawString(1*inch, height - 4.1*inch, f"Vastra Count: {pass_data['vastra_count']}")
        if pass_data.get('vastra_names'):
            c.drawString(1*inch, height - 4.4*inch, f"Names: {', '.join(pass_data['vastra_names'])}")
    
    # Attendant Details
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1*inch, height - 5*inch, "Your Attendant:")
    c.setFont("Helvetica", 11)
    c.drawString(1*inch, height - 5.3*inch, f"{attendant_name} - {attendant_phone}")
    
    # QR Code
    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(pass_data['qr_code_string'])
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    c.drawImage(qr_buffer, width/2 - 1.5*inch, height - 8*inch, 3*inch, 3*inch)
    
    # Footer
    c.setFont("Helvetica", 9)
    c.drawCentredString(width/2, 1*inch, "Please show this QR code at the gate")
    c.drawCentredString(width/2, 0.7*inch, "Temple timing: 6:00 AM - 9:00 PM")
    
    c.save()
    buffer.seek(0)
    return buffer
