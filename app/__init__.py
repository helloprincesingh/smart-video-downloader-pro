import os
from flask import Flask, render_template, send_from_directory, request, redirect
from flask_login import LoginManager
from werkzeug.middleware.proxy_fix import ProxyFix
from config import Config
from app.database.db import db
from app.models.user import User

def create_app():
    app = Flask(__name__, 
                template_folder='../templates', 
                static_folder='../static')
    app.config.from_object(Config)
    
    # Configure ProxyFix for reverse proxies (Render, Heroku, etc.)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    
    # Redirect HTTP to HTTPS in production
    @app.before_request
    def force_https():
        if not app.debug:
            proto = request.headers.get('X-Forwarded-Proto')
            if proto == 'http':
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)
                
    # Add Security Headers to prevent mixed-content and other security vulnerabilities
    @app.after_request
    def add_security_headers(response):
        # Only force upgrading insecure requests if we are actually accessed over HTTPS
        if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
            response.headers['Content-Security-Policy'] = "upgrade-insecure-requests"
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        if not app.debug:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response
    
    # Initialize DB
    db.init_app(app)
    
    # Initialize Login Manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Create Download Folder if missing
    if not os.path.exists(app.config['DOWNLOAD_FOLDER']):
        os.makedirs(app.config['DOWNLOAD_FOLDER'])
        
    # Create database parent folder if it is a local SQLite database
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_uri and db_uri.startswith('sqlite:///'):
        db_path = db_uri.replace('sqlite:///', '')
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.api import api_bp
    from app.routes.dashboard import dashboard_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)
    
    # Global home route
    @app.route('/')
    def home():
        return render_template("index.html")
        
    # File download route
    @app.route('/file/<filename>')
    def file(filename):
        return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)
        
    # Serve favicon.ico
    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.static_folder, 'favicon.ico', mimetype='image/vnd.microsoft.icon')
        
    # Custom 404/500 handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', error_title="404 - Not Found", error_msg="The page you are looking for does not exist."), 404

    @app.errorhandler(500)
    def internal_error(e):
        return render_template('base.html', error_title="500 - Server Error", error_msg="Something went wrong on our end. Please try again."), 500
        
    # Create tables automatically inside application context
    with app.app_context():
        db.create_all()
        
    return app
