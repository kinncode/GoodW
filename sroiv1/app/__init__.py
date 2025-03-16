import os
from datetime import timedelta
from flask import Flask, session, render_template, request, redirect, url_for, flash, jsonify
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, current_user, logout_user
from flask_caching import Cache
from flask_migrate import Migrate
from dotenv import load_dotenv
from config import Config

mail = Mail()
db = SQLAlchemy()
bcrypt = Bcrypt()
login_manager = LoginManager()
cache = Cache()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 加載 .env.local 文件
    load_dotenv('.env.local')
    
    # 測試環境變數是否加載
    if not os.environ.get('GEMINI_API_KEY'):
        raise ValueError("GEMINI_API_KEY 未正確加載！")
    
    app.config['DEBUG'] = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True

    # 使用更安全的 secret key 設置
    app.secret_key = os.environ.get('SECRET_KEY', 'your_fallback_secret_key')
    
    # 數據庫配置
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://@DESKTOP-DDIAQJQ\SQLEXPRESS/SROIV2?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Session 配置
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_TYPE'] = 'filesystem'  # 或者使用其他 session 存儲方式

    app.config['SESSION_COOKIE_SECURE'] = False  # 開發環境設為 False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # 郵件配置
    app.config.update(
        MAIL_SERVER='Yourmail',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME='sroistust@gmail.com',
        MAIL_PASSWORD='Yourspassword',
        MAIL_DEFAULT_SENDER='XXX@gmail.com'  
    )

    # 初始化擴展
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    cache.init_app(app)
    migrate.init_app(app, db)

    # 設置 user_loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # 註冊 Blueprint
    from app.routes import main_bp
    from app.admin_routes import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')  # 確保這裡的 url_prefix 正確

    login_manager.login_view = 'main.login'  # 設定登入頁面的路由
    login_manager.login_message = '請先登入！'  # 設定提示訊息
    login_manager.login_message_category = 'warning'  # 設定提示訊息類型

    @app.before_request
    def check_maintenance_mode():
        # 忽略靜態文件請求
        if request.path.startswith('/static/'):
            return
            
        # 忽略登入頁面
        if request.endpoint == 'main.login':
            return
            
        from app.models import SystemSettings
        settings = SystemSettings.query.first()
        if settings and settings.maintenance_mode:
            # 如果是管理員，允許訪問
            if current_user.is_authenticated and current_user.role == 'admin':
                return
                
            # 如果不是訪問維護頁面，則重定向到維護頁面
            if request.endpoint != 'main.maintenance':
                return render_template('maintenance.html'), 503

    @app.before_request
    def log_request_info():
        print('Headers: %s', request.headers)
        print('Body: %s', request.get_data())
        
    @app.before_request
    def check_session_token():
        if current_user.is_authenticated:
            # 如果用戶的 session_token 為空或與存儲的不匹配，則登出用戶
            stored_token = getattr(current_user, 'session_token', None)
            session_token = session.get('session_token')
            if not stored_token or stored_token != session_token:
                logout_user()
                session.clear()
                flash('您的會話已過期，請重新登入', 'warning')
                return redirect(url_for('main.login'))

    @app.before_request
    def update_last_activity():
        if current_user.is_authenticated:
            current_user.update_activity(request.remote_addr)

    @app.before_request
    def check_user_status():
        if current_user.is_authenticated:
            # 忽略登出路由
            if request.endpoint == 'main.logout':
                return
            
            # 檢查帳號狀態
            can_access, error_message = current_user.check_account_status()
            if not can_access:
                logout_user()
                session.clear()
                flash(error_message, 'danger')
                return redirect(url_for('main.login'))

    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({'error': '資源未找到'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': '伺服器內部錯誤'}), 500

    return app