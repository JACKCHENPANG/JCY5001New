"""
数据同步API路由
处理桌面软件的数据同步请求
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from typing import Dict, Any
import json
import logging

from extensions import db
from models.user import User, Device, TestBatch, TestResult, ImpedanceDetail

logger = logging.getLogger(__name__)

sync_bp = Blueprint('sync', __name__, url_prefix='/api/sync')


@sync_bp.route('/devices', methods=['POST'])
@jwt_required()
def register_device():
    """注册或更新设备信息"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        device_id = data.get('device_id')
        if not device_id:
            return jsonify({'error': '设备ID不能为空'}), 400
        
        # 检查设备是否已存在
        existing_device = Device.query.filter_by(device_id=device_id).first()
        
        if existing_device:
            # 更新设备信息
            existing_device.name = data.get('name', existing_device.name)
            existing_device.model = data.get('model', existing_device.model)
            existing_device.firmware_version = data.get('firmware_version', existing_device.firmware_version)
            existing_device.status = data.get('status', existing_device.status)
            existing_device.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            logger.info(f"设备信息已更新: {device_id}")
            return jsonify({
                'message': '设备信息更新成功',
                'device': existing_device.to_dict()
            }), 200
        else:
            # 创建新设备
            new_device = Device(
                device_id=device_id,
                user_id=current_user_id,
                name=data.get('name', f'JCY5001A-{device_id[:8]}'),
                model=data.get('model', 'JCY5001A'),
                firmware_version=data.get('firmware_version')
            )
            
            db.session.add(new_device)
            db.session.commit()
            
            logger.info(f"新设备注册成功: {device_id}")
            return jsonify({
                'message': '设备注册成功',
                'device': new_device.to_dict()
            }), 201
            
    except Exception as e:
        logger.error(f"注册设备失败: {e}")
        db.session.rollback()
        return jsonify({'error': f'注册设备失败: {str(e)}'}), 500


