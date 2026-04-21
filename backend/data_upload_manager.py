"""
数据上传管理器
负责将测试结果上传到远程服务器
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from queue import Queue, Empty

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class DataUploadManager:
    """数据上传管理器"""
    
    def __init__(self, config: Optional[Dict] = None, db_manager=None):
        """
        初始化数据上传管理器

        Args:
            config: 上传配置
            db_manager: 数据库管理器（用于断点续传）
        """
        self.config = config or {}
        self.db_manager = db_manager
        self.upload_queue = Queue()
        self.upload_thread = None
        self.is_running = False
        self._upload_paused = False  # 🚀 新增：上传暂停状态

        # 新增断点续传支持
        self.enable_resumable = self.config.get('enable_resumable', True)
        self.resumable_manager = None

        # 默认配置
        self.default_config = {
            'enabled': True,
            'server_url': 'https://ukukukukukukukuk.uk',
            'endpoint': '/api/test-results',
            'timeout': 30,
            'retry_count': 3,
            'retry_delay': 1.0,
            'batch_size': 10,
            'device_id': 'JCY5001A_001',
            'software_version': 'V0.80.08',
            'auth_token': '',  # 认证令牌
            'auth_type': 'bearer',  # 认证类型: bearer, basic, api_key
            'auto_auth': True,  # 自动认证
            'username': 'admin',  # 登录用户名
            'password': 'Admin123!',  # 登录密码
            'token_refresh_threshold': 300,  # 令牌刷新阈值（秒）
            # 新增断点续传配置
            'enable_resumable': True,  # 启用断点续传
            'network_check_interval': 30,  # 网络检查间隔（秒）
            'resume_check_interval': 60,  # 续传检查间隔（秒）
            'max_concurrent_uploads': 3  # 最大并发上传数
        }
        
        # 合并配置
        self.upload_config = {**self.default_config, **self.config}

        # 修复使用统一的设备ID管理器
        from utils.device_id_manager import get_device_id
        self.device_id = get_device_id()
        # 更新配置中的设备ID
        self.upload_config['device_id'] = self.device_id

        # 认证相关属性
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None

        # 创建HTTP会话
        self.session = self._create_session()

        # 新增初始化断点续传管理器
        if self.enable_resumable and self.db_manager:
            try:
                from backend.resumable_upload_manager import ResumableUploadManager
                self.resumable_manager = ResumableUploadManager(self.upload_config, self.db_manager)
                logger.info("✅ 断点续传功能已启用")
            except Exception as e:
                logger.warning(f"⚠️ 断点续传功能初始化失败，使用标准模式: {e}")
                self.enable_resumable = False
        else:
            logger.info("断点续传功能已禁用或数据库管理器未提供")

        # 新增初始化数据库同步管理器
        self.sync_manager = None
        if self.upload_config.get('enable_database_sync', True) and self.db_manager:
            try:
                from backend.database_sync_manager import DatabaseSyncManager
                sync_config = {
                    'enabled': True,
                    'server_url': self.upload_config['server_url'],
                    'timeout': self.upload_config['timeout'],
                    'retry_count': self.upload_config['retry_count'],
                    'retry_delay': self.upload_config['retry_delay'],
                    'batch_size': self.upload_config['batch_size'],
                    'sync_interval': self.upload_config.get('sync_interval', 300),  # 5分钟
                    'auto_auth': self.upload_config['auto_auth'],
                    'username': self.upload_config['username'],
                    'password': self.upload_config['password'],
                }
                self.sync_manager = DatabaseSyncManager(sync_config, self.db_manager)
                logger.info("✅ 数据库同步功能已启用")
            except Exception as e:
                logger.warning(f"⚠️ 数据库同步功能初始化失败: {e}")
                self.sync_manager = None
        else:
            logger.info("数据库同步功能已禁用或数据库管理器未提供")

        # 🚀 性能优化：延迟启动上传线程，避免初始化时的网络阻塞
        # 不在构造函数中立即启动，改为在需要时启动
        logger.info("数据上传管理器初始化完成，上传线程将在需要时启动")

        # 🚀 性能优化：延迟启动数据库同步服务
        if self.sync_manager:
            logger.info("数据库同步服务将在需要时启动")

        # 心跳管理器引用（用于联动控制）
        self.heartbeat_manager = None

    def set_heartbeat_manager(self, heartbeat_manager):
        """设置心跳管理器引用（用于联动控制）"""
        self.heartbeat_manager = heartbeat_manager
        logger.debug("心跳管理器引用已设置，启用联动控制")

    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        
        # 修复减少重试次数和延迟，避免退出卡顿
        retry_strategy = Retry(
            total=min(self.upload_config['retry_count'], 1),  # 最多1次重试
            backoff_factor=0.1,  # 减少重试延迟
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f"JCY5001A/{self.upload_config['software_version']}"
        }

        # 添加认证头
        auth_token = self.upload_config.get('auth_token', '')
        auth_type = self.upload_config.get('auth_type', 'bearer')

        if auth_token:
            if auth_type.lower() == 'bearer':
                headers['Authorization'] = f'Bearer {auth_token}'
            elif auth_type.lower() == 'api_key':
                headers['X-API-Key'] = auth_token
            elif auth_type.lower() == 'basic':
                headers['Authorization'] = f'Basic {auth_token}'

        session.headers.update(headers)
        
        return session

    def _get_hardware_fingerprint(self) -> str:
        """
        获取硬件指纹作为设备ID（已弃用，使用统一的设备ID管理器）

        Returns:
            硬件指纹字符串
        """
        # 修复使用统一的设备ID管理器
        from utils.device_id_manager import get_device_id
        return get_device_id()

    def _authenticate(self) -> bool:
        """自动认证获取令牌"""
        if not self.upload_config.get('auto_auth', False):
            logger.debug("自动认证已禁用")
            return True

        try:
            username = self.upload_config.get('username')
            password = self.upload_config.get('password')

            if not username or not password:
                logger.warning("未配置用户名或密码，无法自动认证")
                return False

            login_url = f"{self.upload_config['server_url']}/api/auth/login"
            login_data = {
                'username': username,
                'password': password
            }

            # 修复：如果数据上传功能被禁用，完全跳过网络请求
            if not self.upload_config.get('enabled', False):
                logger.debug("数据上传功能已禁用，跳过认证和网络请求")
                return False

            # 🚀 性能优化：快速检查服务器可用性
            try:
                health_url = f"{self.upload_config['server_url']}/health"
                health_response = self.session.get(health_url, timeout=1)
                if health_response.status_code != 200:
                    logger.debug("服务器健康检查失败，跳过认证")
                    return False
            except:
                logger.debug("服务器不可用，跳过认证")
                return False

            logger.info(f"正在进行自动认证: {username}")

            # 🚀 性能优化：使用更短的超时时间
            auth_timeout = min(self.upload_config.get('timeout', 10), 3)  # 最多3秒
            response = self.session.post(
                login_url,
                json=login_data,
                timeout=auth_timeout
            )

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                self.refresh_token = result.get('refresh_token')

                # 计算令牌过期时间（提前5分钟刷新）
                from datetime import datetime, timedelta
                self.token_expires_at = datetime.now() + timedelta(hours=2) - timedelta(minutes=5)

                # 更新会话头部
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })

                logger.info("自动认证成功")
                return True
            else:
                logger.error(f"自动认证失败: HTTP {response.status_code}, {response.text}")
                return False

        except Exception as e:
            # 减少重复的网络错误日志
            if not hasattr(self, '_auth_error_logged'):
                self._auth_error_logged = True
                logger.error(f"自动认证异常: {e}")
            else:
                logger.debug(f"自动认证异常: {e}")
            return False

    def _refresh_token_if_needed(self) -> bool:
        """如果需要则刷新令牌"""
        if not self.refresh_token or not self.token_expires_at:
            return self._authenticate()

        from datetime import datetime
        if datetime.now() >= self.token_expires_at:
            try:
                refresh_url = f"{self.upload_config['server_url']}/api/auth/refresh"

                # 临时使用refresh token
                temp_headers = {'Authorization': f'Bearer {self.refresh_token}'}

                response = self.session.post(
                    refresh_url,
                    headers=temp_headers,
                    timeout=self.upload_config['timeout']
                )

                if response.status_code == 200:
                    result = response.json()
                    self.access_token = result.get('access_token')

                    # 更新过期时间
                    from datetime import datetime, timedelta
                    self.token_expires_at = datetime.now() + timedelta(hours=2) - timedelta(minutes=5)

                    # 更新会话头部
                    self.session.headers.update({
                        'Authorization': f'Bearer {self.access_token}'
                    })

                    logger.info("令牌刷新成功")
                    return True
                else:
                    logger.warning("令牌刷新失败，尝试重新认证")
                    return self._authenticate()

            except Exception as e:
                logger.error(f"令牌刷新异常: {e}")
                return self._authenticate()

        return True

    def start_upload_thread(self):
        """启动上传线程"""
        if not self.is_running:
            self.is_running = True

            # 新增启动断点续传管理器
            if self.enable_resumable and self.resumable_manager:
                self.resumable_manager.start()

            self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
            self.upload_thread.start()
            logger.info("数据上传线程已启动")
        else:
            logger.debug("上传线程已在运行中")

    def start_services_delayed(self):
        """🚀 延迟启动服务（用于性能优化）"""
        try:
            # 启动上传线程
            if self.upload_config['enabled']:
                self.start_upload_thread()

                # 联动启动心跳服务
                if self.heartbeat_manager:
                    logger.info("数据上传已启用，联动启动心跳服务")
                    self.heartbeat_manager.start()

            # 启动数据库同步服务
            if self.sync_manager:
                self.sync_manager.start_sync_service()

            logger.info("✅ 数据上传服务延迟启动完成")

        except Exception as e:
            logger.error(f"延迟启动数据上传服务失败: {e}")

    def ensure_upload_thread_running(self):
        """确保上传线程正在运行"""
        try:
            is_running_status = self.is_running
            thread_exists = self.upload_thread is not None
            thread_alive = self.upload_thread and self.upload_thread.is_alive()

            logger.debug(f"线程状态检查: is_running={is_running_status}, thread_exists={thread_exists}, thread_alive={thread_alive}")

            # 检查线程状态
            if not self.is_running or not self.upload_thread or not self.upload_thread.is_alive():
                logger.warning(f"检测到上传线程未运行，正在重新启动... (is_running={is_running_status}, thread_exists={thread_exists}, thread_alive={thread_alive})")

                # 先停止现有线程（如果存在）
                if self.is_running:
                    logger.debug("停止现有线程...")
                    self.is_running = False
                    if self.upload_thread and self.upload_thread.is_alive():
                        logger.debug("等待现有线程结束...")
                        self.upload_thread.join(timeout=2)
                        logger.debug("现有线程已结束")

                # 重新启动线程
                logger.debug("重新启动上传线程...")
                self.start_upload_thread()
                logger.info("✅ 上传线程已重新启动")
                return True
            else:
                logger.debug("上传线程运行正常")
                return True

        except Exception as e:
            logger.error(f"检查上传线程状态失败: {e}")
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")
            return False

    def _force_check_upload_thread(self):
        """强制检查并重启上传线程"""
        try:
            logger.debug(f" [FORCE_CHECK] 开始强制检查上传线程状态")

            # 详细状态检查
            is_running_status = self.is_running
            thread_exists = self.upload_thread is not None
            thread_alive = self.upload_thread and self.upload_thread.is_alive()

            logger.debug(f" [FORCE_CHECK] 当前状态: is_running={is_running_status}, thread_exists={thread_exists}, thread_alive={thread_alive}")

            # 如果线程不正常，强制重启
            if not is_running_status or not thread_exists or not thread_alive:
                logger.warning(f"🔧 [FORCE_CHECK] 检测到线程异常，强制重启: is_running={is_running_status}, thread_exists={thread_exists}, thread_alive={thread_alive}")

                # 强制停止现有线程
                if self.is_running:
                    logger.debug(f" [FORCE_CHECK] 停止现有线程...")
                    self.is_running = False
                    if self.upload_thread and self.upload_thread.is_alive():
                        logger.debug(f" [FORCE_CHECK] 等待现有线程结束...")
                        self.upload_thread.join(timeout=3)
                        if self.upload_thread.is_alive():
                            logger.warning("🔧 [FORCE_CHECK] 线程未能在3秒内结束")
                        else:
                            logger.debug(f" [FORCE_CHECK] 现有线程已结束")

                # 强制重新启动
                logger.debug(f" [FORCE_CHECK] 强制重新启动上传线程...")
                self.is_running = True

                # 启动断点续传管理器（如果需要）
                if self.enable_resumable and self.resumable_manager:
                    self.resumable_manager.start()

                # 创建新线程
                self.upload_thread = threading.Thread(target=self._upload_worker, daemon=True)
                self.upload_thread.start()

                logger.debug(f" [FORCE_CHECK] ✅ 上传线程强制重启完成")
                return True
            else:
                logger.debug(f" [FORCE_CHECK] 上传线程状态正常")
                return True

        except Exception as e:
            logger.error(f"🔧 [FORCE_CHECK] 强制检查失败: {e}")
            import traceback
            logger.error(f"🔧 [FORCE_CHECK] 异常详情: {traceback.format_exc()}")
            return False

    def stop_upload_thread(self):
        """停止上传线程"""
        logger.info("正在停止数据上传线程...")
        self.is_running = False

        # 联动停止心跳服务
        if self.heartbeat_manager:
            logger.info("数据上传已停止，联动停止心跳服务")
            self.heartbeat_manager.stop()

        # 新增停止断点续传管理器
        if self.enable_resumable and self.resumable_manager:
            self.resumable_manager.stop()

        # 新增停止数据库同步服务
        if self.sync_manager:
            self.sync_manager.stop_sync_service()

        # 修复关闭HTTP会话，中断所有网络请求
        try:
            if hasattr(self, 'session') and self.session:
                self.session.close()
                logger.debug("数据上传HTTP会话已关闭")
        except:
            pass

        # 修复减少线程等待时间，避免退出卡顿
        if self.upload_thread and self.upload_thread.is_alive():
            self.upload_thread.join(timeout=2)  # 从5秒减少到2秒
            if self.upload_thread.is_alive():
                logger.warning("数据上传线程未能在2秒内停止")
            else:
                logger.info("数据上传线程已停止")

    def stop(self):
        """停止数据上传管理器（别名方法）"""
        self.stop_upload_thread()

    # 新增数据库同步相关方法

    def trigger_manual_sync(self, sync_type: str = 'incremental') -> Dict[str, Any]:
        """
        触发手动数据同步

        Args:
            sync_type: 同步类型 ('incremental' 或 'full')

        Returns:
            同步结果字典
        """
        if not self.sync_manager:
            return {'success': False, 'message': '数据库同步功能未启用'}

        try:
            return self.sync_manager.manual_sync(sync_type)
        except Exception as e:
            logger.error(f"触发手动同步失败: {e}")
            return {'success': False, 'message': f'触发同步失败: {e}'}

    def get_sync_status(self) -> Dict[str, Any]:
        """
        获取数据同步状态

        Returns:
            同步状态字典
        """
        if not self.sync_manager:
            return {
                'enabled': False,
                'message': '数据库同步功能未启用'
            }

        try:
            return self.sync_manager.get_sync_status()
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            return {
                'enabled': False,
                'error': str(e)
            }

    def sync_specific_test_results(self, test_result_ids: List[int]) -> Dict[str, Any]:
        """
        同步指定的测试结果

        Args:
            test_result_ids: 测试结果ID列表

        Returns:
            同步结果字典
        """
        if not self.sync_manager:
            return {'success': False, 'message': '数据库同步功能未启用'}

        try:
            return self.sync_manager.sync_specific_test_results(test_result_ids)
        except Exception as e:
            logger.error(f"同步指定测试结果失败: {e}")
            return {'success': False, 'message': f'同步失败: {e}'}

    def is_sync_enabled(self) -> bool:
        """
        检查数据同步功能是否启用

        Returns:
            是否启用数据同步
        """
        return self.sync_manager is not None and self.sync_manager.sync_config.get('enabled', False)
    
    def _upload_worker(self):
        """上传工作线程"""
        logger.info("数据上传工作线程开始运行")

        # 新增添加心跳计数器，确保线程持续运行
        heartbeat_counter = 0

        while self.is_running:
            try:
                # 从队列获取上传任务
                upload_data = self.upload_queue.get(timeout=1.0)

                if upload_data is None:  # 停止信号
                    logger.info("收到停止信号，上传线程即将退出")
                    break

                # 新增重置心跳计数器
                heartbeat_counter = 0

                # 🚀 性能优化：检查是否暂停上传
                if self._upload_paused:
                    logger.debug("上传已暂停，跳过本次上传任务")
                    self.upload_queue.task_done()
                    continue

                # 执行上传
                logger.debug(f"开始处理上传任务: 通道{upload_data.get('channel_number', 'N/A')}")
                self._perform_upload(upload_data)

                # 标记任务完成
                self.upload_queue.task_done()
                logger.debug("上传任务处理完成")

            except Empty:
                # 优化队列为空时的处理逻辑
                heartbeat_counter += 1
                if heartbeat_counter % 60 == 0:  # 每60秒输出一次心跳日志
                    logger.debug(f"上传线程运行中，等待队列数据... (心跳: {heartbeat_counter})")
                continue
            except Exception as e:
                logger.error(f"上传工作线程异常: {e}")
                # 新增异常时不退出，继续运行
                import traceback
                logger.error(f"异常详情: {traceback.format_exc()}")
                continue

        logger.info("数据上传工作线程已退出")
    
    def _perform_upload(self, upload_data: Dict):
        """执行数据上传"""
        try:
            # 检查上传数据是否有效
            if upload_data is None:
                logger.error("上传数据无效，跳过上传")
                return

            # 检查并刷新令牌
            if not self._refresh_token_if_needed():
                # 减少重复的认证失败日志
                if not hasattr(self, '_upload_auth_error_logged'):
                    self._upload_auth_error_logged = True
                    logger.error("认证失败，无法上传数据")
                else:
                    logger.debug("认证失败，无法上传数据")
                return

            # 性能优化在上传线程中处理批次ID
            if 'temp_batch_id' in upload_data:
                # 确保测试批次存在
                batch_info = upload_data.get('batch_info')
                batch_id = self._ensure_batch_exists(batch_info)
                if not batch_id:
                    logger.error("无法获取或创建测试批次，跳过上传")
                    return

                # 替换临时批次ID为真实批次ID
                upload_data['batch_id'] = batch_id
                # 清理临时字段
                upload_data.pop('temp_batch_id', None)
                upload_data.pop('batch_info', None)

            # 修复检查阻抗明细数据但不分离，确保一次性上传完整数据
            frequency_data = upload_data.get('frequency_data', [])

            logger.debug(f" [上传修复] 阻抗明细数据检查: 数据点数={len(frequency_data)}")
            if frequency_data:
                logger.debug(f" [上传修复] 阻抗明细数据示例: {frequency_data[0] if frequency_data else 'None'}")
                logger.info("✅ [上传修复] 测试结果将包含完整的阻抗明细数据一次性上传")
            else:
                logger.warning("⚠️ [上传修复] 没有找到阻抗明细数据 (frequency_data)")

            upload_type = upload_data.get('upload_type', 'unknown')
            logger.debug(f" [上传修复] 上传类型: {upload_type}")

            url = f"{self.upload_config['server_url']}{self.upload_config['endpoint']}"

            logger.info(f"开始上传完整测试结果到: {url}")
            logger.debug(f"上传数据: {json.dumps(upload_data, ensure_ascii=False, indent=2)}")

            # 修复一次性发送包含阻抗数据的完整测试结果
            response = self.session.post(
                url,
                json=upload_data,
                timeout=self.upload_config['timeout']
            )

            # 检查响应状态
            if response.status_code in [200, 201]:
                logger.info(f"✅ 完整测试结果上传成功: {response.status_code}")
                if frequency_data:
                    logger.info(f"   包含阻抗明细数据: {len(frequency_data)}个频点")
                logger.debug(f"服务器响应: {response.text}")

                # 修复不再单独上传阻抗数据，因为已经包含在测试结果中

            else:
                logger.warning(f"测试结果上传失败: HTTP {response.status_code}, {response.text}")

        except requests.exceptions.Timeout:
            logger.warning(f"数据上传超时: {self.upload_config['timeout']}秒")
        except requests.exceptions.ConnectionError:
            logger.debug(f"数据上传连接失败: {self.upload_config['server_url']} (服务器未运行)")
        except requests.exceptions.RequestException as e:
            logger.warning(f"数据上传请求异常: {e}")
        except Exception as e:
            logger.error(f"数据上传未知异常: {e}")

    def _upload_impedance_details(self, result_id: int, frequency_data: List[Dict]):
        """
        上传阻抗详情数据

        Args:
            result_id: 测试结果ID
            frequency_data: 频率数据列表
        """
        try:
            if not frequency_data:
                logger.debug("没有阻抗频谱数据需要上传")
                return

            # 格式化阻抗数据（优化：减少精度以减小数据量）
            impedance_data_list = []
            measurement_time = datetime.now().isoformat()  # 统一时间戳

            for freq_point in frequency_data:
                impedance_data = {
                    'frequency': round(freq_point.get('frequency', 0), 3),  # 3位小数
                    'z_real': round(freq_point.get('impedance_real', 0), 3),  # 3位小数
                    'z_imag': round(freq_point.get('impedance_imag', 0), 3),  # 3位小数
                    'z_magnitude': round(freq_point.get('impedance_magnitude', 0), 3),  # 3位小数
                    'phase_angle': round(freq_point.get('impedance_phase', 0), 2),  # 2位小数
                    'measurement_time': measurement_time  # 复用时间戳
                }
                impedance_data_list.append(impedance_data)

            # 上传阻抗详情
            impedance_url = f"{self.upload_config['server_url']}/api/test-results/{result_id}/impedance"

            payload = {
                'impedance_data': impedance_data_list
            }

            # 计算数据大小用于日志
            import json
            payload_size = len(json.dumps(payload, ensure_ascii=False))

            logger.info(f"开始上传阻抗详情数据到: {impedance_url}")
            logger.info(f"阻抗数据: {len(impedance_data_list)}个频点, 数据大小: {payload_size/1024:.1f}KB")

            # 设置压缩请求头
            headers = {
                'Content-Type': 'application/json',
                'Accept-Encoding': 'gzip, deflate'
            }

            response = self.session.post(
                impedance_url,
                json=payload,
                headers=headers,
                timeout=self.upload_config['timeout']
            )

            if response.status_code in [200, 201]:
                logger.info(f"阻抗详情上传成功: {len(impedance_data_list)}个频点")
                logger.debug(f"服务器响应: {response.text}")
            else:
                logger.warning(f"阻抗详情上传失败: HTTP {response.status_code}, {response.text}")
                # 记录失败的数据大小，用于分析
                logger.warning(f"失败的数据大小: {payload_size/1024:.1f}KB")

        except Exception as e:
            logger.error(f"上传阻抗详情失败: {e}")

    def upload_test_result(self, test_result: Dict, batch_info: Optional[Dict] = None):
        """
        上传单个测试结果

        Args:
            test_result: 测试结果数据
            batch_info: 批次信息
        """
        if not self.upload_config['enabled']:
            logger.debug("数据上传功能已禁用")
            return

        try:
            logger.debug(f" [UPLOAD_DEBUG] 断点续传状态: enable_resumable={self.enable_resumable}, resumable_manager={self.resumable_manager is not None}")

            # 新增优先使用断点续传管理器
            if self.enable_resumable and self.resumable_manager:
                logger.debug(f" [UPLOAD_DEBUG] 使用断点续传管理器上传数据")
                self.resumable_manager.upload_test_result(test_result, batch_info)
                return

            logger.debug(f" [UPLOAD_DEBUG] 使用标准上传队列模式")

            # 强制检查确保上传线程正在运行
            thread_status = self._force_check_upload_thread()
            logger.debug(f" [UPLOAD_DEBUG] 线程检查结果: {thread_status}")

            if not thread_status:
                logger.error("🔧 [UPLOAD_DEBUG] 无法启动上传线程，跳过数据上传")
                return

            # 降级到标准上传模式
            # 格式化上传数据
            upload_data = self._format_single_result(test_result, batch_info)

            # 添加到上传队列
            self.upload_queue.put(upload_data)
            logger.info(f"✅ 测试结果已添加到上传队列: 通道{test_result.get('channel_number', 'N/A')}")

            # 强制日志检查队列状态
            queue_size = self.upload_queue.qsize()
            thread_alive = self.upload_thread and self.upload_thread.is_alive()
            logger.debug(f" [UPLOAD_DEBUG] 上传队列状态: 队列大小={queue_size}, 线程运行={thread_alive}")

        except Exception as e:
            logger.error(f"准备上传数据失败: {e}")
            import traceback
            logger.error(f"异常详情: {traceback.format_exc()}")
    
    def upload_batch_results(self, test_results: List[Dict], batch_info: Optional[Dict] = None):
        """
        批量上传测试结果

        Args:
            test_results: 测试结果列表
            batch_info: 批次信息
        """
        if not self.upload_config['enabled']:
            logger.debug("数据上传功能已禁用")
            return

        try:
            # 新增优先使用断点续传管理器
            if self.enable_resumable and self.resumable_manager:
                self.resumable_manager.upload_batch_results(test_results, batch_info)
                return

            # 降级到标准上传模式
            # 格式化上传数据
            upload_data = self._format_batch_results(test_results, batch_info)

            # 添加到上传队列
            self.upload_queue.put(upload_data)
            logger.info(f"批量测试结果已添加到上传队列: {len(test_results)}个结果")

        except Exception as e:
            logger.error(f"准备批量上传数据失败: {e}")
    
    def _ensure_batch_exists(self, batch_info: Optional[Dict] = None) -> Optional[int]:
        """确保测试批次存在，如果不存在则创建"""
        try:
            # 检查并刷新认证令牌
            if not self._refresh_token_if_needed():
                logger.error("认证失败，无法确保批次存在")
                return None

            # 生成批次ID（限制长度在3-50字符之间）
            device_short_id = self.upload_config['device_id'][:8]  # 只取前8位
            date_str = datetime.now().strftime('%Y%m%d')
            batch_id_str = f"{device_short_id}_{date_str}"

            if batch_info and batch_info.get('batch_number'):
                # 确保用户提供的批次号也符合长度限制
                user_batch = batch_info['batch_number']
                if len(user_batch) > 50:
                    user_batch = user_batch[:50]
                batch_id_str = user_batch

            # 首先尝试获取现有批次
            batch_url = f"{self.upload_config['server_url']}/api/test-batches"
            response = self.session.get(batch_url, timeout=self.upload_config['timeout'])

            if response.status_code == 200:
                batches = response.json().get('batches', [])
                for batch in batches:
                    if batch.get('batch_id') == batch_id_str:
                        logger.info(f"找到现有测试批次: {batch['id']}")
                        return batch['id']

            # 如果批次不存在，创建新批次
            logger.info(f"创建新测试批次: {batch_id_str}")

            # 首先确保设备存在
            device_id = self._ensure_device_exists()
            if not device_id:
                logger.error("无法创建或获取设备ID")
                return None

            batch_data = {
                'batch_id': batch_id_str,
                'device_id': device_id,
                'start_time': datetime.now().isoformat(),
                'notes': f"自动创建的测试批次 - {batch_info.get('test_mode', '未知模式') if batch_info else '自动模式'}"
            }

            response = self.session.post(
                batch_url,
                json=batch_data,
                timeout=self.upload_config['timeout']
            )

            if response.status_code == 201:
                result = response.json()
                batch_id = result.get('batch', {}).get('id')
                logger.info(f"测试批次创建成功: {batch_id}")
                return batch_id
            else:
                logger.error(f"创建测试批次失败: HTTP {response.status_code}, {response.text}")
                return None

        except Exception as e:
            logger.error(f"确保测试批次存在时发生错误: {e}")
            return None

    def _ensure_device_exists(self) -> Optional[int]:
        """确保设备存在，如果不存在则创建"""
        try:
            # 检查并刷新认证令牌
            if not self._refresh_token_if_needed():
                logger.error("认证失败，无法确保设备存在")
                return None

            device_id_str = self.upload_config['device_id']

            # 首先尝试获取现有设备
            devices_url = f"{self.upload_config['server_url']}/api/devices"
            response = self.session.get(devices_url, timeout=self.upload_config['timeout'])

            if response.status_code == 200:
                devices = response.json().get('devices', [])
                for device in devices:
                    if device.get('device_id') == device_id_str:
                        logger.info(f"找到现有设备: {device['id']}")
                        return device['id']

            # 如果设备不存在，创建新设备
            logger.info(f"创建新设备: {device_id_str}")

            device_data = {
                'device_id': device_id_str,
                'name': f"JCY5001A设备 - {device_id_str}",
                'model': 'JCY5001A',
                'location': '自动注册',
                'description': f"自动创建的设备 - 软件版本: {self.upload_config.get('software_version', 'Unknown')}"
            }

            response = self.session.post(
                devices_url,
                json=device_data,
                timeout=self.upload_config['timeout']
            )

            if response.status_code == 201:
                result = response.json()
                device_id = result.get('device', {}).get('id')
                logger.info(f"设备创建成功: {device_id}")
                return device_id
            else:
                logger.error(f"创建设备失败: HTTP {response.status_code}, {response.text}")
                return None

        except Exception as e:
            logger.error(f"确保设备存在时发生错误: {e}")
            return None

    def _format_single_result(self, test_result: Dict, batch_info: Optional[Dict] = None) -> Dict:
        """格式化单个测试结果为服务器API格式（快速版本，不进行网络请求）"""
        # 获取批次信息（使用桌面软件中的批次）
        batch_number = None
        if batch_info and batch_info.get('batch_number'):
            batch_number = batch_info['batch_number']
        else:
            # 使用桌面软件中的批次信息（限制长度）
            device_short = self.device_id[:8]  # 只取前8位
            date_str = datetime.now().strftime('%Y%m%d')
            batch_number = test_result.get('batch_number') or f"B_{device_short}_{date_str}"

        # 生成测试ID（参考桌面软件格式：TEST_batch_id_sequence）
        import uuid
        sequence = uuid.uuid4().hex[:6].upper()  # 6位序列号
        test_id = f"TEST_{batch_number}_{sequence}"

        temp_batch_id = batch_number

        # 处理时间戳格式化
        timestamp = test_result.get('timestamp', datetime.now())
        if isinstance(timestamp, str):
            # 如果是字符串，尝试解析为datetime对象
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                timestamp = datetime.now()
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now()

        # 格式化为服务器API期望的格式（参考桌面软件数据库结构）
        formatted_result = {
            'test_id': test_id,
            'temp_batch_id': temp_batch_id,  # 临时批次ID，在上传线程中解析
            'batch_info': batch_info,  # 保存批次信息，供上传线程使用
            'test_time': timestamp.isoformat(),
            'device_id_str': self.device_id,  # 修复使用硬件指纹作为设备ID字符串

            # 基本测试信息
            'channel_number': test_result.get('channel_number'),
            'battery_code': test_result.get('battery_code', ''),  # 修复使用正确的字段名
            'voltage': test_result.get('voltage'),
            'test_result': 'pass' if test_result.get('is_pass', False) else 'fail',
            'error_code': test_result.get('fail_reason', ''),

            # 阻抗测试结果（参考桌面软件数据库字段）
            'rs_value': test_result.get('rs_value'),
            'rct_value': test_result.get('rct_value'),
            'rsei_value': test_result.get('rsei_value'),  # SEI膜电阻
            'w_impedance': test_result.get('w_impedance'),  # Warburg阻抗
            'rs_grade': test_result.get('rs_grade'),  # Rs等级
            'rct_grade': test_result.get('rct_grade'),  # Rct等级

            # 测试详情
            'test_start_time': test_result.get('test_start_time'),
            'test_end_time': test_result.get('test_end_time'),
            'test_duration': test_result.get('test_duration'),
            'test_mode': test_result.get('test_mode'),
            'frequency_list': test_result.get('frequency_list', []),
            'raw_data': test_result.get('raw_data', {}),  # 原始数据

            # 批次和操作信息
            'batch_number': batch_number,
            'operator': test_result.get('operator'),
            'battery_type': test_result.get('battery_type'),
            'battery_spec': test_result.get('battery_spec'),

            # 新增完整的电池信息
            'standard_voltage': test_result.get('standard_voltage'),
            'standard_capacity': test_result.get('standard_capacity'),
            'nominal_voltage': test_result.get('nominal_voltage'),
            'manufacturer': test_result.get('manufacturer'),
            'production_date': test_result.get('production_date'),

            # 分析结果
            'outlier_result': test_result.get('outlier_result'),
            'baseline_filename': test_result.get('baseline_filename'),
            'baseline_id': test_result.get('baseline_id'),
            'max_deviation_percent': test_result.get('max_deviation_percent'),
            'frequency_deviations': test_result.get('frequency_deviations'),

            # 扩展分析数据
            'rct_coefficient_of_variation': test_result.get('rct_coefficient_of_variation'),
            'capacity_prediction': test_result.get('capacity_prediction'),
            'voltage_range_min': test_result.get('voltage_range_min'),
            'voltage_range_max': test_result.get('voltage_range_max'),
            'rs_range_min': test_result.get('rs_range_min'),
            'rs_range_max': test_result.get('rs_range_max'),
            'rct_range_min': test_result.get('rct_range_min'),
            'rct_range_max': test_result.get('rct_range_max'),

            # Warburg扩散相关
            'warburg_coefficient': test_result.get('warburg_coefficient'),
            'warburg_01hz': test_result.get('warburg_01hz'),
            'warburg_001hz': test_result.get('warburg_001hz'),
            'has_warburg_diffusion': test_result.get('has_warburg_diffusion'),

            # SEI膜相关
            'has_sei': test_result.get('has_sei'),
            'sei_confidence': test_result.get('sei_confidence'),
            'double_layer_capacitance': test_result.get('double_layer_capacitance'),
            'sei_capacitance': test_result.get('sei_capacitance'),
            'total_capacitance': test_result.get('total_capacitance'),

            # 其他测试参数
            'capacity': test_result.get('capacity'),
            'temperature': test_result.get('temperature', 25.0),
            'thickness': test_result.get('thickness'),

            # EIS分析结果
            'w_impedance': test_result.get('w_impedance'),  # Warburg阻抗
            'rs_grade': test_result.get('rs_grade'),
            'rct_grade': test_result.get('rct_grade'),

            # 离群检测结果
            'outlier_result': test_result.get('outlier_result'),
            'baseline_filename': test_result.get('baseline_filename'),
            'baseline_id': test_result.get('baseline_id'),
            'max_deviation_percent': test_result.get('max_deviation_percent'),
            'frequency_deviations': test_result.get('frequency_deviations', {}),

            # 容量预测和变异系数
            'capacity_prediction': test_result.get('capacity_prediction'),
            'rct_coefficient_of_variation': test_result.get('rct_coefficient_of_variation'),

            # 修复增强版EIS分析结果
            'rsei_value': test_result.get('rsei_value', 0.0),  # SEI膜电阻
            'impedance_ratio': test_result.get('impedance_ratio', 0.0),
            'warburg_coefficient': test_result.get('warburg_coefficient', 0.0),
            'double_layer_capacitance': test_result.get('double_layer_capacitance', 0.0),
            'sei_capacitance': test_result.get('sei_capacitance', 0.0),
            'health_status': test_result.get('health_status', ''),
            'health_score': test_result.get('health_score', 0.0),

            # 修复添加阻抗明细数据
            'frequency_data': test_result.get('frequency_data', [])
        }

        return formatted_result
    
    def _format_batch_results(self, test_results: List[Dict], batch_info: Optional[Dict] = None) -> Dict:
        """格式化批量测试结果"""
        return {
            'upload_type': 'batch_results',
            'device_info': {
                'device_id': self.device_id,  # 使用硬件指纹
                'software_version': self.upload_config['software_version'],
                'upload_time': datetime.now().isoformat()
            },
            'batch_info': batch_info or {},
            'test_results': [self._clean_test_result(result) for result in test_results],
            'result_count': len(test_results)
        }
    
    def _clean_test_result(self, test_result: Dict) -> Dict:
        """清理测试结果数据，移除不需要上传的字段"""
        # 需要上传的字段
        upload_fields = [
            'test_id', 'channel_number', 'battery_code', 'voltage', 'rs_value', 'rct_value',
            'rs_grade', 'rct_grade', 'is_pass', 'fail_reason', 'test_start_time',
            'test_end_time', 'test_duration', 'test_mode', 'frequency_list',
            'operator', 'battery_type', 'battery_spec', 'batch_number',
            'outlier_result', 'max_deviation_percent', 'rsei_value', 'w_impedance'
        ]

        cleaned_result = {}
        for field in upload_fields:
            if field in test_result:
                value = test_result[field]
                # 转换datetime对象为字符串
                if hasattr(value, 'isoformat'):
                    value = value.isoformat()
                cleaned_result[field] = value

        # 如果没有test_id，生成一个
        if 'test_id' not in cleaned_result:
            import uuid
            sequence = uuid.uuid4().hex[:6].upper()
            batch_number = test_result.get('batch_number', 'UNKNOWN')
            cleaned_result['test_id'] = f"TEST_{batch_number}_{sequence}"

        return cleaned_result
    
    def get_upload_status(self) -> Dict:
        """获取上传状态"""
        status = {
            'enabled': self.upload_config['enabled'],
            'server_url': self.upload_config['server_url'],
            'queue_size': self.upload_queue.qsize(),
            'thread_running': self.is_running and self.upload_thread and self.upload_thread.is_alive(),
            'resumable_enabled': self.enable_resumable
        }

        # 新增包含断点续传状态
        if self.enable_resumable and self.resumable_manager:
            resumable_status = self.resumable_manager.get_upload_status()
            status['resumable_status'] = resumable_status

        return status
    
    def update_config(self, new_config: Dict):
        """更新配置"""
        self.upload_config.update(new_config)
        logger.info(f"数据上传配置已更新: {new_config}")
    
    def test_connection(self) -> bool:
        """测试服务器连接"""
        try:
            # 修复：如果数据上传功能被禁用，直接返回False，不进行网络请求
            if not self.upload_config.get('enabled', False):
                logger.debug("数据上传功能已禁用，跳过连接测试")
                return False

            # 首先测试基本连接
            health_url = f"{self.upload_config['server_url']}/health"
            response = self.session.get(health_url, timeout=5)

            if response.status_code != 200:
                return False

            # 如果启用了自动认证，测试认证功能
            if self.upload_config.get('auto_auth', False):
                return self._authenticate()

            return True
        except:
            return False

    def pause_upload_thread(self):
        """🚀 暂停上传线程（用于设置页面性能优化）"""
        try:
            self._upload_paused = True
            logger.info("数据上传线程已暂停")
        except Exception as e:
            logger.error(f"暂停上传线程失败: {e}")

    def resume_upload_thread(self):
        """🚀 恢复上传线程（用于设置页面性能优化）"""
        try:
            self._upload_paused = False
            logger.info("数据上传线程已恢复")
        except Exception as e:
            logger.error(f"恢复上传线程失败: {e}")

    def is_upload_paused(self) -> bool:
        """🚀 检查上传是否暂停"""
        return self._upload_paused

    def __del__(self):
        """析构函数"""
        self.stop_upload_thread()
