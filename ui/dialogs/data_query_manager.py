# -*- coding: utf-8 -*-
"""
数据查询管理器
负责数据查询相关功能

从data_export_dialog.py中提取，遵循单一职责原则

Author: Augment Agent  
Date: 2025-06-04
"""

import logging
from typing import List, Dict, Optional
from PyQt5.QtCore import QThread, pyqtSignal
from data.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


class DataQueryWorker(QThread):
    """异步数据查询工作线程 - 解决数据分析卡死问题"""

    query_completed = pyqtSignal(list, int)  # 查询完成信号 (数据, 总数)
    query_failed = pyqtSignal(str)           # 查询失败信号
    progress_updated = pyqtSignal(str)       # 进度更新信号

    def __init__(self, db_manager, batch_id=None, batch_number=None, start_date=None, end_date=None,
                 channel_number=None, channel_numbers=None, battery_code=None,
                 battery_code_fuzzy=False, is_pass=None, limit=20, offset=0):
        super().__init__()
        self.db_manager = db_manager
        self.batch_id = batch_id
        self.batch_number = batch_number
        self.start_date = start_date
        self.end_date = end_date
        self.channel_number = channel_number
        self.channel_numbers = channel_numbers
        self.battery_code = battery_code
        self.battery_code_fuzzy = battery_code_fuzzy
        self.is_pass = is_pass
        self.limit = limit
        self.offset = offset

    def run(self):
        """执行异步数据查询"""
        try:
            self.progress_updated.emit("正在查询数据...")

            # 先查询总数
            total_count = self.db_manager.get_test_results_count(
                batch_id=self.batch_id,
                batch_number=self.batch_number,
                start_date=self.start_date,
                end_date=self.end_date,
                channel_number=self.channel_number,
                channel_numbers=self.channel_numbers,
                battery_code=self.battery_code,
                battery_code_fuzzy=self.battery_code_fuzzy,
                is_pass=self.is_pass
            )

            self.progress_updated.emit(f"找到 {total_count} 条记录，正在加载...")

            # 查询分页数据（不包含JSON字段，提升性能）
            data = self.db_manager.get_test_results(
                batch_id=self.batch_id,
                batch_number=self.batch_number,
                start_date=self.start_date,
                end_date=self.end_date,
                channel_number=self.channel_number,
                channel_numbers=self.channel_numbers,
                battery_code=self.battery_code,
                battery_code_fuzzy=self.battery_code_fuzzy,
                is_pass=self.is_pass,
                limit=self.limit,
                offset=self.offset,
                include_json=False  # 性能优化：不加载JSON字段
            )

            self.query_completed.emit(data, total_count)

        except Exception as e:
            logger.error(f"异步数据查询失败: {e}")
            self.query_failed.emit(str(e))


class DataQueryManager:
    """
    数据查询管理器
    
    职责：
    - 管理数据查询逻辑
    - 处理分页查询
    - 管理查询状态
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化数据查询管理器
        
        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.query_worker = None
        
        # 分页相关变量
        self.current_page = 0
        self.page_size = 20  # 每页显示20条数据
        self.total_count = 0
        self.total_pages = 0
        
        # 查询状态
        self._is_querying = False
        
        logger.debug("数据查询管理器初始化完成")
    
    def start_query(self, batch_id=None, batch_number=None, start_date=None, end_date=None,
                   channel_number=None, channel_numbers=None, battery_code=None,
                   battery_code_fuzzy=False, is_pass=None, append_mode=False):
        """
        开始数据查询

        Args:
            batch_id: 批次ID
            batch_number: 批次号（模糊查询）
            start_date: 开始日期
            end_date: 结束日期
            channel_number: 单个通道号
            channel_numbers: 多个通道号列表
            battery_code: 电池码搜索文本
            battery_code_fuzzy: 是否模糊搜索电池码
            is_pass: 是否合格
            append_mode: 是否为追加模式

        Returns:
            DataQueryWorker: 查询工作线程
        """
        try:
            # 检查是否正在查询中，避免重复查询
            if self._is_querying:
                logger.debug("查询正在进行中，跳过重复查询")
                return None
            
            # 停止之前的查询
            if self.query_worker and self.query_worker.isRunning():
                self.query_worker.terminate()
                self.query_worker.wait()
            
            # 设置查询状态
            self._is_querying = True
            
            # 计算偏移量
            offset = self.current_page * self.page_size
            
            # 创建查询工作线程
            self.query_worker = DataQueryWorker(
                db_manager=self.db_manager,
                batch_id=batch_id,
                batch_number=batch_number,
                start_date=start_date,
                end_date=end_date,
                channel_number=channel_number,
                channel_numbers=channel_numbers,
                battery_code=battery_code,
                battery_code_fuzzy=battery_code_fuzzy,
                is_pass=is_pass,
                limit=self.page_size,
                offset=offset
            )
            
            # 连接信号
            self.query_worker.query_completed.connect(
                lambda data, total: self._on_query_completed(data, total, append_mode)
            )
            self.query_worker.query_failed.connect(self._on_query_failed)
            
            # 启动查询
            self.query_worker.start()
            
            logger.debug(f"开始查询数据，页码: {self.current_page}, 偏移: {offset}")
            return self.query_worker
            
        except Exception as e:
            logger.error(f"启动数据查询失败: {e}")
            self._reset_query_state()
            return None
    
    def start_new_query(self, **kwargs):
        """开始新的查询（重置分页）"""
        self.current_page = 0
        self.total_count = 0
        self.total_pages = 0
        return self.start_query(**kwargs)
    
    def next_page(self, **kwargs):
        """下一页"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            return self.start_query(append_mode=False, **kwargs)
        return None
    
    def prev_page(self, **kwargs):
        """上一页"""
        if self.current_page > 0:
            self.current_page -= 1
            return self.start_query(append_mode=False, **kwargs)
        return None
    
    def load_more_data(self, **kwargs):
        """加载更多数据（追加模式）"""
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            return self.start_query(append_mode=True, **kwargs)
        return None
    
    def get_pagination_info(self):
        """获取分页信息"""
        return {
            'current_page': self.current_page,
            'total_pages': self.total_pages,
            'total_count': self.total_count,
            'page_size': self.page_size,
            'has_prev': self.current_page > 0,
            'has_next': self.current_page < self.total_pages - 1
        }
    
    def is_querying(self):
        """检查是否正在查询"""
        return self._is_querying
    
    def stop_query(self):
        """停止当前查询"""
        if self.query_worker and self.query_worker.isRunning():
            self.query_worker.terminate()
            self.query_worker.wait()
        self._reset_query_state()
    
    def _on_query_completed(self, data, total_count, append_mode=False):
        """查询完成处理"""
        try:
            self.total_count = total_count
            self.total_pages = (total_count + self.page_size - 1) // self.page_size
            self._reset_query_state()
            
            logger.debug(f"查询完成，数据量: {len(data)}, 总数: {total_count}")
            
        except Exception as e:
            logger.error(f"查询完成处理失败: {e}")
            self._reset_query_state()
    
    def _on_query_failed(self, error_msg):
        """查询失败处理"""
        logger.error(f"数据查询失败: {error_msg}")
        self._reset_query_state()
    
    def _reset_query_state(self):
        """重置查询状态"""
        self._is_querying = False
    
    def cleanup(self):
        """清理资源"""
        self.stop_query()
        logger.debug("数据查询管理器清理完成")
