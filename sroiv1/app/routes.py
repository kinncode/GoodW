from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify, current_app
from .models import User, Project, Stakeholder, Contribution, Result, ResultIndicator, ImpactFactor
from . import db, bcrypt
from datetime import datetime, timedelta
from .mailconfig import verify_codes, send_verification_email
import random
import string
from flask_login import login_user, logout_user, login_required, current_user
import uuid
import time
import requests
from .forms import ImpactFactorsForm
from .analysis import ImpactAnalysis
from app.ai_service import AIService
import google.generativeai as genai

main_bp = Blueprint('main', __name__)

# ===== 基本頁面路由 =====
@main_bp.route('/')
def index():
    return render_template('index.html')

# ===== 用戶認證相關路由 =====
@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        verify_code = request.form.get('verifyCode')
        
        # 驗證碼檢查
        stored = verify_codes.get(email)
        if not stored or verify_code != stored['code']:
            flash('驗證碼錯誤', 'danger')
            return redirect(url_for('main.register'))
            
        if datetime.now() > stored['expire_at']:
            flash('驗證碼已過期', 'danger')
            return redirect(url_for('main.register'))
        
        # 檢查用戶名和郵箱是否已存在
        if User.query.filter_by(username=username).first():
            flash('該用戶名已被使用', 'danger')
            return redirect(url_for('main.register'))
            
        if User.query.filter_by(email=email).first():
            flash('該電子信箱已被註冊', 'danger')
            return redirect(url_for('main.register'))
            
        try:
            # 創建新用戶
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(
                username=username, 
                email=email, 
                password=hashed_password,
                role='user'
            )
            
            db.session.add(new_user)
            db.session.commit()
            del verify_codes[email]
            flash('註冊成功！請登入', 'success')
            return redirect(url_for('main.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('註冊失敗，請稍後重試', 'danger')
            return redirect(url_for('main.register'))
        
    return render_template('register.html')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    # 使用 next 參數來處理重定向
    next_page = request.args.get('next')
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(next_page or url_for('main.my_projects'))
        
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            new_token = str(uuid.uuid4())
            user.session_token = new_token
            user.login_time = datetime.utcnow()
            user.ip_address = request.remote_addr
            user.last_activity = datetime.utcnow()
            db.session.commit()
            
            login_user(user)
            session['user_id'] = user.id
            session['session_token'] = new_token
            session['username'] = user.username
            session['role'] = user.role
            session.permanent = True
            flash('登入成功！', 'success')
            
            # 根據角色重導向到不同頁面
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(next_page or url_for('main.index'))  # 改為導向首頁
        else:
            flash('無效的使用者名稱或密碼', 'danger')
            return redirect(url_for('main.login'))
            
    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    logout_user()  # 使用 Flask-Login 登出
    session.clear()  # 清除 session
    flash('您已登出', 'info')
    return redirect(url_for('main.login'))

# ===== 驗證碼相關路由 =====
@main_bp.route('/send-verify-code', methods=['POST'])
def send_verify_code():
    try:
        email = request.json.get('email')
        if not email:
            return jsonify({'error': 'Email is required'}), 400
            
        if User.query.filter_by(email=email).first():
            return jsonify({'error': '該電子信箱已被註冊'}), 400
            
        code = ''.join(random.choices(string.digits, k=6))
        verify_codes[email] = {
            'code': code,
            'expire_at': datetime.now() + timedelta(minutes=5)
        }
        
        try:
            send_verification_email(email, code)
            print(f"驗證碼已發送到 {email}：{code}")
            return jsonify({'message': '驗證碼已發送'}), 200
        except Exception as e:
            print(f"發送郵件時發生錯誤：{str(e)}")
            return jsonify({'error': '驗證碼發送失敗，請稍後重試'}), 500
            
    except Exception as e:
        print(f"處理請求時發生錯誤：{str(e)}")
        return jsonify({'error': '發生未知錯誤'}), 500

@main_bp.route('/verify-code', methods=['POST'])
def verify_code():
    email = request.json.get('email')
    code = request.json.get('code')
    
    if not email or not code:
        return jsonify({'error': 'Email and code are required'}), 400
        
    stored = verify_codes.get(email)
    if not stored:
        return jsonify({'error': '驗證碼不存在'}), 400
        
    if datetime.now() > stored['expire_at']:
        del verify_codes[email]
        return jsonify({'error': '驗證碼已過期'}), 400
        
    if code != stored['code']:
        return jsonify({'error': '驗證碼錯誤'}), 400
        
    return jsonify({'message': '驗證成功'}), 200

# ===== 專案相關路由 =====
@main_bp.route('/my_projects')
@login_required
def my_projects():
    try:
        projects = Project.query.filter_by(user_id=current_user.id).all()
        return render_template('my_projects.html', 
                             projects=projects,
                             load_project_scripts=True)  # 只在需要時加載特定腳本
    except Exception as e:
        flash('讀取專案時發生錯誤', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/create_project', methods=['GET', 'POST'])
@login_required
def create_project():
    try:
        if request.method == 'POST':
            # 驗證表單數據
            form_data = request.form
            
            # 檢查必填欄位
            required_fields = [
                'organizationName', 'projectName', 'projectStartDate', 
                'projectEndDate', 'analysisStartDate', 'analysisEndDate',
                'projectAttribute', 'analysisNature'
            ]
            
            if not all(form_data.get(field) for field in required_fields):
                flash('請填寫所有必要欄位', 'danger')
                return redirect(url_for('main.create_project'))
            
            # 創建專案
            new_project = Project(
                user_id=current_user.id,
                organization_name=form_data['organizationName'],
                project_name=form_data['projectName'],
                project_activity=form_data.get('projectActivity', ''),
                project_goal=form_data.get('projectGoal', ''),
                project_attribute=form_data['projectAttribute'],
                project_start_date=datetime.strptime(form_data['projectStartDate'], '%Y-%m-%d'),
                project_end_date=datetime.strptime(form_data['projectEndDate'], '%Y-%m-%d'),
                analysis_start_date=datetime.strptime(form_data['analysisStartDate'], '%Y-%m-%d'),
                analysis_end_date=datetime.strptime(form_data['analysisEndDate'], '%Y-%m-%d'),
                analysis_nature=form_data['analysisNature']
            )
            
            db.session.add(new_project)
            db.session.commit()
            flash('專案創建成功！', 'success')
            return redirect(url_for('main.my_projects'))
            
    except Exception as e:
        db.session.rollback()
        print(f"創建專案時發生錯誤: {str(e)}")
        flash('創建專案時發生錯誤，請稍後再試', 'danger')
        return redirect(url_for('main.my_projects'))
        
    return render_template('create_project.html')

@main_bp.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    if 'user_id' not in session:
        flash('請先登入！', 'warning')
        return redirect(url_for('main.login'))
        
    try:
        project = Project.query.get_or_404(project_id)
        if project.user_id != session['user_id']:
            flash('您沒有權限刪除此專案！', 'danger')
            return redirect(url_for('main.my_projects'))
            
        # 開始事務
        db.session.begin_nested()
        
        try:
            # 先刪除相關的 contributions 記錄
            Contribution.query.filter_by(project_id=project_id).delete(synchronize_session=False)
            db.session.flush()
            
            # 再刪除相關的 stakeholders 記錄
            Stakeholder.query.filter_by(project_id=project_id).delete(synchronize_session=False)
            db.session.flush()
            
            # 最後刪除專案
            db.session.delete(project)
            db.session.commit()
            
            flash('專案已成功刪除！', 'success')
            
        except Exception as e:
            db.session.rollback()
            raise e
            
    except Exception as e:
        print(f"刪除專案時發生錯誤: {str(e)}")
        db.session.rollback()
        flash('刪除專案時發生錯誤！', 'danger')
    
    return redirect(url_for('main.my_projects'))

#編輯獲取專案資料路由。
@main_bp.route('/get_project/<int:project_id>')
def get_project(project_id):
    try:
        # 檢查用戶是否登入
        if 'user_id' not in session:
            return jsonify({'error': '請先登入'}), 401

        # 獲取專案資料
        project = Project.query.get_or_404(project_id)
        
        # 確認是否為專案擁有者
        if project.user_id != session['user_id']:
            return jsonify({'error': '無權限訪問此專案'}), 403

        # 返回專案資料
        return jsonify({
            'organizationName': project.organization_name,
            'projectName': project.project_name,
            'projectActivity': project.project_activity,
            'projectGoal': project.project_goal,
            'projectAttribute': project.project_attribute,
            'projectStartDate': project.project_start_date.strftime('%Y-%m-%d'),
            'projectEndDate': project.project_end_date.strftime('%Y-%m-%d'),
            'analysisStartDate': project.analysis_start_date.strftime('%Y-%m-%d'),
            'analysisEndDate': project.analysis_end_date.strftime('%Y-%m-%d'),
            'analysisNature': project.analysis_nature
        })
    except Exception as e:
        print(f"獲取專案資料時發生錯誤: {str(e)}")
        return jsonify({'error': '獲取專案資料失敗'}), 500
#編輯專案的路由   
@main_bp.route('/update_project/<int:project_id>', methods=['POST'])
def update_project(project_id):
    if 'user_id' not in session:
        flash('請先登入！', 'warning')
        return redirect(url_for('main.login'))

    try:
        # 獲取專案並驗證所有權
        project = Project.query.get_or_404(project_id)
        if project.user_id != session['user_id']:
            flash('您沒有權限編輯此專案！', 'danger')
            return redirect(url_for('main.my_projects'))

        # 驗證必填欄位
        required_fields = [
            'organizationName', 'projectName', 'projectStartDate',
            'projectEndDate', 'analysisStartDate', 'analysisEndDate',
            'projectAttribute', 'analysisNature'
        ]
        
        for field in required_fields:
            if not request.form.get(field):
                flash(f'請填寫所有必要欄位', 'danger')
                return redirect(url_for('main.my_projects'))

        # 日期驗證
        try:
            project_start = datetime.strptime(request.form['projectStartDate'], '%Y-%m-%d').date()
            project_end = datetime.strptime(request.form['projectEndDate'], '%Y-%m-%d').date()
            analysis_start = datetime.strptime(request.form['analysisStartDate'], '%Y-%m-%d').date()
            analysis_end = datetime.strptime(request.form['analysisEndDate'], '%Y-%m-%d').date()

            if project_end < project_start:
                flash('專案結束日期必須晚於開始日期', 'danger')
                return redirect(url_for('main.my_projects'))
            
            if analysis_end < analysis_start:
                flash('分析結束日期必須晚於開始日期', 'danger')
                return redirect(url_for('main.my_projects'))

        except ValueError:
            flash('日期格式不正確', 'danger')
            return redirect(url_for('main.my_projects'))

        # 更新專案資料
        project.organization_name = request.form['organizationName']
        project.project_name = request.form['projectName']
        project.project_activity = request.form['projectActivity']
        project.project_goal = request.form['projectGoal']
        project.project_attribute = request.form['projectAttribute']
        project.project_start_date = project_start
        project.project_end_date = project_end
        project.analysis_start_date = analysis_start
        project.analysis_end_date = analysis_end
        project.analysis_nature = request.form['analysisNature']

        db.session.commit()
        flash('專案更新成功！', 'success')
        
    except Exception as e:
        print(f"更新專案時發生錯誤: {str(e)}")
        db.session.rollback()
        flash('更新專案時發生錯誤！', 'danger')
    
    return redirect(url_for('main.my_projects'))

 # 利害關係人路由器
@main_bp.route('/stakeholder_form/<int:project_id>', methods=['GET', 'POST'])
def stakeholderForm(project_id):
    if 'user_id' not in session:
        flash('請先登入！', 'warning')
        return redirect(url_for('main.login'))
        
    project = Project.query.get_or_404(project_id)
    if project.user_id != session['user_id']:
        flash('您沒有權限訪問此專案！', 'danger')
        return redirect(url_for('main.my_projects'))
    
    # 檢查是否已存在貢獻資料
    has_contributions = Contribution.query.filter_by(project_id=project_id).first() is not None
    
    if request.method == 'POST':
        try:
            return redirect(url_for('main.contributions', project_id=project_id))
        except Exception as e:
            flash(f'發生錯誤：{str(e)}', 'danger')
            return redirect(url_for('main.stakeholderForm', project_id=project_id))
    
    stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
    contributions = Contribution.query.filter_by(project_id=project_id).all()
    
    return render_template('stakeholderForm.html', 
                         project_id=project_id, 
                         stakeholders=stakeholders,
                         contributions=contributions,
                         has_contributions=has_contributions)  # 傳遞到模板

@main_bp.route('/save_stakeholders', methods=['POST'])
def save_stakeholders():
    if 'user_id' not in session:
        return jsonify({'error': '請先登入'}), 401
        
    try:
        data = request.get_json()
        project_id = request.args.get('project_id')
        
        if not project_id:
            return jsonify({'error': '缺少專案 ID'}), 400
            
        project = Project.query.get_or_404(project_id)
        if project.user_id != session['user_id']:
            return jsonify({'error': '無權限訪問此專案'}), 403
            
        # 檢查是否已存在貢獻資料
        has_contributions = Contribution.query.filter_by(project_id=project_id).first() is not None
        if has_contributions:
            return jsonify({'error': '已存在貢獻資料，無法修改利害關係人！'}), 403
            
        # 開始事務
        db.session.begin_nested()
        
        try:
            # 獲取現有的利害關係人
            existing_stakeholders = {s.id: s for s in Stakeholder.query.filter_by(project_id=project_id).all()}
            print(f"現有的利害關係人: {existing_stakeholders}")  # 調試用
            
            processed_ids = set()
            
            # 更新或新增利害關係人資料
            for item in data:
                if not all(item.get(field) for field in ['name', 'group', 'reason']):
                    continue
                
                if item.get('old_id') and int(item['old_id']) in existing_stakeholders:
                    # 更新現有記錄
                    stakeholder = existing_stakeholders[int(item['old_id'])]
                    stakeholder.stakeholder_name = item['name']
                    stakeholder.stakeholder_group = item['group']
                    stakeholder.stakeholder_reason = item['reason']
                    processed_ids.add(int(item['old_id']))
                else:
                    # 新增記錄
                    new_stakeholder = Stakeholder(
                        project_id=project_id,
                        stakeholder_name=item['name'],
                        stakeholder_group=item['group'],
                        stakeholder_reason=item['reason']
                    )
                    db.session.add(new_stakeholder)
            
            db.session.commit()
            print("利害關係人資料儲存成功")  # 調試用
            return jsonify({
                'message': '利害關係人資料保存成功',
                'count': len(data)
            }), 200
            
        except Exception as e:
            db.session.rollback()
            raise e
            
    except Exception as e:
        print(f"保存利害關係人資料時發生錯誤: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/contributions/<int:project_id>', methods=['GET', 'POST'])
@login_required
def contributions(project_id):
    # 獲取專案資訊
    project = Project.query.get_or_404(project_id)
    
    # 獲取該專案的所有利害關係者
    stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
    
    # 獲取該專案的所有貢獻資料
    contributions = Contribution.query.filter_by(project_id=project_id).all()
    
    if request.method == 'POST':
        try:
            return redirect(url_for('main.results', project_id=project_id))
        except Exception as e:
            flash(f'發生錯誤：{str(e)}', 'danger')
            return redirect(url_for('main.contributions', project_id=project_id))
        
    return render_template('contributions.html',
                         project=project,
                         project_id=project_id,
                         stakeholders=stakeholders,
                         contributions=contributions)

@main_bp.route('/save_contributions', methods=['POST'])
def save_contributions():
    if 'user_id' not in session:
        return jsonify({'error': '請先登入'}), 401
        
    try:
        data = request.get_json()
        project_id = request.args.get('project_id')
        
        if not project_id:
            return jsonify({'error': '缺少專案 ID'}), 400
            
        project = Project.query.get_or_404(project_id)
        if project.user_id != session['user_id']:
            return jsonify({'error': '無權限訪問此專案'}), 403
            
        # 開始事務
        db.session.begin_nested()
        
        try:
            # 刪除舊的貢獻資料
            Contribution.query.filter_by(project_id=project_id).delete()
            db.session.flush()
            
            # 添加新的貢獻資料
            for item in data:
                if not all(key in item and item[key] for key in ['stakeholder_id', 'resource_type', 'resource_amount', 'output_description']):
                    raise ValueError('缺少必要欄位或欄位值為空')
                
                new_contribution = Contribution(
                    project_id=project_id,
                    stakeholder_id=int(item['stakeholder_id']),
                    resource_type=item['resource_type'],
                    resource_amount=float(item['resource_amount']),
                    output_description=item['output_description']
                )
                db.session.add(new_contribution)
            
            db.session.commit()
            return jsonify({'message': '貢獻資料保存成功'}), 200
            
        except Exception as e:
            db.session.rollback()
            raise e
            
    except ValueError as ve:
        db.session.rollback()
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        print(f"保存貢獻資料時發生錯誤: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
# 成果路由器
@main_bp.route('/project/<int:project_id>/results', methods=['GET', 'POST'])
@login_required
def results(project_id):
    if 'user_id' not in session:
        flash('請先登入！', 'warning')
        return redirect(url_for('main.login'))
        
    project = Project.query.get_or_404(project_id)
    if project.user_id != session['user_id']:
        flash('您沒有權限訪問此專案！', 'danger')
        return redirect(url_for('main.my_projects'))
    
    stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
    if not stakeholders:
        flash('請先新增利害關係人！', 'warning')
        return redirect(url_for('main.stakeholderForm', project_id=project_id))
        
    results = Result.query.filter_by(project_id=project_id).all()
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            stakeholder_ids = request.form.getlist('stakeholder_id[]')
            descriptions = request.form.getlist('result_description[]')
            event_chains = request.form.getlist('event_chain[]')
            indicator_names = request.form.getlist('indicator_name[]')
            
            # 驗證是否有填寫資料
            if not any(stakeholder_ids) or not any(descriptions) or not any(indicator_names):
                flash('請至少填寫一筆完整的成果資料', 'warning')
                return render_template('resultsForm.html',
                                     project_id=project_id,
                                     stakeholders=stakeholders,
                                     results=results)
            
            # 獲取現有的結果
            existing_results = Result.query.filter_by(project_id=project_id).all()
            existing_result_map = {
                (str(r.stakeholder_id), r.result_description): r 
                for r in existing_results
            }
            
            # 新增新的結果和指標
            for i in range(len(stakeholder_ids)):
                if stakeholder_ids[i] and descriptions[i]:  # 確保必要欄位有值
                    # 檢查是否已存在相同的結果
                    key = (stakeholder_ids[i], descriptions[i])
                    if key in existing_result_map:
                        # 更新現有結果
                        result = existing_result_map[key]
                        result.event_chain = event_chains[i] if event_chains[i] else None
                        if result.indicators:
                            result.indicators[0].indicator_name = indicator_names[i]
                    else:
                        # 創建新結果
                        result = Result(
                            project_id=project_id,
                            stakeholder_id=stakeholder_ids[i],
                            result_description=descriptions[i],
                            event_chain=event_chains[i] if event_chains[i] else None
                        )
                        db.session.add(result)
                        db.session.flush()
                        
                        # 新增對應的指標
                        indicator = ResultIndicator(
                            result_id=result.id,
                            indicator_name=indicator_names[i],
                            scale_population=1,  # 預設值
                            duration=1,          # 預設值
                            weight=1             # 預設值
                        )
                        db.session.add(indicator)
            
            # 刪除未更新的舊結果
            for result in existing_results:
                key = (str(result.stakeholder_id), result.result_description)
                if key not in [(sid, desc) for sid, desc in zip(stakeholder_ids, descriptions)]:
                    # 先刪除相關的 ImpactFactor
                    ImpactFactor.query.filter_by(result_id=result.id).delete()
                    # 再刪除相關的 ResultIndicator
                    ResultIndicator.query.filter_by(result_id=result.id).delete()
                    # 最後刪除 Result
                    db.session.delete(result)
            
            db.session.commit()
            flash('成果資料已成功儲存！', 'success')
            
            if action == 'next':
                return redirect(url_for('main.result_indicators', project_id=project_id))
            else:
                return redirect(url_for('main.results', project_id=project_id))
            
        except Exception as e:
            db.session.rollback()
            flash('儲存失敗，請稍後再試。', 'danger')
            print(str(e))
    
    return render_template('resultsForm.html', 
                         project_id=project_id,
                         stakeholders=stakeholders,
                         results=results)

@main_bp.route('/project/<int:project_id>/result_indicators', methods=['GET', 'POST'])
@login_required
def result_indicators(project_id):
    if 'user_id' not in session:
        flash('請先登入！', 'warning')
        return redirect(url_for('main.login'))
        
    project = Project.query.get_or_404(project_id)
    if project.user_id != session['user_id']:
        flash('您沒有權限訪問此專案！', 'danger')
        return redirect(url_for('main.my_projects'))
    
    results = Result.query.filter_by(project_id=project_id).all()
    if not results:
        flash('請先設定成果！', 'warning')
        return redirect(url_for('main.results', project_id=project_id))

    if request.method == 'POST':
        try:
            # 獲取表單數據
            scale_populations = request.form.getlist('scale_population[]')
            durations = request.form.getlist('duration[]')
            weights = request.form.getlist('weight[]')
            pricing_variables = request.form.getlist('pricing_variable[]')
            pricing_amounts = request.form.getlist('pricing_amount[]')
            data_sources = request.form.getlist('data_source[]')
            is_advanced_mode = request.form.get('advancedMode') == 'true'
            
            # 基本驗證
            if not all(scale_populations) or not all(durations):
                return jsonify({
                    'success': False,
                    'message': '請填寫所有必要欄位'
                })

            # 進階模式驗證
            if is_advanced_mode:
                if not any(pricing_amounts):
                    return jsonify({
                        'success': False,
                        'message': '請在進階模式下填寫至少一筆定價資訊'
                    })
            
            # 一般模式驗證
            else:
                if not all(weights):
                    return jsonify({
                        'success': False,
                        'message': '請填寫所有權重值'
                    })

            # 更新每個結果的指標
            for i, result in enumerate(results):
                if i < len(scale_populations):
                    indicator = result.indicators[0]
                    try:
                        # 更新基本欄位
                        indicator.scale_population = int(scale_populations[i])
                        indicator.duration = int(durations[i])
                        
                        # 根據模式更新資料
                        if is_advanced_mode:
                            # 進階模式：使用定價資料
                            indicator.pricing_variable = pricing_variables[i] if i < len(pricing_variables) else None
                            indicator.pricing_amount = float(pricing_amounts[i]) if i < len(pricing_amounts) and pricing_amounts[i] else 0
                            indicator.data_source = data_sources[i] if i < len(data_sources) else None
                            indicator.weight = 1  # 將 weight 設為 1 而不是 0
                        else:
                            # 一般模式：使用權重
                            indicator.weight = int(weights[i]) if i < len(weights) else 1
                            indicator.pricing_variable = None
                            indicator.pricing_amount = 0
                            indicator.data_source = None
                            
                    except (ValueError, TypeError) as e:
                        return jsonify({
                            'success': False,
                            'message': f'數據格式錯誤：{str(e)}'
                        })
            
            db.session.commit()
            
            # 計算並更新 SROI 分數
            update_project_sroi(project_id)
            
            # 根據按鈕動作決定行為
            if request.form.get('action') == 'save':
                return jsonify({
                    'success': True,
                    'message': '資料已成功儲存'
                })
            else:  # action == 'next'
                return jsonify({
                    'success': True,
                    'redirect_url': url_for('main.impact_factors', project_id=project_id)
                })
                
        except Exception as e:
            db.session.rollback()
            print(f"Error saving indicators: {str(e)}")
            return jsonify({
                'success': False,
                'message': f'儲存失敗：{str(e)}'
            })

    # GET 請求返回模板
    return render_template('resultIndicatorsForm.html',
                         project_id=project_id,
                         results=results)

@main_bp.route('/reset_stakeholder_data/<int:project_id>', methods=['POST'])
def reset_stakeholder_data(project_id):
    if 'user_id' not in session:
        return jsonify({'error': '請先登入'}), 401
        
    try:
        project = Project.query.get_or_404(project_id)
        if project.user_id != session['user_id']:
            return jsonify({'error': '無權限訪問此專案'}), 403
            
        # 刪除所有相關資料
        with db.session.begin_nested():
            # 刪除 contributions
            Contribution.query.filter_by(project_id=project_id).delete()
            # 刪除 results 和相關的 indicators
            results = Result.query.filter_by(project_id=project_id).all()
            for result in results:
                ResultIndicator.query.filter_by(result_id=result.id).delete()
            Result.query.filter_by(project_id=project_id).delete()
            # 刪除 stakeholders
            Stakeholder.query.filter_by(project_id=project_id).delete()
            
        db.session.commit()
        return jsonify({'message': '資料已重設成功，現在可以修改利害關係人資料'}), 200
            
    except Exception as e:
        print(f"重設資料時發生錯誤: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main_bp.route('/delete_stakeholder/<int:stakeholder_id>', methods=['DELETE'])
def delete_stakeholder(stakeholder_id):
    if 'user_id' not in session:
        return jsonify({'error': '請先登入'}), 401
        
    try:
        stakeholder = Stakeholder.query.get_or_404(stakeholder_id)
        project = Project.query.get_or_404(stakeholder.project_id)
        
        if project.user_id != session['user_id']:
            return jsonify({'error': '無權限刪除此利害關係人'}), 403
            
        # 檢查是否已存在貢獻資料
        has_contributions = Contribution.query.filter_by(project_id=project.id).first() is not None
        if has_contributions:
            return jsonify({'error': '已存在貢獻資料，無法刪除利害關係人！'}), 403
            
        # 先刪除與此利害關係人相關的結果和指標
        results = Result.query.filter_by(stakeholder_id=stakeholder_id).all()
        for result in results:
            # 刪除相關的指標
            ResultIndicator.query.filter_by(result_id=result.id).delete()
            # 刪除結果
            db.session.delete(result)
            
        # 最後刪除利害關係人
        db.session.delete(stakeholder)
        db.session.commit()
        
        return jsonify({'message': '利害關係人已成功刪除'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"刪除利害關係人時發生錯誤: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/project/<int:project_id>/impact_factors', methods=['GET', 'POST'])
@login_required
def impact_factors(project_id):
    form = ImpactFactorsForm()
    if 'user_id' not in session:
        flash('請先登入！', 'warning')
        return redirect(url_for('main.login'))
        
    project = Project.query.get_or_404(project_id)
    if project.user_id != session['user_id']:
        flash('您沒有權限訪問此專案！', 'danger')
        return redirect(url_for('main.my_projects'))
    
    # 獲取所有結果及其關聯資料
    results = Result.query\
        .filter_by(project_id=project_id)\
        .join(Stakeholder)\
        .join(ResultIndicator)\
        .options(
            db.joinedload(Result.stakeholder),
            db.joinedload(Result.indicators),
            db.joinedload(Result.impact_factors)
        ).all()

    if not results:
        flash('請先設定成果和指標！', 'warning')
        return redirect(url_for('main.results', project_id=project_id))

    if request.method == 'POST':
        current_app.logger.info(f'Received form data: {request.form}')
        try:
            for result in results:
                # 取得對應的因子值
                deadweight = request.form.get(f'deadweight_{result.id}', 0)
                displacement = request.form.get(f'displacement_{result.id}', 0)
                attribution = request.form.get(f'attribution_{result.id}', 0)
                drop_off = request.form.get(f'drop_off_{result.id}', 0)
                
                # 更新或創建 ImpactFactor
                impact_factor = ImpactFactor.query.filter_by(result_id=result.id).first()
                if not impact_factor:
                    impact_factor = ImpactFactor(result_id=result.id)
                    db.session.add(impact_factor)
                
                impact_factor.deadweight = float(deadweight)
                impact_factor.displacement = float(displacement)
                impact_factor.attribution = float(attribution)
                impact_factor.drop_off = float(drop_off)
            
            db.session.commit()
            
            # 計算並更新 SROI 分數
            update_project_sroi(project_id)
            
            # 根據按鈕動作決定行為
            if request.form.get('action') == 'save':
                flash('影響力因子已成功儲存', 'success')
                return redirect(url_for('main.impact_factors', project_id=project_id))
            else:  # action == 'analyze'
                return redirect(url_for('main.project_analysis', project_id=project_id))
                
        except Exception as e:
            db.session.rollback()
            flash('儲存失敗，請稍後再試', 'danger')
            print(f"Error: {str(e)}")
            return redirect(url_for('main.impact_factors', project_id=project_id))

    # 準備模板所需的資料結構
    results_data = []
    for result in results:
        # 獲取或創建影響力因子
        impact_factor = ImpactFactor.query.filter_by(result_id=result.id).first()
        if not impact_factor:
            impact_factor = ImpactFactor(
                result_id=result.id,
                deadweight=0,
                displacement=0,
                attribution=0,
                drop_off=0
            )
            db.session.add(impact_factor)
            db.session.commit()

        result_data = {
            'id': result.id,
            'stakeholder_name': result.stakeholder.stakeholder_name,
            'result_description': result.result_description,
            'indicator_name': result.indicators[0].indicator_name if result.indicators else '',
            'scale_population': result.indicators[0].scale_population if result.indicators else 0,
            'weight': result.indicators[0].weight if result.indicators else 0,
            'impact_factors': [impact_factor]  # 使用實際的影響力因子物件
        }
        results_data.append(result_data)
    
    # GET 請求返回模板
    return render_template('impactFactorsForm.html',
                         project_id=project_id,
                         results=results_data,
                         form=form)

@main_bp.route('/project/<int:project_id>/stakeholders', methods=['GET', 'POST'])
@login_required
def project_stakeholders(project_id):
    project = Project.query.get_or_404(project_id)
    
    # 只檢查新建立的專案
    if not project.stakeholders:  # 如果還沒有利害關係人
        can_continue, message = current_user.can_continue_project()
        if not can_continue:
            flash(message, 'warning')
            return redirect(url_for('main.my_projects'))
    
    # ... 原有的專案處理代碼 ...

@main_bp.route('/my_profile', methods=['GET', 'POST'])
@login_required
def my_profile():
    if request.method == 'POST':
        try:
            # 獲取表單數據
            email = request.form.get('email')
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # 驗證當前密碼
            if current_password:
                if not current_user.check_password(current_password):
                    flash('當前密碼不正確', 'danger')
                    return redirect(url_for('main.my_profile'))
                
                # 更新密碼
                if new_password:
                    if new_password != confirm_password:
                        flash('新密碼與確認密碼不符', 'danger')
                        return redirect(url_for('main.my_profile'))
                    current_user.set_password(new_password)
                    flash('密碼已更新', 'success')
            
            # 更新電子郵件
            if email and email != current_user.email:
                if User.query.filter_by(email=email).first():
                    flash('此電子郵件已被使用', 'danger')
                    return redirect(url_for('main.my_profile'))
                current_user.email = email
            
            db.session.commit()
            flash('個人資料已更新', 'success')
            return redirect(url_for('main.my_profile'))
            
        except Exception as e:
            db.session.rollback()
            flash('更新失敗，請稍後再試', 'danger')
            return redirect(url_for('main.my_profile'))
    
    return render_template('my_profile.html')


@main_bp.route('/project/<int:project_id>/analysis')
@login_required
def project_analysis(project_id):
    project = Project.query.get_or_404(project_id)
    if project.user_id != current_user.id:
        flash('您沒有權限訪問此專案！', 'danger')
        return redirect(url_for('main.my_projects'))
    
    try:
        # 更新 SROI 分數
        update_project_sroi(project_id)
        
        analyzer = ImpactAnalysis(project_id)
        analysis_data = analyzer.get_project_summary()
        
        return render_template('analysis_report.html',
                             project=project,
                             analysis_data=analysis_data)
    except Exception as e:
        print(f"Analysis Error: {str(e)}")
        flash(f'生成分析報告時發生錯誤：{str(e)}', 'danger')
        return redirect(url_for('main.my_projects'))

def update_project_sroi(project_id):
    """更新專案的 SROI 分數"""
    try:
        project = Project.query.get_or_404(project_id)
        analyzer = ImpactAnalysis(project_id)
        project_sroi = analyzer.calculate_project_sroi()
        project.sroi_score = f"{project_sroi:10.2f}"  # 格式化為10位字符的字串，包含2位小數
        project.last_calculated = datetime.utcnow()
        db.session.commit()
        return True
    except Exception as e:
        print(f"Error updating SROI: {str(e)}")
        db.session.rollback()
        return False

@main_bp.route('/delete_result/<int:result_id>', methods=['DELETE'])
@login_required
def delete_result(result_id):
    try:
        result = Result.query.get_or_404(result_id)
        project = Project.query.get_or_404(result.project_id)
        
        if project.user_id != current_user.id:
            return jsonify({'success': False, 'message': '無權限刪除此結果'}), 403
            
        # 先刪除相關的 ImpactFactor
        ImpactFactor.query.filter_by(result_id=result_id).delete()
        # 再刪除相關的 ResultIndicator
        ResultIndicator.query.filter_by(result_id=result_id).delete()
        # 最後刪除 Result
        db.session.delete(result)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '結果已成功刪除'}), 200
        
    except Exception as e:
        db.session.rollback()
        print(f"刪除結果時發生錯誤: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@main_bp.route('/get_related_data_count/<int:project_id>')
def get_related_data_count(project_id):
    if 'user_id' not in session:
        return jsonify({'error': '請先登入'}), 401
        
    try:
        project = Project.query.get_or_404(project_id)
        if project.user_id != session['user_id']:
            return jsonify({'error': '無權限訪問此專案'}), 403
            
        # 獲取相關資料的數量
        stakeholders = Stakeholder.query.filter_by(project_id=project_id).count()
        contributions = Contribution.query.filter_by(project_id=project_id).count()
        results = Result.query.filter_by(project_id=project_id).count()
        
        return jsonify({
            'stakeholders': stakeholders,
            'contributions': contributions,
            'results': results
        }), 200
            
    except Exception as e:
        print(f"獲取資料數量時發生錯誤: {str(e)}")
        return jsonify({'error': str(e)}), 500

@main_bp.route('/api/ai/assistant', methods=['POST'])
@login_required
def ai_assistant():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '無效的請求數據'}), 400
        
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'error': '請提供提示'}), 400
        
        context = data.get('context', 'general')
        response = AIService.generate_response(prompt, context)
        return jsonify({'response': response})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main_bp.route('/ai/evaluate', methods=['POST'])
@login_required
def ai_evaluate():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({'error': '缺少必要的 prompt 參數'}), 400
        
        # 使用 AIService 進行評估
        response = AIService.generate_response(prompt, context='analysis')
        
        return jsonify({
            'response': response
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500




