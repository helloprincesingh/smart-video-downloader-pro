from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.models.user import User
from app.models.download import DownloadHistory
from app.models.favorite import Favorite
from app.models.analytics import Analytics
from app.database.db import db
from app.auth.supabase_auth import SupabaseAuth
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.app_context_processor
def inject_supabase_status():
    """Inject Supabase configuration parameters to templates globally."""
    return {
        'supabase_configured': SupabaseAuth.is_configured(),
        'supabase_url': os.environ.get('SUPABASE_URL', ''),
        'supabase_anon_key': os.environ.get('SUPABASE_ANON_KEY', '')
    }

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
        
    if request.method == 'POST':
        # Local SQLite auth fallback
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not email or not password:
            flash('Email and Password are required.', 'danger')
            return render_template('signup.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html')
            
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already registered.', 'danger')
            return render_template('signup.html')
            
        # Create user locally
        new_user = User(email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Account created successfully (Local Fallback)!', 'success')
            return redirect(url_for('dashboard.home'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            
    return render_template('signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
        
    if request.method == 'POST':
        # Local SQLite auth fallback
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        if not email or not password:
            flash('Please enter email and password.', 'danger')
            return render_template('login.html')
            
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Invalid email or password.', 'danger')
            return render_template('login.html')
            
        login_user(user, remember=remember)
        flash('Logged in successfully (Local Fallback)!', 'success')
        return redirect(url_for('dashboard.home'))
        
    return render_template('login.html')

@auth_bp.route('/auth/supabase-login', methods=['POST'])
def supabase_login():
    """Sync frontend Supabase session to backend Flask-Login session."""
    data = request.get_json() or {}
    access_token = data.get('access_token')
    email = data.get('email')
    supabase_uid = data.get('user_id')
    
    if not email or not supabase_uid:
        return jsonify({'error': 'Email and User ID are required'}), 400
        
    # Verify JWT if Supabase is configured
    if SupabaseAuth.is_configured() and access_token:
        user_info = SupabaseAuth.verify_token(access_token)
        if not user_info:
            return jsonify({'error': 'Invalid Supabase session token'}), 401
        email = user_info.get('email', email)
        supabase_uid = user_info.get('id', supabase_uid)
        
    # Match user in db
    user = User.query.filter_by(supabase_uid=supabase_uid).first()
    if not user:
        user = User.query.filter_by(email=email).first()
        if user:
            # Link local user to Supabase
            user.supabase_uid = supabase_uid
        else:
            # Create user
            user = User(email=email, supabase_uid=supabase_uid)
            db.session.add(user)
            
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'Database error: {str(e)}'}), 500
            
    login_user(user, remember=True)
    
    # Log analytics
    try:
        analytics = Analytics(user_id=user.id, event_type='login')
        db.session.add(analytics)
        db.session.commit()
    except Exception:
        pass
        
    return jsonify({'success': True, 'message': 'Logged in successfully'})

@auth_bp.route('/logout')
def logout():
    if current_user.is_authenticated:
        try:
            analytics = Analytics(user_id=current_user.id, event_type='logout')
            db.session.add(analytics)
            db.session.commit()
        except Exception:
            pass
        logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    # Render reset password form
    if request.method == 'POST':
        # Local password reset logic if not using Supabase
        if not SupabaseAuth.is_configured():
            if not current_user.is_authenticated:
                flash('Please log in to reset your password.', 'danger')
                return redirect(url_for('auth.login'))
            new_password = request.form.get('password')
            confirm = request.form.get('confirm_password')
            if not new_password or new_password != confirm:
                flash('Passwords must match.', 'danger')
                return render_template('reset_password.html')
                
            current_user.set_password(new_password)
            db.session.commit()
            flash('Password updated successfully!', 'success')
            return redirect(url_for('dashboard.home'))
            
    # For Supabase, the page is rendered and JS client updates password
    return render_template('reset_password.html')
