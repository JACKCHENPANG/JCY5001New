import os
import sys
import logging
from datetime import datetime

# 添加src目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, jsonify
from flask_cors import CORS

from config import Config
from extensions import db, migrate, jwt

def create_app(config_class=Config):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    
    # JWT回调函数
    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user.id if hasattr(user, 'id') else user
    
    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data):
        from models.user import User
        from flask import current_app
        identity = jwt_data["sub"]
        current_app.logger.info(f"JWT用户查找: identity={identity}")
        # 将字符串identity转换为整数
        user_id = int(identity) if isinstance(identity, str) else identity
        user = User.query.filter_by(id=user_id).one_or_none()
        current_app.logger.info(f"查找到的用户: {user}")
        return user
    
    # 启用CORS
    CORS(app, origins="*")
    
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    
    # 注册蓝图
    from routes.auth import auth_bp
    from routes.devices import devices_bp
    from routes.batteries import batteries_bp
    from routes.test_batches import test_batches_bp
    from routes.test_results import test_results_bp
    from routes.data import data_bp
    from routes.debug import debug_bp
    from routes.predict import predict_bp
    from routes.admin import admin_bp
    from routes.public import public_bp
    from routes.web_api import web_api_bp
    from routes.sync_api import sync_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(devices_bp, url_prefix='/api/devices')
    app.register_blueprint(batteries_bp, url_prefix='/api/batteries')
    app.register_blueprint(test_batches_bp, url_prefix='/api/test-batches')
    app.register_blueprint(test_results_bp, url_prefix='/api/test-results')
    app.register_blueprint(data_bp, url_prefix='/api/data')
    app.register_blueprint(debug_bp, url_prefix='/api/debug')
    app.register_blueprint(predict_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp, url_prefix='/api/public')
    app.register_blueprint(web_api_bp, url_prefix='/api/web')
    app.register_blueprint(sync_bp)
    
    # 健康检查端点
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        })
    
    # 根路径
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # API信息端点
    @app.route('/api')
    def api_info():
        return jsonify({
            'name': '电池阻抗测试系统API',
            'version': '1.0.0',
            'description': '支持JCY5001设备的电池阻抗测试数据管理系统',
            'endpoints': {
                'auth': '/api/auth',
                'devices': '/api/devices',
                'batteries': '/api/batteries',
                'test_batches': '/api/test-batches',
                'test_results': '/api/test-results',
                'data': '/api/data',
                'predict': '/api/predict',
                'admin': '/api/admin',
                'public': '/api/public',
                'web': '/api/web',
                'health': '/health'
            },
            'documentation': 'https://api-docs.jcytest.com',
            'support': 'support@jcytest.com'
        })
    
    # 错误处理
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'error': 'Not Found',
            'message': '请求的资源不存在',
            'status_code': 404
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return jsonify({
            'error': 'Internal Server Error',
            'message': '服务器内部错误',
            'status_code': 500
        }), 500
    
    # JWT错误处理
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            'error': 'Token Expired',
            'message': '令牌已过期，请重新登录',
            'status_code': 401
        }), 401
    
    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({
            'error': 'Invalid Token',
            'message': '无效的令牌',
            'status_code': 401
        }), 401
    
    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({
            'error': 'Authorization Required',
            'message': '需要提供有效的访问令牌',
            'status_code': 401
        }), 401
    
    return app

def init_database(app):
    """初始化数据库 - 使用新的迁移机制"""
    from database_migration import init_database_with_migration

    success = init_database_with_migration(app)
    if success:
        print("✅ 数据库初始化成功")
        print("管理员账号: admin")
        print("管理员密码: Admin123!")
    else:
        print("❌ 数据库初始化失败")
        # 回退到旧的初始化方法
        print("尝试使用传统方法初始化数据库...")
        init_database_legacy(app)

def init_database_legacy(app):
    """传统数据库初始化方法（备用）"""
    with app.app_context():
        try:
            # 导入所有模型
            from models.user import User, Device, TestBatch, TestResult, ImpedanceDetail

            # 创建所有表
            db.create_all()

            # 创建默认管理员用户
            admin_user = User.query.filter_by(username='admin').first()
            if not admin_user:
                admin_user = User(
                    username='admin',
                    email='admin@jcytest.com',
                    role='admin',
                    company='JCY Technology',
                    password='Admin123!'
                )
                db.session.add(admin_user)

                # 先flush以获取admin_user.id
                db.session.flush()

                # 创建示例设备
                sample_device = Device(
                    device_id='JCY5001',
                    user_id=admin_user.id,
                    name='JCY5001测试设备',
                    model='JCY5001',
                    firmware_version='1.0.0'
                )
                db.session.add(sample_device)

                db.session.commit()
                print("默认管理员用户和示例设备创建成功")
                print("管理员账号: admin")
                print("管理员密码: Admin123!")
        except Exception as e:
            print(f"传统数据库初始化失败: {e}")
            db.session.rollback()

if __name__ == '__main__':
    app = create_app()
    
    # 初始化数据库
    init_database(app)
    
    # 获取端口号
    port = int(os.environ.get('FLASK_RUN_PORT', 5002))
    
    # 启动应用
    print(f"电池阻抗测试系统API服务启动中...")
    print(f"访问地址: http://0.0.0.0:{port}")
    print(f"API文档: http://0.0.0.0:{port}/api")
    print(f"健康检查: http://0.0.0.0:{port}/health")
    
    app.run(host='0.0.0.0', port=port, debug=True)

