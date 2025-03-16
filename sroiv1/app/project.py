# projects.py
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from app.templates.services import db, cache
from app.models import Project, Stakeholder, Contribution
from datetime import datetime

projects_bp = Blueprint('projects', __name__, url_prefix='/api')

@projects_bp.route('/projects', methods=['GET'])
@login_required
@cache.cached(timeout=300)  # 快取 5 分鐘
def get_projects():
    """獲取用戶的所有專案"""
    try:
        projects = Project.query.filter_by(user_id=current_user.id).all()
        return jsonify({
            'status': 'success',
            'data': [{
                'id': project.id,
                'organization_name': project.organization_name,
                'project_name': project.project_name,
                'project_activity': project.project_activity,
                'project_goal': project.project_goal,
                'project_attribute': project.project_attribute,
                'project_start_date': project.project_start_date.strftime('%Y-%m-%d') if project.project_start_date else None,
                'project_end_date': project.project_end_date.strftime('%Y-%m-%d') if project.project_end_date else None,
                'analysis_start_date': project.analysis_start_date.strftime('%Y-%m-%d') if project.analysis_start_date else None,
                'analysis_end_date': project.analysis_end_date.strftime('%Y-%m-%d') if project.analysis_end_date else None,
                'analysis_nature': project.analysis_nature,
                'created_at': project.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'sroi_score': project.sroi_score if project.sroi_score else '未評分'
            } for project in projects]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@projects_bp.route('/projects', methods=['POST'])
@login_required
def create_project():
    """創建新專案"""
    try:
        data = request.get_json()
        
        # 檢查必填欄位
        required_fields = [
            'organizationName', 'projectName', 'projectStartDate', 
            'projectEndDate', 'analysisStartDate', 'analysisEndDate',
            'projectAttribute', 'analysisNature'
        ]
        
        if not all(data.get(field) for field in required_fields):
            return jsonify({
                'status': 'error',
                'message': '請填寫所有必要欄位'
            }), 400
        
        new_project = Project(
            user_id=current_user.id,
            organization_name=data['organizationName'],
            project_name=data['projectName'],
            project_activity=data.get('projectActivity', ''),
            project_goal=data.get('projectGoal', ''),
            project_attribute=data['projectAttribute'],
            project_start_date=datetime.strptime(data['projectStartDate'], '%Y-%m-%d'),
            project_end_date=datetime.strptime(data['projectEndDate'], '%Y-%m-%d'),
            analysis_start_date=datetime.strptime(data['analysisStartDate'], '%Y-%m-%d'),
            analysis_end_date=datetime.strptime(data['analysisEndDate'], '%Y-%m-%d'),
            analysis_nature=data['analysisNature']
        )
        
        db.session.add(new_project)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '專案創建成功',
            'data': {
                'id': new_project.id,
                'project_name': new_project.project_name
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400

@projects_bp.route('/projects/<int:project_id>', methods=['DELETE'])
@login_required
def delete_project(project_id):
    """刪除專案"""
    try:
        project = Project.query.get_or_404(project_id)
        
        if project.user_id != current_user.id:
            return jsonify({
                'status': 'error',
                'message': '您沒有權限刪除此專案'
            }), 403
            
        with db.session.begin():
            # 刪除相關資料
            Contribution.query.filter_by(project_id=project_id).delete()
            Stakeholder.query.filter_by(project_id=project_id).delete()
            db.session.delete(project)
            
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '專案已成功刪除'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@projects_bp.route('/projects/<int:project_id>/stakeholders', methods=['GET'])
@login_required
def get_stakeholders(project_id):
    """獲取專案的利害關係人"""
    try:
        project = Project.query.get_or_404(project_id)
        if project.user_id != current_user.id:
            return jsonify({
                'status': 'error',
                'message': '您沒有權限訪問此專案'
            }), 403
            
        stakeholders = Stakeholder.query.filter_by(project_id=project_id).all()
        return jsonify({
            'status': 'success',
            'data': [{
                'id': s.id,
                'name': s.name,
                'type': s.type,
                'description': s.description
            } for s in stakeholders]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500