@sync_bp.route('/test-results', methods=['POST'])
@jwt_required()
def sync_test_results():
    """同步测试结果数据"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': '请求数据为空'}), 400
        
        device_id = data.get('device_id')
        test_results = data.get('test_results', [])
        
        if not device_id:
            return jsonify({'error': '设备ID不能为空'}), 400
        
        if not test_results:
            return jsonify({'error': '测试结果数据为空'}), 400
        
        # 验证设备权限（先查找设备，如果不存在则尝试创建）
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({'error': '设备不存在或无权限访问'}), 403

        # 检查设备是否属于当前用户（管理员可以访问所有设备）
        current_user = User.query.get(current_user_id)
        if current_user.role != 'admin' and device.user_id != current_user_id:
            return jsonify({'error': '设备不存在或无权限访问'}), 403
        
        synced_count = 0
        failed_count = 0
        errors = []
        
        for test_result_data in test_results:
            try:
                # 检查测试结果是否已存在
                test_id = test_result_data.get('test_id')
                logger.info(f"处理测试结果: {test_id}")

                # 使用更严格的重复检测
                existing_result = TestResult.query.filter_by(test_id=test_id).first()

                if existing_result:
                    logger.info(f"测试结果已存在，跳过: {test_id}")
                    synced_count += 1  # 已存在的也算作同步成功
                    continue

                # 双重检查：再次检查是否存在（不手动开启事务）
                existing_check = TestResult.query.filter_by(test_id=test_id).first()
                if existing_check:
                    logger.info(f"再次检查发现重复，跳过: {test_id}")
                    synced_count += 1
                    continue
                
                # 确保测试批次存在
                batch_id = _ensure_test_batch_exists(device, test_result_data)
                logger.info(f"获取批次ID: {batch_id}")

                # 创建测试结果
                test_result = TestResult(
                    test_id=test_id,
                    batch_id=batch_id,
                    battery_code=test_result_data.get('battery_code'),
                    channel_number=test_result_data.get('channel_number'),
                    test_start_time=datetime.fromisoformat(test_result_data['test_start_time'].replace('Z', '+00:00')),
                    test_end_time=datetime.fromisoformat(test_result_data['test_end_time'].replace('Z', '+00:00')) if test_result_data.get('test_end_time') else None,
                    test_duration=test_result_data.get('test_duration'),
                    voltage=test_result_data.get('voltage'),
                    rs_value=test_result_data.get('rs_value'),
                    rct_value=test_result_data.get('rct_value'),
                    rsei_value=test_result_data.get('rsei_value'),
                    w_impedance=test_result_data.get('w_impedance'),
                    rs_grade=test_result_data.get('rs_grade'),
                    rct_grade=test_result_data.get('rct_grade'),
                    is_pass=test_result_data.get('is_pass', False),
                    fail_reason=test_result_data.get('fail_reason'),
                    test_mode=test_result_data.get('test_mode'),
                    frequency_list=test_result_data.get('frequency_list'),
                    raw_data=test_result_data.get('raw_data'),
                    outlier_result=test_result_data.get('outlier_result'),
                    baseline_filename=test_result_data.get('baseline_filename'),
                    baseline_id=test_result_data.get('baseline_id'),
                    max_deviation_percent=test_result_data.get('max_deviation_percent'),
                    frequency_deviations=test_result_data.get('frequency_deviations'),
                    operator=test_result_data.get('operator'),
                    battery_type=test_result_data.get('battery_type'),
                    battery_spec=test_result_data.get('battery_spec'),
                    batch_number=test_result_data.get('batch_number'),
                    rct_coefficient_of_variation=test_result_data.get('rct_coefficient_of_variation'),
                    capacity_prediction=test_result_data.get('capacity_prediction'),
                    voltage_range_min=test_result_data.get('voltage_range_min'),
                    voltage_range_max=test_result_data.get('voltage_range_max'),
                    rs_range_min=test_result_data.get('rs_range_min'),
                    rs_range_max=test_result_data.get('rs_range_max'),
                    rct_range_min=test_result_data.get('rct_range_min'),
                    rct_range_max=test_result_data.get('rct_range_max'),
                    warburg_coefficient=test_result_data.get('warburg_coefficient'),
                    warburg_01hz=test_result_data.get('warburg_01hz'),
                    warburg_001hz=test_result_data.get('warburg_001hz'),
                    has_warburg_diffusion=test_result_data.get('has_warburg_diffusion'),
                    has_sei=test_result_data.get('has_sei'),
                    sei_confidence=test_result_data.get('sei_confidence'),
                    double_layer_capacitance=test_result_data.get('double_layer_capacitance'),
                    sei_capacitance=test_result_data.get('sei_capacitance'),
                    total_capacitance=test_result_data.get('total_capacitance'),
                    impedance_ratio=test_result_data.get('impedance_ratio'),
                    capacity=test_result_data.get('capacity'),
                    thickness=test_result_data.get('thickness'),
                    temperature=test_result_data.get('temperature'),
                    test_result=test_result_data.get('test_result'),
                    error_code=test_result_data.get('error_code')
                )
                
                db.session.add(test_result)

                # 立即提交这条记录
                try:
                    db.session.commit()
                    synced_count += 1
                    logger.info(f"测试结果同步成功: {test_id}")
                except Exception as commit_error:
                    db.session.rollback()
                    # 如果是重复键错误，不算失败
                    if "UNIQUE constraint failed" in str(commit_error) or "IntegrityError" in str(commit_error):
                        logger.info(f"测试结果已存在（提交时发现），跳过: {test_id}")
                        synced_count += 1
                    else:
                        failed_count += 1
                        error_msg = f"提交测试结果失败 {test_id}: {str(commit_error)}"
                        errors.append(error_msg)
                        logger.error(error_msg)

            except Exception as e:
                db.session.rollback()
                failed_count += 1
                error_msg = f"同步测试结果失败 {test_result_data.get('test_id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # 更新设备同步时间
        try:
            device.update_sync_time()
            db.session.commit()
        except Exception as e:
            logger.warning(f"更新设备同步时间失败: {e}")
            db.session.rollback()
        
        logger.info(f"测试结果同步完成: 成功 {synced_count}, 失败 {failed_count}")
        
        return jsonify({
            'message': '测试结果同步完成',
            'synced_count': synced_count,
            'failed_count': failed_count,
            'errors': errors
        }), 200
        
    except Exception as e:
        logger.error(f"同步测试结果异常: {e}")
        db.session.rollback()
        return jsonify({'error': f'同步测试结果失败: {str(e)}'}), 500


def _ensure_test_batch_exists(device: Device, test_result_data: Dict) -> int:
    """确保测试批次存在"""
    batch_number = test_result_data.get('batch_number') or 'DEFAULT_BATCH'

    # 确保batch_number不为空
    if not batch_number or batch_number.strip() == '':
        batch_number = 'DEFAULT_BATCH'
    
    # 查找现有批次
    existing_batch = TestBatch.query.filter_by(
        batch_id=batch_number,
        device_id=device.id
    ).first()
    
    if existing_batch:
        return existing_batch.id
    
    # 创建新批次
    new_batch = TestBatch(
        batch_id=batch_number,
        device_id=device.id,
        user_id=device.user_id,
        start_time=datetime.utcnow()
    )
    new_batch.status = 'running'  # 设置状态
    
    db.session.add(new_batch)
    db.session.flush()  # 获取ID
    
    return new_batch.id


@sync_bp.route('/impedance-details', methods=['POST'])
@jwt_required()
def sync_impedance_details():
    """同步阻抗明细数据"""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()

        if not data:
            return jsonify({'error': '请求数据为空'}), 400

        device_id = data.get('device_id')
        test_id = data.get('test_id')
        impedance_details = data.get('impedance_details', [])

        if not device_id:
            return jsonify({'error': '设备ID不能为空'}), 400

        if not test_id:
            return jsonify({'error': '测试ID不能为空'}), 400

        if not impedance_details:
            return jsonify({'error': '阻抗明细数据为空'}), 400

        # 验证设备权限
        device = Device.query.filter_by(device_id=device_id).first()
        if not device:
            return jsonify({'error': '设备不存在或无权限访问'}), 403

        # 检查设备是否属于当前用户（管理员可以访问所有设备）
        current_user = User.query.get(current_user_id)
        if current_user.role != 'admin' and device.user_id != current_user_id:
            return jsonify({'error': '设备不存在或无权限访问'}), 403

        # 查找对应的测试结果
        test_result = TestResult.query.filter_by(test_id=test_id).first()
        if not test_result:
            # 如果直接查找失败，尝试通过设备ID和原始ID查找
            # test_id格式: device_id_original_id
            if '_' in test_id:
                original_id = test_id.split('_')[-1]
                # 查找该设备的测试结果中是否有匹配的
                alternative_test_result = TestResult.query.join(TestBatch).filter(
                    TestBatch.device_id == device.id,
                    TestResult.test_id.like(f'%_{original_id}')
                ).first()

                if alternative_test_result:
                    test_result = alternative_test_result
                    logger.info(f"通过原始ID找到测试结果: {test_result.test_id}")
                else:
                    logger.warning(f"无法找到测试结果: {test_id}, 原始ID: {original_id}")
                    return jsonify({'error': f'测试结果不存在: {test_id}'}), 404
            else:
                return jsonify({'error': f'测试结果不存在: {test_id}'}), 404

        synced_count = 0
        failed_count = 0
        errors = []

        for detail_data in impedance_details:
            try:
                # 检查阻抗明细是否已存在（基于测试ID和频率）
                frequency = detail_data.get('frequency')
                existing_detail = ImpedanceDetail.query.filter_by(
                    test_id=test_result.id,
                    frequency=frequency
                ).first()

                if existing_detail:
                    logger.debug(f"阻抗明细已存在，跳过: 测试ID {test_id}, 频率 {frequency}")
                    synced_count += 1  # 已存在的也算同步成功
                    continue

                # 创建阻抗明细
                impedance_detail = ImpedanceDetail(
                    test_id=test_result.id,
                    batch_id=detail_data.get('batch_id'),
                    channel_number=detail_data.get('channel_number'),
                    battery_code=detail_data.get('battery_code'),
                    test_timestamp=detail_data.get('test_timestamp'),
                    frequency=frequency,
                    impedance_real=detail_data.get('impedance_real'),
                    impedance_imag=detail_data.get('impedance_imag'),
                    voltage=detail_data.get('voltage'),
                    test_sequence=detail_data.get('test_sequence'),
                    z_value=detail_data.get('z_value'),
                    baseline_z_value=detail_data.get('baseline_z_value'),
                    deviation_percent=detail_data.get('deviation_percent'),
                    # 兼容字段
                    z_real=detail_data.get('z_real') or detail_data.get('impedance_real'),
                    z_imag=detail_data.get('z_imag') or detail_data.get('impedance_imag'),
                    z_magnitude=detail_data.get('z_magnitude') or detail_data.get('z_value'),
                    phase_angle=detail_data.get('phase_angle'),
                    measurement_time=datetime.fromisoformat(detail_data['measurement_time'].replace('Z', '+00:00')) if detail_data.get('measurement_time') else None
                )

                db.session.add(impedance_detail)

                # 立即提交这条记录
                try:
                    db.session.commit()
                    synced_count += 1
                    logger.debug(f"阻抗明细同步成功: 频率 {frequency}")
                except Exception as commit_error:
                    db.session.rollback()
                    # 如果是重复键错误，不算失败
                    if "UNIQUE constraint failed" in str(commit_error) or "IntegrityError" in str(commit_error):
                        logger.debug(f"阻抗明细已存在（提交时发现），跳过: 频率 {frequency}")
                        synced_count += 1
                    else:
                        failed_count += 1
                        error_msg = f"提交阻抗明细失败 频率 {frequency}: {str(commit_error)}"
                        errors.append(error_msg)
                        logger.error(error_msg)

            except Exception as e:
                db.session.rollback()
                failed_count += 1
                error_msg = f"同步阻抗明细失败 频率 {detail_data.get('frequency', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

        logger.info(f"阻抗明细同步完成: 成功 {synced_count}, 失败 {failed_count}")

        return jsonify({
            'message': '阻抗明细同步完成',
            'synced_count': synced_count,
            'failed_count': failed_count,
            'errors': errors
        }), 200

    except Exception as e:
        logger.error(f"同步阻抗明细异常: {e}")
        db.session.rollback()
        return jsonify({'error': f'同步阻抗明细失败: {str(e)}'}), 500


@sync_bp.route('/status/<device_id>', methods=['GET'])
@jwt_required()
def get_sync_status(device_id):
    """获取设备同步状态"""
    try:
        current_user_id = get_jwt_identity()

        # 验证设备权限
        device = Device.query.filter_by(device_id=device_id, user_id=current_user_id).first()
        if not device:
            return jsonify({'error': '设备不存在或无权限访问'}), 403

        # 统计同步数据
        test_results_count = TestResult.query.join(TestBatch).filter(
            TestBatch.device_id == device.id
        ).count()

        impedance_details_count = ImpedanceDetail.query.join(TestResult).join(TestBatch).filter(
            TestBatch.device_id == device.id
        ).count()

        return jsonify({
            'device_id': device_id,
            'device_name': device.name,
            'last_sync': device.last_sync.isoformat() if device.last_sync else None,
            'test_results_count': test_results_count,
            'impedance_details_count': impedance_details_count,
            'status': device.status
        }), 200

    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        return jsonify({'error': f'获取同步状态失败: {str(e)}'}), 500


@sync_bp.route('/devices/<device_id>', methods=['GET'])
@jwt_required()
def get_device_info(device_id):
    """获取设备信息"""
    try:
        current_user_id = get_jwt_identity()

        # 验证设备权限
        device = Device.query.filter_by(device_id=device_id, user_id=current_user_id).first()
        if not device:
            return jsonify({'error': '设备不存在或无权限访问'}), 404

        return jsonify({
            'message': '设备信息获取成功',
            'device': device.to_dict()
        }), 200

    except Exception as e:
        logger.error(f"获取设备信息失败: {e}")
        return jsonify({'error': f'获取设备信息失败: {str(e)}'}), 500
