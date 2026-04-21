"""
数据库同步管理器
负责将桌面软件数据库数据同步到云端数据库
"""

import json
import logging
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from queue import Queue, Empty

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class DatabaseSyncManager:
    """数据库同步管理器"""
    
    def __init__(self, config: Optional[Dict] = None, db_manager=None):
        """
        初始化数据库同步管理器
        
        Args:
            config: 同步配置
            db_manager: 数据库管理器
        """
        self.config = config or {}
        self.db_manager = db_manager
        self.sync_queue = Queue()
        self.sync_thread = None
        self.is_running = False
        
        # 默认配置
        self.default_config = {
            'enabled': True,
            'server_url': 'https://ukukukukukukukuk.uk',
            'sync_endpoint': '/api/sync/test-results',
            'batch_endpoint': '/api/sync/test-batches',
            'device_endpoint': '/api/sync/devices',
            'timeout': 60,
            'retry_count': 3,
            'retry_delay': 2.0,
            'batch_size': 50,
            'sync_interval': 300,  # 5分钟同步一次
            'incremental_sync': True,  # 增量同步
            'auto_auth': True,
            'username': 'admin',
            'password': 'Admin123!',
        }
        
        # 合并配置
        self.sync_config = {**self.default_config, **self.config}
        
        # 修复使用统一的设备ID管理器
        from utils.device_id_manager import get_device_id
        self.device_id = get_device_id()
        
        # 认证相关属性
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        
        # 创建HTTP会话
        self.session = self._create_session()
        
        # 同步状态跟踪
        self.last_sync_time = None
        self.sync_status = {
            'last_sync': None,
            'total_synced': 0,
            'failed_count': 0,
            'last_error': None
        }
        
        logger.info(f"数据库同步管理器初始化完成，设备ID: {self.device_id[:16]}...")
    
    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        
        # 修复减少重试次数和延迟，避免退出卡顿
        retry_strategy = Retry(
            total=min(self.sync_config['retry_count'], 1),  # 最多1次重试
            backoff_factor=0.1,  # 减少重试延迟
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # 设置默认headers
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f"JCY5001A-Sync/1.0"
        }
        
        session.headers.update(headers)
        return session
    
    def _get_hardware_fingerprint(self) -> str:
        """获取硬件指纹作为设备ID"""
        try:
            # 尝试从license_manager获取硬件指纹
            try:
                from utils.license_manager import LicenseManager
                license_manager = LicenseManager()
                fingerprint = license_manager.get_hardware_fingerprint()
                if fingerprint:
                    logger.info(f"使用硬件指纹作为设备ID: {fingerprint[:16]}...")
                    return fingerprint
            except Exception as e:
                logger.debug(f"无法从license_manager获取硬件指纹: {e}")
            
            # 备选方案：生成简化的硬件指纹
            import platform
            import hashlib
            import uuid
            
            fingerprint_data = []
            fingerprint_data.append(f"NODE:{platform.node()}")
            
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                               for elements in range(0, 2*6, 2)][::-1])
                fingerprint_data.append(f"MAC:{mac}")
            except:
                pass
            
            fingerprint_data.append(f"OS:{platform.system()}")
            fingerprint_data.append(f"ARCH:{platform.machine()}")
            
            fingerprint_str = "|".join(sorted(fingerprint_data))
            hardware_fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()
            
            logger.info(f"生成备选硬件指纹作为设备ID: {hardware_fingerprint[:16]}...")
            return hardware_fingerprint
            
        except Exception as e:
            logger.error(f"获取硬件指纹失败: {e}")
            fallback_id = f"JCY5001A_{platform.node()}"
            logger.warning(f"使用备选设备ID: {fallback_id}")
            return fallback_id
    
    def _authenticate(self) -> bool:
        """自动认证获取令牌"""
        if not self.sync_config.get('auto_auth', False):
            logger.debug("自动认证已禁用")
            return True
        
        try:
            username = self.sync_config.get('username')
            password = self.sync_config.get('password')
            
            if not username or not password:
                logger.warning("未配置用户名或密码，无法自动认证")
                return False
            
            login_url = f"{self.sync_config['server_url']}/api/auth/login"
            login_data = {
                'username': username,
                'password': password
            }
            
            logger.info(f"正在进行自动认证: {username}")
            
            response = self.session.post(
                login_url,
                json=login_data,
                timeout=self.sync_config['timeout']
            )
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                self.refresh_token = result.get('refresh_token')
                
                # 计算令牌过期时间（提前5分钟刷新）
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
            logger.error(f"自动认证异常: {e}")
            return False
    
    def _refresh_token_if_needed(self) -> bool:
        """如果需要则刷新令牌"""
        if not self.refresh_token or not self.token_expires_at:
            return self._authenticate()
        
        if datetime.now() >= self.token_expires_at:
            try:
                refresh_url = f"{self.sync_config['server_url']}/api/auth/refresh"
                
                # 临时使用refresh token
                temp_headers = {'Authorization': f'Bearer {self.refresh_token}'}
                
                response = self.session.post(
                    refresh_url,
                    headers=temp_headers,
                    timeout=self.sync_config['timeout']
                )
                
                if response.status_code == 200:
                    result = response.json()
                    self.access_token = result.get('access_token')
                    
                    # 更新过期时间
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
    
    def start_sync_service(self):
        """启动同步服务"""
        if not self.is_running:
            self.is_running = True
            self.sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
            self.sync_thread.start()
            logger.info("数据库同步服务已启动")
    
    def stop_sync_service(self):
        """停止同步服务"""
        logger.info("正在停止数据库同步服务...")
        self.is_running = False

        # 修复关闭HTTP会话，中断所有网络请求
        try:
            if hasattr(self, 'session') and self.session:
                self.session.close()
                logger.debug("数据库同步HTTP会话已关闭")
        except:
            pass

        # 修复减少线程等待时间，避免退出卡顿
        if self.sync_thread and self.sync_thread.is_alive():
            self.sync_thread.join(timeout=2)  # 从5秒减少到2秒
            if self.sync_thread.is_alive():
                logger.warning("数据库同步线程未能在2秒内停止")
            else:
                logger.info("数据库同步服务已停止")
    
    def _sync_worker(self):
        """同步工作线程"""
        while self.is_running:
            try:
                # 执行定期同步
                if self._should_sync():
                    self.perform_full_sync()
                
                # 处理手动同步请求
                try:
                    sync_request = self.sync_queue.get(timeout=1)
                    self._process_sync_request(sync_request)
                except Empty:
                    pass
                
                time.sleep(1)  # 避免CPU占用过高
                
            except Exception as e:
                logger.error(f"同步工作线程异常: {e}")
                time.sleep(5)  # 异常后等待5秒再继续
    
    def _should_sync(self) -> bool:
        """判断是否应该执行同步"""
        if not self.sync_config['enabled']:
            return False

        if self.last_sync_time is None:
            return True

        sync_interval = self.sync_config['sync_interval']
        return (datetime.now() - self.last_sync_time).total_seconds() >= sync_interval

    def _process_sync_request(self, sync_request: Dict):
        """处理同步请求"""
        try:
            sync_type = sync_request.get('type', 'full')

            if sync_type == 'full':
                self.perform_full_sync()
            elif sync_type == 'incremental':
                self.perform_incremental_sync()
            elif sync_type == 'test_results':
                test_result_ids = sync_request.get('test_result_ids', [])
                self.sync_specific_test_results(test_result_ids)
            else:
                logger.warning(f"未知的同步类型: {sync_type}")

        except Exception as e:
            logger.error(f"处理同步请求失败: {e}")

    def perform_full_sync(self) -> Dict[str, Any]:
        """执行完整同步"""
        logger.info("开始执行完整数据同步...")

        sync_result = {
            'success': False,
            'synced_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            # 检查并刷新令牌
            if not self._refresh_token_if_needed():
                error_msg = "认证失败，无法执行同步"
                logger.error(error_msg)
                sync_result['errors'].append(error_msg)
                return sync_result

            # 1. 确保设备已注册
            if not self._ensure_device_registered():
                error_msg = "设备注册失败"
                logger.error(error_msg)
                sync_result['errors'].append(error_msg)
                return sync_result

            # 2. 同步测试结果数据
            test_results_result = self._sync_test_results()
            sync_result['synced_count'] += test_results_result.get('synced_count', 0)
            sync_result['failed_count'] += test_results_result.get('failed_count', 0)
            sync_result['errors'].extend(test_results_result.get('errors', []))

            # 3. 同步阻抗明细数据
            impedance_result = self._sync_impedance_details()
            sync_result['synced_count'] += impedance_result.get('synced_count', 0)
            sync_result['failed_count'] += impedance_result.get('failed_count', 0)
            sync_result['errors'].extend(impedance_result.get('errors', []))

            # 更新同步状态
            self.last_sync_time = datetime.now()
            self.sync_status['last_sync'] = self.last_sync_time.isoformat()
            self.sync_status['total_synced'] += sync_result['synced_count']
            self.sync_status['failed_count'] += sync_result['failed_count']

            if sync_result['failed_count'] == 0:
                sync_result['success'] = True
                self.sync_status['last_error'] = None
                logger.info(f"完整同步成功完成，同步了 {sync_result['synced_count']} 条记录")
            else:
                self.sync_status['last_error'] = f"同步失败 {sync_result['failed_count']} 条记录"
                logger.warning(f"同步部分失败: 成功 {sync_result['synced_count']}, 失败 {sync_result['failed_count']}")

        except Exception as e:
            error_msg = f"完整同步异常: {e}"
            logger.error(error_msg)
            sync_result['errors'].append(error_msg)
            self.sync_status['last_error'] = error_msg

        return sync_result

    def perform_incremental_sync(self) -> Dict[str, Any]:
        """执行增量同步"""
        logger.info("开始执行增量数据同步...")

        sync_result = {
            'success': False,
            'synced_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            # 检查并刷新令牌
            if not self._refresh_token_if_needed():
                error_msg = "认证失败，无法执行增量同步"
                logger.error(error_msg)
                sync_result['errors'].append(error_msg)
                return sync_result

            # 获取上次同步时间
            last_sync = self.sync_status.get('last_sync')
            if last_sync:
                last_sync_time = datetime.fromisoformat(last_sync)
            else:
                # 如果没有上次同步记录，同步最近24小时的数据
                last_sync_time = datetime.now() - timedelta(hours=24)

            logger.info(f"增量同步起始时间: {last_sync_time}")

            # 同步增量测试结果数据
            test_results_result = self._sync_test_results(since_time=last_sync_time)
            sync_result['synced_count'] += test_results_result.get('synced_count', 0)
            sync_result['failed_count'] += test_results_result.get('failed_count', 0)
            sync_result['errors'].extend(test_results_result.get('errors', []))

            # 同步增量阻抗明细数据
            impedance_result = self._sync_impedance_details(since_time=last_sync_time)
            sync_result['synced_count'] += impedance_result.get('synced_count', 0)
            sync_result['failed_count'] += impedance_result.get('failed_count', 0)
            sync_result['errors'].extend(impedance_result.get('errors', []))

            # 更新同步状态
            self.last_sync_time = datetime.now()
            self.sync_status['last_sync'] = self.last_sync_time.isoformat()
            self.sync_status['total_synced'] += sync_result['synced_count']
            self.sync_status['failed_count'] += sync_result['failed_count']

            if sync_result['failed_count'] == 0:
                sync_result['success'] = True
                self.sync_status['last_error'] = None
                logger.info(f"增量同步成功完成，同步了 {sync_result['synced_count']} 条记录")
            else:
                self.sync_status['last_error'] = f"增量同步失败 {sync_result['failed_count']} 条记录"
                logger.warning(f"增量同步部分失败: 成功 {sync_result['synced_count']}, 失败 {sync_result['failed_count']}")

        except Exception as e:
            error_msg = f"增量同步异常: {e}"
            logger.error(error_msg)
            sync_result['errors'].append(error_msg)
            self.sync_status['last_error'] = error_msg

        return sync_result

    def _ensure_device_registered(self) -> bool:
        """确保设备已在云端注册"""
        try:
            # 检查设备是否已存在
            check_url = f"{self.sync_config['server_url']}/api/devices/{self.device_id}"

            response = self.session.get(check_url, timeout=self.sync_config['timeout'])

            if response.status_code == 200:
                logger.info("设备已在云端注册")
                return True
            elif response.status_code == 404:
                # 设备不存在，需要注册
                return self._register_device()
            else:
                logger.error(f"检查设备注册状态失败: HTTP {response.status_code}, {response.text}")
                # 如果检查失败，尝试直接注册
                return self._register_device()

        except Exception as e:
            logger.error(f"检查设备注册状态异常: {e}")
            # 异常时尝试直接注册
            return self._register_device()

    def _register_device(self) -> bool:
        """注册设备到云端"""
        try:
            import platform

            device_data = {
                'device_id': self.device_id,
                'name': f"JCY5001A-{platform.node()}",
                'model': 'JCY5001A',
                'firmware_version': 'V0.80.20',
                'status': 'active'
            }

            # 使用同步API的设备注册端点
            register_url = f"{self.sync_config['server_url']}/api/sync/devices"

            response = self.session.post(
                register_url,
                json=device_data,
                timeout=self.sync_config['timeout']
            )

            if response.status_code in [200, 201]:
                logger.info(f"设备注册成功: {self.device_id}")
                return True
            else:
                logger.error(f"设备注册失败: HTTP {response.status_code}, {response.text}")
                return False

        except Exception as e:
            logger.error(f"设备注册异常: {e}")
            return False

    def _sync_test_results(self, since_time: Optional[datetime] = None) -> Dict[str, Any]:
        """同步测试结果数据"""
        result = {
            'synced_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            if not self.db_manager:
                result['errors'].append("数据库管理器未初始化")
                return result

            # 构建查询条件
            where_clause = ""
            params = []

            if since_time:
                where_clause = "WHERE created_at > ?"
                params.append(since_time.isoformat())

            # 查询本地测试结果
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                query = f"""
                    SELECT * FROM test_results
                    {where_clause}
                    ORDER BY created_at ASC
                """

                cursor.execute(query, params)
                test_results = cursor.fetchall()

                # 获取列名
                column_names = [description[0] for description in cursor.description]

                logger.info(f"找到 {len(test_results)} 条测试结果需要同步")

                # 批量同步
                batch_size = self.sync_config['batch_size']
                for i in range(0, len(test_results), batch_size):
                    batch = test_results[i:i + batch_size]
                    batch_result = self._sync_test_results_batch(batch, column_names)

                    result['synced_count'] += batch_result.get('synced_count', 0)
                    result['failed_count'] += batch_result.get('failed_count', 0)
                    result['errors'].extend(batch_result.get('errors', []))

                    # 避免过快请求
                    time.sleep(0.1)

        except Exception as e:
            error_msg = f"同步测试结果异常: {e}"
            logger.error(error_msg)
            result['errors'].append(error_msg)

        return result

    def _sync_test_results_batch(self, batch: List[Tuple], column_names: List[str]) -> Dict[str, Any]:
        """批量同步测试结果"""
        result = {
            'synced_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            # 转换为字典格式
            batch_data = []
            for row in batch:
                row_dict = dict(zip(column_names, row))

                # 格式化数据以匹配云端API
                formatted_data = self._format_test_result_for_sync(row_dict)
                batch_data.append(formatted_data)

            # 发送到云端
            sync_url = f"{self.sync_config['server_url']}{self.sync_config['sync_endpoint']}"

            payload = {
                'device_id': self.device_id,
                'test_results': batch_data
            }

            response = self.session.post(
                sync_url,
                json=payload,
                timeout=self.sync_config['timeout']
            )

            if response.status_code in [200, 201]:
                response_data = response.json()
                synced_count = response_data.get('synced_count', len(batch_data))
                result['synced_count'] = synced_count
                logger.info(f"批量同步测试结果成功: {synced_count} 条")
            else:
                error_msg = f"批量同步测试结果失败: HTTP {response.status_code}, {response.text}"
                logger.error(error_msg)
                result['failed_count'] = len(batch_data)
                result['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"批量同步测试结果异常: {e}"
            logger.error(error_msg)
            result['failed_count'] = len(batch)
            result['errors'].append(error_msg)

        return result

    def _format_test_result_for_sync(self, row_dict: Dict) -> Dict:
        """格式化测试结果数据以匹配云端API"""
        try:
            # 生成唯一的test_id
            test_id = f"{self.device_id}_{row_dict.get('id', '')}"

            # 处理时间字段
            test_start_time = row_dict.get('test_start_time')
            if test_start_time:
                if isinstance(test_start_time, str):
                    test_start_time = datetime.fromisoformat(test_start_time.replace('Z', '+00:00'))
                elif not isinstance(test_start_time, datetime):
                    test_start_time = datetime.now()
            else:
                test_start_time = datetime.now()

            test_end_time = row_dict.get('test_end_time')
            if test_end_time and isinstance(test_end_time, str):
                test_end_time = datetime.fromisoformat(test_end_time.replace('Z', '+00:00'))

            # 格式化数据
            formatted_data = {
                'test_id': test_id,
                'device_id': self.device_id,
                'channel_number': row_dict.get('channel_number'),
                'battery_code': row_dict.get('battery_code', ''),
                'test_start_time': test_start_time.isoformat(),
                'test_end_time': test_end_time.isoformat() if test_end_time else None,
                'test_duration': row_dict.get('test_duration'),
                'voltage': row_dict.get('voltage'),
                'rs_value': row_dict.get('rs_value'),
                'rct_value': row_dict.get('rct_value'),
                'rsei_value': row_dict.get('rsei_value'),
                'w_impedance': row_dict.get('w_impedance'),
                'rs_grade': row_dict.get('rs_grade'),
                'rct_grade': row_dict.get('rct_grade'),
                'is_pass': bool(row_dict.get('is_pass', False)),
                'fail_reason': row_dict.get('fail_reason'),
                'test_mode': row_dict.get('test_mode'),
                'frequency_list': row_dict.get('frequency_list'),
                'raw_data': row_dict.get('raw_data'),
                'outlier_result': row_dict.get('outlier_result'),
                'baseline_filename': row_dict.get('baseline_filename'),
                'baseline_id': row_dict.get('baseline_id'),
                'max_deviation_percent': row_dict.get('max_deviation_percent'),
                'frequency_deviations': row_dict.get('frequency_deviations'),
                'operator': row_dict.get('operator'),
                'battery_type': row_dict.get('battery_type'),
                'battery_spec': row_dict.get('battery_spec'),
                'batch_number': row_dict.get('batch_number'),
                'rct_coefficient_of_variation': row_dict.get('rct_coefficient_of_variation'),
                'capacity_prediction': row_dict.get('capacity_prediction'),
                'voltage_range_min': row_dict.get('voltage_range_min'),
                'voltage_range_max': row_dict.get('voltage_range_max'),
                'rs_range_min': row_dict.get('rs_range_min'),
                'rs_range_max': row_dict.get('rs_range_max'),
                'rct_range_min': row_dict.get('rct_range_min'),
                'rct_range_max': row_dict.get('rct_range_max'),
                'warburg_coefficient': row_dict.get('warburg_coefficient'),
                'warburg_01hz': row_dict.get('warburg_01hz'),
                'warburg_001hz': row_dict.get('warburg_001hz'),
                'has_warburg_diffusion': bool(row_dict.get('has_warburg_diffusion', False)),
                'has_sei': bool(row_dict.get('has_sei', False)),
                'sei_confidence': row_dict.get('sei_confidence'),
                'double_layer_capacitance': row_dict.get('double_layer_capacitance'),
                'sei_capacitance': row_dict.get('sei_capacitance'),
                'total_capacitance': row_dict.get('total_capacitance'),
                'impedance_ratio': row_dict.get('impedance_ratio'),
                'capacity': row_dict.get('capacity', 3000),  # 默认容量
                'thickness': row_dict.get('thickness'),
                'temperature': row_dict.get('temperature', 25.0),  # 默认温度
                'test_result': 'pass' if row_dict.get('is_pass') else 'fail',
                'error_code': row_dict.get('error_code'),
                # 保留原始ID用于关联阻抗明细数据
                'original_id': row_dict.get('id')
            }

            return formatted_data

        except Exception as e:
            logger.error(f"格式化测试结果数据失败: {e}")
            raise

    def _sync_impedance_details(self, since_time: Optional[datetime] = None) -> Dict[str, Any]:
        """同步阻抗明细数据"""
        result = {
            'synced_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            if not self.db_manager:
                result['errors'].append("数据库管理器未初始化")
                return result

            # 首先获取已同步到云端的测试结果ID列表
            synced_test_ids = self._get_synced_test_result_ids()
            if not synced_test_ids:
                logger.info("没有已同步的测试结果，跳过阻抗明细同步")
                return result

            logger.info(f"找到 {len(synced_test_ids)} 个已同步的测试结果")

            # 构建查询条件，只查询已同步测试结果的阻抗明细
            where_conditions = ["batch_id IN ({})".format(','.join(['?'] * len(synced_test_ids)))]
            params = list(synced_test_ids)

            if since_time:
                where_conditions.append("created_at > ?")
                params.append(since_time.isoformat())

            where_clause = "WHERE " + " AND ".join(where_conditions)

            # 查询本地阻抗明细数据
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                query = f"""
                    SELECT * FROM impedance_details
                    {where_clause}
                    ORDER BY created_at ASC
                """

                cursor.execute(query, params)
                impedance_details = cursor.fetchall()

                # 获取列名
                column_names = [description[0] for description in cursor.description]

                logger.info(f"找到 {len(impedance_details)} 条阻抗明细数据需要同步")

                if not impedance_details:
                    logger.info("没有需要同步的阻抗明细数据")
                    return result

                # 按测试结果ID分组批量同步
                grouped_data = self._group_impedance_by_test_result(impedance_details, column_names)

                for test_result_id, details in grouped_data.items():
                    detail_result = self._sync_impedance_details_for_test(test_result_id, details)

                    result['synced_count'] += detail_result.get('synced_count', 0)
                    result['failed_count'] += detail_result.get('failed_count', 0)
                    result['errors'].extend(detail_result.get('errors', []))

                    # 避免过快请求
                    time.sleep(0.1)

        except Exception as e:
            error_msg = f"同步阻抗明细数据异常: {e}"
            logger.error(error_msg)
            result['errors'].append(error_msg)

        return result

    def _get_synced_test_result_ids(self) -> List[int]:
        """获取已同步到云端的测试结果ID列表"""
        try:
            # 查询云端已有的测试结果
            check_url = f"{self.sync_config['server_url']}/api/sync/status/{self.device_id}"

            response = self.session.get(check_url, timeout=self.sync_config['timeout'])

            if response.status_code == 200:
                # 如果有状态API，可以获取更详细的信息
                # 这里我们使用一个简化的方法：查询本地最近同步的测试结果
                return self._get_recently_synced_test_ids()
            else:
                logger.warning(f"无法获取云端同步状态: HTTP {response.status_code}")
                return self._get_recently_synced_test_ids()

        except Exception as e:
            logger.warning(f"获取已同步测试结果ID失败: {e}")
            return self._get_recently_synced_test_ids()

    def _get_recently_synced_test_ids(self) -> List[int]:
        """获取最近可能已同步的测试结果ID"""
        try:
            if not self.db_manager:
                return []

            # 获取最近24小时的测试结果ID
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                # 查询最近的测试结果ID
                query = """
                    SELECT id FROM test_results
                    WHERE created_at > datetime('now', '-1 day')
                    ORDER BY created_at DESC
                    LIMIT 100
                """

                cursor.execute(query)
                results = cursor.fetchall()

                test_ids = [row[0] for row in results]
                logger.info(f"获取到 {len(test_ids)} 个最近的测试结果ID")

                return test_ids

        except Exception as e:
            logger.error(f"获取最近测试结果ID失败: {e}")
            return []

    def _group_impedance_by_test_result(self, impedance_details: List[Tuple],
                                       column_names: List[str]) -> Dict[int, List[Dict]]:
        """按测试结果ID分组阻抗明细数据"""
        grouped = {}

        for row in impedance_details:
            row_dict = dict(zip(column_names, row))
            # 使用batch_id作为分组键，这对应测试结果的原始ID
            batch_id = row_dict.get('batch_id')

            if batch_id is None:
                logger.warning(f"阻抗明细数据缺少batch_id，跳过: {row_dict}")
                continue

            if batch_id not in grouped:
                grouped[batch_id] = []

            grouped[batch_id].append(row_dict)

        logger.info(f"阻抗明细数据分组完成: {len(grouped)} 个测试结果")
        return grouped

    def _sync_impedance_details_for_test(self, test_result_id: int, details: List[Dict]) -> Dict[str, Any]:
        """为特定测试结果同步阻抗明细数据"""
        result = {
            'synced_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            # 检查是否有阻抗明细数据
            if not details:
                logger.debug(f"测试结果 {test_result_id} 没有阻抗明细数据")
                return result

            # 格式化阻抗明细数据
            formatted_details = []
            for detail in details:
                try:
                    formatted_detail = self._format_impedance_detail_for_sync(detail)
                    formatted_details.append(formatted_detail)
                except Exception as e:
                    logger.warning(f"格式化阻抗明细数据失败: {e}")
                    continue

            if not formatted_details:
                logger.warning(f"测试结果 {test_result_id} 没有有效的阻抗明细数据")
                return result

            # 生成云端测试结果ID
            cloud_test_id = f"{self.device_id}_{test_result_id}"

            logger.info(f"准备同步阻抗明细: 测试ID {cloud_test_id}, 数据量 {len(formatted_details)}")

            # 发送到云端
            sync_url = f"{self.sync_config['server_url']}/api/sync/impedance-details"

            payload = {
                'device_id': self.device_id,
                'test_id': cloud_test_id,
                'impedance_details': formatted_details
            }

            response = self.session.post(
                sync_url,
                json=payload,
                timeout=self.sync_config['timeout']
            )

            if response.status_code in [200, 201]:
                response_data = response.json()
                synced_count = response_data.get('synced_count', len(formatted_details))
                result['synced_count'] = synced_count
                logger.info(f"同步阻抗明细数据成功: {synced_count} 条 (测试ID: {test_result_id})")
            else:
                error_msg = f"同步阻抗明细数据失败: HTTP {response.status_code}, {response.text}"
                logger.error(error_msg)
                result['failed_count'] = len(formatted_details)
                result['errors'].append(error_msg)

        except Exception as e:
            error_msg = f"同步阻抗明细数据异常: {e}"
            logger.error(error_msg)
            result['failed_count'] = len(details)
            result['errors'].append(error_msg)

        return result

    def _format_impedance_detail_for_sync(self, detail_dict: Dict) -> Dict:
        """格式化阻抗明细数据以匹配云端API"""
        try:
            formatted_data = {
                'batch_id': detail_dict.get('batch_id'),
                'channel_number': detail_dict.get('channel_number'),
                'battery_code': detail_dict.get('battery_code', ''),
                'test_timestamp': detail_dict.get('test_timestamp', ''),
                'frequency': detail_dict.get('frequency'),
                'impedance_real': detail_dict.get('impedance_real'),
                'impedance_imag': detail_dict.get('impedance_imag'),
                'voltage': detail_dict.get('voltage'),
                'test_sequence': detail_dict.get('test_sequence', 0),
                'z_value': detail_dict.get('z_value'),
                'baseline_z_value': detail_dict.get('baseline_z_value'),
                'deviation_percent': detail_dict.get('deviation_percent'),
                # 兼容字段
                'z_real': detail_dict.get('impedance_real'),
                'z_imag': detail_dict.get('impedance_imag'),
                'z_magnitude': detail_dict.get('z_value'),
                'phase_angle': None,  # 如果需要可以计算
                'measurement_time': detail_dict.get('test_timestamp')
            }

            return formatted_data

        except Exception as e:
            logger.error(f"格式化阻抗明细数据失败: {e}")
            raise

    # 公共接口方法

    def sync_specific_test_results(self, test_result_ids: List[int]) -> Dict[str, Any]:
        """同步指定的测试结果"""
        logger.info(f"开始同步指定的测试结果: {test_result_ids}")

        sync_result = {
            'success': False,
            'synced_count': 0,
            'failed_count': 0,
            'errors': []
        }

        try:
            # 检查并刷新令牌
            if not self._refresh_token_if_needed():
                error_msg = "认证失败，无法执行同步"
                logger.error(error_msg)
                sync_result['errors'].append(error_msg)
                return sync_result

            if not self.db_manager:
                sync_result['errors'].append("数据库管理器未初始化")
                return sync_result

            # 查询指定的测试结果
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()

                placeholders = ','.join(['?'] * len(test_result_ids))
                query = f"SELECT * FROM test_results WHERE id IN ({placeholders})"

                cursor.execute(query, test_result_ids)
                test_results = cursor.fetchall()

                # 获取列名
                column_names = [description[0] for description in cursor.description]

                logger.info(f"找到 {len(test_results)} 条指定的测试结果")

                # 同步测试结果
                if test_results:
                    batch_result = self._sync_test_results_batch(test_results, column_names)
                    sync_result['synced_count'] += batch_result.get('synced_count', 0)
                    sync_result['failed_count'] += batch_result.get('failed_count', 0)
                    sync_result['errors'].extend(batch_result.get('errors', []))

                # 同步相关的阻抗明细数据
                for test_id in test_result_ids:
                    impedance_query = "SELECT * FROM impedance_details WHERE batch_id = ?"
                    cursor.execute(impedance_query, (test_id,))
                    impedance_details = cursor.fetchall()

                    if impedance_details:
                        impedance_column_names = [description[0] for description in cursor.description]
                        details_list = [dict(zip(impedance_column_names, row)) for row in impedance_details]

                        detail_result = self._sync_impedance_details_for_test(test_id, details_list)
                        sync_result['synced_count'] += detail_result.get('synced_count', 0)
                        sync_result['failed_count'] += detail_result.get('failed_count', 0)
                        sync_result['errors'].extend(detail_result.get('errors', []))

            if sync_result['failed_count'] == 0:
                sync_result['success'] = True
                logger.info(f"指定测试结果同步成功完成，同步了 {sync_result['synced_count']} 条记录")
            else:
                logger.warning(f"指定测试结果同步部分失败: 成功 {sync_result['synced_count']}, 失败 {sync_result['failed_count']}")

        except Exception as e:
            error_msg = f"同步指定测试结果异常: {e}"
            logger.error(error_msg)
            sync_result['errors'].append(error_msg)

        return sync_result

    def manual_sync(self, sync_type: str = 'incremental') -> Dict[str, Any]:
        """手动触发同步"""
        sync_request = {
            'type': sync_type,
            'timestamp': datetime.now().isoformat()
        }

        self.sync_queue.put(sync_request)
        logger.info(f"已添加手动同步请求: {sync_type}")

        return {'success': True, 'message': f'已触发{sync_type}同步'}

    def get_sync_status(self) -> Dict[str, Any]:
        """获取同步状态"""
        return {
            'device_id': self.device_id,
            'is_running': self.is_running,
            'sync_config': {
                'enabled': self.sync_config['enabled'],
                'server_url': self.sync_config['server_url'],
                'sync_interval': self.sync_config['sync_interval'],
                'incremental_sync': self.sync_config['incremental_sync']
            },
            'sync_status': self.sync_status.copy()
        }
