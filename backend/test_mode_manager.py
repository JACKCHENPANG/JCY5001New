"""
测试模式识别管理器

职责：
- 识别当前的测试模式
- 区分增强模式、连续模式、单次模式
- 提供测试模式的详细描述
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class TestModeManager:
    """
    测试模式识别管理器
    
    职责：
    - 识别和记录测试模式
    - 区分不同的测试模式类型
    - 提供测试模式的详细信息
    """
    
    def __init__(self, config_manager):
        """
        初始化测试模式管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        
        logger.debug("测试模式识别管理器初始化完成")
    
    def get_current_test_mode(self) -> str:
        """
        获取当前测试模式
        
        Returns:
            测试模式描述字符串
        """
        try:
            # 获取配置信息
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            auto_detect = self.config_manager.get('test.auto_detect', True)
            use_parallel_staggered = self.config_manager.get('test.use_parallel_staggered_mode', False)
            test_mode = self.config_manager.get('test_params.test_mode', 'simultaneous')
            
            # 判断测试模式优先级
            # 1. 首先判断是否为连续模式
            if continuous_mode:
                if use_parallel_staggered or test_mode == 'staggered':
                    return "连续增强模式"
                else:
                    return "连续模式"
            
            # 2. 判断是否为增强模式（并行错频）
            if use_parallel_staggered or test_mode == 'staggered':
                if auto_detect:
                    return "自动增强模式"
                else:
                    return "增强模式"
            
            # 3. 判断是否为自动检测模式
            if auto_detect and not continuous_mode:
                return "自动模式"
            
            # 4. 默认为单次模式
            return "单次模式"
            
        except Exception as e:
            logger.error(f"获取当前测试模式失败: {e}")
            return "未知模式"
    
    def get_test_mode_details(self) -> Dict[str, Any]:
        """
        获取测试模式的详细信息
        
        Returns:
            包含测试模式详细信息的字典
        """
        try:
            # 获取配置信息
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            auto_detect = self.config_manager.get('test.auto_detect', True)
            use_parallel_staggered = self.config_manager.get('test.use_parallel_staggered_mode', False)
            test_mode = self.config_manager.get('test_params.test_mode', 'simultaneous')
            
            # 获取连续模式相关配置
            continuous_delay = self.config_manager.get('test.continuous_mode_delay', 2.0)
            count_limit_enabled = self.config_manager.get('test.count_limit_enabled', False)
            max_count = self.config_manager.get('test.max_count', 100)
            
            # 获取并行错频相关配置
            critical_frequency = self.config_manager.get('test.critical_frequency', 15.0)
            
            # 构建详细信息
            details = {
                'mode_name': self.get_current_test_mode(),
                'continuous_mode': continuous_mode,
                'auto_detect': auto_detect,
                'use_parallel_staggered': use_parallel_staggered,
                'test_mode': test_mode,
                'features': []
            }
            
            # 添加功能特性描述
            if continuous_mode:
                details['features'].append(f"连续测试（间隔{continuous_delay:.1f}秒）")
                if count_limit_enabled:
                    details['features'].append(f"限制次数（最多{max_count}次）")
                else:
                    details['features'].append("无限次数")
            
            if use_parallel_staggered or test_mode == 'staggered':
                details['features'].append(f"并行错频（临界频率{critical_frequency:.1f}Hz）")
            
            if auto_detect and not continuous_mode:
                details['features'].append("自动电池检测")
            
            # 添加配置摘要
            details['config_summary'] = {
                'continuous_delay': continuous_delay,
                'max_count': max_count if count_limit_enabled else None,
                'critical_frequency': critical_frequency,
                'count_limit_enabled': count_limit_enabled
            }
            
            return details
            
        except Exception as e:
            logger.error(f"获取测试模式详细信息失败: {e}")
            return {
                'mode_name': '未知模式',
                'continuous_mode': False,
                'auto_detect': False,
                'use_parallel_staggered': False,
                'test_mode': 'unknown',
                'features': ['获取信息失败'],
                'config_summary': {}
            }
    
    def get_mode_description_for_database(self) -> str:
        """
        获取用于数据库存储的测试模式描述
        
        Returns:
            简洁的测试模式描述，适合数据库存储
        """
        try:
            mode_name = self.get_current_test_mode()
            
            # 根据模式名称返回标准化的描述
            mode_mapping = {
                "连续增强模式": "连续增强模式",
                "连续模式": "连续模式", 
                "自动增强模式": "自动增强模式",
                "增强模式": "增强模式",
                "自动模式": "自动模式",
                "单次模式": "单次模式"
            }
            
            return mode_mapping.get(mode_name, mode_name)
            
        except Exception as e:
            logger.error(f"获取数据库测试模式描述失败: {e}")
            return "未知模式"
    
    def is_enhanced_mode(self) -> bool:
        """
        判断是否为增强模式（并行错频）
        
        Returns:
            是否为增强模式
        """
        try:
            use_parallel_staggered = self.config_manager.get('test.use_parallel_staggered_mode', False)
            test_mode = self.config_manager.get('test_params.test_mode', 'simultaneous')
            
            return use_parallel_staggered or test_mode == 'staggered'
            
        except Exception as e:
            logger.error(f"判断增强模式失败: {e}")
            return False
    
    def is_continuous_mode(self) -> bool:
        """
        判断是否为连续模式
        
        Returns:
            是否为连续模式
        """
        try:
            return self.config_manager.get('test.continuous_mode', False)
            
        except Exception as e:
            logger.error(f"判断连续模式失败: {e}")
            return False
    
    def is_auto_detect_mode(self) -> bool:
        """
        判断是否为自动检测模式
        
        Returns:
            是否为自动检测模式
        """
        try:
            auto_detect = self.config_manager.get('test.auto_detect', False)  # 修复：默认值改为False，与屏蔽状态一致
            continuous_mode = self.config_manager.get('test.continuous_mode', False)
            
            # 自动检测模式：启用自动检测且不是连续模式
            return auto_detect and not continuous_mode
            
        except Exception as e:
            logger.error(f"判断自动检测模式失败: {e}")
            return False
    
    def get_mode_priority_info(self) -> Dict[str, Any]:
        """
        获取模式优先级信息（用于调试和日志）
        
        Returns:
            模式优先级信息字典
        """
        try:
            return {
                'continuous_mode': self.is_continuous_mode(),
                'enhanced_mode': self.is_enhanced_mode(),
                'auto_detect_mode': self.is_auto_detect_mode(),
                'final_mode': self.get_current_test_mode(),
                'priority_order': [
                    '1. 连续模式检查',
                    '2. 增强模式检查',
                    '3. 自动检测模式检查',
                    '4. 默认单次模式'
                ]
            }
            
        except Exception as e:
            logger.error(f"获取模式优先级信息失败: {e}")
            return {'error': str(e)}
    
    def cleanup(self):
        """清理资源"""
        try:
            logger.debug("测试模式识别管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"测试模式识别管理器清理失败: {e}")
