from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask_login import UserMixin
from flask import current_app
from app import db

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 新增欄位
    account_expires = db.Column(db.DateTime)  # 帳號到期日
    is_active = db.Column(db.Boolean, default=True)  # 帳號狀態
    last_login = db.Column(db.DateTime)  # 最後登入時間
    login_count = db.Column(db.Integer, default=0)  # 登入次數
    password_expires = db.Column(db.DateTime)  # 密碼到期日
    failed_login_attempts = db.Column(db.Integer, default=0)  # 失敗登入次數
    locked_until = db.Column(db.DateTime)  # 帳號鎖定時間
    session_token = db.Column(db.String(100))  # 新增會話令牌欄位
    ip_address = db.Column(db.String(45))  # IPv6 最長 45 字符
    login_time = db.Column(db.DateTime)  # 本次登入時間
    last_activity = db.Column(db.DateTime)  # 最後活動時間

    # 關聯到專案
    projects = db.relationship('Project', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def is_account_locked(self):
        if self.locked_until and self.locked_until > datetime.utcnow():
            return True
        return False

    def is_account_expired(self):
        """檢查帳號是否過期"""
        if self.account_expires and datetime.now() > self.account_expires:
            return True
        return False

    def is_password_expired(self):
        """檢查密碼是否過期"""
        if self.password_expires and datetime.now() > self.password_expires:
            return True
        return False

    def get_account_status(self):
        if not self.is_active:
            return "停用", False
        if self.is_account_locked():
            return "已鎖定", False
        if self.is_account_expired():
            return "已過期", False
        if self.is_password_expired():
            return "密碼過期", False
        return "正常", True

    def check_account_status(self):
        """檢查帳號狀態，返回 (可否登入, 錯誤訊息)"""
        if not self.is_active:
            return False, "帳號已被停用"
        
        if self.is_account_expired():
            return False, "帳號已過期"
            
        if self.is_password_expired():
            return False, "密碼已過期，請聯繫管理員重設密碼"
            
        if self.locked_until and datetime.now() < self.locked_until:
            return False, "帳號已被鎖定"
            
        return True, None

    def check_login(self, password):
        db = current_app.extensions['sqlalchemy'].db
        # 檢查帳號狀態
        status, can_login = self.check_account_status()
        if not can_login:
            return False, status

        # 檢查密碼
        if not self.check_password(password):
            self.failed_login_attempts += 1
            if self.failed_login_attempts >= 5:  # 5次失敗後鎖定
                self.locked_until = datetime.utcnow() + timedelta(minutes=30)
            db.session.commit()
            return False, "密碼錯誤"

        # 登入成功，重設失敗次數
        self.failed_login_attempts = 0
        self.last_login = datetime.utcnow()
        self.login_count += 1
        db.session.commit()
        return True, "登入成功"

    def can_create_project(self):
        if not self.is_active:
            return False, "您的帳號已被停用"
        if self.is_account_expired():
            return False, "您的帳號已過期"
        if self.is_password_expired():
            return False, "您的密碼已過期，請更新密碼"
        return True, None

    def get_account_warning(self):
        """獲取帳號警告訊息"""
        if self.account_expires:
            days_left = (self.account_expires - datetime.utcnow()).days
            if 0 < days_left <= 7:
                return f"您的帳號將在 {days_left} 天後到期"
        return None

    def invalidate_session(self):
        """使當前會話失效"""
        self.session_token = None
        db.session.commit()

    def update_activity(self, ip=None):
        """更新用戶活動時間"""
        self.last_activity = datetime.utcnow()
        if ip:
            self.ip_address = ip
        db.session.commit()

class Project(db.Model):
    __tablename__ = 'myprojects'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    organization_name = db.Column(db.String(255), nullable=False)
    project_name = db.Column(db.String(255), nullable=False)
    project_activity = db.Column(db.Text, nullable=True)
    project_goal = db.Column(db.Text, nullable=True)
    project_attribute = db.Column(db.String(50), nullable=False)
    project_start_date = db.Column(db.Date, nullable=False)
    project_end_date = db.Column(db.Date, nullable=True)
    analysis_start_date = db.Column(db.Date, nullable=True)
    analysis_end_date = db.Column(db.Date, nullable=True)
    analysis_nature = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)
    sroi_score = db.Column(db.String(10), nullable=True)

    # 添加級聯刪除關係
    stakeholders = db.relationship('Stakeholder', 
                                  cascade='all, delete-orphan',
                                  passive_deletes=True,
                                  lazy=True)
    contributions = db.relationship('Contribution', 
                                   cascade='all, delete-orphan',
                                   passive_deletes=True,
                                   lazy=True)
    results = db.relationship('Result', 
                             cascade='all, delete-orphan',
                             passive_deletes=True,
                             lazy=True)

    def to_dict(self):
        """將專案轉換為字典格式，用於 API 響應"""
        return {
            'id': self.id,
            'organization_name': self.organization_name,
            'project_name': self.project_name,
            'project_activity': self.project_activity,
            'project_goal': self.project_goal,
            'project_attribute': self.project_attribute,
            'project_start_date': self.project_start_date.strftime('%Y-%m-%d') if self.project_start_date else None,
            'project_end_date': self.project_end_date.strftime('%Y-%m-%d') if self.project_end_date else None,
            'analysis_start_date': self.analysis_start_date.strftime('%Y-%m-%d') if self.analysis_start_date else None,
            'analysis_end_date': self.analysis_end_date.strftime('%Y-%m-%d') if self.analysis_end_date else None,
            'analysis_nature': self.analysis_nature,
            'sroi_score': self.sroi_score,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': self.updated_at.strftime('%Y-%m-%d %H:%M:%S')
        }

    def update_from_dict(self, data):
        """從字典更新專案資料"""
        for key, value in data.items():
            if hasattr(self, key):
                if key.endswith('_date') and value:
                    try:
                        value = datetime.strptime(value, '%Y-%m-%d').date()
                    except ValueError:
                        continue
                setattr(self, key, value)

    def __repr__(self):
        return f'<Project {self.project_name}>'

