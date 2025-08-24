# app.py
from flask import Flask, request, jsonify, render_template
from flask_mail import Mail, Message
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
import database  # Our database module

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Gmail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', '')

mail = Mail(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def is_gmail_configured():
    """Check if Gmail is properly configured"""
    return all([
        app.config['MAIL_USERNAME'],
        app.config['MAIL_PASSWORD'],
        app.config['MAIL_DEFAULT_SENDER']
    ])

def save_appointment_to_db(appointment_data):
    """Save appointment to SQLite database"""
    try:
        conn = database.get_db_connection()
        c = conn.cursor()
        
        c.execute('''
        INSERT INTO appointments (name, phone, email, service, message)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            appointment_data['name'],
            appointment_data['phone'],
            appointment_data.get('email', ''),
            appointment_data.get('service', ''),
            appointment_data.get('message', '')
        ))
        
        conn.commit()
        appointment_id = c.lastrowid
        conn.close()
        
        logger.info(f"Appointment saved to database with ID: {appointment_id}")
        return appointment_id
        
    except Exception as e:
        logger.error(f"Error saving to database: {str(e)}")
        return None

def get_appointment_count_today():
    """Get count of appointments created today"""
    try:
        conn = database.get_db_connection()
        c = conn.cursor()
        
        c.execute('''
        SELECT COUNT(*) as count FROM appointments 
        WHERE DATE(created_at) = DATE('now')
        ''')
        
        result = c.fetchone()
        conn.close()
        
        return result['count'] if result else 0
        
    except Exception as e:
        logger.error(f"Error getting appointment count: {str(e)}")
        return 0

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/book-appointment', methods=['POST'])
def book_appointment():
    try:
        data = request.get_json()
        
        # Extract form data
        name = data.get('name')
        phone = data.get('phone')
        email = data.get('email')
        service = data.get('service')
        message = data.get('message')
        
        # Basic validation
        if not name or not phone:
            return jsonify({'success': False, 'message': 'Name and phone number are required.'})
        
        # Create appointment record
        appointment = {
            'name': name,
            'phone': phone,
            'email': email,
            'service': service,
            'message': message,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Save to database
        appointment_id = save_appointment_to_db(appointment)
        
        if not appointment_id:
            logger.error("Failed to save appointment to database")
            return jsonify({
                'success': False, 
                'message': 'Failed to save appointment. Please try again or call us directly.'
            })
        
        # Log the appointment
        logger.info(f"New appointment request: {appointment}")
        
        # Send email notification if Gmail is configured
        email_sent = False
        if is_gmail_configured():
            try:
                # Email to clinic
                clinic_msg = Message(
                    subject=f"📅 New Appointment Request from {name}",
                    recipients=[app.config['MAIL_DEFAULT_SENDER']],
                    body=f"""
                    New appointment request received:
                    
                    ID: #{appointment_id}
                    👤 Name: {name}
                    📞 Phone: {phone}
                    📧 Email: {email or 'Not provided'}
                    🏥 Service: {service}
                    💬 Message: {message or 'No message'}
                    
                    ⏰ Received at: {appointment['timestamp']}
                    
                    Please contact the patient within 24 hours.
                    """
                )
                mail.send(clinic_msg)
                
                # Optional: Send confirmation email to patient if they provided email
                if email:
                    try:
                        patient_msg = Message(
                            subject=f"Appointment Request Received - Chember Clinic",
                            recipients=[email],
                            body=f"""
                            Dear {name},
                            
                            Thank you for your appointment request with Chember Ortho and Pain Rehab Clinic.
                            
                            We have received your request for: {service}
                            
                            Our team will contact you at {phone} within 24 hours to confirm your appointment.
                            
                            If you have any urgent questions, please call us at +91 79807 17479.
                            
                            Best regards,
                            Chember Clinic Team
                            """
                        )
                        mail.send(patient_msg)
                    except Exception as e:
                        logger.warning(f"Could not send confirmation to patient: {str(e)}")
                
                email_sent = True
                logger.info("Notification emails sent successfully")
                
            except Exception as e:
                logger.error(f"Failed to send email: {str(e)}")
                email_sent = False
        else:
            logger.warning("Gmail not configured - skipping email notification")
        
        # Get today's appointment count
        today_count = get_appointment_count_today()
        
        response_message = f'Appointment request received successfully (Reference #: {appointment_id}). We will contact you shortly.'
        if not email_sent:
            response_message += ' Please call us directly at +91 79807 17479 if you need urgent appointment.'
        
        return jsonify({
            'success': True, 
            'message': response_message,
            'appointment_id': appointment_id,
            'today_count': today_count
        })
        
    except Exception as e:
        logger.error(f"Error processing appointment: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'An error occurred while processing your request. Please call us at +91 79807 17479.'
        })

@app.route('/appointments', methods=['GET'])
def get_appointments():
    """Admin endpoint to view appointments (add authentication in production)"""
    try:
        conn = database.get_db_connection()
        c = conn.cursor()
        
        # Get query parameters for filtering
        status = request.args.get('status', 'all')
        limit = request.args.get('limit', 50)
        
        if status == 'all':
            c.execute('''
            SELECT * FROM appointments 
            ORDER BY created_at DESC 
            LIMIT ?
            ''', (limit,))
        else:
            c.execute('''
            SELECT * FROM appointments 
            WHERE status = ?
            ORDER BY created_at DESC 
            LIMIT ?
            ''', (status, limit))
        
        appointments = c.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        appointments_list = []
        for appt in appointments:
            appointments_list.append(dict(appt))
        
        return jsonify({
            'success': True,
            'count': len(appointments_list),
            'appointments': appointments_list
        })
        
    except Exception as e:
        logger.error(f"Error fetching appointments: {str(e)}")
        return jsonify({
            'success': False, 
            'message': 'Error fetching appointments'
        })

@app.route('/health')
def health_check():
    gmail_configured = is_gmail_configured()
    
    # Check database health
    db_health = False
    try:
        conn = database.get_db_connection()
        c = conn.cursor()
        c.execute('SELECT 1')
        db_health = True
        conn.close()
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
    
    return jsonify({
        'status': 'healthy', 
        'timestamp': datetime.now().isoformat(),
        'email_configured': gmail_configured,
        'database_healthy': db_health,
        'service': 'Chember Ortho and Pain Rehab Clinic API'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Check if Gmail is configured
    if not is_gmail_configured():
        logger.warning("Gmail is not properly configured. Email notifications will not be sent.")
        logger.warning("Please set MAIL_USERNAME, MAIL_PASSWORD, and MAIL_DEFAULT_SENDER in your .env file")
    
    app.run(host='0.0.0.0', port=port, debug=debug_mode)