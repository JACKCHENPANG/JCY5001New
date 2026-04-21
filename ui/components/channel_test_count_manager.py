# -*- coding: utf-8 -*-
"""
通道测试计数管理器
负责单个通道的测试计数功能，包括计数增加、重置、显示更新、数据保存等

Author: Jack
Date: 2025-06-27
"""

import logging
import json
import os
from typing import Optional
from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class ChannelTestCountManager(QObject):
    """通道测试计数管理器"""
    
    # 信号定义
    count_updated = pyqtSignal(int, int)  # 计数更新信号 (channel, count)
    count_reset = pyqtSignal(int)  # 计数重置信号 (channel)
    
    def __init__(self, channel_number: int, config_manager=None, parent=None):
        """
        初始化测试计数管理器
        
        Args:
            channel_number: 通道号
            config_manager: 配置管理器
            parent: 父对象
        """
        super().__init__(parent)
        
        self.channel_number = channel_number
        self.config_manager = config_manager
        
        # 测试计数
        self.test_count = 0
        
        # UI元素引用
        self.count_label = None
        
        # 数据文件路径
        self.count_file_path = f"data/channel_{channel_number}_test_count.json"
        
        # 加载测试计数
        self._load_test_count()
        
    def set_ui_elements(self, ui_elements: dict):
        """
        设置UI元素引用
        
        Args:
            ui_elements: UI元素字典
        """
        self.count_label = ui_elements.get('test_count_label')
        # 初始化显示
        self._update_test_count_display()
        
    def _load_test_count(self):
        """加载测试计数"""
        try:
            if os.path.exists(self.count_file_path):
                with open(self.count_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.test_count = data.get('test_count', 0)
                    logger.debug(f"通道{self.channel_number}加载测试计数: {self.test_count}")
            else:
                self.test_count = 0
                logger.debug(f"通道{self.channel_number}测试计数文件不存在，初始化为0")
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}加载测试计数失败: {e}")
            self.test_count = 0

    def _save_test_count(self):
        """保存测试计数"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.count_file_path), exist_ok=True)
            
            data = {
                'channel_number': self.channel_number,
                'test_count': self.test_count,
                'last_updated': str(logger.handlers[0].formatter.formatTime(logger.makeRecord('', 0, '', 0, '', (), None)))
            }
            
            with open(self.count_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            logger.debug(f"通道{self.channel_number}保存测试计数: {self.test_count}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}保存测试计数失败: {e}")

    def increment_test_count(self):
        """增加测试计数"""
        try:
            self.test_count += 1
            self._save_test_count()
            self._update_test_count_display()
            self._update_test_count_color()
            
            # 发送计数更新信号
            self.count_updated.emit(self.channel_number, self.test_count)
            
            logger.debug(f"通道{self.channel_number}测试计数增加: {self.test_count}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}增加测试计数失败: {e}")

    def reset_test_count(self):
        """重置测试计数"""
        try:
            self.test_count = 0
            self._save_test_count()
            self._update_test_count_display()
            self._update_test_count_color()
            
            # 发送计数重置信号
            self.count_reset.emit(self.channel_number)
            
            logger.debug(f"通道{self.channel_number}测试计数已重置")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}重置测试计数失败: {e}")

    def _update_test_count_display(self):
        """更新测试计数显示"""
        try:
            if self.count_label:
                self.count_label.setText(str(self.test_count))
                logger.debug(f"通道{self.channel_number}测试计数显示已更新: {self.test_count}")
            else:
                logger.debug(f"通道{self.channel_number}测试计数标签未设置")
                
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试计数显示失败: {e}")

    def _update_test_count_color(self):
        """更新测试计数颜色"""
        try:
            if not self.count_label:
                return
                
            # 根据配置获取颜色阈值
            if self.config_manager:
                warning_threshold = self.config_manager.get('test_count.warning_threshold', 100)
                danger_threshold = self.config_manager.get('test_count.danger_threshold', 200)
            else:
                warning_threshold = 100
                danger_threshold = 200
            
            # 根据计数设置颜色
            if self.test_count >= danger_threshold:
                # 危险：红色
                self.count_label.setStyleSheet("color: #ff4444; font-weight: bold;")
            elif self.test_count >= warning_threshold:
                # 警告：橙色
                self.count_label.setStyleSheet("color: #ff8800; font-weight: bold;")
            else:
                # 正常：默认颜色
                self.count_label.setStyleSheet("color: #333333;")
                
            logger.debug(f"通道{self.channel_number}测试计数颜色已更新: {self.test_count}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}更新测试计数颜色失败: {e}")

    def get_test_count(self) -> int:
        """获取当前测试计数"""
        return self.test_count

    def set_test_count(self, count: int):
        """设置测试计数"""
        try:
            if count < 0:
                logger.warning(f"通道{self.channel_number}测试计数不能为负数: {count}")
                return
                
            self.test_count = count
            self._save_test_count()
            self._update_test_count_display()
            self._update_test_count_color()
            
            # 发送计数更新信号
            self.count_updated.emit(self.channel_number, self.test_count)
            
            logger.debug(f"通道{self.channel_number}测试计数已设置: {self.test_count}")
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}设置测试计数失败: {e}")

    def update_test_count(self, count: int):
        """更新测试计数（外部调用）"""
        self.set_test_count(count)

    def get_count_statistics(self) -> dict:
        """获取计数统计信息"""
        try:
            # 获取颜色阈值
            if self.config_manager:
                warning_threshold = self.config_manager.get('test_count.warning_threshold', 100)
                danger_threshold = self.config_manager.get('test_count.danger_threshold', 200)
            else:
                warning_threshold = 100
                danger_threshold = 200
            
            # 确定状态
            if self.test_count >= danger_threshold:
                status = "danger"
                status_text = "危险"
            elif self.test_count >= warning_threshold:
                status = "warning"
                status_text = "警告"
            else:
                status = "normal"
                status_text = "正常"
            
            statistics = {
                'channel_number': self.channel_number,
                'test_count': self.test_count,
                'status': status,
                'status_text': status_text,
                'warning_threshold': warning_threshold,
                'danger_threshold': danger_threshold,
                'progress_to_warning': min(100, (self.test_count / warning_threshold) * 100),
                'progress_to_danger': min(100, (self.test_count / danger_threshold) * 100)
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}获取计数统计信息失败: {e}")
            return {}

    def export_count_data(self) -> dict:
        """导出计数数据"""
        try:
            export_data = {
                'channel_number': self.channel_number,
                'test_count': self.test_count,
                'export_time': str(logger.handlers[0].formatter.formatTime(logger.makeRecord('', 0, '', 0, '', (), None))),
                'statistics': self.get_count_statistics()
            }
            
            return export_data
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}导出计数数据失败: {e}")
            return {}

    def import_count_data(self, import_data: dict) -> bool:
        """导入计数数据"""
        try:
            if 'test_count' not in import_data:
                logger.error(f"通道{self.channel_number}导入数据缺少test_count字段")
                return False
            
            count = import_data['test_count']
            if not isinstance(count, int) or count < 0:
                logger.error(f"通道{self.channel_number}导入的计数值无效: {count}")
                return False
            
            self.set_test_count(count)
            logger.info(f"通道{self.channel_number}计数数据导入成功: {count}")
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}导入计数数据失败: {e}")
            return False

    def backup_count_data(self, backup_path: str) -> bool:
        """备份计数数据"""
        try:
            backup_data = self.export_count_data()
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"通道{self.channel_number}计数数据备份成功: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}备份计数数据失败: {e}")
            return False

    def restore_count_data(self, backup_path: str) -> bool:
        """恢复计数数据"""
        try:
            if not os.path.exists(backup_path):
                logger.error(f"通道{self.channel_number}备份文件不存在: {backup_path}")
                return False
            
            with open(backup_path, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            return self.import_count_data(backup_data)
            
        except Exception as e:
            logger.error(f"通道{self.channel_number}恢复计数数据失败: {e}")
            return False