class Stakeholder(db.Model):
    __tablename__ = 'stakeholders'
    id = db.Column(db.Integer, primary_key=True)  # 自動增長主鍵
    project_id = db.Column(db.Integer, db.ForeignKey('myprojects.id', ondelete='CASCADE'), nullable=False)  # 外鍵，關聯到 myprojects 表的 id
    stakeholder_name = db.Column(db.String(255), nullable=False)  # 主要利害關係者名稱
    stakeholder_group = db.Column(db.String(255), nullable=False)  # 組群名稱
    stakeholder_reason = db.Column(db.Text, nullable=False)  # 納入理由
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)  # 記錄建立時間
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)  # 記錄最後更新時間

    def __repr__(self):
        return f'<Stakeholder {self.stakeholder_name}>'

class Contribution(db.Model):
    __tablename__ = 'contributions'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('myprojects.id', ondelete='CASCADE'), nullable=False)
    stakeholder_id = db.Column(db.Integer, db.ForeignKey('stakeholders.id', ondelete='CASCADE'), nullable=False)
    resource_type = db.Column(db.String(50), nullable=False)
    resource_amount = db.Column(db.Float, nullable=False)
    output_description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now(), nullable=False)
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), nullable=False)

class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('myprojects.id', ondelete='CASCADE'), nullable=False)
    stakeholder_id = db.Column(db.Integer, db.ForeignKey('stakeholders.id', ondelete='CASCADE'), nullable=False)
    result_description = db.Column(db.Text, nullable=False)
    event_chain = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # 關聯
    stakeholder = db.relationship('Stakeholder', 
                                  foreign_keys=[stakeholder_id],
                                  passive_deletes=True)
    indicators = db.relationship('ResultIndicator', 
                                 backref='result', 
                                 cascade='all, delete-orphan',
                                 passive_deletes=True)

class ResultIndicator(db.Model):
    __tablename__ = 'result_indicators'
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('results.id', ondelete='CASCADE'), nullable=False)
    indicator_name = db.Column(db.String(255), nullable=False)
    scale_population = db.Column(db.Integer, nullable=False)
    duration = db.Column(db.Integer, nullable=False)
    weight = db.Column(db.Integer, nullable=False)
    pricing_variable = db.Column(db.String(255))
    pricing_amount = db.Column(db.Float)
    data_source = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

# 填寫四個因子表單
class ImpactFactor(db.Model):
    __tablename__ = 'impact_factors'
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('results.id', ondelete='CASCADE'), nullable=False)
    deadweight = db.Column(db.Float, default=0)
    displacement = db.Column(db.Float, default=0)
    attribution = db.Column(db.Float, default=0)
    drop_off = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    result = db.relationship('Result', backref='impact_factors')
    
# 管理員的後端監控
class SystemSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    system_name = db.Column(db.String(100), nullable=False)
    maintenance_mode = db.Column(db.Boolean, default=False)
    allow_registration = db.Column(db.Boolean, default=True)
    version = db.Column(db.String(20))
    last_update = db.Column(db.DateTime, default=datetime.utcnow)
    
class SystemLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20))  # 'info', 'warning', 'error'
    username = db.Column(db.String(80))
    ip_address = db.Column(db.String(45))
    action = db.Column(db.String(255))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def level_class(self):
        return {
            'info': 'info',
            'warning': 'warning',
            'error': 'danger'
        }.get(self.level, 'secondary')
 


