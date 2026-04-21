"""
产品信息获取管理器

职责：
- 从产品设置中获取电池类型、电池规格
- 从批次信息中获取操作员信息
- 确保产品信息与当前批次信息保持一致
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ProductInfoManager:
    """
    产品信息获取管理器
    
    职责：
    - 获取电池类型和规格信息
    - 获取操作员信息
    - 确保信息的一致性和准确性
    """
    
    def __init__(self, config_manager):
        """
        初始化产品信息管理器
        
        Args:
            config_manager: 配置管理器
        """
        self.config_manager = config_manager
        
        logger.debug("产品信息获取管理器初始化完成")
    
    def get_battery_type(self) -> str:
        """
        获取电池类型
        
        Returns:
            电池类型字符串
        """
        try:
            # 优先从产品设置中获取
            battery_type = self.config_manager.get('product.battery_type', '')
            
            # 如果产品设置中没有，尝试从批次信息中获取
            if not battery_type:
                battery_type = self.config_manager.get('batch_info.cell_type', '')
            
            # 如果都没有，使用默认值
            if not battery_type:
                battery_type = '磷酸铁锂'
                logger.warning("未找到电池类型配置，使用默认值：磷酸铁锂")
            
            logger.debug(f"获取电池类型: {battery_type}")
            return battery_type
            
        except Exception as e:
            logger.error(f"获取电池类型失败: {e}")
            return '磷酸铁锂'
    
    def get_battery_spec(self) -> str:
        """
        获取电池规格
        
        Returns:
            电池规格字符串
        """
        try:
            # 优先从产品设置中获取
            battery_spec = self.config_manager.get('product.battery_spec', '')
            
            # 如果产品设置中没有，尝试从批次信息中获取
            if not battery_spec:
                battery_spec = self.config_manager.get('batch_info.cell_spec', '')
            
            # 如果都没有，使用默认值
            if not battery_spec:
                battery_spec = '21700'
                logger.warning("未找到电池规格配置，使用默认值：21700")
            
            logger.debug(f"获取电池规格: {battery_spec}")
            return battery_spec
            
        except Exception as e:
            logger.error(f"获取电池规格失败: {e}")
            return '21700'
    
    def get_operator(self) -> str:
        """
        获取操作员信息
        
        Returns:
            操作员姓名字符串
        """
        try:
            # 优先从批次信息中获取（最新的操作员信息）
            operator = self.config_manager.get('batch_info.operator', '')
            
            # 如果批次信息中没有，尝试从产品设置中获取
            if not operator:
                operator = self.config_manager.get('product.operator', '')
            
            # 如果都没有，使用默认值
            if not operator:
                operator = 'system'
                logger.warning("未找到操作员信息，使用默认值：system")
            
            logger.debug(f"获取操作员信息: {operator}")
            return operator
            
        except Exception as e:
            logger.error(f"获取操作员信息失败: {e}")
            return 'system'
    
    def get_standard_voltage(self) -> float:
        """
        获取标准电压
        
        Returns:
            标准电压值
        """
        try:
            # 从产品设置中获取标准电压
            standard_voltage = self.config_manager.get('product.standard_voltage', 3.2)
            
            logger.debug(f"获取标准电压: {standard_voltage}V")
            return float(standard_voltage)
            
        except Exception as e:
            logger.error(f"获取标准电压失败: {e}")
            return 3.2
    
    def get_standard_capacity(self) -> float:
        """
        获取标准容量
        
        Returns:
            标准容量值（转换为AH）
        """
        try:
            # 从产品设置中获取容量和单位
            capacity = self.config_manager.get('product.capacity', 3000)
            capacity_unit = self.config_manager.get('product.capacity_unit', 'mAh')
            
            # 转换为AH
            if capacity_unit.lower() == 'mah':
                capacity_ah = capacity / 1000.0
            elif capacity_unit.lower() == 'ah':
                capacity_ah = capacity
            else:
                # 默认按mAh处理
                capacity_ah = capacity / 1000.0
                logger.warning(f"未知容量单位：{capacity_unit}，按mAh处理")
            
            logger.debug(f"获取标准容量: {capacity_ah:.3f}AH（原始：{capacity}{capacity_unit}）")
            return capacity_ah
            
        except Exception as e:
            logger.error(f"获取标准容量失败: {e}")
            return 3.0
    
    def get_batch_number(self) -> str:
        """
        获取批次号

        Returns:
            批次号字符串
        """
        try:
            # 修复优先从产品设置中获取批次号
            batch_number = self.config_manager.get('product.batch_number', '')

            # 如果产品设置中没有，尝试从批次信息中获取
            if not batch_number:
                batch_number = self.config_manager.get('batch_info.batch_number', '')

            # 如果都没有，生成默认批次号
            if not batch_number:
                from datetime import datetime
                batch_number = f"BATCH-{datetime.now().strftime('%Y%m%d')}-001"
                logger.warning(f"未找到批次号，生成默认值：{batch_number}")

            logger.debug(f"获取批次号: {batch_number}")
            return batch_number

        except Exception as e:
            logger.error(f"获取批次号失败: {e}")
            return "BATCH-UNKNOWN"
    
    def get_manufacturer(self) -> str:
        """
        获取制造商信息

        Returns:
            制造商名称字符串
        """
        try:
            manufacturer = self.config_manager.get('product.manufacturer', '')
            logger.debug(f"获取制造商信息: {manufacturer}")
            return manufacturer

        except Exception as e:
            logger.error(f"获取制造商信息失败: {e}")
            return ''

    def get_complete_product_info(self) -> Dict[str, Any]:
        """
        获取完整的产品信息

        Returns:
            包含所有产品信息的字典
        """
        try:
            product_info = {
                'battery_type': self.get_battery_type(),
                'battery_spec': self.get_battery_spec(),
                'operator': self.get_operator(),
                'standard_voltage': self.get_standard_voltage(),
                'standard_capacity': self.get_standard_capacity(),
                'batch_number': self.get_batch_number(),
                'manufacturer': self.get_manufacturer()  # 新增制造商信息
            }

            logger.debug(f"获取完整产品信息: {product_info}")
            return product_info

        except Exception as e:
            logger.error(f"获取完整产品信息失败: {e}")
            return {
                'battery_type': '磷酸铁锂',
                'battery_spec': '21700',
                'operator': 'system',
                'standard_voltage': 3.2,
                'standard_capacity': 3.0,
                'batch_number': 'BATCH-UNKNOWN',
                'manufacturer': ''  # 新增默认制造商为空
            }
    
    def validate_product_info(self) -> Dict[str, bool]:
        """
        验证产品信息的完整性
        
        Returns:
            验证结果字典
        """
        try:
            validation_result = {
                'battery_type_valid': bool(self.config_manager.get('product.battery_type')),
                'battery_spec_valid': bool(self.config_manager.get('product.battery_spec')),
                'operator_valid': bool(self.config_manager.get('batch_info.operator') or 
                                     self.config_manager.get('product.operator')),
                'standard_voltage_valid': bool(self.config_manager.get('product.standard_voltage')),
                'standard_capacity_valid': bool(self.config_manager.get('product.capacity')),
                'batch_number_valid': bool(self.config_manager.get('batch_info.batch_number') or 
                                         self.config_manager.get('product.batch_number'))
            }
            
            # 计算总体有效性
            validation_result['overall_valid'] = all(validation_result.values())
            
            logger.debug(f"产品信息验证结果: {validation_result}")
            return validation_result
            
        except Exception as e:
            logger.error(f"验证产品信息失败: {e}")
            return {
                'battery_type_valid': False,
                'battery_spec_valid': False,
                'operator_valid': False,
                'standard_voltage_valid': False,
                'standard_capacity_valid': False,
                'batch_number_valid': False,
                'overall_valid': False
            }
    
    def sync_product_info_to_batch(self):
        """
        同步产品信息到批次信息（确保一致性）
        """
        try:
            # 获取产品信息
            battery_type = self.config_manager.get('product.battery_type')
            battery_spec = self.config_manager.get('product.battery_spec')
            operator = self.config_manager.get('product.operator')
            batch_number = self.config_manager.get('product.batch_number')
            
            # 同步到批次信息
            if battery_type:
                self.config_manager.set('batch_info.cell_type', battery_type)
            
            if battery_spec:
                self.config_manager.set('batch_info.cell_spec', battery_spec)
            
            if operator:
                self.config_manager.set('batch_info.operator', operator)
            
            if batch_number:
                self.config_manager.set('batch_info.batch_number', batch_number)
            
            logger.debug("产品信息已同步到批次信息")
            
        except Exception as e:
            logger.error(f"同步产品信息到批次信息失败: {e}")
    
    def cleanup(self):
        """清理资源"""
        try:
            logger.debug("产品信息获取管理器资源清理完成")
            
        except Exception as e:
            logger.error(f"产品信息获取管理器清理失败: {e}")
