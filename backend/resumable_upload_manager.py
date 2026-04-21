# -*- coding: utf-8 -*-
"""
支持断点续传的数据上传管理器
在网络中断后能够继续传输未完成的数据

Author: Jack
Date: 2025-07-07
"""

import logging
import json
import uuid
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from queue import Queue, Empty

from backend.network_monitor import SimpleNetworkMonitor
from backend.data_upload_manager import DataUploadManager

logger = logging.getLogger(__name__)


class ResumableUploadManager:
    """
    支持断点续传的数据上传管理器
    
    功能：
    - 持久化上传队列
    - 网络中断检测
    - 自动断点续传
    - 数据完整性保证
    """
    
    def __init__(self, config: Optional[Dict] = None, db_manager=None):
        """
        初始化断点续传上传管理器
        
        Args:
            config: 上传配置
            db_manager: 数据库管理器
        """
        self.config = config or {}
        self.db_manager = db_manager
        
        # 基础上传管理器（禁用断点续传避免循环依赖）
        base_config = config.copy()
        base_config['enable_resumable'] = False  # 避免循环依赖
        self.base_upload_manager = DataUploadManager(base_config, db_manager)
        
        # 网络监控器
        self.network_monitor = SimpleNetworkMonitor(
            server_url=self.config.get('server_url', 'http://localhost:5002'),
            check_interval=self.config.get('network_check_interval', 30)
        )
        
        # 上传控制
        self.is_running = False
        self.upload_thread = None
        self.resume_thread = None
        
        # 配置参数
        self.max_concurrent_uploads = self.config.get('max_concurrent_uploads', 3)
        self.resume_check_interval = self.config.get('resume_check_interval', 60)  # 秒
        
        # 设置网络监控回调
        self.network_monitor.set_callbacks(
            on_recovered=self._on_network_recovered
        )
        
        logger.info("断点续传上传管理器初始化完成")
    
    def start(self):
        """启动上传管理器"""
        if self.is_running:
            logger.debug("断点续传上传管理器已在运行")
            return
        
        self.is_running = True
        
        # 启动网络监控
        self.network_monitor.start_monitoring()
        
        # 启动上传处理线程
        self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
        self.upload_thread.start()
        
        # 启动断点续传检查线程
        self.resume_thread = threading.Thread(target=self._resume_worker, daemon=True)
        self.resume_thread.start()
        
        logger.info("断点续传上传管理器已启动")
    
    def stop(self):
        """停止上传管理器"""
        if not self.is_running:
            return

        logger.info("正在停止断点续传上传管理器...")
        self.is_running = False

        # 停止网络监控
        self.network_monitor.stop_monitoring()

        # 停止基础上传管理器
        self.base_upload_manager.stop()

        # 修复等待工作线程停止，使用短超时
        for thread_name, thread in [("上传线程", self.upload_thread), ("续传线程", self.resume_thread)]:
            if thread and thread.is_alive():
                thread.join(timeout=1)  # 1秒超时
                if thread.is_alive():
                    logger.warning(f"断点续传{thread_name}未能在1秒内停止")

        logger.info("断点续传上传管理器已停止")
    
    def upload_test_result(self, test_result: Dict, batch_info: Optional[Dict] = None, priority: int = 0):
        """
        上传测试结果（支持断点续传）

        Args:
            test_result: 测试结果数据
            batch_info: 批次信息
            priority: 优先级（数字越大优先级越高）
        """
        try:
            if not self.db_manager:
                logger.error("数据库管理器未初始化，无法使用断点续传功能")
                # 降级到基础上传管理器
                self.base_upload_manager.upload_test_result(test_result, batch_info)
                return

            # 修复创建测试结果副本，避免修改原始数据
            test_result_copy = test_result.copy()

            # 生成唯一上传ID
            upload_id = self._generate_upload_id('test_result', test_result_copy)

            # 修复从副本中分离阻抗数据，保持原始数据完整
            frequency_data = test_result_copy.pop('frequency_data', [])

            # 修复确保上传的测试结果包含完整的阻抗明细数据
            if frequency_data:
                # 将阻抗数据重新添加到上传数据中，确保一次性上传完整数据
                test_result_copy['frequency_data'] = frequency_data
                logger.debug(f" 测试结果包含阻抗明细数据: {len(frequency_data)}个频点")
            else:
                logger.warning("⚠️ 测试结果不包含阻抗明细数据")

            # 格式化上传数据（包含完整的阻抗数据）
            upload_data = self.base_upload_manager._format_single_result(test_result_copy, batch_info)

            # 修复统一上传，不再分离测试结果和阻抗数据
            success = self.db_manager.add_to_upload_queue(
                upload_id=upload_id,
                data_type='test_result_with_impedance',  # 明确标识包含阻抗数据
                upload_data=upload_data,
                priority=priority
            )

            if success:
                logger.info(f"✅ 完整测试结果已添加到断点续传队列: {upload_id}")
                if frequency_data:
                    logger.info(f"   包含阻抗明细数据: {len(frequency_data)}个频点")
            else:
                logger.error(f"❌ 添加测试结果到断点续传队列失败: {upload_id}")
                # 修复降级时使用原始数据（包含阻抗数据）
                self.base_upload_manager.upload_test_result(test_result, batch_info)

        except Exception as e:
            logger.error(f"断点续传上传测试结果失败: {e}")
            # 修复降级时使用原始数据（包含阻抗数据）
            self.base_upload_manager.upload_test_result(test_result, batch_info)
    
    def upload_batch_results(self, test_results: List[Dict], batch_info: Optional[Dict] = None, priority: int = 0):
        """
        批量上传测试结果（支持断点续传）
        
        Args:
            test_results: 测试结果列表
            batch_info: 批次信息
            priority: 优先级
        """
        try:
            for i, test_result in enumerate(test_results):
                # 为批量上传中的每个结果设置递减优先级
                item_priority = priority + len(test_results) - i
                self.upload_test_result(test_result, batch_info, item_priority)
            
            logger.info(f"批量测试结果已添加到断点续传队列: {len(test_results)}个结果")
            
        except Exception as e:
            logger.error(f"断点续传批量上传失败: {e}")
            # 降级到基础上传管理器
            self.base_upload_manager.upload_batch_results(test_results, batch_info)
    
    def _upload_worker(self):
        """上传工作线程"""
        logger.debug("断点续传上传工作线程开始运行")
        
        while self.is_running:
            try:
                # 检查网络状态
                if not self.network_monitor.is_connected():
                    time.sleep(5)  # 网络未连接时等待
                    continue
                
                # 获取待上传的数据
                pending_uploads = self.db_manager.get_pending_uploads(self.max_concurrent_uploads)
                
                if not pending_uploads:
                    time.sleep(2)  # 没有待上传数据时等待
                    continue
                
                # 处理上传
                for upload_item in pending_uploads:
                    if not self.is_running:
                        break
                    
                    self._process_upload_item(upload_item)
                
            except Exception as e:
                logger.error(f"上传工作线程异常: {e}")
                time.sleep(5)
        
        logger.debug("断点续传上传工作线程已停止")
    
    def _resume_worker(self):
        """断点续传检查工作线程"""
        logger.debug("断点续传检查工作线程开始运行")
        
        while self.is_running:
            try:
                time.sleep(self.resume_check_interval)
                
                if not self.is_running:
                    break
                
                # 检查是否有失败的上传需要重试
                self._check_failed_uploads()
                
            except Exception as e:
                logger.error(f"断点续传检查线程异常: {e}")
        
        logger.debug("断点续传检查工作线程已停止")
    
    def _process_upload_item(self, upload_item: Dict):
        """
        处理单个上传项目

        Args:
            upload_item: 上传项目数据
        """
        upload_id = upload_item['upload_id']
        data_type = upload_item['data_type']
        upload_data = upload_item['upload_data']

        try:
            # 更新状态为上传中
            self.db_manager.update_upload_status(upload_id, 'uploading')

            # 修复统一处理包含阻抗数据的完整测试结果
            if data_type in ['test_result', 'test_result_with_impedance']:
                success = self._upload_test_result_data(upload_data)
            elif data_type == 'impedance_data':
                # 修复不再单独处理阻抗数据，因为已经包含在测试结果中
                logger.info(f"跳过单独的阻抗数据上传（已包含在测试结果中）: {upload_id}")
                success = True  # 直接标记为成功
            else:
                logger.error(f"未知的数据类型: {data_type}")
                success = False

            if success:
                # 上传成功
                self.db_manager.update_upload_status(upload_id, 'completed')
                logger.info(f"✅ 上传成功: {upload_id}")
            else:
                # 上传失败
                self.db_manager.update_upload_status(upload_id, 'failed', '上传失败')
                logger.warning(f"❌ 上传失败: {upload_id}")

        except Exception as e:
            # 上传异常
            error_msg = f"上传异常: {e}"
            self.db_manager.update_upload_status(upload_id, 'failed', error_msg)
            logger.error(f"处理上传项目异常: {upload_id}, {e}")
    
    def _upload_test_result_data(self, upload_data: Dict) -> bool:
        """
        上传测试结果数据
        
        Args:
            upload_data: 上传数据
            
        Returns:
            是否上传成功
        """
        try:
            # 使用基础上传管理器的上传逻辑
            self.base_upload_manager._perform_upload(upload_data)
            return True
        except Exception as e:
            logger.error(f"上传测试结果数据失败: {e}")
            return False
    
    def _upload_impedance_data(self, upload_data: Dict) -> bool:
        """
        🔧 已废弃：上传阻抗数据（现在阻抗数据已包含在测试结果中一次性上传）

        Args:
            upload_data: 上传数据

        Returns:
            是否上传成功
        """
        try:
            frequency_data = upload_data.get('frequency_data', [])

            # 修复不再单独上传阻抗数据，因为已经包含在测试结果中
            logger.debug(f" 阻抗数据已包含在测试结果中，无需单独上传: {len(frequency_data)}个频点")
            return True

        except Exception as e:
            logger.error(f"处理阻抗数据失败: {e}")
            return False
    
    def _check_failed_uploads(self):
        """检查失败的上传并重试"""
        try:
            if not self.db_manager:
                return
            
            # 获取失败的上传项目
            failed_uploads = self.db_manager.get_pending_uploads(limit=50)
            failed_count = len([item for item in failed_uploads if item['status'] == 'failed'])
            
            if failed_count > 0:
                logger.info(f"发现 {failed_count} 个失败的上传项目，准备重试")
                
        except Exception as e:
            logger.error(f"检查失败上传异常: {e}")
    
    def _on_network_recovered(self):
        """网络恢复回调"""
        logger.info("🔄 网络已恢复，开始断点续传...")
        
        try:
            # 立即检查待上传的数据
            if self.db_manager:
                pending_uploads = self.db_manager.get_pending_uploads(limit=10)
                if pending_uploads:
                    logger.info(f"发现 {len(pending_uploads)} 个待续传的数据项目")
                else:
                    logger.info("没有待续传的数据")
        except Exception as e:
            logger.error(f"网络恢复处理异常: {e}")
    
    def _generate_upload_id(self, data_type: str, data: Dict) -> str:
        """
        生成唯一上传ID
        
        Args:
            data_type: 数据类型
            data: 数据内容
            
        Returns:
            唯一上传ID
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        channel = data.get('channel_number', 'X')
        
        return f"{data_type}_{timestamp}_{channel}_{unique_id}"
    
    def get_upload_status(self) -> Dict:
        """获取上传状态"""
        status = {
            'is_running': self.is_running,
            'network_connected': self.network_monitor.is_connected(),
            'base_manager_status': self.base_upload_manager.get_upload_status()
        }
        
        if self.db_manager:
            status['queue_stats'] = self.db_manager.get_upload_queue_stats()
        
        return status
    
    def cleanup_old_records(self, days_old: int = 7) -> int:
        """
        清理旧的上传记录
        
        Args:
            days_old: 清理多少天前的记录
            
        Returns:
            清理的记录数
        """
        if self.db_manager:
            return self.db_manager.cleanup_completed_uploads(days_old)
        return 0
