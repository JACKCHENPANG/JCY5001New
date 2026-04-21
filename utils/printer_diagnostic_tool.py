"""
打印机诊断工具
用于诊断和修复打印机连接问题，特别是更换打印机后的配置问题
"""

import logging
import json
import win32print
import win32ui
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class PrinterDiagnosticTool:
    """打印机诊断工具"""
    
    def __init__(self, config_manager: ConfigManager = None):
        """
        初始化诊断工具
        
        Args:
            config_manager: 配置管理器，如果为None则创建新实例
        """
        self.config_manager = config_manager or ConfigManager()
        self.diagnostic_results = {}
        
    def run_full_diagnostic(self) -> Dict[str, Any]:
        """
        运行完整的打印机诊断
        
        Returns:
            诊断结果字典
        """
        logger.info("开始打印机诊断...")
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'system_printers': self._detect_system_printers(),
            'configured_printer': self._check_configured_printer(),
            'niimbot_printers': self._detect_niimbot_printers(),
            'printer_status': self._check_printer_status(),
            'recommendations': []
        }
        
        # 生成修复建议
        results['recommendations'] = self._generate_recommendations(results)
        
        self.diagnostic_results = results
        logger.info("打印机诊断完成")
        
        return results
    
    def _detect_system_printers(self) -> List[Dict[str, Any]]:
        """检测系统中所有打印机"""
        try:
            printers = []
            printer_list = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            
            for printer_info in printer_list:
                printer_name = printer_info[2]
                
                try:
                    # 获取打印机详细信息
                    handle = win32print.OpenPrinter(printer_name)
                    printer_details = win32print.GetPrinter(handle, 2)
                    win32print.ClosePrinter(handle)
                    
                    printer_data = {
                        'name': printer_name,
                        'status': printer_details.get('Status', 0),
                        'attributes': printer_details.get('Attributes', 0),
                        'driver_name': printer_details.get('pDriverName', 'Unknown'),
                        'port_name': printer_details.get('pPortName', 'Unknown'),
                        'is_niimbot': 'NIIMBOT' in printer_name.upper() or 'K3_W' in printer_name.upper(),
                        'is_available': self._test_printer_availability(printer_name)
                    }
                    
                    printers.append(printer_data)
                    logger.debug(f"发现打印机: {printer_name}")
                    
                except Exception as e:
                    logger.warning(f"获取打印机 {printer_name} 详细信息失败: {e}")
                    printers.append({
                        'name': printer_name,
                        'status': 'unknown',
                        'error': str(e),
                        'is_niimbot': 'NIIMBOT' in printer_name.upper() or 'K3_W' in printer_name.upper(),
                        'is_available': False
                    })
            
            logger.info(f"检测到 {len(printers)} 台打印机")
            return printers
            
        except Exception as e:
            logger.error(f"检测系统打印机失败: {e}")
            return []
    
    def _check_configured_printer(self) -> Dict[str, Any]:
        """检查配置的打印机"""
        configured_name = self.config_manager.get('printer.name', '')
        
        result = {
            'configured_name': configured_name,
            'exists': False,
            'is_available': False,
            'status': 'not_configured' if not configured_name else 'unknown'
        }
        
        if configured_name:
            try:
                # 检查配置的打印机是否存在
                handle = win32print.OpenPrinter(configured_name)
                printer_info = win32print.GetPrinter(handle, 2)
                win32print.ClosePrinter(handle)
                
                result.update({
                    'exists': True,
                    'is_available': self._test_printer_availability(configured_name),
                    'status': printer_info.get('Status', 0),
                    'driver_name': printer_info.get('pDriverName', 'Unknown'),
                    'port_name': printer_info.get('pPortName', 'Unknown')
                })
                
            except Exception as e:
                result.update({
                    'exists': False,
                    'error': str(e),
                    'status': 'not_found'
                })
                logger.warning(f"配置的打印机 {configured_name} 不可用: {e}")
        
        return result
    
    def _detect_niimbot_printers(self) -> List[Dict[str, Any]]:
        """专门检测NIIMBOT打印机"""
        niimbot_printers = []
        
        try:
            printer_list = win32print.EnumPrinters(
                win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
            )
            
            for printer_info in printer_list:
                printer_name = printer_info[2]
                
                if 'NIIMBOT' in printer_name.upper() or 'K3_W' in printer_name.upper():
                    try:
                        handle = win32print.OpenPrinter(printer_name)
                        printer_details = win32print.GetPrinter(handle, 2)
                        win32print.ClosePrinter(handle)
                        
                        niimbot_data = {
                            'name': printer_name,
                            'status': printer_details.get('Status', 0),
                            'attributes': printer_details.get('Attributes', 0),
                            'driver_name': printer_details.get('pDriverName', 'Unknown'),
                            'port_name': printer_details.get('pPortName', 'Unknown'),
                            'is_available': self._test_niimbot_availability(
                                printer_name, 
                                printer_details.get('Status', 0),
                                printer_details.get('Attributes', 0)
                            ),
                            'recommended': True  # NIIMBOT打印机是推荐的
                        }
                        
                        niimbot_printers.append(niimbot_data)
                        logger.info(f"发现NIIMBOT打印机: {printer_name}")
                        
                    except Exception as e:
                        logger.warning(f"检查NIIMBOT打印机 {printer_name} 失败: {e}")
            
        except Exception as e:
            logger.error(f"检测NIIMBOT打印机失败: {e}")
        
        return niimbot_printers
    
    def _test_printer_availability(self, printer_name: str) -> bool:
        """测试打印机可用性"""
        try:
            handle = win32print.OpenPrinter(printer_name)
            printer_info = win32print.GetPrinter(handle, 2)
            win32print.ClosePrinter(handle)
            
            status = printer_info.get('Status', 0)
            
            # 针对NIIMBOT打印机的特殊检查
            if 'NIIMBOT' in printer_name.upper() or 'K3_W' in printer_name.upper():
                return self._test_niimbot_availability(
                    printer_name, 
                    status, 
                    printer_info.get('Attributes', 0)
                )
            else:
                # 通用打印机检查
                return status == 0 or (status & 0x00000001) == 0
                
        except Exception as e:
            logger.debug(f"测试打印机 {printer_name} 可用性失败: {e}")
            return False
    
    def _test_niimbot_availability(self, printer_name: str, status: int, attributes: int) -> bool:
        """测试NIIMBOT打印机可用性"""
        try:
            # NIIMBOT打印机状态检查逻辑
            if status == 0:
                return True  # 完全正常状态
            elif status == 0x00000020:
                return True  # 手动进纸状态，打印机在线
            elif status == 0x00000040:
                return True  # 缺纸状态，打印机在线但缺纸
            else:
                return False  # 其他状态认为不可用
                
        except Exception as e:
            logger.error(f"检查NIIMBOT打印机 {printer_name} 可用性失败: {e}")
            return False
    
    def _check_printer_status(self) -> Dict[str, Any]:
        """检查打印机整体状态"""
        system_printers = self.diagnostic_results.get('system_printers', [])
        configured_printer = self.diagnostic_results.get('configured_printer', {})
        niimbot_printers = self.diagnostic_results.get('niimbot_printers', [])
        
        available_printers = [p for p in system_printers if p.get('is_available', False)]
        available_niimbot = [p for p in niimbot_printers if p.get('is_available', False)]
        
        return {
            'total_printers': len(system_printers),
            'available_printers': len(available_printers),
            'niimbot_count': len(niimbot_printers),
            'available_niimbot': len(available_niimbot),
            'configured_available': configured_printer.get('is_available', False),
            'has_working_printer': len(available_printers) > 0,
            'has_working_niimbot': len(available_niimbot) > 0
        }
    
    def _generate_recommendations(self, results: Dict[str, Any]) -> List[Dict[str, str]]:
        """生成修复建议"""
        recommendations = []
        
        system_printers = results.get('system_printers', [])
        configured_printer = results.get('configured_printer', {})
        niimbot_printers = results.get('niimbot_printers', [])
        printer_status = results.get('printer_status', {})
        
        # 检查是否有可用的打印机
        if not printer_status.get('has_working_printer', False):
            recommendations.append({
                'level': 'error',
                'title': '没有可用的打印机',
                'description': '系统中没有检测到可用的打印机，请检查打印机连接和驱动程序',
                'action': 'check_connection_and_driver'
            })
        
        # 检查配置的打印机
        if not configured_printer.get('exists', False):
            if configured_printer.get('configured_name'):
                recommendations.append({
                    'level': 'error',
                    'title': '配置的打印机不存在',
                    'description': f"配置的打印机 '{configured_printer['configured_name']}' 在系统中不存在",
                    'action': 'update_printer_config'
                })
            else:
                recommendations.append({
                    'level': 'warning',
                    'title': '未配置打印机',
                    'description': '系统中没有配置打印机，需要选择一台可用的打印机',
                    'action': 'configure_printer'
                })
        
        elif not configured_printer.get('is_available', False):
            recommendations.append({
                'level': 'warning',
                'title': '配置的打印机不可用',
                'description': f"配置的打印机 '{configured_printer['configured_name']}' 存在但不可用",
                'action': 'check_printer_status'
            })
        
        # 推荐NIIMBOT打印机
        if printer_status.get('has_working_niimbot', False):
            available_niimbot = [p for p in niimbot_printers if p.get('is_available', False)]
            if available_niimbot:
                best_niimbot = available_niimbot[0]
                if configured_printer.get('configured_name') != best_niimbot['name']:
                    recommendations.append({
                        'level': 'info',
                        'title': '推荐使用NIIMBOT打印机',
                        'description': f"发现可用的NIIMBOT打印机: {best_niimbot['name']}",
                        'action': 'use_niimbot_printer',
                        'printer_name': best_niimbot['name']
                    })
        
        # 如果有其他可用打印机但没有配置
        elif printer_status.get('has_working_printer', False) and not configured_printer.get('is_available', False):
            available_printers = [p for p in system_printers if p.get('is_available', False)]
            if available_printers:
                recommendations.append({
                    'level': 'info',
                    'title': '发现可用打印机',
                    'description': f"发现可用打印机，建议配置: {', '.join([p['name'] for p in available_printers[:3]])}",
                    'action': 'configure_available_printer'
                })
        
        return recommendations
    
    def apply_fix(self, fix_action: str, **kwargs) -> bool:
        """
        应用修复操作
        
        Args:
            fix_action: 修复操作类型
            **kwargs: 修复参数
            
        Returns:
            是否修复成功
        """
        try:
            if fix_action == 'update_printer_config':
                return self._update_printer_config(kwargs.get('printer_name'))
            elif fix_action == 'use_niimbot_printer':
                return self._use_niimbot_printer(kwargs.get('printer_name'))
            elif fix_action == 'configure_available_printer':
                return self._configure_available_printer(kwargs.get('printer_name'))
            else:
                logger.warning(f"未知的修复操作: {fix_action}")
                return False
                
        except Exception as e:
            logger.error(f"应用修复操作 {fix_action} 失败: {e}")
            return False
    
    def _update_printer_config(self, printer_name: str) -> bool:
        """更新打印机配置"""
        if not printer_name:
            return False
            
        try:
            # 验证打印机是否可用
            if not self._test_printer_availability(printer_name):
                logger.error(f"打印机 {printer_name} 不可用，无法配置")
                return False
            
            # 更新配置
            self.config_manager.set('printer.name', printer_name)
            logger.info(f"✅ 已更新打印机配置: {printer_name}")
            return True
            
        except Exception as e:
            logger.error(f"更新打印机配置失败: {e}")
            return False
    
    def _use_niimbot_printer(self, printer_name: str) -> bool:
        """配置使用NIIMBOT打印机"""
        return self._update_printer_config(printer_name)
    
    def _configure_available_printer(self, printer_name: str) -> bool:
        """配置可用打印机"""
        return self._update_printer_config(printer_name)
    
    def print_diagnostic_report(self) -> str:
        """打印诊断报告"""
        if not self.diagnostic_results:
            return "请先运行诊断"
        
        report = []
        report.append("=" * 60)
        report.append("打印机诊断报告")
        report.append("=" * 60)
        report.append(f"诊断时间: {self.diagnostic_results['timestamp']}")
        report.append("")
        
        # 系统打印机
        system_printers = self.diagnostic_results.get('system_printers', [])
        report.append(f"系统打印机 ({len(system_printers)} 台):")
        for printer in system_printers:
            status = "✅ 可用" if printer.get('is_available', False) else "❌ 不可用"
            niimbot = " [NIIMBOT]" if printer.get('is_niimbot', False) else ""
            report.append(f"  - {printer['name']}{niimbot} - {status}")
        report.append("")
        
        # 配置的打印机
        configured = self.diagnostic_results.get('configured_printer', {})
        report.append("配置的打印机:")
        if configured.get('configured_name'):
            status = "✅ 可用" if configured.get('is_available', False) else "❌ 不可用"
            report.append(f"  - {configured['configured_name']} - {status}")
        else:
            report.append("  - 未配置")
        report.append("")
        
        # 修复建议
        recommendations = self.diagnostic_results.get('recommendations', [])
        if recommendations:
            report.append("修复建议:")
            for i, rec in enumerate(recommendations, 1):
                level_icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(rec['level'], "ℹ️")
                report.append(f"  {i}. {level_icon} {rec['title']}")
                report.append(f"     {rec['description']}")
            report.append("")
        
        return "\n".join(report)


