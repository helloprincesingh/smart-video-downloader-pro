from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from models import User
from database import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if not email or not password:
            flash('Email and Password are required.', 'danger')
            return render_template('signup.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('signup.html')
            
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email address already registered.', 'danger')
            return render_template('signup.html')
            
        # Create new user
        new_user = User(email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash('Account created successfully!', 'success')
            return redirect(url_for('dashboard.home'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
            
    return render_template('signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        if not email or not password:
            flash('Please enter email and password.', 'danger')
            return render_template('login.html')
            
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash('Please check your login details and try again.', 'danger')
            return render_template('login.html')
            
        login_user(user, remember=remember)
        return redirect(url_for('dashboard.home'))
        
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('home'))
