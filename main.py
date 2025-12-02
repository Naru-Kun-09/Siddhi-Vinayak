from flask import Flask
from flask_cors import CORS
from app.controllers.auth_controller import auth_bp
from app.controllers.pass_controller import pass_bp
from app.controllers.attendant_controller import attendant_bp
from app.controllers.scanner_controller import scanner_bp
from app.controllers.aarti_controller import aarti_bp
from app.controllers.admin_controller import admin_bp

app = Flask(__name__)
CORS(app)

# Register all blueprints
app.register_blueprint(auth_bp, url_prefix='/api')
app.register_blueprint(pass_bp, url_prefix='/api')
app.register_blueprint(attendant_bp, url_prefix='/api')
app.register_blueprint(scanner_bp, url_prefix='/api')
app.register_blueprint(aarti_bp, url_prefix='/api')
app.register_blueprint(admin_bp, url_prefix='/api')

@app.route('/')
def home():
    return {'message': 'Siddhivinayak PRO API', 'version': '1.0'}, 200

@app.route('/health')
def health():
    return {'status': 'healthy'}, 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