def main():
    """主函数 - 用于独立运行诊断工具"""
    print("🔍 启动打印机诊断工具...")
    
    try:
        # 创建诊断工具
        diagnostic_tool = PrinterDiagnosticTool()
        
        # 运行诊断
        results = diagnostic_tool.run_full_diagnostic()
        
        # 打印报告
        print(diagnostic_tool.print_diagnostic_report())
        
        # 如果有修复建议，询问是否应用
        recommendations = results.get('recommendations', [])
        auto_fix_recommendations = [r for r in recommendations if r.get('action') in [
            'update_printer_config', 'use_niimbot_printer', 'configure_available_printer'
        ]]
        
        if auto_fix_recommendations:
            print("\n🔧 发现可自动修复的问题:")
            for i, rec in enumerate(auto_fix_recommendations, 1):
                print(f"  {i}. {rec['title']}")
            
            choice = input("\n是否应用自动修复? (y/n): ").lower().strip()
            if choice == 'y':
                for rec in auto_fix_recommendations:
                    action = rec.get('action')
                    printer_name = rec.get('printer_name')
                    
                    if printer_name:
                        success = diagnostic_tool.apply_fix(action, printer_name=printer_name)
                        if success:
                            print(f"✅ 已应用修复: {rec['title']}")
                        else:
                            print(f"❌ 修复失败: {rec['title']}")
        
        print("\n✅ 诊断完成")
        
    except Exception as e:
        print(f"❌ 诊断工具运行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
