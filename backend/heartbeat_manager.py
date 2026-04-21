# -*- coding: utf-8 -*-
"""
设备心跳管理器
负责向后端服务器发送设备心跳信息，监控设备在线状态

Author: Jack
Date: 2025-01-09
"""

import json
import logging
import threading
import time
import platform
import psutil
from datetime import datetime
from typing import Dict, Optional, Any, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """设备心跳管理器"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        初始化心跳管理器

        Args:
            config: 心跳配置
        """
        self.config = config or {}
        
        # 默认配置
        self.default_config = {
            'enabled': True,
            'server_url': 'https://ukukukukukukukuk.uk',
            'heartbeat_endpoint': '/api/heartbeat/',
            'heartbeat_interval': 30,  # 心跳间隔（秒）
            'timeout': 10,  # 请求超时（秒）
            'retry_count': 2,  # 重试次数
            'retry_delay': 1.0,  # 重试延迟（秒）
            'device_id': '',  # 设备ID（自动获取）
            'auto_auth': True,  # 自动认证
            'username': 'admin',  # 登录用户名
            'password': 'Admin123!',  # 登录密码
            'collect_system_info': True,  # 收集系统信息
        }
        
        # 合并配置
        self.heartbeat_config = {**self.default_config, **self.config}
        
        # 获取设备ID
        self.device_id = self._get_device_id()
        self.heartbeat_config['device_id'] = self.device_id
        
        # 心跳线程相关
        self.heartbeat_thread = None
        self.is_running = False
        self._stop_event = threading.Event()
        self._paused = False  # 🚀 新增：暂停状态
        
        # 认证相关
        self.access_token = None
        self.token_expires_at = None
        
        # 设备状态
        self.current_status = 'offline'
        self.current_task = '系统启动中'
        self.error_message = None
        
        # 状态回调
        self.status_callback: Optional[Callable[[str, Dict], None]] = None
        
        # 创建HTTP会话
        self.session = self._create_session()
        
        logger.info(f"✅ 心跳管理器初始化完成 - 设备ID: {self.device_id[:16]}...")
    
    def _get_device_id(self) -> str:
        """获取设备ID（使用统一的设备ID管理器）"""
        # 修复使用统一的设备ID管理器
        from utils.device_id_manager import get_device_id
        return get_device_id()
    
    def _get_cached_device_id(self) -> str:
        """获取缓存的设备ID"""
        try:
            import os
            cache_file = os.path.join(os.path.expanduser("~"), ".jcy5001_device_id")
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    device_id = f.read().strip()
                    if device_id:
                        return device_id
        except Exception as e:
            logger.debug(f"读取缓存设备ID失败: {e}")
        return None
    
    def _cache_device_id(self, device_id: str):
        """缓存设备ID"""
        try:
            import os
            cache_file = os.path.join(os.path.expanduser("~"), ".jcy5001_device_id")
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(device_id)
            logger.debug(f"设备ID已缓存: {device_id[:16]}...")
        except Exception as e:
            logger.debug(f"缓存设备ID失败: {e}")
    
    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        
        # 修复减少重试次数和延迟，避免退出卡顿
        retry_strategy = Retry(
            total=min(self.heartbeat_config['retry_count'], 1),  # 最多1次重试
            backoff_factor=0.1,  # 减少重试延迟
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认headers
        session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': f"JCY5001A-Heartbeat/1.0"
        })
        
        return session
    
    def _authenticate(self) -> bool:
        """自动认证获取令牌"""
        if not self.heartbeat_config.get('auto_auth', False):
            logger.debug("自动认证已禁用")
            return True

        try:
            username = self.heartbeat_config.get('username')
            password = self.heartbeat_config.get('password')

            if not username or not password:
                logger.warning("未配置用户名或密码，无法自动认证")
                return False

            login_url = f"{self.heartbeat_config['server_url']}/api/auth/login"
            login_data = {
                'username': username,
                'password': password
            }

            # 🚀 性能优化：快速检查服务器可用性
            try:
                health_url = f"{self.heartbeat_config['server_url']}/health"
                health_response = self.session.get(health_url, timeout=1)
                if health_response.status_code != 200:
                    logger.debug("心跳服务器健康检查失败，跳过认证")
                    return False
            except:
                logger.debug("心跳服务器不可用，跳过认证")
                return False

            logger.debug(f"正在进行心跳认证: {username}")

            # 🚀 性能优化：使用更短的超时时间
            auth_timeout = min(self.heartbeat_config.get('timeout', 10), 3)  # 最多3秒
            response = self.session.post(
                login_url,
                json=login_data,
                timeout=auth_timeout
            )

            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')

                # 计算令牌过期时间（提前5分钟刷新）
                from datetime import datetime, timedelta
                self.token_expires_at = datetime.now() + timedelta(hours=2) - timedelta(minutes=5)

                # 更新会话头部
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })

                logger.info("心跳认证成功")
                return True
            else:
                logger.error(f"心跳认证失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            logger.debug(f"心跳认证异常: {e}")
            return False
    
    def _refresh_token_if_needed(self) -> bool:
        """如果需要则刷新令牌"""
        if not self.access_token or not self.token_expires_at:
            return self._authenticate()

        from datetime import datetime
        if datetime.now() >= self.token_expires_at:
            logger.debug("令牌即将过期，重新认证")
            return self._authenticate()

        return True
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """收集系统信息"""
        try:
            if not self.heartbeat_config.get('collect_system_info', True):
                return {}
            
            # CPU使用率
            cpu_usage = psutil.cpu_percent(interval=0.1)
            
            # 内存使用率
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # 磁盘使用率
            disk = psutil.disk_usage('/')
            disk_usage = (disk.used / disk.total) * 100
            
            # 系统温度（如果可用）
            temperature = None
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    # 尝试获取CPU温度
                    for name, entries in temps.items():
                        if 'cpu' in name.lower() or 'core' in name.lower():
                            if entries:
                                temperature = entries[0].current
                                break
            except:
                pass
            
            return {
                'cpu_usage': round(cpu_usage, 1),
                'memory_usage': round(memory_usage, 1),
                'disk_usage': round(disk_usage, 1),
                'temperature': temperature
            }
            
        except Exception as e:
            logger.debug(f"收集系统信息失败: {e}")
            return {}
    
    def _get_ip_address(self) -> Optional[str]:
        """获取本机IP地址"""
        try:
            import socket
            # 连接到一个远程地址来获取本机IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            try:
                # 备选方案：获取所有网络接口
                import netifaces
                for interface in netifaces.interfaces():
                    addresses = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addresses:
                        for addr in addresses[netifaces.AF_INET]:
                            ip = addr['addr']
                            if not ip.startswith('127.') and not ip.startswith('169.254.'):
                                return ip
            except:
                pass
            
            return None
    
    def start(self):
        """启动心跳服务"""
        if not self.heartbeat_config['enabled']:
            logger.info("心跳功能已禁用")
            return
        
        if self.is_running:
            logger.warning("心跳服务已在运行")
            return
        
        self.is_running = True
        self._stop_event.clear()
        
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        
        logger.info(f"✅ 心跳服务已启动 - 间隔: {self.heartbeat_config['heartbeat_interval']}秒")
    
    def stop(self):
        """停止心跳服务"""
        if not self.is_running:
            return

        logger.info("正在停止心跳服务...")

        self.is_running = False
        self._stop_event.set()

        # 修复：如果心跳功能被禁用，完全跳过网络连接
        if self.heartbeat_config['enabled']:
            # 修复快速发送最后一次离线心跳，使用短超时
            try:
                # 临时减少超时时间，避免退出卡顿
                original_timeout = self.heartbeat_config['timeout']
                self.heartbeat_config['timeout'] = 1  # 1秒超时
                self.send_heartbeat(status='offline', current_task='系统关闭')
                self.heartbeat_config['timeout'] = original_timeout  # 恢复原超时
            except:
                pass
        else:
            logger.debug("心跳功能已禁用，跳过离线心跳发送")

        # 修复关闭HTTP会话，中断所有网络请求
        try:
            if hasattr(self, 'session') and self.session:
                self.session.close()
                logger.debug("心跳HTTP会话已关闭")
        except:
            pass

        # 修复减少线程等待时间，避免退出卡顿
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2)  # 从5秒减少到2秒
            if self.heartbeat_thread.is_alive():
                logger.warning("心跳工作线程未能在2秒内停止")

        logger.info("✅ 心跳服务已停止")
    
    def _heartbeat_worker(self):
        """心跳工作线程"""
        logger.info("心跳工作线程开始运行")
        
        # 首次认证
        if not self._authenticate():
            logger.error("心跳认证失败，心跳服务无法启动")
            self.is_running = False
            return
        
        # 发送首次在线心跳
        self.send_heartbeat(status='online', current_task='系统就绪')
        
        while self.is_running and not self._stop_event.is_set():
            try:
                # 等待心跳间隔
                if self._stop_event.wait(self.heartbeat_config['heartbeat_interval']):
                    break  # 收到停止信号

                # 🚀 性能优化：检查是否暂停
                if not self._paused:
                    # 发送心跳
                    self.send_heartbeat()
                else:
                    logger.debug("心跳已暂停，跳过本次发送")

            except Exception as e:
                logger.error(f"心跳工作线程异常: {e}")
                # 短暂等待后继续
                if self._stop_event.wait(5):
                    break
        
        logger.info("心跳工作线程已退出")
    
    def send_heartbeat(self, status: Optional[str] = None, current_task: Optional[str] = None, 
                      error_message: Optional[str] = None) -> bool:
        """
        发送心跳数据

        Args:
            status: 设备状态 ('online', 'offline', 'error', 'maintenance')
            current_task: 当前任务描述
            error_message: 错误信息

        Returns:
            是否发送成功
        """
        try:
            # 🚀 优先检查是否暂停，立即返回
            if self._paused:
                logger.debug("心跳已暂停，立即跳过发送")
                return False

            # 修复：检查数据上传功能是否启用，如果禁用则不发送心跳
            if hasattr(self, 'config_manager'):
                data_upload_enabled = self.config_manager.get('data_upload.enabled', False)
                if not data_upload_enabled:
                    logger.debug("数据上传功能已禁用，跳过心跳发送")
                    return False

            # 检查并刷新令牌
            if not self._refresh_token_if_needed():
                logger.debug("心跳认证失败，跳过本次心跳")
                return False
            
            # 更新状态
            if status:
                self.current_status = status
            if current_task:
                self.current_task = current_task
            if error_message is not None:
                self.error_message = error_message
            
            # 收集系统信息
            system_info = self._collect_system_info()
            
            # 构建心跳数据
            heartbeat_data = {
                'device_id': self.device_id,
                'status': self.current_status,
                'ip_address': self._get_ip_address(),
                'current_task': self.current_task,
                'error_message': self.error_message,
                **system_info  # 展开系统信息
            }
            
            # 发送心跳请求
            url = f"{self.heartbeat_config['server_url']}{self.heartbeat_config['heartbeat_endpoint']}"

            # 🚀 性能优化：在暂停状态下使用极短超时，正常状态下使用标准超时
            if self._paused:
                heartbeat_timeout = 0.1  # 暂停状态下使用极短超时
            else:
                heartbeat_timeout = min(self.heartbeat_config.get('timeout', 10), 5)  # 正常状态下最多5秒

            response = self.session.post(
                url,
                json=heartbeat_data,
                timeout=heartbeat_timeout
            )
            
            if response.status_code in [200, 201]:
                logger.debug(f"心跳发送成功: {self.current_status}")
                
                # 调用状态回调
                if self.status_callback:
                    try:
                        self.status_callback('heartbeat_sent', heartbeat_data)
                    except Exception as e:
                        logger.error(f"心跳状态回调失败: {e}")
                
                return True
            else:
                logger.warning(f"心跳发送失败: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            logger.debug(f"心跳发送超时: {self.heartbeat_config['timeout']}秒")
            return False
        except requests.exceptions.ConnectionError:
            logger.debug(f"心跳连接失败: {self.heartbeat_config['server_url']}")
            return False
        except Exception as e:
            logger.debug(f"心跳发送异常: {e}")
            return False
    
    def update_status(self, status: str, current_task: str = None, error_message: str = None):
        """
        更新设备状态并立即发送心跳

        Args:
            status: 设备状态
            current_task: 当前任务
            error_message: 错误信息
        """
        self.send_heartbeat(status=status, current_task=current_task, error_message=error_message)
    
    def set_status_callback(self, callback: Callable[[str, Dict], None]):
        """设置状态回调函数"""
        self.status_callback = callback
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            'enabled': self.heartbeat_config['enabled'],
            'running': self.is_running,
            'device_id': self.device_id,
            'current_status': self.current_status,
            'current_task': self.current_task,
            'error_message': self.error_message,
            'server_url': self.heartbeat_config['server_url'],
            'heartbeat_interval': self.heartbeat_config['heartbeat_interval']
        }
    
    def test_connection(self) -> bool:
        """测试服务器连接"""
        try:
            # 测试健康检查端点
            health_url = f"{self.heartbeat_config['server_url']}/health"
            response = self.session.get(health_url, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def update_config(self, new_config: Dict):
        """更新配置"""
        self.heartbeat_config.update(new_config)
        logger.info(f"心跳配置已更新: {new_config}")

    def pause_heartbeat(self):
        """🚀 暂停心跳发送（用于网络优化）"""
        try:
            self._paused = True
            logger.info("心跳发送已暂停")

            # 🚀 立即中断当前可能正在进行的网络请求
            if hasattr(self, 'session') and self.session:
                try:
                    # 关闭当前会话，中断正在进行的请求
                    self.session.close()
                    # 重新创建会话
                    self.session = requests.Session()
                    logger.debug("心跳会话已重置，中断正在进行的请求")
                except Exception as session_error:
                    logger.debug(f"重置心跳会话失败: {session_error}")

        except Exception as e:
            logger.error(f"暂停心跳失败: {e}")

    def resume_heartbeat(self):
        """🚀 恢复心跳发送（用于网络优化）"""
        try:
            self._paused = False
            logger.info("心跳发送已恢复")
        except Exception as e:
            logger.error(f"恢复心跳失败: {e}")

    def is_paused(self) -> bool:
        """🚀 检查是否暂停"""
        return self._paused
    
    def __del__(self):
        """析构函数"""
        self.stop()