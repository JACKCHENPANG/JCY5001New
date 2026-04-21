#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
序列号优化器

负责优化序列号存储和管理，减少启动时的性能影响

Author: Jack
Date: 2025-06-20
"""

import logging
import json
import os
from datetime import datetime, timedelta
from typing import Set, List, Dict, Any

logger = logging.getLogger(__name__)


class SerialNumberOptimizer:
    """序列号优化器"""
    
    def __init__(self, config_manager):
        """
        初始化序列号优化器
        
        Args:
            config_manager: 配置管理器实例
        """
        self.config_manager = config_manager
        
    def optimize_serial_storage(self) -> Dict[str, Any]:
        """
        优化序列号存储
        
        Returns:
            优化结果统计
        """
        try:
            logger.info("🔄 开始优化序列号存储...")
            
            # 获取当前已使用的序列号列表
            used_list = self.config_manager.get('serial_numbers.used_list', [])
            original_count = len(used_list)
            
            
            if original_count == 0:
                logger.info("✅ 没有序列号需要优化")
                return {
                    'original_count': 0,
                    'optimized_count': 0,
                    'removed_count': 0,
                    'optimization_applied': False
                }
            
            # 应用优化策略
            optimized_list = self._apply_optimization_strategies(used_list)
            optimized_count = len(optimized_list)
            removed_count = original_count - optimized_count
            
            # 更新配置
            if removed_count > 0:
                self.config_manager.set('serial_numbers.used_list', optimized_list, emit_signal=False)
                logger.info(f"✅ 序列号优化完成: 原始{original_count}个 -> 优化后{optimized_count}个 (清理{removed_count}个)")
                
                # 创建备份
                self._create_backup(used_list)
                
                return {
                    'original_count': original_count,
                    'optimized_count': optimized_count,
                    'removed_count': removed_count,
                    'optimization_applied': True
                }
            else:
                logger.info("✅ 序列号已经是最优状态，无需优化")
                return {
                    'original_count': original_count,
                    'optimized_count': optimized_count,
                    'removed_count': 0,
                    'optimization_applied': False
                }
                
        except Exception as e:
            logger.error(f"❌ 序列号优化失败: {e}")
            return {
                'original_count': 0,
                'optimized_count': 0,
                'removed_count': 0,
                'optimization_applied': False,
                'error': str(e)
            }
    
    def _apply_optimization_strategies(self, used_list: List[str]) -> List[str]:
        """
        应用优化策略
        
        Args:
            used_list: 原始序列号列表
            
        Returns:
            优化后的序列号列表
        """
        try:
            # 策略1: 去重
            unique_serials = list(set(used_list))
            logger.info(f"📝 去重后: {len(unique_serials)}个序列号")
            
            # 策略2: 移除明显无效的序列号
            valid_serials = self._remove_invalid_serials(unique_serials)
            logger.info(f"📝 移除无效序列号后: {len(valid_serials)}个序列号")
            
            # 策略3: 保留最近的序列号（基于日期）
            recent_serials = self._keep_recent_serials(valid_serials)
            logger.info(f"📝 保留最近序列号后: {len(recent_serials)}个序列号")
            
            # 策略4: 限制总数量
            limited_serials = self._limit_total_count(recent_serials)
            logger.info(f"📝 限制总数量后: {len(limited_serials)}个序列号")
            
            return limited_serials
            
        except Exception as e:
            logger.error(f"❌ 应用优化策略失败: {e}")
            return used_list
    
    def _remove_invalid_serials(self, serials: List[str]) -> List[str]:
        """
        移除明显无效的序列号
        
        Args:
            serials: 序列号列表
            
        Returns:
            有效的序列号列表
        """
        valid_serials = []
        invalid_count = 0
        
        for serial in serials:
            # 检查基本有效性
            if self._is_valid_serial_format(serial):
                valid_serials.append(serial)
            else:
                invalid_count += 1
                logger.debug(f"🗑️ 移除无效序列号: {serial}")
        
        if invalid_count > 0:
            logger.info(f"🗑️ 移除了 {invalid_count} 个无效序列号")
        
        return valid_serials
    
    def _is_valid_serial_format(self, serial: str) -> bool:
        """
        检查序列号格式是否有效
        
        Args:
            serial: 序列号
            
        Returns:
            是否有效
        """
        if not serial or not serial.strip():
            return False
        
        serial = serial.strip()
        
        # 长度检查
        if len(serial) < 5 or len(serial) > 50:
            return False
        
        # 排除明显错误的序列号
        invalid_patterns = [
            'JCY-2025060-',  # 不完整的序列号
            'JCY-2025060SYSTEM-',  # 系统错误
            'JCY-2025060WIN3-',  # 系统错误
            'JCY-2025060⬇️-500',  # 包含特殊字符
            '098-089-',  # 不完整
            '60CF84ECB65504202505291505011',  # 过长的无效序列号
            '60CF84ECB6550420250529F209484',  # 过长的无效序列号
        ]
        
        for pattern in invalid_patterns:
            if pattern in serial:
                return False
        
        # 检查是否只包含数字（可能是错误输入）
        if serial.isdigit() and len(serial) < 10:
            return False
        
        return True
    
    def _keep_recent_serials(self, serials: List[str], days: int = 90) -> List[str]:
        """
        保留最近指定天数内的序列号
        
        Args:
            serials: 序列号列表
            days: 保留天数
            
        Returns:
            最近的序列号列表
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            recent_serials = []
            old_count = 0
            
            for serial in serials:
                serial_date = self._extract_date_from_serial(serial)
                if serial_date and serial_date >= cutoff_date:
                    recent_serials.append(serial)
                elif not serial_date:
                    # 无法提取日期的序列号保留（可能是特殊格式）
                    recent_serials.append(serial)
                else:
                    old_count += 1
            
            if old_count > 0:
                logger.info(f"🗑️ 移除了 {old_count} 个超过{days}天的旧序列号")
            
            return recent_serials
            
        except Exception as e:
            logger.error(f"❌ 保留最近序列号失败: {e}")
            return serials
    
    def _extract_date_from_serial(self, serial: str) -> datetime:
        """
        从序列号中提取日期
        
        Args:
            serial: 序列号
            
        Returns:
            提取的日期，如果无法提取则返回None
        """
        try:
            # 尝试匹配 JCY-YYYYMMDD-XXXX 格式
            if '-' in serial:
                parts = serial.split('-')
                if len(parts) >= 2:
                    date_part = parts[1]
                    if len(date_part) == 8 and date_part.isdigit():
                        year = int(date_part[:4])
                        month = int(date_part[4:6])
                        day = int(date_part[6:8])
                        return datetime(year, month, day)
            
            # 尝试匹配 BAT-YYYYMMDD-XXXX 格式
            if serial.startswith('BAT-') and '-' in serial:
                parts = serial.split('-')
                if len(parts) >= 2:
                    date_part = parts[1]
                    if len(date_part) == 8 and date_part.isdigit():
                        year = int(date_part[:4])
                        month = int(date_part[4:6])
                        day = int(date_part[6:8])
                        return datetime(year, month, day)
            
            return None
            
        except Exception:
            return None
    
    def _limit_total_count(self, serials: List[str], max_count: int = 1000) -> List[str]:
        """
        限制序列号总数量
        
        Args:
            serials: 序列号列表
            max_count: 最大数量
            
        Returns:
            限制后的序列号列表
        """
        if len(serials) <= max_count:
            return serials
        
        # 按日期排序，保留最新的
        dated_serials = []
        undated_serials = []
        
        for serial in serials:
            serial_date = self._extract_date_from_serial(serial)
            if serial_date:
                dated_serials.append((serial, serial_date))
            else:
                undated_serials.append(serial)
        
        # 按日期降序排序
        dated_serials.sort(key=lambda x: x[1], reverse=True)
        
        # 保留最新的序列号
        keep_dated_count = min(max_count - len(undated_serials), len(dated_serials))
        if keep_dated_count < 0:
            keep_dated_count = 0
            undated_serials = undated_serials[:max_count]
        
        result = [item[0] for item in dated_serials[:keep_dated_count]] + undated_serials
        
        removed_count = len(serials) - len(result)
        if removed_count > 0:
            logger.info(f"🗑️ 为控制总数量，移除了 {removed_count} 个较旧的序列号")
        
        return result
    
    def _create_backup(self, original_list: List[str]):
        """
        创建原始序列号列表的备份
        
        Args:
            original_list: 原始序列号列表
        """
        try:
            backup_dir = "backup/serial_numbers"
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"used_serials_backup_{timestamp}.json")
            
            backup_data = {
                'timestamp': timestamp,
                'count': len(original_list),
                'serials': original_list
            }
            
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 序列号备份已创建: {backup_file}")
            
        except Exception as e:
            logger.error(f"❌ 创建序列号备份失败: {e}")
    
    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """
        获取优化建议
        
        Returns:
            优化建议
        """
        try:
            used_list = self.config_manager.get('serial_numbers.used_list', [])
            count = len(used_list)
            
            recommendations = {
                'current_count': count,
                'recommendations': []
            }
            
            if count > 2000:
                recommendations['recommendations'].append({
                    'level': 'high',
                    'message': f'序列号数量过多({count}个)，建议立即优化以提升启动性能',
                    'action': 'immediate_optimization'
                })
            elif count > 1000:
                recommendations['recommendations'].append({
                    'level': 'medium',
                    'message': f'序列号数量较多({count}个)，建议定期优化',
                    'action': 'scheduled_optimization'
                })
            elif count > 500:
                recommendations['recommendations'].append({
                    'level': 'low',
                    'message': f'序列号数量适中({count}个)，可考虑优化',
                    'action': 'optional_optimization'
                })
            else:
                recommendations['recommendations'].append({
                    'level': 'info',
                    'message': f'序列号数量正常({count}个)，无需优化',
                    'action': 'no_action'
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ 获取优化建议失败: {e}")
            return {
                'current_count': 0,
                'recommendations': [{
                    'level': 'error',
                    'message': f'获取建议失败: {e}',
                    'action': 'check_error'
                }]
            }


def optimize_serial_numbers(config_manager) -> Dict[str, Any]:
    """
    优化序列号存储的便捷函数
    
    Args:
        config_manager: 配置管理器
        
    Returns:
        优化结果
    """
    optimizer = SerialNumberOptimizer(config_manager)
    return optimizer.optimize_serial_storage()


def get_serial_optimization_recommendations(config_manager) -> Dict[str, Any]:
    """
    获取序列号优化建议的便捷函数
    
    Args:
        config_manager: 配置管理器
        
    Returns:
        优化建议
    """
    optimizer = SerialNumberOptimizer(config_manager)
    return optimizer.get_optimization_recommendations()
