from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt
)

from extensions import db
from models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['username', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'error': 'Missing Required Field',
                    'message': f'字段 {field} 是必需的',
                    'status_code': 400
                }), 400
        
        username = data['username'].strip()
        email = data.get('email', '').strip().lower() if data.get('email') else None
        password = data['password']
        company = data.get('company', '').strip() if data.get('company') else None
        role = 'user'  # 默认为普通用户，不允许用户选择角色

        # 验证用户名
        if len(username) < 3 or len(username) > 50:
            return jsonify({
                'error': 'Invalid Username',
                'message': '用户名长度必须在3-50个字符之间',
                'status_code': 400
            }), 400
        
        # 验证邮箱格式（如果提供了邮箱）
        if email:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                return jsonify({
                    'error': 'Invalid Email',
                    'message': '邮箱格式不正确',
                    'status_code': 400
                }), 400
        
        # 验证密码强度
        if len(password) < 8:
            return jsonify({
                'error': 'Weak Password',
                'message': '密码长度至少8个字符',
                'status_code': 400
            }), 400
        
        # 检查用户名是否已存在
        if User.query.filter_by(username=username).first():
            return jsonify({
                'error': 'Username Exists',
                'message': '用户名已存在',
                'status_code': 409
            }), 409
        
        # 检查邮箱是否已存在（如果提供了邮箱）
        if email and User.query.filter_by(email=email).first():
            return jsonify({
                'error': 'Email Exists',
                'message': '邮箱已被注册',
                'status_code': 409
            }), 409
        
        # 创建新用户
        user = User(
            username=username,
            email=email,
            password=password,
            company=company,
            role=role
        )
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': '用户注册成功',
            'user': user.to_dict(),
            'status_code': 201
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"用户注册错误: {str(e)}")
        return jsonify({
            'error': 'Registration Failed',
            'message': '注册时发生错误',
            'status_code': 500
        }), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        
        # 验证必需字段
        if not data.get('username') or not data.get('password'):
            return jsonify({
                'error': 'Missing Credentials',
                'message': '用户名和密码是必需的',
                'status_code': 400
            }), 400
        
        username = data['username'].strip()
        password = data['password']
        
        # 查找用户（支持用户名或邮箱登录）
        user = User.query.filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({
                'error': 'Invalid Credentials',
                'message': '用户名或密码错误',
                'status_code': 401
            }), 401
        
        if not user.is_active:
            return jsonify({
                'error': 'Account Disabled',
                'message': '账户已被禁用',
                'status_code': 403
            }), 403
        
        # 更新最后登录时间
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # 创建访问令牌
        access_token = create_access_token(
            identity=str(user.id),  # 转换为字符串
            expires_delta=timedelta(hours=2)
        )
        refresh_token = create_refresh_token(
            identity=str(user.id),  # 转换为字符串
            expires_delta=timedelta(days=7)
        )
        
        return jsonify({
            'message': '登录成功',
            'access_token': access_token,
            'refresh_token': refresh_token,
            'user': user.to_dict(),
            'status_code': 200
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"用户登录错误: {str(e)}")
        return jsonify({
            'error': 'Login Failed',
            'message': '登录时发生错误',
            'status_code': 500
        }), 500

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """刷新访问令牌"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在或已被禁用',
                'status_code': 404
            }), 404
        
        # 创建新的访问令牌
        access_token = create_access_token(
            identity=str(user.id),  # 转换为字符串
            expires_delta=timedelta(hours=2)
        )
        
        return jsonify({
            'message': '令牌刷新成功',
            'access_token': access_token,
            'status_code': 200
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"令牌刷新错误: {str(e)}")
        return jsonify({
            'error': 'Token Refresh Failed',
            'message': '令牌刷新时发生错误',
            'status_code': 500
        }), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """获取用户资料"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        return jsonify({
            'user': user.to_dict(),
            'status_code': 200
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"获取用户资料错误: {str(e)}")
        return jsonify({
            'error': 'Profile Fetch Failed',
            'message': '获取用户资料时发生错误',
            'status_code': 500
        }), 500

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """更新用户资料"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        data = request.get_json()
        
        # 更新允许的字段
        if 'email' in data:
            email = data['email'].strip().lower()
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                return jsonify({
                    'error': 'Invalid Email',
                    'message': '邮箱格式不正确',
                    'status_code': 400
                }), 400
            
            # 检查邮箱是否已被其他用户使用
            existing_user = User.query.filter(
                User.email == email, User.id != user.id
            ).first()
            if existing_user:
                return jsonify({
                    'error': 'Email Exists',
                    'message': '邮箱已被其他用户使用',
                    'status_code': 409
                }), 409
            
            user.email = email
        
        if 'company' in data:
            user.company = data['company'].strip() if data['company'] else None
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': '用户资料更新成功',
            'user': user.to_dict(),
            'status_code': 200
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"更新用户资料错误: {str(e)}")
        return jsonify({
            'error': 'Profile Update Failed',
            'message': '更新用户资料时发生错误',
            'status_code': 500
        }), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """修改密码"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        data = request.get_json()
        
        # 验证必需字段
        required_fields = ['current_password', 'new_password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'error': 'Missing Required Field',
                    'message': f'字段 {field} 是必需的',
                    'status_code': 400
                }), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # 验证当前密码
        if not user.check_password(current_password):
            return jsonify({
                'error': 'Invalid Current Password',
                'message': '当前密码错误',
                'status_code': 400
            }), 400
        
        # 验证新密码强度
        if len(new_password) < 8:
            return jsonify({
                'error': 'Weak Password',
                'message': '新密码长度至少8个字符',
                'status_code': 400
            }), 400
        
        # 更新密码
        user.set_password(new_password)
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'message': '密码修改成功',
            'status_code': 200
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"修改密码错误: {str(e)}")
        return jsonify({
            'error': 'Password Change Failed',
            'message': '修改密码时发生错误',
            'status_code': 500
        }), 500

