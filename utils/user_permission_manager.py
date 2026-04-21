# -*- coding: utf-8 -*-
"""
用户权限管理器
管理操作员和管理员权限
"""

from PyQt5.QtCore import QObject, pyqtSignal
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class UserRole(Enum):
    """用户角色枚举"""
    OPERATOR = "operator"      # 操作员
    ADMINISTRATOR = "admin"    # 管理员

class UserPermissionManager(QObject):
    """用户权限管理器"""

    # 信号定义
    role_changed = pyqtSignal(str)  # 角色变更信号

    def __init__(self):
        super().__init__()
        self._current_role = UserRole.OPERATOR  # 默认为操作员
        self._is_logged_in = False

    def set_user_role(self, role: UserRole):
        """设置用户角色"""
        old_role = self._current_role
        self._current_role = role
        self._is_logged_in = True

        logger.info(f"用户角色变更: {old_role.value} → {role.value}")
        self.role_changed.emit(role.value)

    def get_current_role(self) -> UserRole:
        """获取当前用户角色"""
        return self._current_role

    def is_administrator(self) -> bool:
        """是否为管理员"""
        return self._current_role == UserRole.ADMINISTRATOR

    def is_operator(self) -> bool:
        """是否为操作员"""
        return self._current_role == UserRole.OPERATOR

    def can_edit_product_info(self) -> bool:
        """是否可以编辑产品信息"""
        # 开放电池信息编辑权限给所有用户
        return True

    def can_edit_batch_info(self) -> bool:
        """是否可以编辑批次信息"""
        # 批次信息所有用户都可以编辑
        return True

    def can_edit_settings(self) -> bool:
        """是否可以编辑系统设置"""
        return self.is_administrator()

    def login_as_operator(self):
        """以操作员身份登录"""
        self.set_user_role(UserRole.OPERATOR)

    def login_as_administrator(self, password: str = "") -> bool:
        """以管理员身份登录"""
        # 简单的密码验证（实际项目中应该使用更安全的方式）
        admin_password = "JCY5001-ADMIN"  # 修改管理员密码为JCY5001-ADMIN

        if password == admin_password:
            self.set_user_role(UserRole.ADMINISTRATOR)
            return True
        else:
            logger.warning("管理员密码错误")
            return False

    def logout(self):
        """登出"""
        self._is_logged_in = False
        self.set_user_role(UserRole.OPERATOR)  # 默认回到操作员角色

    def is_logged_in(self) -> bool:
        """是否已登录"""
        return self._is_logged_in

# 全局权限管理器实例 - 使用单例模式确保对象不被删除
_permission_manager_instance = None

def get_permission_manager():
    """获取权限管理器单例"""
    global _permission_manager_instance
    if _permission_manager_instance is None:
        _permission_manager_instance = UserPermissionManager()
    return _permission_manager_instance

# 为了兼容性，保留原来的变量名
permission_manager = get_permission_manager()
