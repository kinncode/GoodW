from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import current_user, login_required
from app import db, bcrypt, mail, cache
from app.models import User, Project, SystemLog, SystemSettings
from datetime import datetime, timedelta
import psutil
from functools import wraps
import random
import string
from flask_mail import Message
from sqlalchemy.orm import joinedload
from flask_caching import Cache
import uuid

# 創建 'admin' 藍圖
admin_bp = Blueprint('admin', __name__)

# 管理員權限裝飾器
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('您沒有權限訪問此頁面', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function

# 帳號管理頁面：顯示所有用戶
@admin_bp.route('/admin/users', methods=['GET'])
@login_required
@admin_required
def manage_users():
    # 使用 count() 直接獲取數量
    total_users = User.query.count()
    
    # 修改這裡：使用 User.projects 而不是字串 'projects'
    users = User.query.options(joinedload(User.projects)).all()
    
    # 獲取本月新增用戶數
    current_month = datetime.now().replace(day=1)
    new_users_this_month = User.query.filter(User.created_at >= current_month).count()
    
    # 獲取最近活動
    recent_activities = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(5).all()
    recent_activities = [{'timestamp': activity.created_at.strftime('%Y-%m-%d %H:%M'), 
                          'user': activity.username, 
                          'description': activity.action} for activity in recent_activities]
    
    return render_template('admin/manage_users.html',
                         users=users,
                         total_users=total_users,
                         new_users_this_month=new_users_this_month,
                         recent_activities=recent_activities,
                         active_page='users',
                         now=datetime.now())

# 刪除用戶路由
@admin_bp.route('/delete_user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    if current_user.id == user_id:
        return jsonify({'error': '無法刪除自己的帳號'}), 400
        
    try:
        user = User.query.get_or_404(user_id)
        username = user.username  # 保存用戶名以供記錄使用
        
        # 先刪除該用戶的所有專案
        Project.query.filter_by(user_id=user_id).delete()
        
        # 再刪除用戶
        db.session.delete(user)
        db.session.commit()
        
        # 在成功刪除後記錄操作
        try:
            log_activity(f'刪除用戶 {username} 及其所有專案', 'warning')
        except Exception as log_error:
            print(f"記錄刪除操作失敗: {str(log_error)}")
        
        return jsonify({'message': '用戶刪除成功'})
        
    except Exception as e:
        db.session.rollback()
        print(f"刪除用戶時發生錯誤: {str(e)}")
        return jsonify({'error': '刪除用戶時發生錯誤'}), 500

# 新增帳號頁面
@admin_bp.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        role = request.form.get('role', 'user')  # 獲取角色，預設為 'user'

        if not username or not password or not email:
            flash('請填寫所有欄位', 'danger')
            return redirect(url_for('admin.add_user'))

        # 檢查用戶名稱是否已存在
        if User.query.filter_by(username=username).first():
            flash('用戶名稱已存在', 'danger')
            return redirect(url_for('admin.add_user'))

        # 檢查 Email 是否已存在
        if User.query.filter_by(email=email).first():
            flash('Email 已存在', 'danger')
            return redirect(url_for('admin.add_user'))

        # 加密密碼
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        new_user = User(
            username=username, 
            password=hashed_password, 
            email=email,
            role=role
        )

        # 新增用戶到資料庫
        db.session.add(new_user)
        db.session.commit()
        flash(f'用戶 {username} 已新增', 'success')

        return redirect(url_for('admin.manage_users'))

    return render_template('admin/add_user.html', active_page='users')

# 儀表板路由
@admin_bp.route('/admin/dashboard')
@login_required
@admin_required
@cache.cached(timeout=300)  # 快取 5 分鐘
def dashboard():
    # 獲取統計數據
    total_users = User.query.count()
    total_projects = Project.query.count()
    
    # 獲取本月新增數據
    current_month = datetime.now().replace(day=1)
    new_users_this_month = User.query.filter(User.created_at >= current_month).count()
    new_projects_this_month = Project.query.filter(Project.created_at >= current_month).count()
    
    # 最近活動（從資料庫獲取）
    recent_activities = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(5).all()
    recent_activities = [{'timestamp': activity.created_at.strftime('%Y-%m-%d %H:%M'), 
                          'user': activity.username, 
                          'description': activity.action} for activity in recent_activities]
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_projects=total_projects,
                         new_users_this_month=new_users_this_month,
                         new_projects_this_month=new_projects_this_month,
                         recent_activities=recent_activities,
                         active_page='dashboard')

# 系統日誌路由
@admin_bp.route('/admin/logs')
@login_required
@admin_required
def system_logs():
    # 從資料庫獲取系統日誌
    logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(100).all()
    return render_template('admin/system_logs.html', 
                         logs=logs,
                         active_page='logs')

# 系統設定路由
@admin_bp.route('/admin/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def system_settings():
    if request.method == 'POST':
        try:
            settings = get_system_settings()
            settings.maintenance_mode = 'maintenance_mode' in request.form
            settings.allow_registration = 'allow_registration' in request.form
            settings.enable_email = 'enable_email' in request.form
            
            db.session.commit()
            log_activity('更新系統設定', 'info')
            flash('系統設定已更新', 'success')
            
        except Exception as e:
            flash('更新設定時發生錯誤', 'danger')
            
    settings = get_system_settings()
    return render_template('admin/system_settings.html', 
                         settings=settings,
                         active_page='settings')

# 添加在現有路由後面
@admin_bp.route('/admin/projects')
@login_required
@admin_required
def manage_projects():
    # 獲取所有專案，包含用戶信息
    projects = db.session.query(Project, User)\
        .join(User)\
        .order_by(Project.created_at.desc())\
        .all()
    
    return render_template('admin/manage_projects.html', 
                         projects=projects,
                         active_page='projects')

@admin_bp.route('/admin/reset-password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    new_password = generate_random_password()  # 生成隨機密碼
    user.set_password(new_password)
    user.password_expires = datetime.now() + timedelta(days=90)  # 90天後密碼過期
    db.session.commit()
    
    # 發送郵件通知用戶
    send_password_reset_email(user.email, new_password)
    
    return jsonify({'message': 'Password reset successful'})

@admin_bp.route('/deactivate-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def deactivate_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        # 檢查是否試圖停用自己
        if user.id == current_user.id:
            return jsonify({'error': '無法停用自己的帳號'}), 400
            
        # 檢查用戶是否已經被停用
        if not user.is_active:
            return jsonify({'error': '該用戶已經是停用狀態'}), 400
            
        user.is_active = False
        db.session.commit()
        
        # 記錄操作
        log_activity(f'停用用戶 {user.username}', 'warning')
        
        return jsonify({'message': '用戶已成功停用'})
        
    except Exception as e:
        db.session.rollback()
        print(f"停用用戶時發生錯誤: {str(e)}")
        return jsonify({'error': '停用用戶時發生錯誤'}), 500

@admin_bp.route('/activate-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def activate_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        # 檢查用戶是否已經是啟用狀態
        if user.is_active:
            return jsonify({'error': '該用戶已經是啟用狀態'}), 400
            
        user.is_active = True
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()
        
        # 記錄操作
        log_activity(f'啟用用戶 {user.username}', 'info')
        
        return jsonify({'message': '用戶已成功啟用'})
        
    except Exception as e:
        db.session.rollback()
        print(f"啟用用戶時發生錯誤: {str(e)}")
        return jsonify({'error': '啟用用戶時發生錯誤'}), 500

@admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    try:
        user = User.query.get_or_404(user_id)
        
        if request.method == 'POST':
            try:
                # 更新用戶資料
                form_data = request.form
                
                # 檢查是否為自己且正在更改角色
                if user.id == current_user.id and form_data.get('role') != user.role:
                    return jsonify({'error': '無法更改自己的角色'}), 400
                
                # 更新到期日
                if form_data.get('account_expires'):
                    user.account_expires = datetime.strptime(form_data.get('account_expires'), '%Y-%m-%d')
                else:
                    user.account_expires = None
                    
                if form_data.get('password_expires'):
                    user.password_expires = datetime.strptime(form_data.get('password_expires'), '%Y-%m-%d')
                else:
                    user.password_expires = None
                    
                user.role = form_data.get('role', 'user')
                
                db.session.commit()
                log_activity(f'編輯用戶 {user.username}', 'info')
                
                return jsonify({
                    'success': True,
                    'message': '用戶資料更新成功'
                })
                
            except ValueError as ve:
                db.session.rollback()
                return jsonify({'error': '日期格式不正確'}), 400
                
            except Exception as e:
                db.session.rollback()
                print(f"編輯用戶時發生錯誤: {str(e)}")
                return jsonify({'error': '更新用戶資料時發生錯誤'}), 500
                
        # GET 請求返回用戶資料
        return jsonify({
            'account_expires': user.account_expires.strftime('%Y-%m-%d') if user.account_expires else '',
            'password_expires': user.password_expires.strftime('%Y-%m-%d') if user.password_expires else '',
            'role': user.role
        })
        
    except Exception as e:
        print(f"獲取用戶資料時發生錯誤: {str(e)}")
        return jsonify({'error': '獲取用戶資料失敗'}), 500

def get_system_settings():
    settings = SystemSettings.query.first()
    if not settings:
        settings = SystemSettings(
            system_name="SROI 管理系統",
            maintenance_mode=False,
            allow_registration=True,
            version="1.0.0",
            last_update=datetime.now()
        )
        db.session.add(settings)
        db.session.commit()
    return settings

def update_system_settings(form_data):
    settings = get_system_settings()
    settings.system_name = form_data.get('system_name', settings.system_name)
    settings.maintenance_mode = 'maintenance_mode' in form_data
    settings.allow_registration = 'allow_registration' in form_data
    db.session.commit()

def generate_random_password(length=12):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(characters) for _ in range(length))

def send_password_reset_email(email, new_password):
    msg = Message('密碼重設通知',
                 sender='your-email@example.com',
                 recipients=[email])
    msg.body = f'您的新密碼是: {new_password}\n請在登入後立即更改密碼。'
    mail.send(msg)

def log_activity(action, level='info', details=None):
    log = SystemLog(
        level=level,
        username=current_user.username,
        ip_address=request.remote_addr,
        action=action,
        details=details
    )
    db.session.add(log)
    db.session.commit()

@admin_bp.route('/system_monitor')
@login_required
def system_monitor():
    if current_user.role != 'admin':
        flash('權限不足', 'danger')
        return redirect(url_for('main.index'))

    # 系統資源資訊
    cpu_percent = psutil.cpu_percent()
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # 系統運行時間
    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime = datetime.now() - boot_time
    
    # 獲取活動會話（改為獲取所有用戶）
    active_sessions = User.query.filter_by(is_active=True).all()
    
    return render_template('admin/system_monitor.html',
                         active_page='monitor',
                         cpu_percent=cpu_percent,
                         memory=memory,
                         disk=disk,
                         uptime=uptime,
                         active_sessions=active_sessions,
                         system_start_time=boot_time)

@admin_bp.route('/force-logout/<int:user_id>', methods=['POST'])
@login_required
def force_logout(user_id):
    if current_user.role != 'admin':
        return jsonify({'error': '權限不足'}), 403
        
    user = User.query.get_or_404(user_id)
    user.invalidate_session()
    
    # 記錄系統日誌
    log = SystemLog(
        level='warning',
        username=user.username,
        action='forced_logout',
        details=f'管理員 {current_user.username} 強制登出用戶'
    )
    db.session.add(log)
    db.session.commit()
    
    return jsonify({'message': '用戶已被強制登出'})

