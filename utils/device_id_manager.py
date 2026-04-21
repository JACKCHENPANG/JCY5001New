#!/usr/bin/env python3
"""
统一设备ID管理器
解决重复设备ID上传的问题
"""

import os
import platform
import hashlib
import uuid
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class DeviceIDManager:
    """统一设备ID管理器 - 单例模式"""
    
    _instance = None
    _lock = threading.Lock()
    _device_id = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._cache_file = os.path.join(os.path.expanduser("~"), ".jcy5001_device_id")
            logger.info("设备ID管理器已初始化")
    
    def get_device_id(self) -> str:
        """获取统一的设备ID"""
        if self._device_id is not None:
            return self._device_id
        
        with self._lock:
            if self._device_id is not None:
                return self._device_id
            
            # 1. 首先尝试从缓存文件读取
            cached_id = self._get_cached_device_id()
            if cached_id:
                logger.info(f"使用缓存的设备ID: {cached_id[:16]}...")
                self._device_id = cached_id
                return self._device_id
            
            # 2. 尝试从license_manager获取硬件指纹
            fingerprint = self._get_hardware_fingerprint_from_license()
            if fingerprint:
                logger.info(f"使用硬件指纹作为设备ID: {fingerprint[:16]}...")
                self._device_id = fingerprint
                self._cache_device_id(fingerprint)
                return self._device_id
            
            # 3. 生成备选硬件指纹
            fingerprint = self._generate_hardware_fingerprint()
            logger.info(f"生成硬件指纹作为设备ID: {fingerprint[:16]}...")
            self._device_id = fingerprint
            self._cache_device_id(fingerprint)
            return self._device_id
    
    def _get_cached_device_id(self) -> Optional[str]:
        """从缓存文件获取设备ID"""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r', encoding='utf-8') as f:
                    device_id = f.read().strip()
                    if device_id and len(device_id) > 10:  # 基本验证
                        return device_id
        except Exception as e:
            logger.debug(f"读取缓存设备ID失败: {e}")
        return None
    
    def _cache_device_id(self, device_id: str):
        """缓存设备ID到文件"""
        try:
            with open(self._cache_file, 'w', encoding='utf-8') as f:
                f.write(device_id)
            logger.debug(f"设备ID已缓存: {device_id[:16]}...")
        except Exception as e:
            logger.debug(f"缓存设备ID失败: {e}")
    
    def _get_hardware_fingerprint_from_license(self) -> Optional[str]:
        """从license_manager获取硬件指纹"""
        try:
            from utils.license_manager import LicenseManager
            license_manager = LicenseManager()
            fingerprint = license_manager.get_hardware_fingerprint()
            return fingerprint if fingerprint else None
        except Exception as e:
            logger.debug(f"无法从license_manager获取硬件指纹: {e}")
            return None
    
    def _generate_hardware_fingerprint(self) -> str:
        """生成稳定的硬件指纹"""
        try:
            fingerprint_data = []
            
            # 1. 计算机名
            fingerprint_data.append(f"NODE:{platform.node()}")
            
            # 2. MAC地址
            try:
                mac = ':'.join(['{:02x}'.format((uuid.getnode() >> elements) & 0xff)
                               for elements in range(0, 2*6, 2)][::-1])
                fingerprint_data.append(f"MAC:{mac}")
            except:
                pass
            
            # 3. 系统信息
            fingerprint_data.append(f"OS:{platform.system()}")
            fingerprint_data.append(f"ARCH:{platform.machine()}")
            
            # 4. 确保排序以保证稳定性
            fingerprint_str = "|".join(sorted(fingerprint_data))
            hardware_fingerprint = hashlib.sha256(fingerprint_str.encode()).hexdigest()
            
            return hardware_fingerprint
            
        except Exception as e:
            logger.error(f"生成硬件指纹失败: {e}")
            # 最终备选方案
            fallback_id = f"JCY5001A_{platform.node()}"
            logger.warning(f"使用备选设备ID: {fallback_id}")
            return fallback_id
    
    def get_device_short_id(self, length: int = 8) -> str:
        """获取设备ID的短版本"""
        device_id = self.get_device_id()
        return device_id[:length]
    
    def clear_cache(self):
        """清除缓存的设备ID（用于测试或重置）"""
        try:
            if os.path.exists(self._cache_file):
                os.remove(self._cache_file)
            self._device_id = None
            logger.info("设备ID缓存已清除")
        except Exception as e:
            logger.error(f"清除设备ID缓存失败: {e}")
    
    def get_device_info(self) -> dict:
        """获取设备信息"""
        device_id = self.get_device_id()
        return {
            'device_id': device_id,
            'device_short_id': device_id[:8],
            'node_name': platform.node(),
            'system': platform.system(),
            'architecture': platform.machine(),
            'cache_file': self._cache_file,
            'cached': os.path.exists(self._cache_file)
        }


# 全局单例实例
device_id_manager = DeviceIDManager()


def get_device_id() -> str:
    """获取统一的设备ID - 便捷函数"""
    return device_id_manager.get_device_id()


def get_device_short_id(length: int = 8) -> str:
    """获取设备ID的短版本 - 便捷函数"""
    return device_id_manager.get_device_short_id(length)


def get_device_info() -> dict:
    """获取设备信息 - 便捷函数"""
    return device_id_manager.get_device_info()


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)
    
    print("=== 设备ID管理器测试 ===")
    
    # 测试获取设备ID
    device_id = get_device_id()
    print(f"设备ID: {device_id}")
    print(f"短设备ID: {get_device_short_id()}")
    
    # 测试设备信息
    info = get_device_info()
    print(f"设备信息: {info}")
    
    # 测试多次调用的一致性
    device_id2 = get_device_id()
    print(f"一致性检查: {device_id == device_id2}")
