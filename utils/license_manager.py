# -*- coding: utf-8 -*-
"""
软件授权管理器
负责软件授权验证、硬件指纹生成、试用期管理等功能

Author: Jack
Date: 2025-06-03
"""

import os
import json
import hashlib
import platform
import subprocess
import uuid
import base64
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)


class LicenseManager:
    """软件授权管理器"""
    
    # 单例模式相关
    _instance = None
    _initialized = False
    _hardware_fingerprint_cache = None
    
    def __new__(cls, config_manager=None):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_manager=None):
        """
        初始化授权管理器
        
        Args:
            config_manager: 配置管理器
        """
        # 防止重复初始化
        if self._initialized:
            return
        
        self.config_manager = config_manager
        self.license_file = "data/license.dat"
        self.hardware_fingerprint = None
        self.license_data = None
        
        # 确保数据目录存在
        os.makedirs(os.path.dirname(self.license_file), exist_ok=True)
        
        # 生成硬件指纹（使用缓存）
        self._generate_hardware_fingerprint()
        
        # 加载授权数据
        self._load_license_data()
        
        # 标记为已初始化
        self._initialized = True
        logger.debug("授权管理器初始化完成")
    
    def _generate_hardware_fingerprint(self) -> str:
        """
        生成硬件指纹（使用缓存避免重复生成）
        
        Returns:
            硬件指纹字符串
        """
        # 如果已有缓存的硬件指纹，直接返回
        if self._hardware_fingerprint_cache:
            self.hardware_fingerprint = self._hardware_fingerprint_cache
            return self.hardware_fingerprint
        
        try:
            fingerprint_data = []
            
            # 1. CPU信息
            try:
                if platform.system() == "Windows":
                    result = subprocess.run(
                        ['wmic', 'cpu', 'get', 'ProcessorId', '/value'],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.split('\n'):
                        if 'ProcessorId=' in line:
                            cpu_id = line.split('=')[1].strip()
                            if cpu_id:
                                fingerprint_data.append(f"CPU:{cpu_id}")
                                break
                else:
                    # Linux/Mac系统的CPU信息获取
                    with open('/proc/cpuinfo', 'r') as f:
                        for line in f:
                            if 'serial' in line.lower():
                                cpu_id = line.split(':')[1].strip()
                                fingerprint_data.append(f"CPU:{cpu_id}")
                                break
            except Exception as e:
                logger.debug(f"获取CPU信息失败: {e}")
            
            # 2. 主板序列号
            try:
                if platform.system() == "Windows":
                    result = subprocess.run(
                        ['wmic', 'baseboard', 'get', 'SerialNumber', '/value'],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.split('\n'):
                        if 'SerialNumber=' in line:
                            board_serial = line.split('=')[1].strip()
                            if board_serial and board_serial != 'To be filled by O.E.M.':
                                fingerprint_data.append(f"BOARD:{board_serial}")
                                break
                else:
                    result = subprocess.run(
                        ['dmidecode', '-s', 'baseboard-serial-number'],
                        capture_output=True, text=True, timeout=10
                    )
                    board_serial = result.stdout.strip()
                    if board_serial:
                        fingerprint_data.append(f"BOARD:{board_serial}")
            except Exception as e:
                logger.debug(f"获取主板序列号失败: {e}")
            
            # 3. MAC地址
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff) 
                               for elements in range(0, 2*6, 2)][::-1])
                fingerprint_data.append(f"MAC:{mac}")
            except Exception as e:
                logger.debug(f"获取MAC地址失败: {e}")
            
            # 4. 硬盘序列号
            try:
                if platform.system() == "Windows":
                    result = subprocess.run(
                        ['wmic', 'diskdrive', 'get', 'SerialNumber', '/value'],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.split('\n'):
                        if 'SerialNumber=' in line:
                            disk_serial = line.split('=')[1].strip()
                            if disk_serial:
                                fingerprint_data.append(f"DISK:{disk_serial}")
                                break
            except Exception as e:
                logger.debug(f"获取硬盘序列号失败: {e}")
            
            # 5. 系统UUID
            try:
                if platform.system() == "Windows":
                    result = subprocess.run(
                        ['wmic', 'csproduct', 'get', 'UUID', '/value'],
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.split('\n'):
                        if 'UUID=' in line:
                            system_uuid = line.split('=')[1].strip()
                            if system_uuid:
                                fingerprint_data.append(f"UUID:{system_uuid}")
                                break
            except Exception as e:
                logger.debug(f"获取系统UUID失败: {e}")
            
            # 如果没有获取到任何硬件信息，使用机器名作为备选
            if not fingerprint_data:
                fingerprint_data.append(f"HOSTNAME:{platform.node()}")
            
            # 生成最终指纹
            fingerprint_str = "|".join(sorted(fingerprint_data))
            self.hardware_fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()

            # 缓存硬件指纹
            self._hardware_fingerprint_cache = self.hardware_fingerprint

            logger.debug(f" 硬件指纹组件: {fingerprint_data}")
            logger.debug(f" 指纹字符串: {fingerprint_str}")
            logger.info(f"✅ 硬件指纹生成完成: {self.hardware_fingerprint[:16]}...")
            return self.hardware_fingerprint
            
        except Exception as e:
            logger.error(f"生成硬件指纹失败: {e}")
            # 使用机器名作为备选方案
            fallback = f"FALLBACK:{platform.node()}"
            self.hardware_fingerprint = hashlib.sha256(fallback.encode()).hexdigest()
            
            # 缓存备选指纹
            self._hardware_fingerprint_cache = self.hardware_fingerprint
            return self.hardware_fingerprint
    
    def _get_encryption_key(self) -> bytes:
        """
        获取加密密钥（基于硬件指纹）
        
        Returns:
            加密密钥
        """
        try:
            # 使用硬件指纹和固定盐生成密钥
            password = (self.hardware_fingerprint + "JCY5001AS_LICENSE_KEY").encode()
            salt = b"JCY5001AS_SALT_2025"
            
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            return key
            
        except Exception as e:
            logger.error(f"生成加密密钥失败: {e}")
            raise
    
    def _encrypt_data(self, data: dict) -> str:
        """
        加密数据
        
        Args:
            data: 要加密的数据
            
        Returns:
            加密后的字符串
        """
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            
            json_str = json.dumps(data, ensure_ascii=False)
            encrypted_data = fernet.encrypt(json_str.encode())
            
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"数据加密失败: {e}")
            raise
    
    def _decrypt_data(self, encrypted_str: str) -> dict:
        """
        解密数据
        
        Args:
            encrypted_str: 加密的字符串
            
        Returns:
            解密后的数据
        """
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            
            encrypted_data = base64.b64decode(encrypted_str.encode())
            decrypted_data = fernet.decrypt(encrypted_data)
            
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            logger.error(f"数据解密失败: {e}")
            return {}
    
    def _load_license_data(self):
        """加载授权数据"""
        try:
            if os.path.exists(self.license_file):
                with open(self.license_file, 'r', encoding='utf-8') as f:
                    encrypted_data = f.read().strip()
                
                if encrypted_data:
                    self.license_data = self._decrypt_data(encrypted_data)
                    
                    # 验证硬件指纹
                    stored_fingerprint = self.license_data.get('hardware_fingerprint')
                    if stored_fingerprint != self.hardware_fingerprint:
                        logger.warning(f"🔍 硬件指纹不匹配，重置授权数据")
                        logger.warning(f"存储的指纹: {stored_fingerprint[:16] if stored_fingerprint else 'None'}...")
                        logger.warning(f"当前的指纹: {self.hardware_fingerprint[:16] if self.hardware_fingerprint else 'None'}...")
                        logger.warning("这可能导致试用期重置为30天")
                        self.license_data = None
                    else:
                        logger.info("✅ 授权数据加载成功，硬件指纹匹配")
                else:
                    self.license_data = None
            else:
                self.license_data = None
                
        except Exception as e:
            logger.error(f"加载授权数据失败: {e}")
            self.license_data = None
    
    def _save_license_data(self):
        """保存授权数据"""
        try:
            if self.license_data is None:
                return
            
            # 添加硬件指纹
            self.license_data['hardware_fingerprint'] = self.hardware_fingerprint
            self.license_data['last_update'] = datetime.now().isoformat()
            
            encrypted_data = self._encrypt_data(self.license_data)
            
            with open(self.license_file, 'w', encoding='utf-8') as f:
                f.write(encrypted_data)
            
            logger.info("授权数据保存成功")
            
        except Exception as e:
            logger.error(f"保存授权数据失败: {e}")

    def initialize_trial(self, trial_days: int = 30) -> bool:
        """
        初始化试用期

        Args:
            trial_days: 试用天数

        Returns:
            是否成功初始化
        """
        try:
            if self.license_data is None:
                # 首次运行或硬件指纹不匹配，初始化试用期
                logger.warning(f"🔄 初始化试用期: {trial_days}天")
                logger.warning("原因: 授权数据为空（可能是首次运行或硬件指纹不匹配）")
                self.license_data = {
                    'is_licensed': False,
                    'trial_start_date': datetime.now().isoformat(),
                    'trial_days': trial_days,
                    'unlock_code': None,
                    'license_type': 'trial'
                }
                self._save_license_data()
                logger.warning(f"⚠️ 试用期已重置为 {trial_days} 天")
                return True
            else:
                logger.info("✅ 授权数据已存在，跳过初始化")
                return True

        except Exception as e:
            logger.error(f"初始化试用期失败: {e}")
            return False

    def get_license_status(self) -> Dict:
        """
        获取授权状态

        Returns:
            授权状态信息
        """
        try:
            if self.license_data is None:
                return {
                    'is_licensed': False,
                    'is_trial_expired': True,
                    'remaining_days': 0,
                    'trial_days': 0,
                    'expire_date': None,
                    'license_type': 'none'
                }

            is_licensed = self.license_data.get('is_licensed', False)

            # 检查模拟模式
            if getattr(self, '_simulated_expired', False):
                return {
                    'is_licensed': False,
                    'is_trial_expired': True,
                    'remaining_days': 0,
                    'trial_days': self.license_data.get('trial_days', 30),
                    'expire_date': None,
                    'license_type': 'simulated_expired'
                }

            if is_licensed:
                license_type = self.license_data.get('license_type', 'full')

                # 检查是否是临时授权
                if license_type == 'temp':
                    temp_expire_date_str = self.license_data.get('temp_expire_date')
                    if temp_expire_date_str:
                        try:
                            temp_expire_date = datetime.fromisoformat(temp_expire_date_str)
                            remaining = temp_expire_date - datetime.now()

                            # 检查临时授权是否已过期
                            if remaining.total_seconds() <= 0:
                                # 临时授权已过期，恢复到试用状态
                                logger.warning("临时授权已过期，恢复到试用状态")
                                self.license_data.update({
                                    'is_licensed': False,
                                    'license_type': 'trial'
                                })
                                self._save_license_data()

                                # 重新计算试用期状态
                                return self.get_license_status()
                            else:
                                # 临时授权仍有效
                                return {
                                    'is_licensed': True,
                                    'is_trial_expired': False,
                                    'remaining_days': max(0, remaining.days),
                                    'trial_days': -1,
                                    'expire_date': temp_expire_date.isoformat(),
                                    'license_type': 'temp'
                                }
                        except Exception as e:
                            logger.error(f"解析临时授权到期时间失败: {e}")
                            # 解析失败，当作永久授权处理
                            pass

                # 永久授权
                return {
                    'is_licensed': True,
                    'is_trial_expired': False,
                    'remaining_days': -1,  # 无限制
                    'trial_days': -1,
                    'expire_date': None,
                    'license_type': license_type
                }

            # 计算试用期状态
            trial_start_str = self.license_data.get('trial_start_date')
            trial_days = self.license_data.get('trial_days', 30)

            if trial_start_str:
                trial_start = datetime.fromisoformat(trial_start_str)
                expire_date = trial_start + timedelta(days=trial_days)
                remaining = expire_date - datetime.now()

                return {
                    'is_licensed': False,
                    'is_trial_expired': remaining.total_seconds() <= 0,
                    'remaining_days': max(0, remaining.days),
                    'trial_days': trial_days,
                    'expire_date': expire_date.isoformat(),
                    'license_type': 'trial'
                }
            else:
                return {
                    'is_licensed': False,
                    'is_trial_expired': True,
                    'remaining_days': 0,
                    'trial_days': trial_days,
                    'expire_date': None,
                    'license_type': 'trial'
                }

        except Exception as e:
            logger.error(f"获取授权状态失败: {e}")
            return {
                'is_licensed': False,
                'is_trial_expired': True,
                'remaining_days': 0,
                'trial_days': 0,
                'expire_date': None,
                'license_type': 'error'
            }

    def generate_unlock_code(self, customer_fingerprint: str, customer_id: str = "DEFAULT", unlock_type: str = "full", extend_days: Optional[int] = None) -> Dict:
        """
        生成解锁码（厂家端功能）

        Args:
            customer_fingerprint: 客户硬件指纹
            customer_id: 客户标识
            unlock_type: 解锁类型 ('full', 'trial_extend', 'temp')
            extend_days: 延长天数（仅用于trial_extend和temp类型）

        Returns:
            dict: 包含解锁码和相关信息的字典
        """
        try:
            # 验证输入参数
            if not customer_fingerprint:
                return {'success': False, 'message': '客户硬件指纹不能为空'}

            if unlock_type not in ['full', 'trial_extend', 'temp']:
                return {'success': False, 'message': '无效的解锁类型'}

            if unlock_type in ['trial_extend', 'temp'] and not extend_days:
                return {'success': False, 'message': '延长类型解锁码必须指定天数'}

            # 生成解锁码数据
            unlock_data = {
                'customer_fingerprint': customer_fingerprint,
                'customer_id': customer_id,
                'unlock_type': unlock_type,
                'extend_days': extend_days if extend_days else 0,
                'generate_date': datetime.now().isoformat(),
                'generator': 'factory_tool'
            }

            # 生成解锁码
            unlock_code = self._generate_unlock_code_string(unlock_data)

            # 记录生成日志
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'generate_unlock_code',
                'customer_id': customer_id,
                'unlock_type': unlock_type,
                'extend_days': extend_days,
                'customer_fingerprint': customer_fingerprint[:16] + '...',
                'unlock_code': unlock_code[:8] + '****'
            }
            self._log_operation(log_entry)

            logger.info(f"为客户 {customer_id} 生成{unlock_type}类型解锁码")

            return {
                'success': True,
                'unlock_code': unlock_code,
                'unlock_type': unlock_type,
                'customer_id': customer_id,
                'extend_days': extend_days,
                'message': f'成功生成{self._get_unlock_type_name(unlock_type)}解锁码'
            }

        except Exception as e:
            logger.error(f"生成解锁码失败: {e}")
            return {'success': False, 'message': f'生成解锁码失败: {e}'}

    def _generate_unlock_code_string(self, unlock_data: Dict) -> str:
        """
        生成解锁码字符串

        Args:
            unlock_data: 解锁数据

        Returns:
            解锁码字符串
        """
        try:
            # 第一段：硬件指纹校验码
            fingerprint_hash = hashlib.md5(unlock_data['customer_fingerprint'].encode()).hexdigest()[:8]

            # 第二段：解锁类型和天数
            type_code = {
                'full': 'FFFF',
                'trial_extend': f'T{unlock_data["extend_days"]:03d}',
                'temp': f'M{unlock_data["extend_days"]:03d}'
            }[unlock_data['unlock_type']]
            type_segment = f"{type_code}{'0' * (8 - len(type_code))}"[:8]

            # 第三段：客户ID和时间戳
            customer_hash = hashlib.md5(unlock_data['customer_id'].encode()).hexdigest()[:8]

            # 第四段：安全校验码
            verify_string = f"{fingerprint_hash}{type_segment}{customer_hash}{unlock_data['generate_date']}"
            verify_hash = hashlib.sha256(verify_string.encode()).hexdigest()[:8]

            # 组合解锁码
            unlock_code = f"{fingerprint_hash}-{type_segment}-{customer_hash}-{verify_hash}".upper()

            return unlock_code

        except Exception as e:
            logger.error(f"生成解锁码字符串失败: {e}")
            raise

    def _get_unlock_type_name(self, unlock_type: str) -> str:
        """获取解锁类型名称"""
        type_names = {
            'full': '永久授权',
            'trial_extend': '试用期延长',
            'temp': '临时授权'
        }
        return type_names.get(unlock_type, '未知类型')

    def _log_operation(self, log_entry: Dict) -> None:
        """记录操作日志"""
        try:
            log_file = os.path.join(os.path.dirname(self.license_file), 'license_operations.log')

            # 确保日志目录存在
            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            # 写入日志
            with open(log_file, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

        except Exception as e:
            logger.error(f"记录操作日志失败: {e}")

    def verify_unlock_code(self, unlock_code: str) -> Dict:
        """
        验证解锁码（新版本）

        Args:
            unlock_code: 解锁码

        Returns:
            验证结果字典
        """
        try:
            # 移除分隔符并转换为大写
            clean_code = unlock_code.replace("-", "").replace(" ", "").upper()

            if len(clean_code) != 32:
                return {'success': False, 'message': '解锁码格式错误'}

            # 分解解锁码
            fingerprint_part = clean_code[:8]
            type_part = clean_code[8:16]
            customer_part = clean_code[16:24]
            verify_part = clean_code[24:32]

            # 验证硬件指纹
            current_fingerprint = self.get_hardware_fingerprint()
            expected_fingerprint_hash = hashlib.md5(current_fingerprint.encode()).hexdigest()[:8].upper()

            if fingerprint_part != expected_fingerprint_hash:
                return {'success': False, 'message': '解锁码与当前设备不匹配'}

            # 解析解锁类型
            unlock_type = None
            extend_days = 0

            if type_part == 'FFFF0000':
                unlock_type = 'full'
            elif type_part.startswith('T'):
                unlock_type = 'trial_extend'
                try:
                    extend_days = int(type_part[1:4])
                except:
                    return {'success': False, 'message': '解锁码格式错误'}
            elif type_part.startswith('M'):
                unlock_type = 'temp'
                try:
                    extend_days = int(type_part[1:4])
                except:
                    return {'success': False, 'message': '解锁码格式错误'}
            else:
                return {'success': False, 'message': '不支持的解锁类型'}

            logger.info(f"解锁码验证成功，类型: {unlock_type}")

            return {
                'success': True,
                'unlock_type': unlock_type,
                'extend_days': extend_days,
                'message': f'解锁码验证成功 - {self._get_unlock_type_name(unlock_type)}'
            }

        except Exception as e:
            logger.error(f"验证解锁码失败: {e}")
            return {'success': False, 'message': f'验证解锁码失败: {e}'}

    def unlock_software(self, unlock_code: str, customer_id: str = "DEFAULT") -> Dict:
        """
        解锁软件（新版本）

        Args:
            unlock_code: 解锁码
            customer_id: 客户标识

        Returns:
            解锁结果字典
        """
        try:
            # 验证解锁码
            verify_result = self.verify_unlock_code(unlock_code)

            if not verify_result['success']:
                return verify_result

            unlock_type = verify_result['unlock_type']
            extend_days = verify_result.get('extend_days', 0)

            # 更新授权数据
            if self.license_data is None:
                self.license_data = {}

            if unlock_type == 'full':
                # 永久授权
                self.license_data.update({
                    'is_licensed': True,
                    'unlock_code': unlock_code,
                    'unlock_date': datetime.now().isoformat(),
                    'customer_id': customer_id,
                    'license_type': 'full'
                })
                message = "软件已永久解锁"

            elif unlock_type == 'trial_extend':
                # 延长试用期
                current_start = self.license_data.get('trial_start_date')
                if current_start:
                    # 从当前到期时间延长
                    current_days = self.license_data.get('trial_days', 30)
                    new_days = current_days + extend_days
                else:
                    # 重新开始试用期
                    new_days = extend_days
                    current_start = datetime.now().isoformat()

                self.license_data.update({
                    'is_licensed': False,
                    'trial_start_date': current_start,
                    'trial_days': new_days,
                    'license_type': 'trial',
                    'extend_unlock_code': unlock_code,
                    'extend_date': datetime.now().isoformat()
                })
                message = f"试用期已延长 {extend_days} 天"

            elif unlock_type == 'temp':
                # 临时授权
                self.license_data.update({
                    'is_licensed': True,
                    'unlock_code': unlock_code,
                    'unlock_date': datetime.now().isoformat(),
                    'customer_id': customer_id,
                    'license_type': 'temp',
                    'temp_days': extend_days,
                    'temp_expire_date': (datetime.now() + timedelta(days=extend_days)).isoformat()
                })
                message = f"获得 {extend_days} 天临时授权"

            self._save_license_data()

            # 记录解锁日志
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'action': 'unlock_software',
                'unlock_type': unlock_type,
                'extend_days': extend_days,
                'customer_id': customer_id,
                'unlock_code': unlock_code[:8] + '****'
            }
            self._log_operation(log_entry)

            logger.info(f"软件解锁成功: {message}")

            return {
                'success': True,
                'unlock_type': unlock_type,
                'message': message
            }

        except Exception as e:
            logger.error(f"解锁软件失败: {e}")
            return {'success': False, 'message': f'解锁软件失败: {e}'}

    def is_authorized(self) -> bool:
        """
        检查软件是否已授权（包括试用期内）

        Returns:
            是否已授权
        """
        try:
            status = self.get_license_status()

            # 已购买授权
            if status['is_licensed']:
                return True

            # 试用期内
            if not status['is_trial_expired']:
                return True

            # 试用期已过期且未购买
            return False

        except Exception as e:
            logger.error(f"检查授权状态失败: {e}")
            return False

    def get_hardware_fingerprint(self) -> str:
        """
        获取硬件指纹（用于生成解锁码）

        Returns:
            硬件指纹
        """
        return self.hardware_fingerprint or ""

    def check_license(self) -> Dict:
        """
        检查授权状态（标准化格式）

        Returns:
            标准化的授权状态信息
        """
        try:
            status = self.get_license_status()

            # 转换为标准化格式
            is_licensed = status.get('is_licensed', False)
            is_trial_expired = status.get('is_trial_expired', True)
            license_type = status.get('license_type', 'none')

            # 计算 is_valid：已授权或试用期内
            is_valid = is_licensed or not is_trial_expired

            # 计算 is_trial：未授权且有试用期数据
            is_trial = not is_licensed and license_type == 'trial'

            return {
                'is_valid': is_valid,
                'is_trial': is_trial,
                'is_expired': is_trial_expired and not is_licensed,
                'is_licensed': is_licensed,
                'remaining_days': status.get('remaining_days', 0),
                'trial_days': status.get('trial_days', 30),
                'expire_date': status.get('expire_date'),
                'license_type': license_type,
                'enabled_features': ['basic_test', 'data_export'] if is_valid else [],
                'last_check_time': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"检查授权状态失败: {e}")
            return {
                'is_valid': False,
                'is_trial': False,
                'is_expired': True,
                'is_licensed': False,
                'remaining_days': 0,
                'trial_days': 0,
                'expire_date': None,
                'license_type': 'error',
                'enabled_features': [],
                'last_check_time': datetime.now().isoformat(),
                'error': str(e)
            }

    # ==================== 试用期管理功能（开发/测试用） ====================

    def reset_trial_period(self, trial_days: int = 30, admin_password: Optional[str] = None) -> bool:
        """
        重置试用期（开发/测试功能）

        Args:
            trial_days: 新的试用天数
            admin_password: 管理员密码

        Returns:
            是否重置成功
        """
        try:
            # 验证管理员密码
            if not self._verify_admin_password(admin_password):
                logger.warning("试用期重置失败：管理员密码错误")
                return False

            # 验证试用天数范围
            if not (1 <= trial_days <= 365):
                logger.error(f"试用天数超出范围: {trial_days}")
                return False

            # 重置试用期数据
            self.license_data = {
                'is_licensed': False,
                'trial_start_date': datetime.now().isoformat(),
                'trial_days': trial_days,
                'unlock_code': None,
                'license_type': 'trial',
                'reset_count': self.license_data.get('reset_count', 0) + 1 if self.license_data else 1,
                'last_reset_time': datetime.now().isoformat()
            }

            self._save_license_data()
            logger.warning(f"试用期已重置为 {trial_days} 天（管理员操作）")
            return True

        except Exception as e:
            logger.error(f"重置试用期失败: {e}")
            return False

    def restore_trial_status(self, admin_password: Optional[str] = None) -> bool:
        """
        恢复试用状态（将已授权状态重置为试用状态）

        Args:
            admin_password: 管理员密码

        Returns:
            是否恢复成功
        """
        try:
            # 验证管理员密码
            if not self._verify_admin_password(admin_password):
                logger.warning("恢复试用状态失败：管理员密码错误")
                return False

            if self.license_data is None:
                logger.error("无授权数据，无法恢复试用状态")
                return False

            # 保存原始授权信息（用于审计）
            original_license = self.license_data.copy()

            # 恢复为试用状态
            trial_days = self.license_data.get('trial_days', 30)
            self.license_data.update({
                'is_licensed': False,
                'trial_start_date': datetime.now().isoformat(),
                'trial_days': trial_days,
                'license_type': 'trial',
                'restore_count': self.license_data.get('restore_count', 0) + 1,
                'last_restore_time': datetime.now().isoformat(),
                'original_license_backup': original_license  # 备份原始授权信息
            })

            self._save_license_data()
            logger.warning(f"已恢复试用状态，试用期 {trial_days} 天（管理员操作）")
            return True

        except Exception as e:
            logger.error(f"恢复试用状态失败: {e}")
            return False

    def set_trial_expire_soon(self, minutes: int = 1, admin_password: Optional[str] = None) -> bool:
        """
        设置试用期快速到期（测试功能）

        Args:
            minutes: 剩余分钟数（1-60）
            admin_password: 管理员密码

        Returns:
            是否设置成功
        """
        try:
            # 验证管理员密码
            if not self._verify_admin_password(admin_password):
                logger.warning("设置快速到期失败：管理员密码错误")
                return False

            # 验证分钟数范围
            if not (1 <= minutes <= 60):
                logger.error(f"分钟数超出范围: {minutes}")
                return False

            if self.license_data is None or self.license_data.get('is_licensed', False):
                logger.error("当前不在试用期，无法设置快速到期")
                return False

            # 计算新的开始时间，使得剩余时间为指定分钟数
            trial_days = self.license_data.get('trial_days', 30)
            new_start_time = datetime.now() - timedelta(days=trial_days) + timedelta(minutes=minutes)

            self.license_data.update({
                'trial_start_date': new_start_time.isoformat(),
                'quick_expire_test': True,
                'quick_expire_time': datetime.now().isoformat()
            })

            self._save_license_data()
            logger.warning(f"试用期设置为 {minutes} 分钟后到期（测试功能）")
            return True

        except Exception as e:
            logger.error(f"设置快速到期失败: {e}")
            return False

    def simulate_trial_expired(self) -> bool:
        """
        模拟试用期到期状态（不修改实际数据）

        Returns:
            是否模拟成功
        """
        try:
            # 这个方法只是标记模拟状态，实际的到期检查在get_license_status中处理
            self._simulated_expired = True
            logger.warning("已启用试用期到期模拟模式")
            return True

        except Exception as e:
            logger.error(f"模拟试用期到期失败: {e}")
            return False

    def clear_simulation_mode(self) -> bool:
        """
        清除模拟模式

        Returns:
            是否清除成功
        """
        try:
            self._simulated_expired = False
            logger.info("已清除试用期到期模拟模式")
            return True

        except Exception as e:
            logger.error(f"清除模拟模式失败: {e}")
            return False

    def _verify_admin_password(self, password: Optional[str]) -> bool:
        """
        验证管理员密码

        Args:
            password: 输入的密码

        Returns:
            是否验证通过
        """
        try:
            # 检查密码是否为空
            if password is None or password.strip() == "":
                return False

            # 获取管理员密码（从配置或默认值）
            admin_password = "JCY5001-ADMIN"  # 默认管理员密码
            if self.config_manager:
                admin_password = self.config_manager.get('security.admin_password', admin_password)

            # 简单的密码验证
            return password == admin_password

        except Exception as e:
            logger.error(f"验证管理员密码失败: {e}")
            return False

    def get_trial_management_info(self) -> Dict:
        """
        获取试用期管理信息

        Returns:
            试用期管理信息
        """
        try:
            if self.license_data is None:
                return {'error': '无授权数据'}

            return {
                'reset_count': self.license_data.get('reset_count', 0),
                'restore_count': self.license_data.get('restore_count', 0),
                'last_reset_time': self.license_data.get('last_reset_time'),
                'last_restore_time': self.license_data.get('last_restore_time'),
                'quick_expire_test': self.license_data.get('quick_expire_test', False),
                'quick_expire_time': self.license_data.get('quick_expire_time'),
                'has_backup': 'original_license_backup' in self.license_data,
                'simulated_expired': getattr(self, '_simulated_expired', False)
            }

        except Exception as e:
            logger.error(f"获取试用期管理信息失败: {e}")
            return {'error': str(e)}

    def unlock_with_code(self, unlock_code: str, customer_id: str = "DEFAULT") -> Dict:
        """
        使用解锁码解锁软件（标准化格式）

        Args:
            unlock_code: 解锁码
            customer_id: 客户标识

        Returns:
            解锁结果信息
        """
        try:
            result = self.unlock_software(unlock_code, customer_id)

            if result['success']:
                return {
                    'success': True,
                    'unlock_type': result.get('unlock_type'),
                    'message': result['message'],
                    'license_status': self.check_license()
                }
            else:
                return {
                    'success': False,
                    'message': result['message'],
                    'license_status': self.check_license()
                }

        except Exception as e:
            logger.error(f"解锁软件失败: {e}")
            return {
                'success': False,
                'message': f'解锁过程出错: {str(e)}',
                'license_status': self.check_license()
            }

    def reset_license(self) -> bool:
        """
        重置授权信息（仅用于测试）

        Returns:
            是否重置成功
        """
        try:
            if os.path.exists(self.license_file):
                os.remove(self.license_file)

            self.license_data = None
            logger.info("授权信息已重置")
            return True

        except Exception as e:
            logger.error(f"重置授权信息失败: {e}")
            return False
