# -*- coding: utf-8 -*-
"""
数据导出管理器
负责数据导出相关功能

从data_export_dialog.py中提取，遵循单一职责原则

Author: Augment Agent  
Date: 2025-06-04
"""

import logging
from typing import List, Dict
from PyQt5.QtCore import QThread, pyqtSignal
from data.database_manager import DatabaseManager
from utils.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class DataExportWorker(QThread):
    """数据导出工作线程 - 支持同时导出结果数据和明细数据"""

    progress_updated = pyqtSignal(int)  # 进度更新信号
    export_completed = pyqtSignal(str)  # 导出完成信号
    export_failed = pyqtSignal(str)     # 导出失败信号

    def __init__(self, data: List[Dict], export_path: str, export_format: str, db_manager=None):
        super().__init__()
        self.data = data
        self.export_path = export_path
        self.export_format = export_format
        self.db_manager = db_manager  # 用于查询明细数据
        self.config_manager = ConfigManager()  # 用于获取范围配置

    def _get_voltage_range_text(self) -> str:
        """获取电压范围文本 - 从测试配置中获取"""
        try:
            # 从测试配置中获取电压范围
            voltage_range = self.config_manager.get('test_params.voltage_range', {'min': 2.0, 'max': 5.0})
            min_voltage = voltage_range.get('min', 2.0)
            max_voltage = voltage_range.get('max', 5.0)
            return f"{min_voltage:.3f}V-{max_voltage:.3f}V"
        except Exception as e:
            logger.error(f"获取电压范围失败: {e}")
            return "--"

    def _get_rs_range_text(self) -> str:
        """获取Rs范围文本 - 从判断设置配置中获取"""
        try:
            # 修复从grade_settings配置中获取Rs范围，与实际判断逻辑一致
            rs_min = self.config_manager.get('grade_settings.rs_min', 0.1)
            rs_max = self.config_manager.get('grade_settings.rs_max', 50.0)

            return f"{rs_min:.3f}mΩ-{rs_max:.3f}mΩ"
        except Exception as e:
            logger.error(f"获取Rs范围失败: {e}")
            return "--"

    def _get_rct_range_text(self) -> str:
        """获取Rct范围文本 - 从判断设置配置中获取"""
        try:
            # 修复从grade_settings配置中获取Rct范围，与实际判断逻辑一致
            rct_min = self.config_manager.get('grade_settings.rct_min', 5.0)
            rct_max = self.config_manager.get('grade_settings.rct_max', 100.0)

            return f"{rct_min:.3f}mΩ-{rct_max:.3f}mΩ"
        except Exception as e:
            logger.error(f"获取Rct范围失败: {e}")
            return "--"

    def _get_voltage_range_from_db(self, item: Dict) -> str:
        """从数据库记录中获取电压范围文本"""
        try:
            voltage_min = item.get('voltage_range_min')
            voltage_max = item.get('voltage_range_max')

            if voltage_min is not None and voltage_max is not None:
                return f"{voltage_min:.3f}V-{voltage_max:.3f}V"
            else:
                # 如果数据库中没有范围信息，使用当前配置作为备用
                return self._get_voltage_range_text()
        except Exception as e:
            logger.error(f"从数据库获取电压范围失败: {e}")
            return "--"

    def _get_rs_range_from_db(self, item: Dict) -> str:
        """从数据库记录中获取Rs范围文本"""
        try:
            rs_min = item.get('rs_range_min')
            rs_max = item.get('rs_range_max')

            if rs_min is not None and rs_max is not None:
                return f"{rs_min:.3f}mΩ-{rs_max:.3f}mΩ"
            else:
                # 如果数据库中没有范围信息，使用当前配置作为备用
                return self._get_rs_range_text()
        except Exception as e:
            logger.error(f"从数据库获取Rs范围失败: {e}")
            return "--"

    def _get_rct_range_from_db(self, item: Dict) -> str:
        """从数据库记录中获取Rct范围文本"""
        try:
            rct_min = item.get('rct_range_min')
            rct_max = item.get('rct_range_max')

            if rct_min is not None and rct_max is not None:
                return f"{rct_min:.3f}mΩ-{rct_max:.3f}mΩ"
            else:
                # 如果数据库中没有范围信息，使用当前配置作为备用
                return self._get_rct_range_text()
        except Exception as e:
            logger.error(f"从数据库获取Rct范围失败: {e}")
            return "--"

    def _format_test_result(self, is_pass: bool, fail_reason: str) -> str:
        """格式化测试结果显示"""
        if is_pass:
            return '合格'
        else:
            # 根据失败原因生成简化的测试结果显示
            if fail_reason:
                if '电压' in fail_reason:
                    return '不合格-电压'
                elif 'Rs' in fail_reason:
                    return '不合格-Rs'
                elif 'Rct' in fail_reason:
                    return '不合格-Rct'
                elif '离群率' in fail_reason:
                    return '不合格-离群率'
                elif '接触不良' in fail_reason:
                    return '不合格-接触不良'
                elif '异常' in fail_reason:
                    return '不合格-异常'
                else:
                    return '不合格'
            else:
                return '不合格'

    def run(self):
        """执行导出任务"""
        try:
            if self.export_format == "Excel":
                self._export_to_excel()
            elif self.export_format == "CSV":
                self._export_to_csv()
            else:
                raise ValueError(f"不支持的导出格式: {self.export_format}")

            self.export_completed.emit(self.export_path)

        except Exception as e:
            logger.error(f"数据导出失败: {e}")
            self.export_failed.emit(str(e))

    def _export_to_excel(self):
        """导出到Excel文件 - 同时导出结果数据和明细数据"""
        try:
            import xlsxwriter

            workbook = xlsxwriter.Workbook(self.export_path)

            # 定义格式
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#4CAF50',
                'font_color': 'white',
                'border': 1,
                'align': 'center'
            })

            data_format = workbook.add_format({
                'border': 1,
                'align': 'center'
            })

            pass_format = workbook.add_format({
                'border': 1,
                'align': 'center',
                'bg_color': '#E8F5E8'
            })

            fail_format = workbook.add_format({
                'border': 1,
                'align': 'center',
                'bg_color': '#FFEBEE'
            })

            # 1. 导出测试结果数据
            self._export_results_sheet(workbook, header_format, data_format, pass_format, fail_format)

            # 2. 导出明细数据（如果有数据库管理器）
            if self.db_manager:
                self._export_details_sheet(workbook, header_format, data_format)

            workbook.close()

        except ImportError:
            raise ImportError("需要安装xlsxwriter库: pip install xlsxwriter")

    def _export_results_sheet(self, workbook, header_format, data_format, pass_format, fail_format):
        """导出测试结果工作表"""
        worksheet = workbook.add_worksheet('测试结果')

        # 写入表头 - 与界面显示保持一致，合并Rs和Rct档位列
        headers = [
            '批次号', '通道号', '电池编码', '测试开始时间', '测试结束时间',
            '测试时长(s)', '电压(V)', 'Rs(mΩ)', 'Rct(mΩ)', 'W阻抗(mΩ)',
            'Rs-Rct档位', '电压范围', 'Rs范围', 'Rct范围',
            '离群率(%)', '基准ID',
            # 新增完整EIS分析参数
            'Rsei(mΩ)', 'Warburg系数(mΩ·s^-0.5)', 'Warburg_0.1Hz(mΩ)', 'Warburg_0.01Hz(mΩ)',
            '检测到Warburg', '检测到SEI', 'SEI置信度', '双电层电容(mF)', 'SEI电容(mF)', '总电容(mF)',
            '特征频率(Hz)', '主时间常数(ms)', 'SEI时间常数(ms)', '相位角范围(°)', '最大相位角(°)', '最小相位角(°)',
            'Rs贡献(%)', 'SEI贡献(%)', 'CT贡献(%)', '极化贡献(%)', '阻抗比(Rp/Rs)', '健康状态', '健康评分', '健康等级', '性能等级', '分析方法',
            '测试结果', '失败原因', '操作员', '电池类型', '电池规格'
        ]

        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)

        # 写入数据
        total_rows = len(self.data)
        for row, item in enumerate(self.data, 1):
            # 更新进度（结果数据占50%）
            progress = int((row / total_rows) * 50)
            self.progress_updated.emit(progress)

            # 选择格式
            if item.get('is_pass'):
                cell_format = pass_format
            else:
                cell_format = fail_format

            # 修复格式化数据行，确保数值显示3位小数，测试时间只保留整数，添加范围列
            fail_reason = item.get('fail_reason', '')
            is_pass = item.get('is_pass', False)

            # 修复根据测试结果显示范围值，从数据库记录中获取历史范围信息
            voltage_range_text = "--" if not is_pass and ('电压' in fail_reason) else self._get_voltage_range_from_db(item)
            rs_range_text = "--" if not is_pass and ('Rs' in fail_reason) else self._get_rs_range_from_db(item)
            rct_range_text = "--" if not is_pass and ('Rct' in fail_reason) else self._get_rct_range_from_db(item)

            # 档位显示逻辑 - 合并Rs和Rct档位，如果测试结果不合格，显示"--"
            if is_pass:
                rs_grade = item.get('rs_grade', '')
                rct_grade = item.get('rct_grade', '')
                combined_grade_text = f"{rs_grade}-{rct_grade}"
            else:
                combined_grade_text = '--'

            # 修复批次号 - 优先从测试结果记录中获取，如果没有则从批次表中获取
            batch_number = item.get('batch_number', '') or item.get('batch_table_batch_number', '')

            # 新增离群率和基准ID字段
            max_deviation_percent = item.get('max_deviation_percent')
            outlier_rate_text = f"{max_deviation_percent:.1f}%" if max_deviation_percent is not None else "--"

            baseline_id = item.get('baseline_id')
            baseline_id_text = str(baseline_id) if baseline_id is not None else "--"

            # 新增格式化EIS参数数据
            def format_eis_value(value, decimal_places=3):
                """格式化EIS参数值"""
                if value is None:
                    return "--"
                try:
                    return f"{float(value):.{decimal_places}f}"
                except (ValueError, TypeError):
                    return "--"

            def format_boolean(value):
                """格式化布尔值"""
                if value is None:
                    return "--"
                return "是" if value else "否"

            data_row = [
                batch_number,
                item.get('channel_number', ''),
                item.get('battery_code', ''),
                item.get('test_start_time', ''),
                item.get('test_end_time', ''),
                f"{int(item.get('test_duration', 0))}" if item.get('test_duration') else '',  # 测试时长只保留整数
                f"{item.get('voltage', 0):.3f}" if item.get('voltage') else '',  # 电压3位小数
                f"{item.get('rs_value', 0):.3f}" if item.get('rs_value') else '',  # Rs值3位小数
                f"{item.get('rct_value', 0):.3f}" if item.get('rct_value') else '',  # Rct值3位小数
                f"{item.get('w_impedance', 0):.3f}" if item.get('w_impedance') else '',  # W阻抗3位小数
                combined_grade_text,  # Rs-Rct档位（合并列）- 不合格时显示"--"
                voltage_range_text,  # 电压范围
                rs_range_text,      # Rs范围
                rct_range_text,     # Rct范围
                outlier_rate_text,  # 新增离群率(%)
                baseline_id_text,   # 新增基准ID
                # 新增完整EIS分析参数
                format_eis_value(item.get('rsei_value')),  # Rsei(mΩ)
                format_eis_value(item.get('warburg_coefficient'), 6),  # Warburg系数(mΩ·s^-0.5)
                format_eis_value(item.get('warburg_01hz')),  # Warburg_0.1Hz(mΩ)
                format_eis_value(item.get('warburg_001hz')),  # Warburg_0.01Hz(mΩ)
                format_boolean(item.get('has_warburg_diffusion')),  # 检测到Warburg
                format_boolean(item.get('has_sei')),  # 检测到SEI
                format_eis_value(item.get('sei_confidence')),  # SEI置信度
                format_eis_value(item.get('double_layer_capacitance')),  # 双电层电容(mF)
                format_eis_value(item.get('sei_capacitance')),  # SEI电容(mF)
                format_eis_value(item.get('total_capacitance')),  # 总电容(mF)
                format_eis_value(item.get('characteristic_frequency'), 1),  # 特征频率(Hz)
                format_eis_value(item.get('main_time_constant')),  # 主时间常数(ms)
                format_eis_value(item.get('sei_time_constant')),  # SEI时间常数(ms)
                format_eis_value(item.get('phase_angle_range'), 1),  # 相位角范围(°)
                format_eis_value(item.get('max_phase_angle'), 1),  # 最大相位角(°)
                format_eis_value(item.get('min_phase_angle'), 1),  # 最小相位角(°)
                format_eis_value(item.get('rs_contribution'), 1),  # Rs贡献(%)
                format_eis_value(item.get('sei_contribution'), 1),  # SEI贡献(%)
                format_eis_value(item.get('ct_contribution'), 1),  # CT贡献(%)
                format_eis_value(item.get('polarization_contribution'), 1),  # 极化贡献(%)
                format_eis_value(item.get('impedance_ratio'), 3),  # 阻抗比(Rp/Rs)
                item.get('health_status', '--'),  # 健康状态
                item.get('health_score', '--'),  # 健康评分
                item.get('health_level', '--'),  # 健康等级
                item.get('performance_grade', '--'),  # 性能等级
                item.get('analysis_method', '--'),  # 分析方法
                self._format_test_result(is_pass, fail_reason),  # 格式化的测试结果
                fail_reason if fail_reason else '',  # 详细失败原因
                # 修复优先从测试结果记录中获取，如果没有则从批次信息中获取
                item.get('operator', '') or item.get('batch_operator', ''),  # 操作员
                item.get('battery_type', '') or item.get('batch_cell_type', ''),  # 电池类型
                item.get('battery_spec', '') or item.get('batch_cell_spec', '')  # 电池规格
            ]

            for col, value in enumerate(data_row):
                if col == 43:  # 修复测试结果列索引更新（增加了阻抗比列）
                    worksheet.write(row, col, value, cell_format)
                else:
                    worksheet.write(row, col, value, data_format)

        # 设置列宽
        worksheet.set_column('A:AV', 15)  # 修复扩展到AV列以包含所有EIS参数列
        worksheet.set_column('C:C', 20)  # 电池码列稍宽
        worksheet.set_column('D:E', 20)  # 时间列稍宽
        worksheet.set_column('M:O', 18)  # 范围列稍宽
        worksheet.set_column('P:P', 12)  # 离群率列
        worksheet.set_column('Q:Q', 10)  # 基准ID列
        # EIS参数列设置
        worksheet.set_column('R:AQ', 12)  # EIS参数列稍窄
        worksheet.set_column('AR:AR', 10)  # 健康状态列
        worksheet.set_column('AS:AT', 8)   # 健康评分和等级列
        worksheet.set_column('AU:AU', 12)  # 性能等级列
        worksheet.set_column('AV:AV', 15)  # 分析方法列

    def _export_details_sheet(self, workbook, header_format, data_format):
        """导出明细数据工作表"""
        worksheet = workbook.add_worksheet('阻抗明细数据')

        # 写入表头 - 与界面显示保持一致，使用专业术语
        detail_headers = [
            '批次号', '通道号', '电池编码', '测试时间', '频率(Hz)',
            '阻抗实部Re(Z)(mΩ)', '阻抗虚部Im(Z)(mΩ)', '阻抗模值|Z|(mΩ)', '电压(V)', '测试序号'
        ]

        for col, header in enumerate(detail_headers):
            worksheet.write(0, col, header, header_format)

        # 收集所有明细数据
        all_details = []
        total_items = len(self.data)

        for i, item in enumerate(self.data):
            # 更新进度（明细数据占50%，从50%开始）
            progress = 50 + int((i / total_items) * 50)
            self.progress_updated.emit(progress)

            # 查询明细数据
            details = self.db_manager.get_impedance_details(
                batch_id=item.get('batch_id'),
                channel_number=item.get('channel_number'),
                battery_code=item.get('battery_code')
            )

            # 修复获取批次号 - 优先从测试结果记录中获取，如果没有则从批次表中获取
            item_batch_number = item.get('batch_number', '') or item.get('batch_table_batch_number', '')

            # 添加批次信息到明细数据
            for detail in details:
                detail_row = {
                    'batch_number': item_batch_number,
                    'channel_number': detail.get('channel_number', ''),
                    'battery_code': detail.get('battery_code', ''),
                    'test_timestamp': detail.get('test_timestamp', ''),
                    'frequency': detail.get('frequency', 0),
                    'impedance_real': detail.get('impedance_real', 0),
                    'impedance_imag': detail.get('impedance_imag', 0),
                    'z_value': (detail.get('impedance_real', 0)**2 + detail.get('impedance_imag', 0)**2)**0.5,
                    'voltage': detail.get('voltage', 0),
                    'test_sequence': detail.get('test_sequence', 0)
                }
                all_details.append(detail_row)

        # 写入明细数据
        for row, detail in enumerate(all_details, 1):
            data_row = [
                detail['batch_number'],
                detail['channel_number'],
                detail['battery_code'],
                detail['test_timestamp'],
                f"{detail['frequency']:.3f}",
                f"{detail['impedance_real']:.3f}",
                f"{detail['impedance_imag']:.3f}",
                f"{detail['z_value']:.3f}",
                f"{detail['voltage']:.3f}",
                detail['test_sequence']
            ]

            for col, value in enumerate(data_row):
                worksheet.write(row, col, value, data_format)

        # 设置列宽
        worksheet.set_column('A:J', 15)
        worksheet.set_column('C:C', 20)  # 电池码列稍宽
        worksheet.set_column('D:D', 20)  # 时间列稍宽

    def _export_to_csv(self):
        """导出到CSV文件"""
        import csv

        with open(self.export_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            # 修复CSV导出字段映射，优先从测试结果记录中获取操作员、电池类型和规格
            fieldnames = [
                'batch_number', 'channel_number', 'battery_code', 'test_start_time',
                'test_end_time', 'test_duration', 'voltage', 'rs_value', 'rct_value',
                'w_impedance', 'rs_grade', 'rct_grade', 'impedance_ratio', 'is_pass', 'fail_reason',
                'test_mode', 'operator', 'battery_type', 'battery_spec'
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            total_rows = len(self.data)
            for i, row in enumerate(self.data):
                # 更新进度
                progress = int(((i + 1) / total_rows) * 100)
                self.progress_updated.emit(progress)

                # 修复处理数据格式，确保数值显示3位小数，测试时间只保留整数
                export_row = {}
                for field in fieldnames:
                    # 修复处理批次号、操作员、电池类型、规格字段的优先级获取
                    if field == 'batch_number':
                        value = row.get('batch_number', '') or row.get('batch_table_batch_number', '')
                    elif field == 'operator':
                        value = row.get('operator', '') or row.get('batch_operator', '')
                    elif field == 'battery_type':
                        value = row.get('battery_type', '') or row.get('batch_cell_type', '')
                    elif field == 'battery_spec':
                        value = row.get('battery_spec', '') or row.get('batch_cell_spec', '')
                    else:
                        value = row.get(field, '')

                    # 格式化特定字段
                    if field == 'test_duration' and value:
                        export_row[field] = int(value)  # 测试时长只保留整数
                    elif field in ['voltage', 'rs_value', 'rct_value', 'w_impedance', 'impedance_ratio'] and value:
                        export_row[field] = f"{value:.3f}"  # 数值3位小数
                    elif field == 'is_pass':
                        export_row[field] = '合格' if value else '不合格'  # 转换为中文
                    else:
                        export_row[field] = value

                writer.writerow(export_row)


class DataExportManager:
    """
    数据导出管理器
    
    职责：
    - 管理数据导出逻辑
    - 处理导出格式
    - 管理导出状态
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化数据导出管理器
        
        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.export_worker = None
        
        logger.debug("数据导出管理器初始化完成")
    
    def start_export(self, data: List[Dict], file_path: str, export_format: str):
        """
        开始数据导出
        
        Args:
            data: 要导出的数据
            file_path: 导出文件路径
            export_format: 导出格式 ("Excel" 或 "CSV")
            
        Returns:
            DataExportWorker: 导出工作线程
        """
        try:
            # 停止之前的导出
            if self.export_worker and self.export_worker.isRunning():
                self.export_worker.terminate()
                self.export_worker.wait()
            
            # 创建导出工作线程
            self.export_worker = DataExportWorker(
                data=data,
                export_path=file_path,
                export_format=export_format,
                db_manager=self.db_manager
            )
            
            # 启动导出
            self.export_worker.start()
            
            logger.debug(f"开始导出数据，格式: {export_format}, 路径: {file_path}")
            return self.export_worker
            
        except Exception as e:
            logger.error(f"启动数据导出失败: {e}")
            return None
    
    def stop_export(self):
        """停止当前导出"""
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.terminate()
            self.export_worker.wait()
    
    def is_exporting(self):
        """检查是否正在导出"""
        return self.export_worker and self.export_worker.isRunning()
    
    def cleanup(self):
        """清理资源"""
        self.stop_export()
        logger.debug("数据导出管理器清理完成")
