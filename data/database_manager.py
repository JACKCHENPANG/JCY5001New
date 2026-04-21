# -*- coding: utf-8 -*-
"""
数据库管理器
负责测试数据的存储、查询和管理

Author: Jack
Date: 2025-01-27
"""

import sqlite3
import os
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple, Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """数据库管理器类"""

    def __init__(self, db_path: str = "data/test_results.db", config_manager=None):
        """
        初始化数据库管理器

        Args:
            db_path: 数据库文件路径
            config_manager: 配置管理器（可选）
        """
        self.db_path = db_path
        self.config_manager = config_manager

        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        # 初始化数据库
        self._init_database()

        # 执行数据库迁移
        self._migrate_database()

        logger.debug(f"数据库管理器初始化完成: {db_path}")

    def _init_database(self):
        """初始化数据库表结构"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 创建批次表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS batches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_number TEXT UNIQUE NOT NULL,
                        operator TEXT NOT NULL,
                        cell_type TEXT NOT NULL,
                        cell_spec TEXT NOT NULL,
                        standard_voltage REAL NOT NULL,
                        standard_capacity INTEGER NOT NULL,
                        start_time TIMESTAMP NOT NULL,
                        end_time TIMESTAMP,
                        total_count INTEGER DEFAULT 0,
                        pass_count INTEGER DEFAULT 0,
                        fail_count INTEGER DEFAULT 0,
                        yield_rate REAL DEFAULT 0.0,
                        remarks TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # 创建测试结果表（Jack要求清理后的简化版本）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS test_results (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_id INTEGER NOT NULL,
                        channel_number INTEGER NOT NULL,
                        battery_code TEXT NOT NULL,
                        test_start_time TIMESTAMP NOT NULL,
                        test_end_time TIMESTAMP,
                        test_duration REAL,
                        voltage REAL,
                        rs_value REAL,
                        rct_value REAL,
                        rs_grade INTEGER,
                        rct_grade INTEGER,
                        is_pass BOOLEAN NOT NULL,
                        fail_reason TEXT,
                        test_mode TEXT NOT NULL,
                        frequency_list TEXT,
                        raw_data TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (batch_id) REFERENCES batches (id)
                    )
                ''')

                # 创建频率数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS frequency_data (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        test_result_id INTEGER NOT NULL,
                        frequency REAL NOT NULL,
                        impedance_real REAL NOT NULL,
                        impedance_imag REAL NOT NULL,
                        impedance_magnitude REAL NOT NULL,
                        impedance_phase REAL NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (test_result_id) REFERENCES test_results (id)
                    )
                ''')

                # 创建阻抗测试明细数据表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS impedance_details (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        batch_id INTEGER NOT NULL,
                        channel_number INTEGER NOT NULL,
                        battery_code TEXT NOT NULL,
                        test_timestamp TEXT NOT NULL,
                        frequency REAL NOT NULL,
                        impedance_real REAL NOT NULL,
                        impedance_imag REAL NOT NULL,
                        voltage REAL,
                        test_sequence INTEGER,
                        z_value REAL,
                        baseline_z_value REAL,
                        deviation_percent REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (batch_id) REFERENCES batches (id)
                    )
                ''')

                # 新增创建上传队列表（断点续传支持）
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS upload_queue (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        upload_id TEXT UNIQUE NOT NULL,
                        data_type TEXT NOT NULL,  -- 'test_result' 或 'impedance_data'
                        test_result_id INTEGER,   -- 关联的测试结果ID
                        upload_data TEXT NOT NULL, -- JSON格式的上传数据
                        status TEXT NOT NULL DEFAULT 'pending', -- pending, uploading, completed, failed
                        retry_count INTEGER DEFAULT 0,
                        max_retries INTEGER DEFAULT 3,
                        priority INTEGER DEFAULT 0, -- 优先级，数字越大优先级越高
                        error_message TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP
                    )
                ''')

                # 为上传队列表创建索引
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_upload_queue_status
                    ON upload_queue (status)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_upload_queue_priority
                    ON upload_queue (priority DESC, created_at ASC)
                ''')

                # 创建系统日志表
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS system_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        module TEXT,
                        function TEXT,
                        line_number INTEGER,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')



                # 创建索引
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_batches_number ON batches (batch_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_results_batch ON test_results (batch_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_results_channel ON test_results (channel_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_test_results_time ON test_results (test_start_time)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_frequency_data_test ON frequency_data (test_result_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_impedance_details_batch ON impedance_details (batch_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_impedance_details_channel ON impedance_details (channel_number)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_impedance_details_timestamp ON impedance_details (test_timestamp)')


                conn.commit()
                logger.debug("数据库表结构初始化完成")

        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise

    def _migrate_database(self):
        """执行数据库迁移，添加新字段"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 检查test_results表是否需要添加离群率字段
                cursor.execute("PRAGMA table_info(test_results)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]

                # Jack要求清理后的字段（移除了Rsei、阻抗比、相位角、电容、时间常数、贡献度、健康状态、分析方法、离群率、基准ID等）
                new_fields = [
                    ('operator', 'TEXT'),  # 操作员
                    ('battery_type', 'TEXT'),  # 电池类型
                    ('battery_spec', 'TEXT'),  # 电池规格
                    ('batch_number', 'TEXT'),  # 新增测试时的实际批次号
                    ('rct_coefficient_of_variation', 'REAL'),  # Rct变异系数
                    ('voltage_range_min', 'REAL'),  # 电压范围最小值
                    ('voltage_range_max', 'REAL'),  # 电压范围最大值
                    ('rs_range_min', 'REAL'),  # Rs范围最小值
                    ('rs_range_max', 'REAL'),  # Rs范围最大值
                    ('rct_range_min', 'REAL'),  # Rct范围最小值
                    ('rct_range_max', 'REAL')  # Rct范围最大值
                ]

                for field_name, field_type in new_fields:
                    if field_name not in column_names:
                        try:
                            cursor.execute(f'ALTER TABLE test_results ADD COLUMN {field_name} {field_type}')
                            logger.info(f"添加test_results表字段: {field_name}")
                        except Exception as e:
                            logger.warning(f"添加test_results表字段{field_name}失败: {e}")

                # 检查impedance_details表是否需要添加离群率字段
                cursor.execute("PRAGMA table_info(impedance_details)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]

                # 需要添加的离群率字段
                detail_outlier_fields = [
                    ('z_value', 'REAL'),
                    ('baseline_z_value', 'REAL'),
                    ('deviation_percent', 'REAL')
                ]

                for field_name, field_type in detail_outlier_fields:
                    if field_name not in column_names:
                        try:
                            cursor.execute(f'ALTER TABLE impedance_details ADD COLUMN {field_name} {field_type}')
                            logger.info(f"添加impedance_details表字段: {field_name}")
                        except Exception as e:
                            logger.warning(f"添加impedance_details表字段{field_name}失败: {e}")

                conn.commit()
                logger.info("数据库迁移完成")

        except Exception as e:
            logger.error(f"数据库迁移失败: {e}")
            # 迁移失败不应该阻止程序启动
            pass

    @contextmanager
    def get_connection(self):
        """获取数据库连接的上下文管理器"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # 使结果可以按列名访问
            # 性能优化：设置SQLite PRAGMA，提升批量写入速度
            try:
                # 更好的并发与写入性能
                conn.execute('PRAGMA journal_mode=WAL')
                # 降低fsync次数，权衡安全与性能
                conn.execute('PRAGMA synchronous=NORMAL')
                # 临时表/索引放内存
                conn.execute('PRAGMA temp_store=MEMORY')
                # 约20MB页缓存（负值=KB）
                conn.execute('PRAGMA cache_size=-20000')
                # 保持外键
                conn.execute('PRAGMA foreign_keys=ON')
                # 写阻塞等待3s，减少锁冲突失败
                conn.execute('PRAGMA busy_timeout=3000')
            except Exception as pragma_e:
                logger.debug(f"PRAGMA设置失败: {pragma_e}")
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def create_batch(self, batch_info: Dict[str, Any]) -> int:
        """
        创建新批次

        Args:
            batch_info: 批次信息字典

        Returns:
            批次ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO batches (
                        batch_number, operator, cell_type, cell_spec,
                        standard_voltage, standard_capacity, start_time, remarks
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    batch_info['batch_number'],
                    batch_info['operator'],
                    batch_info['cell_type'],
                    batch_info['cell_spec'],
                    batch_info['standard_voltage'],
                    batch_info['standard_capacity'],
                    datetime.now(),
                    batch_info.get('remarks', '')
                ))

                batch_id = cursor.lastrowid
                conn.commit()

                logger.info(f"批次创建成功: {batch_info['batch_number']} (ID: {batch_id})")
                return batch_id

        except sqlite3.IntegrityError as e:
            # 检查是否是批次号重复错误
            if "batch_number" in str(e):
                # 修复批次号重复时，直接返回现有批次ID，不生成新批次号
                logger.info(f"批次号已存在，重用现有批次: {batch_info['batch_number']}")
                existing_batch = self.get_batch_by_number(batch_info['batch_number'])
                if existing_batch:
                    return existing_batch['id']
                else:
                    # 如果查找失败，说明数据库状态异常，记录错误但不创建重复批次
                    logger.error(f"批次号重复但无法找到现有批次: {batch_info['batch_number']}")
                    raise Exception(f"数据库状态异常：批次号 {batch_info['batch_number']} 重复但无法查找到")
            else:
                logger.error(f"数据库完整性错误: {e}")
                raise
        except Exception as e:
            logger.error(f"创建批次失败: {e}")
            raise

    def get_batch_by_number(self, batch_number: str) -> Optional[Dict[str, Any]]:
        """
        根据批次号获取批次信息

        Args:
            batch_number: 批次号

        Returns:
            批次信息字典，如果不存在返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('SELECT * FROM batches WHERE batch_number = ?', (batch_number,))
                row = cursor.fetchone()

                if row:
                    return dict(row)
                return None

        except Exception as e:
            logger.error(f"获取批次信息失败: {e}")
            raise

    def update_batch_statistics(self, batch_id: int):
        """
        更新批次统计信息

        Args:
            batch_id: 批次ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 计算统计数据
                cursor.execute('''
                    SELECT
                        COUNT(*) as total_count,
                        SUM(CASE WHEN is_pass = 1 THEN 1 ELSE 0 END) as pass_count,
                        SUM(CASE WHEN is_pass = 0 THEN 1 ELSE 0 END) as fail_count
                    FROM test_results
                    WHERE batch_id = ?
                ''', (batch_id,))

                stats = cursor.fetchone()
                total_count = stats['total_count']
                pass_count = stats['pass_count']
                fail_count = stats['fail_count']
                yield_rate = (pass_count / total_count * 100) if total_count > 0 else 0.0

                # 更新批次统计
                cursor.execute('''
                    UPDATE batches
                    SET total_count = ?, pass_count = ?, fail_count = ?,
                        yield_rate = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (total_count, pass_count, fail_count, yield_rate, batch_id))

                conn.commit()
                logger.debug(f"批次统计更新完成: ID={batch_id}, 总数={total_count}, 良率={yield_rate:.1f}%")

        except Exception as e:
            logger.error(f"更新批次统计失败: {e}")
            raise

    def save_test_result(self, test_data: Dict[str, Any]) -> int:
        """
        保存测试结果

        Args:
            test_data: 测试数据字典

        Returns:
            测试结果ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Jack要求清理后的数据存储前进行单位转换验证（只验证Rs和Rct）
                from utils.impedance_unit_validator import ImpedanceUnitValidator

                # 验证和修正单位（只处理Rs和Rct）
                unit_fix_result = ImpedanceUnitValidator.fix_database_unit_conversion(
                    rs_db=test_data['rs_value'],
                    rct_db=test_data['rct_value'],
                    rsei_db=None,  # Jack要求移除Rsei
                    w_coefficient=None  # Jack要求移除W系数
                )

                # 使用修正后的值
                rs_value_corrected = unit_fix_result['rs_mohm']
                rct_value_corrected = unit_fix_result['rct_mohm']

                # 参数验证（只验证Rs和Rct）
                validation_result = ImpedanceUnitValidator.validate_eis_parameters(
                    rs=rs_value_corrected,
                    rct=rct_value_corrected,
                    rsei=None,  # Jack要求移除Rsei
                    w_coefficient=None  # Jack要求移除W系数
                )

                if not validation_result['overall_valid']:
                    logger.warning(f"EIS参数验证失败: {validation_result['errors']}")
                    if validation_result['warnings']:
                        logger.warning(f"EIS参数警告: {validation_result['warnings']}")

                # 🔍 [DEBUG] 外键约束调试 - 检查批次是否存在
                cursor.execute("SELECT COUNT(*) FROM batches WHERE id = ?", (test_data['batch_id'],))
                batch_exists = cursor.fetchone()[0]
                if batch_exists == 0:
                    logger.error(f"❌ 批次ID {test_data['batch_id']} 不存在，无法插入测试结果")
                    # 尝试查询最近的批次
                    cursor.execute("SELECT id, batch_number FROM batches ORDER BY id DESC LIMIT 3")
                    recent_batches = cursor.fetchall()
                    logger.error(f"最近的批次: {recent_batches}")
                    raise ValueError(f"批次ID {test_data['batch_id']} 不存在")

                logger.debug(f"🔍 [DEBUG] 批次ID {test_data['batch_id']} 存在，准备插入测试结果")
                logger.debug(f"🔍 [DEBUG] 电池码: {test_data['battery_code']}, Rs: {rs_value_corrected:.3f}mΩ, Rct: {rct_value_corrected:.3f}mΩ")

                # Jack要求清理后的插入测试结果（移除了已删除的字段）
                cursor.execute('''
                    INSERT INTO test_results (
                        batch_id, channel_number, battery_code, test_start_time,
                        test_end_time, test_duration, voltage, rs_value, rct_value,
                        rs_grade, rct_grade, is_pass, fail_reason,
                        test_mode, frequency_list, raw_data,
                        operator, battery_type, battery_spec, batch_number, rct_coefficient_of_variation,
                        voltage_range_min, voltage_range_max, rs_range_min, rs_range_max, rct_range_min, rct_range_max
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    test_data['batch_id'],
                    test_data['channel_number'],
                    test_data['battery_code'],
                    test_data['test_start_time'],
                    test_data['test_end_time'],
                    test_data['test_duration'],
                    test_data['voltage'],
                    rs_value_corrected,  # 使用修正后的值
                    rct_value_corrected,  # 使用修正后的值
                    test_data.get('rs_grade'),
                    test_data.get('rct_grade'),
                    test_data['is_pass'],
                    test_data.get('fail_reason'),
                    test_data['test_mode'],
                    json.dumps(test_data.get('frequency_list', [])),
                    json.dumps(test_data.get('raw_data', {})),
                    test_data.get('operator'),
                    test_data.get('battery_type'),
                    test_data.get('battery_spec'),
                    test_data.get('batch_number'),  # 新增保存测试时的实际批次号
                    test_data.get('rct_coefficient_of_variation'),
                    test_data.get('voltage_range_min'),
                    test_data.get('voltage_range_max'),
                    test_data.get('rs_range_min'),
                    test_data.get('rs_range_max'),
                    test_data.get('rct_range_min'),
                    test_data.get('rct_range_max')
                ))

                test_result_id = cursor.lastrowid

                # 保存频率数据（性能优化：批量插入）
                if 'frequency_data' in test_data and test_data['frequency_data']:
                    records = [
                        (
                            test_result_id,
                            fd['frequency'],
                            fd['impedance_real'],
                            fd['impedance_imag'],
                            fd['impedance_magnitude'],
                            fd['impedance_phase']
                        )
                        for fd in test_data['frequency_data']
                    ]
                    cursor.executemany('''
                        INSERT INTO frequency_data (
                            test_result_id, frequency, impedance_real, impedance_imag,
                            impedance_magnitude, impedance_phase
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    ''', records)

                conn.commit()

                # 更新批次统计
                self.update_batch_statistics(test_data['batch_id'])

                logger.info(f"测试结果保存成功: {test_data['battery_code']} (ID: {test_result_id})")

                # 移除重复的打印触发，避免重复打印（打印由test_result_manager统一处理）
                # self._trigger_auto_print_for_saved_result(test_data, test_result_id)

                return test_result_id

        except Exception as e:
            logger.error(f"数据库操作失败: {e}")

            # 🔍 [DEBUG] 详细错误分析
            if "FOREIGN KEY constraint failed" in str(e):
                logger.error("❌ 外键约束失败详细分析:")
                logger.error(f"   批次ID: {test_data.get('batch_id', 'UNKNOWN')}")
                logger.error(f"   电池码: {test_data.get('battery_code', 'UNKNOWN')}")
                logger.error(f"   通道号: {test_data.get('channel_number', 'UNKNOWN')}")

                # 检查批次是否存在
                try:
                    with self.get_connection() as check_conn:
                        check_cursor = check_conn.cursor()
                        check_cursor.execute("SELECT COUNT(*) FROM batches WHERE id = ?", (test_data.get('batch_id'),))
                        batch_count = check_cursor.fetchone()[0]
                        logger.error(f"   批次存在检查: {batch_count > 0} (数量: {batch_count})")

                        if batch_count == 0:
                            logger.error("   🔧 尝试创建缺失的批次...")
                            check_cursor.execute('''
                                INSERT OR IGNORE INTO batches (id, batch_number, created_at, total_count, pass_count, fail_count)
                                VALUES (?, ?, datetime('now'), 0, 0, 0)
                            ''', (test_data.get('batch_id'), test_data.get('batch_number', 'UNKNOWN')))
                            check_conn.commit()
                            logger.info(f"   ✅ 批次 {test_data.get('batch_id')} 创建成功")
                except Exception as check_e:
                    logger.error(f"   批次检查失败: {check_e}")

            raise

    def save_impedance_detail(self, detail_data: Dict[str, Any]) -> int:
        """
        保存阻抗测试明细数据

        Args:
            detail_data: 明细数据字典，包含：
                - batch_id: 批次ID
                - channel_number: 通道号 (1-8)
                - battery_code: 电池码
                - test_timestamp: ISO格式时间戳
                - frequency: 测试频点 (Hz)
                - impedance_real: 阻抗实部 (mΩ)
                - impedance_imag: 阻抗虚部 (mΩ)
                - voltage: 电压 (V)
                - test_sequence: 测试序号

        Returns:
            明细记录ID
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO impedance_details (
                        batch_id, channel_number, battery_code, test_timestamp,
                        frequency, impedance_real, impedance_imag, voltage, test_sequence,
                        z_value, baseline_z_value, deviation_percent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    detail_data['batch_id'],
                    detail_data['channel_number'],
                    detail_data['battery_code'],
                    detail_data['test_timestamp'],
                    detail_data['frequency'],
                    detail_data['impedance_real'],
                    detail_data['impedance_imag'],
                    detail_data.get('voltage'),
                    detail_data.get('test_sequence', 0),
                    detail_data.get('z_value'),
                    detail_data.get('baseline_z_value'),
                    detail_data.get('deviation_percent')
                ))

                detail_id = cursor.lastrowid
                conn.commit()

                logger.debug(f"阻抗明细数据保存成功: 通道{detail_data['channel_number']}, "
                           f"频率{detail_data['frequency']:.3f}Hz, "
                           f"实部{detail_data['impedance_real']:.3f}mΩ, "
                           f"虚部{detail_data['impedance_imag']:.3f}mΩ")

                return detail_id

        except Exception as e:
            logger.error(f"保存阻抗明细数据失败: {e}")
            raise

    def get_impedance_details(self, batch_id: Optional[int] = None,
                             channel_number: Optional[int] = None,
                             battery_code: Optional[str] = None,
                             limit: int = 1000) -> List[Dict[str, Any]]:
        """
        查询阻抗测试明细数据

        Args:
            batch_id: 批次ID
            channel_number: 通道号
            battery_code: 电池码
            limit: 查询限制数量

        Returns:
            明细数据列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 构建查询条件
                conditions = []
                params = []

                if batch_id is not None:
                    conditions.append('batch_id = ?')
                    params.append(batch_id)

                if channel_number is not None:
                    conditions.append('channel_number = ?')
                    params.append(channel_number)

                if battery_code is not None:
                    # 修复连续测试模式下的电池码查询
                    # 如果是增强的电池码（包含-T序号），则同时查询原始电池码和增强电池码
                    if '-T' in battery_code and battery_code.count('-T') == 1:
                        # 提取原始电池码（去掉-T序号部分）
                        original_battery_code = battery_code.rsplit('-T', 1)[0]
                        conditions.append('(battery_code = ? OR battery_code = ?)')
                        params.extend([battery_code, original_battery_code])
                        logger.debug(f"连续测试电池码查询：增强码={battery_code}, 原始码={original_battery_code}")
                    else:
                        conditions.append('battery_code = ?')
                        params.append(battery_code)

                where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

                query = f'''
                    SELECT * FROM impedance_details
                    {where_clause}
                    ORDER BY test_timestamp ASC, test_sequence ASC
                    LIMIT ?
                '''

                params.append(limit)
                cursor.execute(query, params)

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"查询阻抗明细数据失败: {e}")
            raise

    def get_impedance_details_by_channel(self, batch_id: int, channel_number: int) -> List[Dict[str, Any]]:
        """
        获取指定批次和通道的阻抗明细数据

        Args:
            batch_id: 批次ID
            channel_number: 通道号

        Returns:
            阻抗明细数据列表
        """
        return self.get_impedance_details(batch_id=batch_id, channel_number=channel_number)

    def get_test_results(self, batch_id: Optional[int] = None,
                        batch_number: Optional[str] = None,
                        start_date: Optional[date] = None,
                        end_date: Optional[date] = None,
                        channel_number: Optional[int] = None,
                        channel_numbers: Optional[List[int]] = None,
                        battery_code: Optional[str] = None,
                        battery_code_fuzzy: bool = False,
                        is_pass: Optional[bool] = None,
                        limit: int = 20,
                        offset: int = 0,
                        include_json: bool = False) -> List[Dict[str, Any]]:
        """
        查询测试结果（性能优化版本，支持分页）

        Args:
            batch_id: 批次ID
            batch_number: 批次号（模糊查询）
            start_date: 开始日期
            end_date: 结束日期
            channel_number: 单个通道号（与channel_numbers互斥）
            channel_numbers: 多个通道号列表（与channel_number互斥）
            battery_code: 电池码搜索文本
            battery_code_fuzzy: 是否模糊搜索电池码
            is_pass: 是否合格
            limit: 查询限制数量（默认20条）
            offset: 偏移量，用于分页
            include_json: 是否包含JSON字段（frequency_list, raw_data）

        Returns:
            测试结果列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 构建查询条件
                conditions = []
                params = []

                if batch_id is not None:
                    conditions.append('tr.batch_id = ?')
                    params.append(batch_id)

                # 批次号模糊查询
                if batch_number is not None and batch_number.strip():
                    conditions.append('(LOWER(tr.batch_number) LIKE LOWER(?) OR LOWER(b.batch_number) LIKE LOWER(?))')
                    batch_pattern = f'%{batch_number.strip()}%'
                    params.extend([batch_pattern, batch_pattern])

                if start_date is not None:
                    conditions.append('DATE(tr.test_start_time) >= ?')
                    params.append(start_date.isoformat())

                if end_date is not None:
                    conditions.append('DATE(tr.test_start_time) <= ?')
                    params.append(end_date.isoformat())

                # 通道号筛选（支持单个或多个）
                if channel_numbers is not None and len(channel_numbers) > 0:
                    # 多通道筛选
                    placeholders = ','.join(['?'] * len(channel_numbers))
                    conditions.append(f'tr.channel_number IN ({placeholders})')
                    params.extend(channel_numbers)
                elif channel_number is not None:
                    # 单通道筛选（向后兼容）
                    conditions.append('tr.channel_number = ?')
                    params.append(channel_number)

                # 电池码筛选
                if battery_code is not None and battery_code.strip():
                    if battery_code_fuzzy:
                        # 模糊搜索（不区分大小写）
                        conditions.append('LOWER(tr.battery_code) LIKE LOWER(?)')
                        params.append(f'%{battery_code.strip()}%')
                    else:
                        # 精确匹配
                        conditions.append('tr.battery_code = ?')
                        params.append(battery_code.strip())

                if is_pass is not None:
                    conditions.append('tr.is_pass = ?')
                    params.append(is_pass)

                where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

                # Jack要求清理后的字段查询（移除了已删除的字段）
                # 修复优先使用测试结果表中的批次号、操作员、电池类型、规格信息
                if include_json:
                    select_fields = "tr.*, b.batch_number as batch_table_batch_number, b.operator as batch_operator, b.cell_type as batch_cell_type, b.cell_spec as batch_cell_spec"
                else:
                    select_fields = """tr.id, tr.batch_id, tr.channel_number, tr.battery_code,
                                     tr.test_start_time, tr.test_end_time, tr.test_duration,
                                     tr.voltage, tr.rs_value, tr.rct_value, tr.rs_grade, tr.rct_grade,
                                     tr.is_pass, tr.fail_reason,
                                     tr.operator, tr.battery_type, tr.battery_spec, tr.batch_number,
                                     tr.voltage_range_min, tr.voltage_range_max, tr.rs_range_min, tr.rs_range_max, tr.rct_range_min, tr.rct_range_max,
                                     b.batch_number as batch_table_batch_number, b.operator as batch_operator, b.cell_type as batch_cell_type, b.cell_spec as batch_cell_spec"""

                query = f'''
                    SELECT {select_fields}
                    FROM test_results tr
                    LEFT JOIN batches b ON tr.batch_id = b.id
                    {where_clause}
                    ORDER BY tr.test_start_time DESC
                    LIMIT ? OFFSET ?
                '''

                params.extend([limit, offset])
                cursor.execute(query, params)

                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    # 性能优化：只在需要时解析JSON字段
                    if include_json:
                        if result.get('frequency_list'):
                            result['frequency_list'] = json.loads(result['frequency_list'])
                        if result.get('raw_data'):
                            result['raw_data'] = json.loads(result['raw_data'])
                    results.append(result)

                return results

        except Exception as e:
            logger.error(f"查询测试结果失败: {e}")
            raise

    def get_test_results_count(self, batch_id: Optional[int] = None,
                              batch_number: Optional[str] = None,
                              start_date: Optional[date] = None,
                              end_date: Optional[date] = None,
                              channel_number: Optional[int] = None,
                              channel_numbers: Optional[List[int]] = None,
                              battery_code: Optional[str] = None,
                              battery_code_fuzzy: bool = False,
                              is_pass: Optional[bool] = None) -> int:
        """
        获取测试结果总数（用于分页）

        Args:
            batch_id: 批次ID
            batch_number: 批次号（模糊查询）
            start_date: 开始日期
            end_date: 结束日期
            channel_number: 单个通道号（与channel_numbers互斥）
            channel_numbers: 多个通道号列表（与channel_number互斥）
            battery_code: 电池码搜索文本
            battery_code_fuzzy: 是否模糊搜索电池码
            is_pass: 是否合格

        Returns:
            符合条件的测试结果总数
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 构建查询条件（与get_test_results保持一致）
                conditions = []
                params = []

                if batch_id is not None:
                    conditions.append('tr.batch_id = ?')
                    params.append(batch_id)

                # 批次号模糊查询
                if batch_number is not None and batch_number.strip():
                    conditions.append('(LOWER(tr.batch_number) LIKE LOWER(?) OR LOWER(b.batch_number) LIKE LOWER(?))')
                    batch_pattern = f'%{batch_number.strip()}%'
                    params.extend([batch_pattern, batch_pattern])

                if start_date is not None:
                    conditions.append('DATE(tr.test_start_time) >= ?')
                    params.append(start_date.isoformat())

                if end_date is not None:
                    conditions.append('DATE(tr.test_start_time) <= ?')
                    params.append(end_date.isoformat())

                # 通道号筛选（支持单个或多个）
                if channel_numbers is not None and len(channel_numbers) > 0:
                    # 多通道筛选
                    placeholders = ','.join(['?'] * len(channel_numbers))
                    conditions.append(f'tr.channel_number IN ({placeholders})')
                    params.extend(channel_numbers)
                elif channel_number is not None:
                    # 单通道筛选（向后兼容）
                    conditions.append('tr.channel_number = ?')
                    params.append(channel_number)

                # 电池码筛选
                if battery_code is not None and battery_code.strip():
                    if battery_code_fuzzy:
                        # 模糊搜索（不区分大小写）
                        conditions.append('LOWER(tr.battery_code) LIKE LOWER(?)')
                        params.append(f'%{battery_code.strip()}%')
                    else:
                        # 精确匹配
                        conditions.append('tr.battery_code = ?')
                        params.append(battery_code.strip())

                if is_pass is not None:
                    conditions.append('tr.is_pass = ?')
                    params.append(is_pass)

                where_clause = 'WHERE ' + ' AND '.join(conditions) if conditions else ''

                query = f'''
                    SELECT COUNT(*) as total
                    FROM test_results tr
                    LEFT JOIN batches b ON tr.batch_id = b.id
                    {where_clause}
                '''

                cursor.execute(query, params)
                result = cursor.fetchone()
                return result['total'] if result else 0

        except Exception as e:
            logger.error(f"查询测试结果总数失败: {e}")
            return 0

    def get_batch_statistics(self, batch_id: int) -> Dict[str, Any]:
        """
        获取批次统计信息

        Args:
            batch_id: 批次ID

        Returns:
            统计信息字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 获取基本统计（修复：只统计合格电池的Rs和Rct）
                cursor.execute('''
                    SELECT
                        COUNT(*) as total_count,
                        SUM(CASE WHEN is_pass = 1 THEN 1 ELSE 0 END) as pass_count,
                        SUM(CASE WHEN is_pass = 0 THEN 1 ELSE 0 END) as fail_count,
                        AVG(voltage) as avg_voltage,
                        AVG(CASE WHEN is_pass = 1 THEN rs_value ELSE NULL END) as avg_rs,
                        AVG(CASE WHEN is_pass = 1 THEN rct_value ELSE NULL END) as avg_rct,
                        MIN(test_start_time) as first_test,
                        MAX(test_end_time) as last_test
                    FROM test_results
                    WHERE batch_id = ?
                ''', (batch_id,))

                stats = dict(cursor.fetchone())

                # 计算良率
                if stats['total_count'] > 0:
                    stats['yield_rate'] = stats['pass_count'] / stats['total_count'] * 100
                else:
                    stats['yield_rate'] = 0.0

                # 获取Rs-Rct档位分布（修复：只统计合格电池的档位）
                cursor.execute('''
                    SELECT rs_grade, rct_grade, COUNT(*) as count
                    FROM test_results
                    WHERE batch_id = ? AND is_pass = 1 AND rs_grade IS NOT NULL AND rct_grade IS NOT NULL
                    GROUP BY rs_grade, rct_grade
                ''', (batch_id,))

                grade_distribution = {}
                for row in cursor.fetchall():
                    key = f"Rs{row['rs_grade']}-Rct{row['rct_grade']}"
                    grade_distribution[key] = row['count']

                stats['grade_distribution'] = grade_distribution

                return stats

        except Exception as e:
            logger.error(f"获取批次统计失败: {e}")
            raise

    def get_recent_batches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取最近的批次列表

        Args:
            limit: 查询限制数量

        Returns:
            批次列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM batches
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (limit,))

                return [dict(row) for row in cursor.fetchall()]

        except Exception as e:
            logger.error(f"获取最近批次失败: {e}")
            raise

    def get_test_results_batches(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取测试结果中实际使用的批次号列表
        只返回批次表中真实存在且有有效batch_number的批次

        Args:
            limit: 查询限制数量

        Returns:
            批次号列表，包含batch_id和对应的批次号
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 只查询批次表中真实存在且batch_number不为空的批次
                cursor.execute('''
                    SELECT DISTINCT
                        tr.batch_id,
                        b.batch_number,
                        MAX(DATE(tr.test_start_time)) as latest_test_date,
                        COUNT(tr.id) as test_count
                    FROM test_results tr
                    INNER JOIN batches b ON tr.batch_id = b.id
                    WHERE tr.batch_id IS NOT NULL
                      AND b.batch_number IS NOT NULL
                      AND b.batch_number != ''
                    GROUP BY tr.batch_id, b.batch_number
                    ORDER BY latest_test_date DESC
                    LIMIT ?
                ''', (limit,))

                results = []
                for row in cursor.fetchall():
                    results.append({
                        'batch_id': row[0],
                        'batch_number': row[1],
                        'latest_test_date': row[2],
                        'test_count': row[3]
                    })

                logger.debug(f"获取到 {len(results)} 个真实批次")
                return results

        except Exception as e:
            logger.error(f"获取测试结果批次列表失败: {e}")
            raise



    def delete_batch(self, batch_id: int) -> bool:
        """
        删除批次及其相关数据

        Args:
            batch_id: 批次ID

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 删除频率数据
                cursor.execute('''
                    DELETE FROM frequency_data
                    WHERE test_result_id IN (
                        SELECT id FROM test_results WHERE batch_id = ?
                    )
                ''', (batch_id,))

                # 删除测试结果
                cursor.execute('DELETE FROM test_results WHERE batch_id = ?', (batch_id,))

                # 删除批次
                cursor.execute('DELETE FROM batches WHERE id = ?', (batch_id,))

                conn.commit()

                logger.info(f"批次删除成功: ID={batch_id}")
                return True

        except Exception as e:
            logger.error(f"删除批次失败: {e}")
            return False

    def backup_database(self, backup_path: str) -> bool:
        """
        备份数据库

        Args:
            backup_path: 备份文件路径

        Returns:
            是否备份成功
        """
        try:
            import shutil

            # 确保备份目录存在
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)

            # 复制数据库文件
            shutil.copy2(self.db_path, backup_path)

            logger.info(f"数据库备份成功: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """
        获取数据库信息

        Returns:
            数据库信息字典
        """
        try:
            info = {
                'db_path': self.db_path,
                'db_size': os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0,
                'created_time': datetime.fromtimestamp(os.path.getctime(self.db_path)) if os.path.exists(self.db_path) else None,
                'modified_time': datetime.fromtimestamp(os.path.getmtime(self.db_path)) if os.path.exists(self.db_path) else None
            }

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 获取表统计
                tables = ['batches', 'test_results', 'frequency_data', 'system_logs']
                table_stats = {}

                for table in tables:
                    cursor.execute(f'SELECT COUNT(*) as count FROM {table}')
                    table_stats[table] = cursor.fetchone()['count']

                info['table_stats'] = table_stats

            return info

        except Exception as e:
            logger.error(f"获取数据库信息失败: {e}")
            return {'error': str(e)}

    def log_system_event(self, level: str, message: str, module: Optional[str] = None,
                        function: Optional[str] = None, line_number: Optional[int] = None):
        """
        记录系统日志

        Args:
            level: 日志级别
            message: 日志消息
            module: 模块名
            function: 函数名
            line_number: 行号
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO system_logs (level, message, module, function, line_number)
                    VALUES (?, ?, ?, ?, ?)
                ''', (level, message, module, function, line_number))

                conn.commit()

        except Exception as e:
            # 避免日志记录失败影响主要功能
            logger.error(f"记录系统日志失败: {e}")

    def cleanup_old_logs(self, days: int = 30):
        """
        清理旧日志

        Args:
            days: 保留天数
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    DELETE FROM system_logs
                    WHERE timestamp < datetime('now', '-{} days')
                '''.format(days))

                deleted_count = cursor.rowcount
                conn.commit()

                logger.info(f"清理旧日志完成: 删除 {deleted_count} 条记录")

        except Exception as e:
            logger.error(f"清理旧日志失败: {e}")

    def delete_test_result(self, test_result_id: int) -> bool:
        """
        删除单个测试结果及其关联的阻抗明细数据

        Args:
            test_result_id: 测试结果ID

        Returns:
            是否删除成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 获取测试结果信息用于日志
                cursor.execute('''
                    SELECT tr.*, b.batch_number
                    FROM test_results tr
                    LEFT JOIN batches b ON tr.batch_id = b.id
                    WHERE tr.id = ?
                ''', (test_result_id,))

                test_result = cursor.fetchone()
                if not test_result:
                    logger.warning(f"测试结果不存在: ID={test_result_id}")
                    return False

                # 先删除频率数据，避免外键阻断
                cursor.execute('DELETE FROM frequency_data WHERE test_result_id = ?', (test_result_id,))
                # 清理上传队列中关联此测试结果的项目
                cursor.execute('DELETE FROM upload_queue WHERE test_result_id = ?', (test_result_id,))

                # 删除阻抗明细数据
                cursor.execute('''
                    DELETE FROM impedance_details
                    WHERE batch_id = ? AND channel_number = ? AND battery_code = ?
                ''', (test_result['batch_id'], test_result['channel_number'], test_result['battery_code']))

                impedance_deleted = cursor.rowcount

                # 删除测试结果
                cursor.execute('DELETE FROM test_results WHERE id = ?', (test_result_id,))

                if cursor.rowcount == 0:
                    logger.warning(f"测试结果删除失败: ID={test_result_id}")
                    return False

                conn.commit()

                logger.info(f"测试结果删除成功: ID={test_result_id}, "
                           f"批次={test_result['batch_number']}, "
                           f"通道={test_result['channel_number']}, "
                           f"电池码={test_result['battery_code']}, "
                           f"删除阻抗明细数据={impedance_deleted}条")

                # 更新批次统计
                self.update_batch_statistics(test_result['batch_id'])

                return True

        except Exception as e:
            logger.error(f"删除测试结果失败: {e}")
            return False

    def delete_test_results(self, test_result_ids: List[int]) -> Dict[str, int]:
        """
        批量删除测试结果及其关联的阻抗明细数据

        Args:
            test_result_ids: 测试结果ID列表

        Returns:
            删除结果统计 {'success': 成功数量, 'failed': 失败数量, 'impedance_details': 明细数据删除数量}
        """
        try:
            success_count = 0
            failed_count = 0
            total_impedance_deleted = 0
            affected_batches = set()

            with self.get_connection() as conn:
                cursor = conn.cursor()

                for test_result_id in test_result_ids:
                    try:
                        # 获取测试结果信息
                        cursor.execute('''
                            SELECT tr.*, b.batch_number
                            FROM test_results tr
                            LEFT JOIN batches b ON tr.batch_id = b.id
                            WHERE tr.id = ?
                        ''', (test_result_id,))

                        test_result = cursor.fetchone()
                        if not test_result:
                            failed_count += 1
                            continue

                        # 先删除频率数据与上传队列记录，避免外键与残留
                        cursor.execute('DELETE FROM frequency_data WHERE test_result_id = ?', (test_result_id,))
                        cursor.execute('DELETE FROM upload_queue WHERE test_result_id = ?', (test_result_id,))

                        # 删除阻抗明细数据
                        cursor.execute('''
                            DELETE FROM impedance_details
                            WHERE batch_id = ? AND channel_number = ? AND battery_code = ?
                        ''', (test_result['batch_id'], test_result['channel_number'], test_result['battery_code']))

                        impedance_deleted = cursor.rowcount
                        total_impedance_deleted += impedance_deleted

                        # 删除测试结果
                        cursor.execute('DELETE FROM test_results WHERE id = ?', (test_result_id,))

                        if cursor.rowcount > 0:
                            success_count += 1
                            affected_batches.add(test_result['batch_id'])
                            logger.debug(f"删除测试结果: ID={test_result_id}, 明细数据={impedance_deleted}条")
                        else:
                            failed_count += 1

                    except Exception as e:
                        logger.error(f"删除单个测试结果失败: ID={test_result_id}, 错误={e}")
                        failed_count += 1

                conn.commit()

                # 更新受影响批次的统计
                for batch_id in affected_batches:
                    self.update_batch_statistics(batch_id)

                logger.info(f"批量删除测试结果完成: 成功={success_count}, 失败={failed_count}, "
                           f"删除阻抗明细数据={total_impedance_deleted}条")

                return {
                    'success': success_count,
                    'failed': failed_count,
                    'impedance_details': total_impedance_deleted
                }

        except Exception as e:
            logger.error(f"批量删除测试结果失败: {e}")
            return {'success': 0, 'failed': len(test_result_ids), 'impedance_details': 0}

    def reset_database(self, keep_batches: bool = True, clear_serial_numbers: bool = True) -> Dict[str, Any]:
        """
        重置数据库（清空测试数据，可选择保留批次信息和序列号记录）

        Args:
            keep_batches: 是否保留批次信息
            clear_serial_numbers: 是否清空序列号记录

        Returns:
            重置结果统计
        """
        try:
            # 创建备份
            backup_path = f"data/backup/database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            backup_success = self.backup_database(backup_path)

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 统计重置前的数据
                cursor.execute('SELECT COUNT(*) as count FROM test_results')
                test_results_count = cursor.fetchone()['count']

                cursor.execute('SELECT COUNT(*) as count FROM impedance_details')
                impedance_details_count = cursor.fetchone()['count']

                cursor.execute('SELECT COUNT(*) as count FROM batches')
                batches_count = cursor.fetchone()['count']

                cursor.execute('SELECT COUNT(*) as count FROM system_logs')
                logs_count = cursor.fetchone()['count']

                # 删除测试数据（注意外键顺序）
                cursor.execute('DELETE FROM frequency_data')
                cursor.execute('DELETE FROM impedance_details')
                cursor.execute('DELETE FROM upload_queue')
                cursor.execute('DELETE FROM test_results')

                if not keep_batches:
                    cursor.execute('DELETE FROM batches')
                else:
                    # 重置批次统计信息
                    cursor.execute('''
                        UPDATE batches SET
                        total_count = 0,
                        pass_count = 0,
                        fail_count = 0,
                        yield_rate = 0.0,
                        end_time = NULL
                    ''')

                # 清理旧日志（保留最近7天）
                cursor.execute('''
                    DELETE FROM system_logs
                    WHERE timestamp < datetime('now', '-7 days')
                ''')

                conn.commit()

                # 新增清空序列号记录
                serial_numbers_cleared = 0
                if clear_serial_numbers:
                    serial_numbers_cleared = self._clear_serial_numbers()

                result = {
                    'backup_created': backup_success,
                    'backup_path': backup_path if backup_success else None,
                    'deleted_test_results': test_results_count,
                    'deleted_impedance_details': impedance_details_count,
                    'deleted_batches': batches_count if not keep_batches else 0,
                    'cleaned_logs': logs_count,
                    'batches_reset': batches_count if keep_batches else 0,
                    'serial_numbers_cleared': serial_numbers_cleared
                }

                logger.info(f"数据库重置完成: {result}")

                # 记录重置操作
                self.log_system_event('INFO', f'数据库重置完成: 删除测试结果{test_results_count}条, '
                                             f'删除阻抗明细{impedance_details_count}条, '
                                             f'保留批次={keep_batches}, '
                                             f'清空序列号={clear_serial_numbers}({serial_numbers_cleared}个)')

                return result

        except Exception as e:
            logger.error(f"数据库重置失败: {e}")
            return {'error': str(e)}

    def _clear_serial_numbers(self) -> int:
        """
        清空序列号记录

        Returns:
            清空的序列号数量
        """
        try:
            if not self.config_manager:
                logger.warning("配置管理器未设置，无法清空序列号记录")
                return 0

            # 获取当前序列号数量
            used_serials = self.config_manager.get('serial_numbers.used_list', [])
            serial_count = len(used_serials)

            # 清空序列号配置
            self.config_manager.set('serial_numbers.used_list', [])
            self.config_manager.set('serial_numbers.current_sequence', 1)

            # 保存配置
            self.config_manager.save_config()

            logger.info(f"✅ 已清空 {serial_count} 个序列号记录")
            return serial_count

        except Exception as e:
            logger.error(f"清空序列号记录失败: {e}")
            return 0

    def validate_data_integrity(self) -> Dict[str, Any]:
        """
        验证数据完整性

        Returns:
            验证结果报告
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # 检查表结构
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row['name'] for row in cursor.fetchall()]

                required_tables = ['batches', 'test_results', 'impedance_details', 'system_logs']
                missing_tables = [table for table in required_tables if table not in tables]

                # 检查测试结果与批次的关联
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM test_results tr
                    LEFT JOIN batches b ON tr.batch_id = b.id
                    WHERE b.id IS NULL
                ''')
                orphaned_test_results = cursor.fetchone()['count']

                # 检查阻抗明细数据与测试结果的关联
                cursor.execute('''
                    SELECT tr.id, tr.batch_id, tr.channel_number, tr.battery_code,
                           COUNT(id.id) as detail_count
                    FROM test_results tr
                    LEFT JOIN impedance_details id ON (
                        tr.batch_id = id.batch_id AND
                        tr.channel_number = id.channel_number AND
                        tr.battery_code = id.battery_code
                    )
                    GROUP BY tr.id, tr.batch_id, tr.channel_number, tr.battery_code
                ''')

                test_results_with_details = cursor.fetchall()
                missing_details = [row for row in test_results_with_details if row['detail_count'] == 0]

                # 检查孤立的阻抗明细数据
                cursor.execute('''
                    SELECT COUNT(*) as count
                    FROM impedance_details id
                    WHERE NOT EXISTS (
                        SELECT 1 FROM test_results tr
                        WHERE tr.batch_id = id.batch_id
                        AND tr.channel_number = id.channel_number
                        AND tr.battery_code = id.battery_code
                    )
                ''')
                orphaned_impedance_details = cursor.fetchone()['count']

                # 检查数据统计
                cursor.execute('SELECT COUNT(*) as count FROM batches')
                total_batches = cursor.fetchone()['count']

                cursor.execute('SELECT COUNT(*) as count FROM test_results')
                total_test_results = cursor.fetchone()['count']

                cursor.execute('SELECT COUNT(*) as count FROM impedance_details')
                total_impedance_details = cursor.fetchone()['count']

                # 检查批次统计准确性
                cursor.execute('''
                    SELECT b.id, b.batch_number, b.total_count, b.pass_count, b.fail_count,
                           COUNT(tr.id) as actual_total,
                           SUM(CASE WHEN tr.is_pass = 1 THEN 1 ELSE 0 END) as actual_pass,
                           SUM(CASE WHEN tr.is_pass = 0 THEN 1 ELSE 0 END) as actual_fail
                    FROM batches b
                    LEFT JOIN test_results tr ON b.id = tr.batch_id
                    GROUP BY b.id, b.batch_number, b.total_count, b.pass_count, b.fail_count
                ''')

                batch_stats_issues = []
                for row in cursor.fetchall():
                    if (row['total_count'] != row['actual_total'] or
                        row['pass_count'] != row['actual_pass'] or
                        row['fail_count'] != row['actual_fail']):
                        batch_stats_issues.append({
                            'batch_id': row['id'],
                            'batch_number': row['batch_number'],
                            'recorded': {
                                'total': row['total_count'],
                                'pass': row['pass_count'],
                                'fail': row['fail_count']
                            },
                            'actual': {
                                'total': row['actual_total'],
                                'pass': row['actual_pass'],
                                'fail': row['actual_fail']
                            }
                        })

                # 生成验证报告
                report = {
                    'timestamp': datetime.now().isoformat(),
                    'table_structure': {
                        'required_tables': required_tables,
                        'existing_tables': tables,
                        'missing_tables': missing_tables,
                        'structure_ok': len(missing_tables) == 0
                    },
                    'data_counts': {
                        'batches': total_batches,
                        'test_results': total_test_results,
                        'impedance_details': total_impedance_details
                    },
                    'data_integrity': {
                        'orphaned_test_results': orphaned_test_results,
                        'test_results_missing_details': len(missing_details),
                        'orphaned_impedance_details': orphaned_impedance_details,
                        'batch_stats_issues': len(batch_stats_issues)
                    },
                    'issues': {
                        'missing_details_list': missing_details[:10],  # 只显示前10个
                        'batch_stats_issues': batch_stats_issues[:5]   # 只显示前5个
                    },
                    'overall_status': 'HEALTHY' if (
                        len(missing_tables) == 0 and
                        orphaned_test_results == 0 and
                        len(missing_details) == 0 and
                        orphaned_impedance_details == 0 and
                        len(batch_stats_issues) == 0
                    ) else 'ISSUES_FOUND'
                }

                logger.info(f"数据完整性验证完成: 状态={report['overall_status']}")
                return report

        except Exception as e:
            logger.error(f"数据完整性验证失败: {e}")
            return {'error': str(e), 'overall_status': 'ERROR'}

    def check_data_integrity(self) -> Dict[str, Any]:
        """
        检查数据完整性（兼容性方法）

        Returns:
            验证结果报告
        """
        return self.validate_data_integrity()





    def read_voltage(self, channel_number: int) -> Optional[float]:
        """
        读取通道电压（兼容性方法）
        
        注意：这个方法主要用于兼容性，实际电压读取应该通过通信管理器进行
        这里返回最近一次测试的电压值作为参考
        
        Args:
            channel_number: 通道号 (1-8)
            
        Returns:
            电压值，如果没有找到返回None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 查询该通道最近一次测试的电压
                cursor.execute('''
                    SELECT voltage FROM test_results 
                    WHERE channel_number = ? AND voltage IS NOT NULL
                    ORDER BY test_start_time DESC 
                    LIMIT 1
                ''', (channel_number,))
                
                row = cursor.fetchone()
                if row and row['voltage'] is not None:
                    voltage = float(row['voltage'])
                    logger.debug(f"从数据库读取通道{channel_number}电压: {voltage:.3f}V")
                    return voltage
                else:
                    logger.debug(f"未找到通道{channel_number}的电压记录")
                    return None
                    
        except Exception as e:
            logger.error(f"读取通道{channel_number}电压失败: {e}")
            return None

    # 新增上传队列管理方法（断点续传支持）

    def add_to_upload_queue(self, upload_id: str, data_type: str, upload_data: Dict[str, Any],
                           test_result_id: Optional[int] = None, priority: int = 0) -> bool:
        """
        添加数据到上传队列

        Args:
            upload_id: 唯一上传ID
            data_type: 数据类型 ('test_result' 或 'impedance_data')
            upload_data: 上传数据
            test_result_id: 关联的测试结果ID
            priority: 优先级（数字越大优先级越高）

        Returns:
            是否添加成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT OR REPLACE INTO upload_queue
                    (upload_id, data_type, test_result_id, upload_data, priority, status, retry_count)
                    VALUES (?, ?, ?, ?, ?, 'pending', 0)
                ''', (upload_id, data_type, test_result_id, json.dumps(upload_data), priority))

                logger.debug(f"数据已添加到上传队列: {upload_id}")
                return True

        except Exception as e:
            logger.error(f"添加数据到上传队列失败: {e}")
            return False

    def get_pending_uploads(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取待上传的数据

        Args:
            limit: 获取数量限制

        Returns:
            待上传数据列表
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT * FROM upload_queue
                    WHERE status IN ('pending', 'failed') AND retry_count < max_retries
                    ORDER BY priority DESC, created_at ASC
                    LIMIT ?
                ''', (limit,))

                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    result['upload_data'] = json.loads(result['upload_data'])
                    results.append(result)

                return results

        except Exception as e:
            logger.error(f"获取待上传数据失败: {e}")
            return []

    def update_upload_status(self, upload_id: str, status: str, error_message: Optional[str] = None) -> bool:
        """
        更新上传状态

        Args:
            upload_id: 上传ID
            status: 新状态 ('uploading', 'completed', 'failed')
            error_message: 错误信息（如果有）

        Returns:
            是否更新成功
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                if status == 'completed':
                    cursor.execute('''
                        UPDATE upload_queue
                        SET status = ?, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                        WHERE upload_id = ?
                    ''', (status, upload_id))
                elif status == 'failed':
                    cursor.execute('''
                        UPDATE upload_queue
                        SET status = ?, retry_count = retry_count + 1, error_message = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE upload_id = ?
                    ''', (status, error_message, upload_id))
                else:
                    cursor.execute('''
                        UPDATE upload_queue
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE upload_id = ?
                    ''', (status, upload_id))

                logger.debug(f"上传状态已更新: {upload_id} -> {status}")
                return True

        except Exception as e:
            logger.error(f"更新上传状态失败: {e}")
            return False

    def get_upload_queue_stats(self) -> Dict[str, int]:
        """
        获取上传队列统计信息

        Returns:
            统计信息字典
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT
                        status,
                        COUNT(*) as count
                    FROM upload_queue
                    GROUP BY status
                ''')

                stats = {}
                for row in cursor.fetchall():
                    stats[row['status']] = row['count']

                # 添加总数
                cursor.execute('SELECT COUNT(*) as total FROM upload_queue')
                stats['total'] = cursor.fetchone()['total']

                return stats

        except Exception as e:
            logger.error(f"获取上传队列统计失败: {e}")
            return {}

    def cleanup_completed_uploads(self, days_old: int = 7) -> int:
        """
        清理已完成的上传记录

        Args:
            days_old: 清理多少天前的记录

        Returns:
            清理的记录数
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    DELETE FROM upload_queue
                    WHERE status = 'completed'
                    AND completed_at < datetime('now', '-{} days')
                '''.format(days_old))

                deleted_count = cursor.rowcount
                logger.info(f"清理了 {deleted_count} 条已完成的上传记录")
                return deleted_count

        except Exception as e:
            logger.error(f"清理上传记录失败: {e}")
            return 0

    # 移除重复的打印触发方法，避免重复打印（打印由test_result_manager统一处理）
    # def _trigger_auto_print_for_saved_result(self, test_data: Dict[str, Any], test_result_id: int):


# ===== 全局数据库管理器实例管理 =====

# 全局数据库管理器实例
_database_manager: Optional[DatabaseManager] = None


def get_database_manager() -> Optional[DatabaseManager]:
    """获取全局数据库管理器实例"""
    return _database_manager


def initialize_database_manager(db_path: str = "data/test_results.db") -> DatabaseManager:
    """
    初始化全局数据库管理器

    Args:
        db_path: 数据库文件路径

    Returns:
        数据库管理器实例
    """
    global _database_manager

    if _database_manager is None:
        _database_manager = DatabaseManager(db_path)

        logger.debug("✅ 全局数据库管理器初始化完成")

    return _database_manager

