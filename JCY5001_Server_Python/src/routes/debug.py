from flask import Blueprint, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/jwt-test', methods=['GET'])
@jwt_required()
def jwt_test():
    """JWT调试测试端点"""
    try:
        current_app.logger.info("JWT测试端点被调用")
        
        # 获取JWT身份
        current_user_id = get_jwt_identity()
        current_app.logger.info(f"JWT身份: {current_user_id}")
        
        # 获取JWT声明
        jwt_claims = get_jwt()
        current_app.logger.info(f"JWT声明: {jwt_claims}")
        
        # 尝试查找用户
        from models.user import User
        user = User.query.get(current_user_id)
        current_app.logger.info(f"查找到的用户: {user}")
        
        if user:
            return jsonify({
                'message': 'JWT验证成功',
                'user_id': current_user_id,
                'username': user.username,
                'jwt_claims': jwt_claims,
                'status_code': 200
            }), 200
        else:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'user_id': current_user_id,
                'status_code': 404
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"JWT测试错误: {str(e)}")
        return jsonify({
            'error': 'JWT Test Failed',
            'message': f'JWT测试失败: {str(e)}',
            'status_code': 500
        }), 500

@debug_bp.route('/no-auth-test', methods=['GET'])
def no_auth_test():
    """无需认证的测试端点"""
    return jsonify({
        'message': '无需认证的端点正常工作',
        'status_code': 200
    }), 200

