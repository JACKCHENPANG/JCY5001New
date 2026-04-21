#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EIS连续测试数据分析器

专门针对EIS（电化学阻抗谱）设备测试的连续测试数据分析，包括：
1. 基于频点的阻抗Z值分析（实部Z'、虚部Z''、模值|Z|、相位角θ）
2. 频点级别的统计分析（均值、标准差、变异系数）
3. 频点间一致性和稳定性评估
4. 异常频点识别和分析
5. EIS专业术语的分析报告

作者：Jack
日期：2025-01-31
版本：EIS专业版
"""

import logging
import statistics
import math
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class ContinuousTestAnalyzer:
    """连续测试数据分析器"""
    
    def __init__(self):
        """初始化分析器"""
        self.analysis_result = {}
        logger.debug("连续测试数据分析器初始化完成")
    
    def analyze_continuous_test_data(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析连续测试数据（优化版，添加性能监控和错误处理）

        Args:
            test_results: 连续测试结果列表

        Returns:
            分析结果字典
        """
        try:
            import time
            start_time = time.time()

            logger.info(f"开始分析连续测试数据，共{len(test_results)}条记录")

            # 数据验证
            if not test_results:
                logger.warning("测试结果为空，无法进行分析")
                return {}

            # 检查数据量，如果过大则记录警告
            if len(test_results) > 10000:
                logger.warning(f"数据量较大({len(test_results)}条)，分析可能需要较长时间")

            # 按通道分组数据
            logger.debug("开始按通道分组数据...")
            channel_data = self._group_data_by_channel(test_results)
            logger.debug(f"数据分组完成，共{len(channel_data)}个通道")

            # 分析每个通道的数据
            logger.debug("开始分析各通道数据...")
            channel_analysis = {}
            for i, (channel_num, data_list) in enumerate(channel_data.items()):
                try:
                    channel_analysis[channel_num] = self._analyze_channel_data(channel_num, data_list)
                    if (i + 1) % 10 == 0:  # 每处理10个通道记录一次进度
                        logger.debug(f"已处理{i + 1}/{len(channel_data)}个通道")
                except Exception as e:
                    logger.error(f"分析通道{channel_num}数据失败: {e}")
                    # 继续处理其他通道，不因单个通道失败而中断
                    continue

            # EIS专业分析频点级别的阻抗分析
            logger.debug("开始进行EIS频点级别阻抗分析...")
            frequency_impedance_analysis = self._analyze_impedance_by_frequency(test_results)

            # 生成整体分析结果（保留原有功能）
            logger.debug("开始生成整体分析结果...")
            overall_analysis = self._generate_overall_analysis(channel_analysis, test_results)

            # EIS专业一致性评价
            logger.debug("开始生成EIS一致性评价...")
            consistency_evaluation = self._evaluate_eis_consistency(channel_analysis, frequency_impedance_analysis)

            # 异常频点识别
            logger.debug("开始识别异常频点...")
            anomalous_frequencies = self._identify_anomalous_frequencies(frequency_impedance_analysis)

            self.analysis_result = {
                'analysis_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'total_records': len(test_results),
                'channel_count': len(channel_data),
                'channel_analysis': channel_analysis,
                'overall_analysis': overall_analysis,
                'consistency_evaluation': consistency_evaluation,
                # 新增EIS专业分析结果
                'frequency_impedance_analysis': frequency_impedance_analysis,
                'anomalous_frequencies': anomalous_frequencies,
                'analysis_type': 'EIS_Professional'  # 标识为EIS专业分析
            }

            elapsed_time = time.time() - start_time
            logger.info(f"连续测试数据分析完成，耗时{elapsed_time:.2f}秒")
            return self.analysis_result

        except Exception as e:
            logger.error(f"分析连续测试数据失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return {}
    
    def _group_data_by_channel(self, test_results: List[Dict[str, Any]]) -> Dict[int, List[Dict[str, Any]]]:
        """按通道分组数据"""
        try:
            channel_data = {}
            
            for result in test_results:
                channel_num = result.get('channel', 0)
                if channel_num > 0:
                    if channel_num not in channel_data:
                        channel_data[channel_num] = []
                    channel_data[channel_num].append(result)
            
            logger.debug(f"数据按通道分组完成，共{len(channel_data)}个通道")
            return channel_data
            
        except Exception as e:
            logger.error(f"按通道分组数据失败: {e}")
            return {}
    
    def _analyze_channel_data(self, channel_num: int, data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析单个通道的数据"""
        try:
            if not data_list:
                return {}
            
            # 提取Rs和Rct值
            rs_values = [item.get('rs_value', 0) for item in data_list if item.get('rs_value', 0) > 0]
            rct_values = [item.get('rct_value', 0) for item in data_list if item.get('rct_value', 0) > 0]
            
            # Rs统计分析
            rs_stats = self._calculate_statistics(rs_values, "Rs")
            
            # Rct统计分析
            rct_stats = self._calculate_statistics(rct_values, "Rct")
            
            # 测试结果统计
            pass_count = sum(1 for item in data_list if item.get('is_pass', False))
            total_count = len(data_list)
            pass_rate = (pass_count / total_count * 100) if total_count > 0 else 0
            
            # 稳定性分析
            stability_analysis = self._analyze_stability(rs_values, rct_values)
            
            analysis = {
                'channel_number': channel_num,
                'test_count': total_count,
                'pass_count': pass_count,
                'fail_count': total_count - pass_count,
                'pass_rate': round(pass_rate, 2),
                'rs_statistics': rs_stats,
                'rct_statistics': rct_stats,
                'stability_analysis': stability_analysis
            }
            
            logger.debug(f"通道{channel_num}数据分析完成")
            return analysis
            
        except Exception as e:
            logger.error(f"分析通道{channel_num}数据失败: {e}")
            return {}
    
    def _calculate_statistics(self, values: List[float], parameter_name: str) -> Dict[str, float]:
        """计算统计指标"""
        try:
            if not values:
                return {
                    'count': 0,
                    'mean': 0,
                    'max': 0,
                    'min': 0,
                    'std_dev': 0,
                    'cv': 0,
                    'range': 0
                }
            
            count = len(values)
            mean = statistics.mean(values)
            max_val = max(values)
            min_val = min(values)
            range_val = max_val - min_val
            
            # 计算标准差
            if count > 1:
                std_dev = statistics.stdev(values)
                cv = (std_dev / mean * 100) if mean != 0 else 0
            else:
                std_dev = 0
                cv = 0
            
            stats = {
                'count': count,
                'mean': round(mean, 3),
                'max': round(max_val, 3),
                'min': round(min_val, 3),
                'std_dev': round(std_dev, 3),
                'cv': round(cv, 2),  # 变异系数，百分比
                'range': round(range_val, 3)
            }
            
            logger.debug(f"{parameter_name}统计计算完成: 均值={mean:.3f}, 标准差={std_dev:.3f}, CV={cv:.2f}%")
            return stats
            
        except Exception as e:
            logger.error(f"计算{parameter_name}统计指标失败: {e}")
            return {}
    
    def _analyze_stability(self, rs_values: List[float], rct_values: List[float]) -> Dict[str, Any]:
        """分析数据稳定性"""
        try:
            stability = {
                'rs_stability': 'unknown',
                'rct_stability': 'unknown',
                'overall_stability': 'unknown',
                'trend_analysis': {}
            }
            
            # 初始化变异系数
            rs_cv = 0
            rct_cv = 0

            # Rs稳定性评估
            if rs_values:
                rs_cv = (statistics.stdev(rs_values) / statistics.mean(rs_values) * 100) if len(rs_values) > 1 and statistics.mean(rs_values) != 0 else 0
                stability['rs_stability'] = self._evaluate_stability_level(rs_cv)

            # Rct稳定性评估
            if rct_values:
                rct_cv = (statistics.stdev(rct_values) / statistics.mean(rct_values) * 100) if len(rct_values) > 1 and statistics.mean(rct_values) != 0 else 0
                stability['rct_stability'] = self._evaluate_stability_level(rct_cv)

            # 整体稳定性评估
            if rs_values and rct_values:
                avg_cv = (rs_cv + rct_cv) / 2
                stability['overall_stability'] = self._evaluate_stability_level(avg_cv)
            
            # 趋势分析（简化版）
            stability['trend_analysis'] = self._analyze_trends(rs_values, rct_values)
            
            return stability
            
        except Exception as e:
            logger.error(f"分析数据稳定性失败: {e}")
            return {}
    
    def _evaluate_stability_level(self, cv: float) -> str:
        """评估稳定性等级"""
        if cv <= 5:
            return "优秀"
        elif cv <= 10:
            return "良好"
        elif cv <= 20:
            return "一般"
        else:
            return "需要关注"
    
    def _analyze_trends(self, rs_values: List[float], rct_values: List[float]) -> Dict[str, str]:
        """分析数据趋势"""
        try:
            trends = {
                'rs_trend': 'stable',
                'rct_trend': 'stable'
            }
            
            # 简化的趋势分析：比较前半部分和后半部分的平均值
            if len(rs_values) >= 4:
                mid_point = len(rs_values) // 2
                first_half_rs = statistics.mean(rs_values[:mid_point])
                second_half_rs = statistics.mean(rs_values[mid_point:])
                
                if second_half_rs > first_half_rs * 1.1:
                    trends['rs_trend'] = 'increasing'
                elif second_half_rs < first_half_rs * 0.9:
                    trends['rs_trend'] = 'decreasing'
            
            if len(rct_values) >= 4:
                mid_point = len(rct_values) // 2
                first_half_rct = statistics.mean(rct_values[:mid_point])
                second_half_rct = statistics.mean(rct_values[mid_point:])
                
                if second_half_rct > first_half_rct * 1.1:
                    trends['rct_trend'] = 'increasing'
                elif second_half_rct < first_half_rct * 0.9:
                    trends['rct_trend'] = 'decreasing'
            
            return trends
            
        except Exception as e:
            logger.error(f"分析数据趋势失败: {e}")
            return {'rs_trend': 'unknown', 'rct_trend': 'unknown'}
    
    def _generate_overall_analysis(self, channel_analysis: Dict[int, Dict], test_results: List[Dict]) -> Dict[str, Any]:
        """生成整体分析结果"""
        try:
            if not channel_analysis:
                return {}
            
            # 收集所有通道的Rs和Rct值
            all_rs_values = []
            all_rct_values = []
            
            for result in test_results:
                if result.get('rs_value', 0) > 0:
                    all_rs_values.append(result['rs_value'])
                if result.get('rct_value', 0) > 0:
                    all_rct_values.append(result['rct_value'])
            
            # 整体统计
            overall_rs_stats = self._calculate_statistics(all_rs_values, "Overall_Rs")
            overall_rct_stats = self._calculate_statistics(all_rct_values, "Overall_Rct")
            
            # 通道间一致性分析
            channel_consistency = self._analyze_channel_consistency(channel_analysis)
            
            overall = {
                'overall_rs_statistics': overall_rs_stats,
                'overall_rct_statistics': overall_rct_stats,
                'channel_consistency': channel_consistency,
                'total_test_cycles': len(set(result.get('cycle', 0) for result in test_results)),
                'active_channels': list(channel_analysis.keys())
            }
            
            return overall
            
        except Exception as e:
            logger.error(f"生成整体分析结果失败: {e}")
            return {}
    
    def _analyze_channel_consistency(self, channel_analysis: Dict[int, Dict]) -> Dict[str, Any]:
        """分析通道间一致性"""
        try:
            if len(channel_analysis) < 2:
                return {'status': 'insufficient_data'}
            
            # 收集各通道的平均值
            channel_rs_means = []
            channel_rct_means = []
            
            for channel_data in channel_analysis.values():
                rs_stats = channel_data.get('rs_statistics', {})
                rct_stats = channel_data.get('rct_statistics', {})
                
                if rs_stats.get('mean', 0) > 0:
                    channel_rs_means.append(rs_stats['mean'])
                if rct_stats.get('mean', 0) > 0:
                    channel_rct_means.append(rct_stats['mean'])
            
            # 计算通道间变异系数
            rs_channel_cv = 0
            rct_channel_cv = 0
            
            if len(channel_rs_means) > 1:
                rs_channel_cv = statistics.stdev(channel_rs_means) / statistics.mean(channel_rs_means) * 100
            
            if len(channel_rct_means) > 1:
                rct_channel_cv = statistics.stdev(channel_rct_means) / statistics.mean(channel_rct_means) * 100
            
            consistency = {
                'rs_channel_cv': round(rs_channel_cv, 2),
                'rct_channel_cv': round(rct_channel_cv, 2),
                'rs_consistency_level': self._evaluate_stability_level(rs_channel_cv),
                'rct_consistency_level': self._evaluate_stability_level(rct_channel_cv)
            }
            
            return consistency
            
        except Exception as e:
            logger.error(f"分析通道间一致性失败: {e}")
            return {}
    
    def _evaluate_consistency(self, channel_analysis: Dict[int, Dict]) -> Dict[str, Any]:
        """评价数据一致性"""
        try:
            if not channel_analysis:
                return {'overall_rating': 'unknown', 'recommendations': []}
            
            # 收集评价指标
            stability_scores = []
            
            for channel_data in channel_analysis.values():
                # 稳定性评分
                rs_stability = channel_data.get('stability_analysis', {}).get('rs_stability', 'unknown')
                rct_stability = channel_data.get('stability_analysis', {}).get('rct_stability', 'unknown')
                
                stability_score = self._convert_level_to_score(rs_stability) + self._convert_level_to_score(rct_stability)
                stability_scores.append(stability_score)
            
            # 计算整体评分
            avg_stability_score = statistics.mean(stability_scores) if stability_scores else 0
            
            # 生成评价结论
            overall_rating = self._generate_overall_rating(avg_stability_score)
            
            # 生成建议
            recommendations = self._generate_recommendations(channel_analysis, avg_stability_score)
            
            evaluation = {
                'overall_rating': overall_rating,
                'stability_score': round(avg_stability_score, 1),
                'recommendations': recommendations,
                'evaluation_criteria': {
                    'excellent': '变异系数 ≤ 5%',
                    'good': '变异系数 ≤ 10%',
                    'fair': '变异系数 ≤ 20%',
                    'needs_attention': '变异系数 > 20%'
                }
            }
            
            return evaluation
            
        except Exception as e:
            logger.error(f"评价数据一致性失败: {e}")
            return {}
    
    def _convert_level_to_score(self, level: str) -> float:
        """将等级转换为分数"""
        level_scores = {
            '优秀': 4.0,
            '良好': 3.0,
            '一般': 2.0,
            '需要关注': 1.0,
            'unknown': 0.0
        }
        return level_scores.get(level, 0.0)
    
    def _generate_overall_rating(self, score: float) -> str:
        """生成整体评价"""
        if score >= 3.5:
            return "优秀"
        elif score >= 2.5:
            return "良好"
        elif score >= 1.5:
            return "一般"
        else:
            return "需要关注"
    
    def _generate_recommendations(self, channel_analysis: Dict[int, Dict], score: float) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        try:
            if score < 2.0:
                recommendations.append("建议检查测试设备的稳定性和校准状态")
                recommendations.append("检查电池样品的一致性和存储条件")
                recommendations.append("考虑增加测试前的预处理时间")
            
            elif score < 3.0:
                recommendations.append("建议优化测试环境的温度和湿度控制")
                recommendations.append("检查测试夹具的接触稳定性")
            
            else:
                recommendations.append("测试数据一致性良好，可继续当前测试流程")
            
            # 检查特定问题
            for channel_num, data in channel_analysis.items():
                rs_cv = data.get('rs_statistics', {}).get('cv', 0)
                rct_cv = data.get('rct_statistics', {}).get('cv', 0)
                
                if rs_cv > 20 or rct_cv > 20:
                    recommendations.append(f"通道{channel_num}数据离散度较大，建议重点检查")
            
            return recommendations
            
        except Exception as e:
            logger.error(f"生成改进建议失败: {e}")
            return ["数据分析异常，建议检查测试系统"]
    
    def get_analysis_result(self) -> Dict[str, Any]:
        """获取分析结果"""
        return self.analysis_result.copy()

    def _analyze_impedance_by_frequency(self, test_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        按频点分析阻抗数据（EIS专业分析）

        Args:
            test_results: 测试结果列表

        Returns:
            频点级别的阻抗分析结果
        """
        try:
            logger.info("开始进行EIS频点级别阻抗分析...")

            # 提取所有频点的阻抗数据
            frequency_data = {}  # {frequency: {channel: [impedance_data_list]}}

            for result in test_results:
                # 从测试结果中提取频点数据
                frequency_data_list = result.get('frequency_data', [])
                channel = result.get('channel', 0)

                if not frequency_data_list or not channel:
                    continue

                for freq_point in frequency_data_list:
                    frequency = freq_point.get('frequency', 0)
                    if frequency <= 0:
                        continue

                    # 提取阻抗数据
                    impedance_real = freq_point.get('impedance_real', 0.0)  # mΩ
                    impedance_imag = freq_point.get('impedance_imag', 0.0)  # mΩ
                    impedance_magnitude = freq_point.get('impedance_magnitude', 0.0)  # mΩ
                    impedance_phase = freq_point.get('impedance_phase', 0.0)  # 度

                    # 计算阻抗模值和相位角（如果没有提供）
                    if impedance_magnitude == 0.0 and (impedance_real != 0.0 or impedance_imag != 0.0):
                        impedance_magnitude = math.sqrt(impedance_real**2 + impedance_imag**2)

                    if impedance_phase == 0.0 and impedance_real != 0.0:
                        # 修复相位角计算 - 不再对虚部取反，因为设备数据已经是正确符号
                        impedance_phase = math.degrees(math.atan2(impedance_imag, impedance_real))

                    # 组织数据
                    impedance_data = {
                        'real': impedance_real,
                        'imag': impedance_imag,
                        'magnitude': impedance_magnitude,
                        'phase': impedance_phase,
                        'timestamp': result.get('timestamp', ''),
                        'cycle': result.get('cycle', 0)
                    }

                    # 存储数据
                    if frequency not in frequency_data:
                        frequency_data[frequency] = {}
                    if channel not in frequency_data[frequency]:
                        frequency_data[frequency][channel] = []

                    frequency_data[frequency][channel].append(impedance_data)

            # 分析每个频点的统计数据
            frequency_analysis = {}

            for frequency in sorted(frequency_data.keys()):
                freq_channels = frequency_data[frequency]

                # 计算该频点下所有通道的统计数据
                all_magnitudes = []
                all_phases = []
                all_reals = []
                all_imags = []

                channel_stats = {}

                for channel, impedance_list in freq_channels.items():
                    if not impedance_list:
                        continue

                    # 提取该通道在该频点的所有测量值
                    channel_magnitudes = [data['magnitude'] for data in impedance_list]
                    channel_phases = [data['phase'] for data in impedance_list]
                    channel_reals = [data['real'] for data in impedance_list]
                    channel_imags = [data['imag'] for data in impedance_list]

                    # 计算通道级统计
                    channel_stats[channel] = {
                        'magnitude_stats': self._calculate_impedance_statistics(channel_magnitudes),
                        'phase_stats': self._calculate_impedance_statistics(channel_phases),
                        'real_stats': self._calculate_impedance_statistics(channel_reals),
                        'imag_stats': self._calculate_impedance_statistics(channel_imags),
                        'test_count': len(impedance_list)
                    }

                    # 收集到整体统计
                    all_magnitudes.extend(channel_magnitudes)
                    all_phases.extend(channel_phases)
                    all_reals.extend(channel_reals)
                    all_imags.extend(channel_imags)

                # 计算该频点的整体统计
                frequency_analysis[frequency] = {
                    'overall_magnitude_stats': self._calculate_impedance_statistics(all_magnitudes),
                    'overall_phase_stats': self._calculate_impedance_statistics(all_phases),
                    'overall_real_stats': self._calculate_impedance_statistics(all_reals),
                    'overall_imag_stats': self._calculate_impedance_statistics(all_imags),
                    'channel_stats': channel_stats,
                    'total_measurements': len(all_magnitudes),
                    'channel_count': len(channel_stats)
                }

            logger.info(f"EIS频点分析完成，共分析{len(frequency_analysis)}个频点")

            return {
                'frequency_count': len(frequency_analysis),
                'frequency_analysis': frequency_analysis,
                'analyzed_frequencies': sorted(frequency_data.keys())
            }

        except Exception as e:
            logger.error(f"EIS频点级别阻抗分析失败: {e}")
            import traceback
            logger.error(f"详细错误信息: {traceback.format_exc()}")
            return {}

    def _calculate_impedance_statistics(self, values: List[float]) -> Dict[str, float]:
        """
        计算阻抗统计指标

        Args:
            values: 数值列表

        Returns:
            统计指标字典
        """
        try:
            if not values:
                return {
                    'mean': 0.0,
                    'std_dev': 0.0,
                    'cv': 0.0,
                    'min': 0.0,
                    'max': 0.0,
                    'count': 0
                }

            mean_val = statistics.mean(values)
            std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
            cv = (std_dev / mean_val * 100) if mean_val != 0 else 0.0

            return {
                'mean': round(mean_val, 6),
                'std_dev': round(std_dev, 6),
                'cv': round(cv, 3),
                'min': round(min(values), 6),
                'max': round(max(values), 6),
                'count': len(values)
            }

        except Exception as e:
            logger.error(f"计算阻抗统计指标失败: {e}")
            return {
                'mean': 0.0,
                'std_dev': 0.0,
                'cv': 0.0,
                'min': 0.0,
                'max': 0.0,
                'count': 0
            }

    def _evaluate_eis_consistency(self, channel_analysis: Dict[int, Dict],
                                 frequency_impedance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        EIS专业一致性评价

        Args:
            channel_analysis: 通道分析结果
            frequency_impedance_analysis: 频点阻抗分析结果

        Returns:
            EIS一致性评价结果
        """
        try:
            logger.info("开始进行EIS专业一致性评价...")

            # 基于频点的一致性评价
            frequency_consistency = self._evaluate_frequency_consistency(frequency_impedance_analysis)

            # 通道间一致性评价
            channel_consistency = self._evaluate_channel_consistency(channel_analysis)

            # 整体EIS评价
            overall_rating = self._calculate_eis_overall_rating(frequency_consistency, channel_consistency)

            # EIS专业建议
            eis_recommendations = self._generate_eis_recommendations(
                frequency_consistency, channel_consistency, overall_rating
            )

            return {
                'analysis_type': 'EIS_Professional',
                'frequency_consistency': frequency_consistency,
                'channel_consistency': channel_consistency,
                'overall_rating': overall_rating,
                'eis_recommendations': eis_recommendations,
                'evaluation_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        except Exception as e:
            logger.error(f"EIS一致性评价失败: {e}")
            return {
                'analysis_type': 'EIS_Professional',
                'overall_rating': 'unknown',
                'error': str(e)
            }

    def _identify_anomalous_frequencies(self, frequency_impedance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        识别异常频点

        Args:
            frequency_impedance_analysis: 频点阻抗分析结果

        Returns:
            异常频点识别结果
        """
        try:
            logger.info("开始识别异常频点...")

            frequency_analysis = frequency_impedance_analysis.get('frequency_analysis', {})
            anomalous_frequencies = []

            # 定义异常判断标准
            cv_threshold = 15.0  # 变异系数阈值（%）
            phase_deviation_threshold = 30.0  # 相位角偏差阈值（度）

            for frequency, freq_data in frequency_analysis.items():
                anomaly_reasons = []

                # 检查阻抗模值变异系数
                magnitude_cv = freq_data.get('overall_magnitude_stats', {}).get('cv', 0)
                if magnitude_cv > cv_threshold:
                    anomaly_reasons.append(f"阻抗模值变异系数过大({magnitude_cv:.2f}%)")

                # 检查相位角变异系数
                phase_cv = freq_data.get('overall_phase_stats', {}).get('cv', 0)
                if phase_cv > cv_threshold:
                    anomaly_reasons.append(f"相位角变异系数过大({phase_cv:.2f}%)")

                # 检查相位角异常值
                phase_mean = freq_data.get('overall_phase_stats', {}).get('mean', 0)
                if abs(phase_mean) > phase_deviation_threshold:
                    anomaly_reasons.append(f"相位角异常({phase_mean:.2f}°)")

                # 如果有异常，记录该频点
                if anomaly_reasons:
                    anomalous_frequencies.append({
                        'frequency': frequency,
                        'anomaly_reasons': anomaly_reasons,
                        'magnitude_cv': magnitude_cv,
                        'phase_cv': phase_cv,
                        'phase_mean': phase_mean
                    })

            # 按异常严重程度排序
            anomalous_frequencies.sort(key=lambda x: len(x['anomaly_reasons']), reverse=True)

            logger.info(f"异常频点识别完成，发现{len(anomalous_frequencies)}个异常频点")

            return {
                'anomalous_count': len(anomalous_frequencies),
                'anomalous_frequencies': anomalous_frequencies,
                'total_frequencies': len(frequency_analysis),
                'anomaly_rate': len(anomalous_frequencies) / len(frequency_analysis) * 100 if frequency_analysis else 0
            }

        except Exception as e:
            logger.error(f"识别异常频点失败: {e}")
            return {
                'anomalous_count': 0,
                'anomalous_frequencies': [],
                'error': str(e)
            }

    def _evaluate_frequency_consistency(self, frequency_impedance_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        评价频点间一致性

        Args:
            frequency_impedance_analysis: 频点阻抗分析结果

        Returns:
            频点一致性评价结果
        """
        try:
            frequency_analysis = frequency_impedance_analysis.get('frequency_analysis', {})

            if not frequency_analysis:
                return {'consistency_rating': 'unknown', 'error': 'no_frequency_data'}

            # 收集所有频点的变异系数
            magnitude_cvs = []
            phase_cvs = []

            for freq_data in frequency_analysis.values():
                magnitude_cv = freq_data.get('overall_magnitude_stats', {}).get('cv', 0)
                phase_cv = freq_data.get('overall_phase_stats', {}).get('cv', 0)

                magnitude_cvs.append(magnitude_cv)
                phase_cvs.append(phase_cv)

            # 计算频点间一致性指标
            avg_magnitude_cv = statistics.mean(magnitude_cvs) if magnitude_cvs else 0
            avg_phase_cv = statistics.mean(phase_cvs) if phase_cvs else 0

            # 评价一致性等级
            if avg_magnitude_cv < 5.0 and avg_phase_cv < 10.0:
                consistency_rating = 'excellent'
            elif avg_magnitude_cv < 10.0 and avg_phase_cv < 20.0:
                consistency_rating = 'good'
            elif avg_magnitude_cv < 15.0 and avg_phase_cv < 30.0:
                consistency_rating = 'fair'
            else:
                consistency_rating = 'poor'

            return {
                'consistency_rating': consistency_rating,
                'avg_magnitude_cv': round(avg_magnitude_cv, 3),
                'avg_phase_cv': round(avg_phase_cv, 3),
                'frequency_count': len(frequency_analysis),
                'magnitude_cv_range': [round(min(magnitude_cvs), 3), round(max(magnitude_cvs), 3)] if magnitude_cvs else [0, 0],
                'phase_cv_range': [round(min(phase_cvs), 3), round(max(phase_cvs), 3)] if phase_cvs else [0, 0]
            }

        except Exception as e:
            logger.error(f"评价频点一致性失败: {e}")
            return {'consistency_rating': 'unknown', 'error': str(e)}

    def _evaluate_channel_consistency(self, channel_analysis: Dict[int, Dict]) -> Dict[str, Any]:
        """
        评价通道间一致性

        Args:
            channel_analysis: 通道分析结果

        Returns:
            通道一致性评价结果
        """
        try:
            if not channel_analysis:
                return {'consistency_rating': 'unknown', 'error': 'no_channel_data'}

            # 收集所有通道的Rs和Rct变异系数
            rs_cvs = []
            rct_cvs = []

            for channel_data in channel_analysis.values():
                rs_cv = channel_data.get('rs_statistics', {}).get('cv', 0)
                rct_cv = channel_data.get('rct_statistics', {}).get('cv', 0)

                rs_cvs.append(rs_cv)
                rct_cvs.append(rct_cv)

            # 计算通道间一致性指标
            avg_rs_cv = statistics.mean(rs_cvs) if rs_cvs else 0
            avg_rct_cv = statistics.mean(rct_cvs) if rct_cvs else 0

            # 评价一致性等级
            if avg_rs_cv < 5.0 and avg_rct_cv < 5.0:
                consistency_rating = 'excellent'
            elif avg_rs_cv < 10.0 and avg_rct_cv < 10.0:
                consistency_rating = 'good'
            elif avg_rs_cv < 15.0 and avg_rct_cv < 15.0:
                consistency_rating = 'fair'
            else:
                consistency_rating = 'poor'

            return {
                'consistency_rating': consistency_rating,
                'avg_rs_cv': round(avg_rs_cv, 3),
                'avg_rct_cv': round(avg_rct_cv, 3),
                'channel_count': len(channel_analysis),
                'rs_cv_range': [round(min(rs_cvs), 3), round(max(rs_cvs), 3)] if rs_cvs else [0, 0],
                'rct_cv_range': [round(min(rct_cvs), 3), round(max(rct_cvs), 3)] if rct_cvs else [0, 0]
            }

        except Exception as e:
            logger.error(f"评价通道一致性失败: {e}")
            return {'consistency_rating': 'unknown', 'error': str(e)}

    def _calculate_eis_overall_rating(self, frequency_consistency: Dict[str, Any],
                                     channel_consistency: Dict[str, Any]) -> str:
        """
        计算EIS整体评价等级

        Args:
            frequency_consistency: 频点一致性结果
            channel_consistency: 通道一致性结果

        Returns:
            整体评价等级
        """
        try:
            freq_rating = frequency_consistency.get('consistency_rating', 'unknown')
            channel_rating = channel_consistency.get('consistency_rating', 'unknown')

            # 评价等级映射
            rating_scores = {
                'excellent': 4,
                'good': 3,
                'fair': 2,
                'poor': 1,
                'unknown': 0
            }

            freq_score = rating_scores.get(freq_rating, 0)
            channel_score = rating_scores.get(channel_rating, 0)

            # 计算综合评分（频点权重60%，通道权重40%）
            overall_score = freq_score * 0.6 + channel_score * 0.4

            # 转换为评价等级
            if overall_score >= 3.5:
                return 'excellent'
            elif overall_score >= 2.5:
                return 'good'
            elif overall_score >= 1.5:
                return 'fair'
            elif overall_score >= 0.5:
                return 'poor'
            else:
                return 'unknown'

        except Exception as e:
            logger.error(f"计算EIS整体评价失败: {e}")
            return 'unknown'

    def _generate_eis_recommendations(self, frequency_consistency: Dict[str, Any],
                                     channel_consistency: Dict[str, Any],
                                     overall_rating: str) -> List[str]:
        """
        生成EIS专业建议

        Args:
            frequency_consistency: 频点一致性结果
            channel_consistency: 通道一致性结果
            overall_rating: 整体评价等级

        Returns:
            EIS专业建议列表
        """
        try:
            recommendations = []

            # 基于整体评价的建议
            if overall_rating == 'excellent':
                recommendations.append("EIS测试数据质量优秀，阻抗谱一致性良好")
                recommendations.append("建议保持当前测试条件和设备校准状态")
            elif overall_rating == 'good':
                recommendations.append("EIS测试数据质量良好，可继续当前测试流程")
                recommendations.append("建议定期检查设备校准和测试环境稳定性")
            elif overall_rating == 'fair':
                recommendations.append("EIS测试数据一致性一般，建议优化测试条件")
                recommendations.append("检查电极接触稳定性和测试夹具状态")
            else:
                recommendations.append("EIS测试数据一致性较差，需要重点检查测试系统")
                recommendations.append("建议重新校准阻抗分析仪和检查测试环境")

            # 基于频点一致性的专业建议
            freq_rating = frequency_consistency.get('consistency_rating', 'unknown')
            avg_magnitude_cv = frequency_consistency.get('avg_magnitude_cv', 0)
            avg_phase_cv = frequency_consistency.get('avg_phase_cv', 0)

            if freq_rating == 'poor':
                recommendations.append(f"频点间阻抗一致性较差（|Z|变异系数: {avg_magnitude_cv:.2f}%）")
                recommendations.append("建议检查频率扫描设置和信号发生器稳定性")

                if avg_phase_cv > 30:
                    recommendations.append(f"相位角变异过大（{avg_phase_cv:.2f}%），检查相位校准")

            # 基于通道一致性的建议
            channel_rating = channel_consistency.get('consistency_rating', 'unknown')
            avg_rs_cv = channel_consistency.get('avg_rs_cv', 0)
            avg_rct_cv = channel_consistency.get('avg_rct_cv', 0)

            if channel_rating == 'poor':
                recommendations.append(f"通道间一致性较差（Rs变异系数: {avg_rs_cv:.2f}%）")
                recommendations.append("建议检查各通道的电极接触和夹具一致性")

                if avg_rct_cv > 15:
                    recommendations.append(f"Rct变异过大（{avg_rct_cv:.2f}%），检查电化学界面稳定性")

            # EIS专业技术建议
            if avg_magnitude_cv > 10:
                recommendations.append("建议增加测试前的电池预处理时间，确保电化学稳定")

            if avg_phase_cv > 20:
                recommendations.append("相位角偏差较大，建议检查交流信号幅值和直流偏置设置")

            return recommendations

        except Exception as e:
            logger.error(f"生成EIS专业建议失败: {e}")
            return ["EIS分析异常，建议检查测试系统和数据完整性"]
