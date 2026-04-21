from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager

# 创建扩展实例
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()

