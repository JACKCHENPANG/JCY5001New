#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
连续测试Excel报告生成器

负责生成连续测试的Excel格式分析报告，包括：
1. 测试概览工作表
2. 通道分析工作表
3. 详细数据工作表
4. 统计图表工作表

作者：Jack
日期：2025-01-31
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)


class ContinuousTestExcelExporter:
    """连续测试Excel报告生成器"""
    
    def __init__(self):
        """初始化Excel导出器"""
        self.workbook = None
        self.formats = {}
        logger.debug("连续测试Excel导出器初始化完成")
    
    def export_analysis_report(self, 
                             analysis_data: Dict[str, Any], 
                             test_results: List[Dict[str, Any]], 
                             batch_info: Dict[str, Any],
                             file_path: str) -> bool:
        """
        导出分析报告到Excel文件
        
        Args:
            analysis_data: 分析数据
            test_results: 原始测试结果
            batch_info: 批次信息
            file_path: 导出文件路径
            
        Returns:
            是否导出成功
        """
        try:
            import xlsxwriter
            
            logger.info(f"开始导出连续测试分析报告到: {file_path}")
            
            # 创建工作簿
            self.workbook = xlsxwriter.Workbook(file_path)
            
            # 定义格式
            self._define_formats()
            
            # 创建各个工作表
            self._create_overview_sheet(analysis_data, batch_info)
            self._create_channel_analysis_sheet(analysis_data)

            # 检查是否有EIS分析数据
            if analysis_data.get('analysis_type') == 'EIS_Professional':
                self._create_eis_analysis_sheet(analysis_data)

            self._create_detailed_data_sheet(test_results)
            self._create_statistics_summary_sheet(analysis_data)
            
            # 关闭工作簿
            self.workbook.close()
            
            logger.info(f"连续测试分析报告导出成功: {file_path}")
            return True
            
        except ImportError:
            logger.error("需要安装xlsxwriter库: pip install xlsxwriter")
            return False
        except Exception as e:
            logger.error(f"导出Excel报告失败: {e}")
            if self.workbook:
                try:
                    self.workbook.close()
                except:
                    pass
            return False
    
    def _define_formats(self):
        """定义Excel格式"""
        try:
            # 标题格式
            self.formats['title'] = self.workbook.add_format({
                'bold': True,
                'font_size': 16,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#4CAF50',
                'font_color': 'white',
                'border': 1
            })
            
            # 表头格式
            self.formats['header'] = self.workbook.add_format({
                'bold': True,
                'font_size': 12,
                'align': 'center',
                'valign': 'vcenter',
                'bg_color': '#E8F5E8',
                'border': 1
            })
            
            # 子标题格式
            self.formats['subtitle'] = self.workbook.add_format({
                'bold': True,
                'font_size': 14,
                'align': 'left',
                'bg_color': '#F0F0F0',
                'border': 1
            })
            
            # 数据格式
            self.formats['data'] = self.workbook.add_format({
                'align': 'center',
                'border': 1
            })
            
            # 数值格式
            self.formats['number'] = self.workbook.add_format({
                'align': 'center',
                'border': 1,
                'num_format': '0.000'
            })
            
            # 百分比格式
            self.formats['percent'] = self.workbook.add_format({
                'align': 'center',
                'border': 1,
                'num_format': '0.00%'
            })
            
            # 优秀格式
            self.formats['excellent'] = self.workbook.add_format({
                'align': 'center',
                'border': 1,
                'bg_color': '#C8E6C9',
                'font_color': '#2E7D32'
            })
            
            # 良好格式
            self.formats['good'] = self.workbook.add_format({
                'align': 'center',
                'border': 1,
                'bg_color': '#FFF9C4',
                'font_color': '#F57F17'
            })
            
            # 需要关注格式
            self.formats['attention'] = self.workbook.add_format({
                'align': 'center',
                'border': 1,
                'bg_color': '#FFCDD2',
                'font_color': '#C62828'
            })
            
        except Exception as e:
            logger.error(f"定义Excel格式失败: {e}")
    
    def _create_overview_sheet(self, analysis_data: Dict[str, Any], batch_info: Dict[str, Any]):
        """创建概览工作表"""
        try:
            worksheet = self.workbook.add_worksheet('测试概览')
            
            # 设置列宽
            worksheet.set_column('A:A', 20)
            worksheet.set_column('B:B', 30)
            worksheet.set_column('C:C', 20)
            worksheet.set_column('D:D', 30)
            
            row = 0
            
            # 标题
            worksheet.merge_range(row, 0, row, 3, '连续测试分析报告', self.formats['title'])
            row += 2
            
            # 基本信息
            worksheet.write(row, 0, '报告生成时间', self.formats['header'])
            worksheet.write(row, 1, analysis_data.get('analysis_time', ''), self.formats['data'])
            worksheet.write(row, 2, '测试记录总数', self.formats['header'])
            worksheet.write(row, 3, analysis_data.get('total_records', 0), self.formats['data'])
            row += 1
            
            worksheet.write(row, 0, '测试通道数', self.formats['header'])
            worksheet.write(row, 1, analysis_data.get('channel_count', 0), self.formats['data'])
            worksheet.write(row, 2, '测试轮次', self.formats['header'])
            overall = analysis_data.get('overall_analysis', {})
            worksheet.write(row, 3, overall.get('total_test_cycles', 0), self.formats['data'])
            row += 2
            
            # 批次信息
            if batch_info:
                worksheet.write(row, 0, '批次信息', self.formats['subtitle'])
                row += 1
                
                worksheet.write(row, 0, '批次号', self.formats['header'])
                worksheet.write(row, 1, batch_info.get('batch_number', ''), self.formats['data'])
                worksheet.write(row, 2, '操作员', self.formats['header'])
                worksheet.write(row, 3, batch_info.get('operator', ''), self.formats['data'])
                row += 1
                
                worksheet.write(row, 0, '电池类型', self.formats['header'])
                worksheet.write(row, 1, batch_info.get('cell_type', ''), self.formats['data'])
                worksheet.write(row, 2, '电池规格', self.formats['header'])
                worksheet.write(row, 3, batch_info.get('cell_spec', ''), self.formats['data'])
                row += 2
            
            # 整体统计
            worksheet.write(row, 0, '整体统计分析', self.formats['subtitle'])
            row += 1
            
            # Rs整体统计
            rs_stats = overall.get('overall_rs_statistics', {})
            if rs_stats:
                worksheet.write(row, 0, 'Rs统计 (mΩ)', self.formats['header'])
                worksheet.write(row, 1, '平均值', self.formats['header'])
                worksheet.write(row, 2, '标准差', self.formats['header'])
                worksheet.write(row, 3, '变异系数', self.formats['header'])
                row += 1
                
                worksheet.write(row, 0, '', self.formats['data'])
                worksheet.write(row, 1, rs_stats.get('mean', 0), self.formats['number'])
                worksheet.write(row, 2, rs_stats.get('std_dev', 0), self.formats['number'])
                worksheet.write(row, 3, f"{rs_stats.get('cv', 0):.2f}%", self.formats['data'])
                row += 1
            
            # Rct整体统计
            rct_stats = overall.get('overall_rct_statistics', {})
            if rct_stats:
                worksheet.write(row, 0, 'Rct统计 (mΩ)', self.formats['header'])
                worksheet.write(row, 1, '平均值', self.formats['header'])
                worksheet.write(row, 2, '标准差', self.formats['header'])
                worksheet.write(row, 3, '变异系数', self.formats['header'])
                row += 1
                
                worksheet.write(row, 0, '', self.formats['data'])
                worksheet.write(row, 1, rct_stats.get('mean', 0), self.formats['number'])
                worksheet.write(row, 2, rct_stats.get('std_dev', 0), self.formats['number'])
                worksheet.write(row, 3, f"{rct_stats.get('cv', 0):.2f}%", self.formats['data'])
                row += 2
            
            # 一致性评价
            consistency = analysis_data.get('consistency_evaluation', {})
            if consistency:
                worksheet.write(row, 0, '一致性评价', self.formats['subtitle'])
                row += 1
                
                overall_rating = consistency.get('overall_rating', 'unknown')
                rating_format = self._get_rating_format(overall_rating)
                
                worksheet.write(row, 0, '整体评价', self.formats['header'])
                worksheet.write(row, 1, overall_rating, rating_format)
                worksheet.write(row, 2, '稳定性评分', self.formats['header'])
                worksheet.write(row, 3, consistency.get('stability_score', 0), self.formats['number'])
                row += 2
                
                # 改进建议
                recommendations = consistency.get('recommendations', [])
                if recommendations:
                    worksheet.write(row, 0, '改进建议', self.formats['subtitle'])
                    row += 1
                    
                    for i, rec in enumerate(recommendations, 1):
                        worksheet.write(row, 0, f'{i}.', self.formats['data'])
                        worksheet.merge_range(row, 1, row, 3, rec, self.formats['data'])
                        row += 1
            
        except Exception as e:
            logger.error(f"创建概览工作表失败: {e}")
    
    def _create_channel_analysis_sheet(self, analysis_data: Dict[str, Any]):
        """创建通道分析工作表"""
        try:
            worksheet = self.workbook.add_worksheet('通道分析')
            
            # 设置列宽
            worksheet.set_column('A:A', 12)
            worksheet.set_column('B:P', 10)
            
            row = 0
            
            # 标题
            worksheet.merge_range(row, 0, row, 15, '各通道详细分析', self.formats['title'])
            row += 2
            
            # 表头
            headers = [
                '通道号', '测试次数', '合格次数', '合格率(%)',
                'Rs均值', 'Rs最大', 'Rs最小', 'Rs标准差', 'Rs变异系数(%)',
                'Rct均值', 'Rct最大', 'Rct最小', 'Rct标准差', 'Rct变异系数(%)',
                'Rs稳定性', 'Rct稳定性'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(row, col, header, self.formats['header'])
            row += 1
            
            # 数据
            channel_analysis = analysis_data.get('channel_analysis', {})
            for channel_num in sorted(channel_analysis.keys()):
                data = channel_analysis[channel_num]
                
                rs_stats = data.get('rs_statistics', {})
                rct_stats = data.get('rct_statistics', {})
                stability = data.get('stability_analysis', {})
                
                # 写入数据
                worksheet.write(row, 0, channel_num, self.formats['data'])
                worksheet.write(row, 1, data.get('test_count', 0), self.formats['data'])
                worksheet.write(row, 2, data.get('pass_count', 0), self.formats['data'])
                worksheet.write(row, 3, data.get('pass_rate', 0), self.formats['number'])
                
                # Rs统计
                worksheet.write(row, 4, rs_stats.get('mean', 0), self.formats['number'])
                worksheet.write(row, 5, rs_stats.get('max', 0), self.formats['number'])
                worksheet.write(row, 6, rs_stats.get('min', 0), self.formats['number'])
                worksheet.write(row, 7, rs_stats.get('std_dev', 0), self.formats['number'])
                worksheet.write(row, 8, rs_stats.get('cv', 0), self.formats['number'])
                
                # Rct统计
                worksheet.write(row, 9, rct_stats.get('mean', 0), self.formats['number'])
                worksheet.write(row, 10, rct_stats.get('max', 0), self.formats['number'])
                worksheet.write(row, 11, rct_stats.get('min', 0), self.formats['number'])
                worksheet.write(row, 12, rct_stats.get('std_dev', 0), self.formats['number'])
                worksheet.write(row, 13, rct_stats.get('cv', 0), self.formats['number'])
                
                # 稳定性评价
                rs_stability = stability.get('rs_stability', 'unknown')
                rct_stability = stability.get('rct_stability', 'unknown')
                
                worksheet.write(row, 14, rs_stability, self._get_rating_format(rs_stability))
                worksheet.write(row, 15, rct_stability, self._get_rating_format(rct_stability))
                
                row += 1
            
        except Exception as e:
            logger.error(f"创建通道分析工作表失败: {e}")

    def _create_eis_analysis_sheet(self, analysis_data: Dict[str, Any]):
        """创建EIS阻抗分析工作表"""
        try:
            worksheet = self.workbook.add_worksheet('EIS阻抗分析')

            # 设置列宽
            worksheet.set_column('A:A', 12)
            worksheet.set_column('B:H', 15)

            row = 0

            # 标题
            worksheet.merge_range(row, 0, row, 7, 'EIS频点阻抗分析', self.formats['title'])
            row += 2

            # 频点阻抗统计表
            frequency_impedance_analysis = analysis_data.get('frequency_impedance_analysis', {})
            if frequency_impedance_analysis:
                worksheet.write(row, 0, '频点阻抗统计', self.formats['subtitle'])
                row += 1

                # 表头
                headers = [
                    '频率(Hz)', '阻抗幅值|Z|(mΩ)', '相位角θ(°)', '测试次数',
                    '|Z|变异系数(%)', 'θ变异系数(%)', '|Z|范围', 'θ范围'
                ]

                for col, header in enumerate(headers):
                    worksheet.write(row, col, header, self.formats['header'])
                row += 1

                # 数据
                frequency_analysis = frequency_impedance_analysis.get('frequency_analysis', {})
                analyzed_frequencies = frequency_impedance_analysis.get('analyzed_frequencies', [])

                for frequency in sorted(analyzed_frequencies):
                    if frequency not in frequency_analysis:
                        continue

                    freq_data = frequency_analysis[frequency]
                    magnitude_stats = freq_data.get('overall_magnitude_stats', {})
                    phase_stats = freq_data.get('overall_phase_stats', {})

                    # 频率
                    worksheet.write(row, 0, frequency, self.formats['number'])

                    # 阻抗幅值|Z|
                    magnitude_mean = magnitude_stats.get('mean', 0)
                    magnitude_std = magnitude_stats.get('std_dev', 0)
                    magnitude_text = f"{magnitude_mean:.3f}±{magnitude_std:.3f}"
                    worksheet.write(row, 1, magnitude_text, self.formats['data'])

                    # 相位角θ
                    phase_mean = phase_stats.get('mean', 0)
                    phase_std = phase_stats.get('std_dev', 0)
                    phase_text = f"{phase_mean:.2f}±{phase_std:.2f}"
                    worksheet.write(row, 2, phase_text, self.formats['data'])

                    # 测试次数
                    test_count = magnitude_stats.get('count', 0)
                    worksheet.write(row, 3, test_count, self.formats['data'])

                    # |Z|变异系数
                    magnitude_cv = magnitude_stats.get('cv', 0)
                    worksheet.write(row, 4, magnitude_cv, self.formats['number'])

                    # θ变异系数
                    phase_cv = phase_stats.get('cv', 0)
                    worksheet.write(row, 5, phase_cv, self.formats['number'])

                    # |Z|范围
                    magnitude_min = magnitude_stats.get('min', 0)
                    magnitude_max = magnitude_stats.get('max', 0)
                    magnitude_range = f"{magnitude_min:.3f}~{magnitude_max:.3f}"
                    worksheet.write(row, 6, magnitude_range, self.formats['data'])

                    # θ范围
                    phase_min = phase_stats.get('min', 0)
                    phase_max = phase_stats.get('max', 0)
                    phase_range = f"{phase_min:.2f}~{phase_max:.2f}"
                    worksheet.write(row, 7, phase_range, self.formats['data'])

                    row += 1

                row += 2

            # EIS一致性评价表
            consistency_evaluation = analysis_data.get('consistency_evaluation', {})
            if consistency_evaluation:
                worksheet.write(row, 0, 'EIS一致性评价', self.formats['subtitle'])
                row += 1

                # 表头
                headers = ['评价项目', '评价结果', '数值指标', '建议']
                for col, header in enumerate(headers):
                    worksheet.write(row, col, header, self.formats['header'])
                row += 1

                # 频点间一致性
                freq_consistency = consistency_evaluation.get('frequency_consistency', {})
                if freq_consistency:
                    rating = freq_consistency.get('consistency_rating', 'unknown')
                    avg_magnitude_cv = freq_consistency.get('avg_magnitude_cv', 0)
                    avg_phase_cv = freq_consistency.get('avg_phase_cv', 0)

                    worksheet.write(row, 0, '频点间一致性', self.formats['data'])
                    worksheet.write(row, 1, rating, self._get_rating_format(rating))
                    worksheet.write(row, 2, f"|Z|平均CV: {avg_magnitude_cv:.2f}%, θ平均CV: {avg_phase_cv:.2f}%", self.formats['data'])
                    worksheet.write(row, 3, "检查测试环境稳定性" if rating == "需改进" else "保持当前测试条件", self.formats['data'])
                    row += 1

                # 通道间一致性
                channel_consistency = consistency_evaluation.get('channel_consistency', {})
                if channel_consistency:
                    rating = channel_consistency.get('consistency_rating', 'unknown')
                    avg_channel_cv = channel_consistency.get('avg_channel_cv', 0)

                    worksheet.write(row, 0, '通道间一致性', self.formats['data'])
                    worksheet.write(row, 1, rating, self._get_rating_format(rating))
                    worksheet.write(row, 2, f"通道平均CV: {avg_channel_cv:.2f}%", self.formats['data'])
                    worksheet.write(row, 3, "检查通道校准" if rating == "需改进" else "通道状态良好", self.formats['data'])
                    row += 1

                # 整体评价
                overall_rating = consistency_evaluation.get('overall_rating', 'unknown')
                if overall_rating:
                    worksheet.write(row, 0, '整体评价', self.formats['data'])
                    worksheet.write(row, 1, overall_rating, self._get_rating_format(overall_rating))
                    worksheet.write(row, 2, '综合所有指标评价', self.formats['data'])
                    worksheet.write(row, 3, '根据具体问题采取相应措施', self.formats['data'])
                    row += 2

            # 异常频点识别表
            anomalous_frequencies = analysis_data.get('anomalous_frequencies', [])
            if isinstance(anomalous_frequencies, list) and anomalous_frequencies:
                worksheet.write(row, 0, '异常频点识别', self.formats['subtitle'])
                row += 1

                # 表头
                headers = ['频率(Hz)', '异常类型', '异常程度', '影响通道', '建议措施']
                for col, header in enumerate(headers):
                    worksheet.write(row, col, header, self.formats['header'])
                row += 1

                # 数据
                for anomaly in anomalous_frequencies:
                    if not isinstance(anomaly, dict):
                        continue

                    frequency = anomaly.get('frequency', 0)
                    anomaly_type = anomaly.get('anomaly_type', 'unknown')
                    severity = anomaly.get('severity', 'unknown')
                    affected_channels = anomaly.get('affected_channels', [])
                    recommendation = anomaly.get('recommendation', '需要进一步检查')

                    worksheet.write(row, 0, frequency, self.formats['number'])
                    worksheet.write(row, 1, anomaly_type, self.formats['data'])
                    worksheet.write(row, 2, severity, self._get_rating_format(severity))

                    # 影响通道
                    channels_text = ", ".join([f"CH{ch}" for ch in affected_channels]) if affected_channels else "--"
                    worksheet.write(row, 3, channels_text, self.formats['data'])
                    worksheet.write(row, 4, recommendation, self.formats['data'])

                    row += 1
            else:
                # 没有异常频点
                worksheet.write(row, 0, '异常频点识别', self.formats['subtitle'])
                row += 1
                worksheet.write(row, 0, '未发现异常频点', self.formats['excellent'])

        except Exception as e:
            logger.error(f"创建EIS阻抗分析工作表失败: {e}")

    def _create_detailed_data_sheet(self, test_results: List[Dict[str, Any]]):
        """创建详细数据工作表"""
        try:
            worksheet = self.workbook.add_worksheet('详细数据')
            
            # 设置列宽
            worksheet.set_column('A:K', 12)
            
            row = 0
            
            # 标题
            worksheet.merge_range(row, 0, row, 10, '连续测试详细数据', self.formats['title'])
            row += 2
            
            # 表头
            headers = [
                '测试轮次', '通道号', '电压(V)', 'Rs(mΩ)', 'Rct(mΩ)',
                'Rs档位', 'Rct档位', '测试结果', '合格状态', '电池码', '备注'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(row, col, header, self.formats['header'])
            row += 1
            
            # 数据
            for result in test_results:
                worksheet.write(row, 0, result.get('cycle', 0), self.formats['data'])
                worksheet.write(row, 1, result.get('channel', 0), self.formats['data'])
                worksheet.write(row, 2, result.get('voltage', 0), self.formats['number'])
                worksheet.write(row, 3, result.get('rs_value', 0), self.formats['number'])
                worksheet.write(row, 4, result.get('rct_value', 0), self.formats['number'])
                worksheet.write(row, 5, result.get('rs_grade', ''), self.formats['data'])
                worksheet.write(row, 6, result.get('rct_grade', ''), self.formats['data'])
                
                # 测试结果
                is_pass = result.get('is_pass', False)
                result_text = '合格' if is_pass else '不合格'
                result_format = self.formats['excellent'] if is_pass else self.formats['attention']
                
                worksheet.write(row, 7, result_text, result_format)
                worksheet.write(row, 8, '✓' if is_pass else '✗', result_format)
                worksheet.write(row, 9, result.get('battery_code', ''), self.formats['data'])
                worksheet.write(row, 10, '', self.formats['data'])
                
                row += 1
            
        except Exception as e:
            logger.error(f"创建详细数据工作表失败: {e}")
    
    def _create_statistics_summary_sheet(self, analysis_data: Dict[str, Any]):
        """创建统计汇总工作表"""
        try:
            worksheet = self.workbook.add_worksheet('统计汇总')
            
            # 设置列宽
            worksheet.set_column('A:D', 20)
            
            row = 0
            
            # 标题
            worksheet.merge_range(row, 0, row, 3, '统计汇总表', self.formats['title'])
            row += 2
            
            # 通道间一致性分析
            overall = analysis_data.get('overall_analysis', {})
            consistency = overall.get('channel_consistency', {})
            
            if consistency:
                worksheet.write(row, 0, '通道间一致性分析', self.formats['subtitle'])
                row += 1
                
                worksheet.write(row, 0, '参数', self.formats['header'])
                worksheet.write(row, 1, '通道间变异系数(%)', self.formats['header'])
                worksheet.write(row, 2, '一致性等级', self.formats['header'])
                worksheet.write(row, 3, '评价', self.formats['header'])
                row += 1
                
                # Rs一致性
                rs_cv = consistency.get('rs_channel_cv', 0)
                rs_level = consistency.get('rs_consistency_level', 'unknown')
                worksheet.write(row, 0, 'Rs', self.formats['data'])
                worksheet.write(row, 1, rs_cv, self.formats['number'])
                worksheet.write(row, 2, rs_level, self._get_rating_format(rs_level))
                worksheet.write(row, 3, self._get_consistency_comment(rs_cv), self.formats['data'])
                row += 1
                
                # Rct一致性
                rct_cv = consistency.get('rct_channel_cv', 0)
                rct_level = consistency.get('rct_consistency_level', 'unknown')
                worksheet.write(row, 0, 'Rct', self.formats['data'])
                worksheet.write(row, 1, rct_cv, self.formats['number'])
                worksheet.write(row, 2, rct_level, self._get_rating_format(rct_level))
                worksheet.write(row, 3, self._get_consistency_comment(rct_cv), self.formats['data'])
                row += 2
            
            # 评价标准说明
            worksheet.write(row, 0, '评价标准', self.formats['subtitle'])
            row += 1
            
            criteria = analysis_data.get('consistency_evaluation', {}).get('evaluation_criteria', {})
            if criteria:
                worksheet.write(row, 0, '等级', self.formats['header'])
                worksheet.write(row, 1, '变异系数范围', self.formats['header'])
                worksheet.write(row, 2, '说明', self.formats['header'])
                row += 1
                
                standards = [
                    ('优秀', criteria.get('excellent', '≤ 5%'), '数据一致性非常好'),
                    ('良好', criteria.get('good', '≤ 10%'), '数据一致性较好'),
                    ('一般', criteria.get('fair', '≤ 20%'), '数据一致性一般'),
                    ('需要关注', criteria.get('needs_attention', '> 20%'), '数据离散度较大')
                ]
                
                for level, range_text, description in standards:
                    worksheet.write(row, 0, level, self._get_rating_format(level))
                    worksheet.write(row, 1, range_text, self.formats['data'])
                    worksheet.write(row, 2, description, self.formats['data'])
                    row += 1
            
        except Exception as e:
            logger.error(f"创建统计汇总工作表失败: {e}")
    
    def _get_rating_format(self, rating: str):
        """根据评价等级获取格式"""
        if rating in ['优秀', 'excellent']:
            return self.formats['excellent']
        elif rating in ['良好', 'good']:
            return self.formats['good']
        elif rating in ['需要关注', 'attention', 'needs_attention']:
            return self.formats['attention']
        else:
            return self.formats['data']
    
    def _get_consistency_comment(self, cv: float) -> str:
        """根据变异系数获取一致性评价"""
        if cv <= 5:
            return "一致性优秀"
        elif cv <= 10:
            return "一致性良好"
        elif cv <= 20:
            return "一致性一般"
        else:
            return "需要关注"
