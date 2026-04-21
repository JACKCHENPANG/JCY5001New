import os
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from sqlalchemy import and_, or_

from extensions import db
from models.user import User, Battery, TestResult, TestBatch
from utils.excel_utils import ExcelTemplateGenerator, ExcelDataParser, ExcelExporter

data_bp = Blueprint('data', __name__)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}
# 最大文件大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_file_size(file):
    """验证文件大小"""
    file.seek(0, 2)  # 移动到文件末尾
    size = file.tell()
    file.seek(0)  # 重置到文件开头
    return size <= MAX_FILE_SIZE

@data_bp.route('/templates/battery', methods=['GET'])
@jwt_required()
def download_battery_template():
    """下载电池出厂数据模板"""
    try:
        generator = ExcelTemplateGenerator()
        template_file = generator.create_battery_template()
        
        filename = f"电池出厂数据模板_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            template_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        current_app.logger.error(f"生成电池模板错误: {str(e)}")
        return jsonify({
            'error': 'Template Generation Failed',
            'message': '模板生成失败',
            'status_code': 500
        }), 500

@data_bp.route('/templates/test-results', methods=['GET'])
@jwt_required()
def download_test_results_template():
    """下载测试结果数据模板"""
    try:
        generator = ExcelTemplateGenerator()
        template_file = generator.create_test_results_template()
        
        filename = f"测试结果数据模板_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            template_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        current_app.logger.error(f"生成测试结果模板错误: {str(e)}")
        return jsonify({
            'error': 'Template Generation Failed',
            'message': '模板生成失败',
            'status_code': 500
        }), 500

@data_bp.route('/templates/devices', methods=['GET'])
@jwt_required()
def download_device_template():
    """下载设备信息模板"""
    try:
        generator = ExcelTemplateGenerator()
        template_file = generator.create_device_template()
        
        filename = f"设备信息模板_{datetime.now().strftime('%Y%m%d')}.xlsx"
        
        return send_file(
            template_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        current_app.logger.error(f"生成设备模板错误: {str(e)}")
        return jsonify({
            'error': 'Template Generation Failed',
            'message': '模板生成失败',
            'status_code': 500
        }), 500

@data_bp.route('/import/batteries', methods=['POST'])
@jwt_required()
def import_battery_data():
    """导入电池出厂数据"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'error': 'No File',
                'message': '未选择文件',
                'status_code': 400
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'error': 'No File Selected',
                'message': '未选择文件',
                'status_code': 400
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'Invalid File Type',
                'message': '文件类型不支持，请上传Excel文件(.xlsx, .xls)',
                'status_code': 400
            }), 400
        
        if not validate_file_size(file):
            return jsonify({
                'error': 'File Too Large',
                'message': f'文件大小超过限制({MAX_FILE_SIZE // (1024*1024)}MB)',
                'status_code': 400
            }), 400
        
        # 解析Excel数据
        parser = ExcelDataParser()
        batteries_data, errors = parser.parse_battery_data(file.read())
        
        if errors:
            return jsonify({
                'error': 'Data Validation Failed',
                'message': '数据验证失败',
                'errors': errors,
                'status_code': 400
            }), 400
        
        if not batteries_data:
            return jsonify({
                'error': 'No Valid Data',
                'message': '没有有效的数据行',
                'status_code': 400
            }), 400
        
        # 检查重复的电池ID
        existing_battery_ids = set()
        duplicate_ids = []
        
        for battery_data in batteries_data:
            battery_id = battery_data['battery_id']
            if battery_id in existing_battery_ids:
                duplicate_ids.append(battery_id)
            else:
                existing_battery_ids.add(battery_id)
        
        if duplicate_ids:
            return jsonify({
                'error': 'Duplicate Battery IDs',
                'message': f'文件中存在重复的电池ID: {", ".join(duplicate_ids)}',
                'status_code': 400
            }), 400
        
        # 检查数据库中是否已存在
        existing_batteries = Battery.query.filter(
            Battery.battery_id.in_(list(existing_battery_ids))
        ).all()
        
        if existing_batteries:
            existing_ids = [b.battery_id for b in existing_batteries]
            return jsonify({
                'error': 'Battery IDs Already Exist',
                'message': f'以下电池ID已存在: {", ".join(existing_ids)}',
                'status_code': 409
            }), 409
        
        # 批量创建电池记录
        created_batteries = []
        for battery_data in batteries_data:
            battery = Battery(
                battery_id=battery_data['battery_id'],
                user_id=user.id,
                batch_number=battery_data.get('batch_number'),
                cell_type=battery_data.get('cell_type'),
                nominal_capacity=battery_data.get('nominal_capacity'),
                nominal_voltage=battery_data.get('nominal_voltage'),
                manufacturer=battery_data.get('manufacturer'),
                production_date=datetime.fromisoformat(battery_data['production_date']).date() if battery_data.get('production_date') else None,
                notes=battery_data.get('notes')
            )
            db.session.add(battery)
            created_batteries.append(battery)
        
        db.session.commit()
        
        return jsonify({
            'message': f'成功导入 {len(created_batteries)} 条电池记录',
            'imported_count': len(created_batteries),
            'batteries': [battery.to_dict() for battery in created_batteries],
            'status_code': 201
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"导入电池数据错误: {str(e)}")
        return jsonify({
            'error': 'Import Failed',
            'message': '导入数据时发生错误',
            'status_code': 500
        }), 500

@data_bp.route('/import/test-results', methods=['POST'])
@jwt_required()
def import_test_results():
    """导入测试结果数据"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        # 检查文件
        if 'file' not in request.files:
            return jsonify({
                'error': 'No File',
                'message': '未选择文件',
                'status_code': 400
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'error': 'No File Selected',
                'message': '未选择文件',
                'status_code': 400
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'error': 'Invalid File Type',
                'message': '文件类型不支持，请上传Excel文件(.xlsx, .xls)',
                'status_code': 400
            }), 400
        
        if not validate_file_size(file):
            return jsonify({
                'error': 'File Too Large',
                'message': f'文件大小超过限制({MAX_FILE_SIZE // (1024*1024)}MB)',
                'status_code': 400
            }), 400
        
        # 解析Excel数据
        parser = ExcelDataParser()
        test_results_data, errors = parser.parse_test_results_data(file.read())
        
        if errors:
            return jsonify({
                'error': 'Data Validation Failed',
                'message': '数据验证失败',
                'errors': errors,
                'status_code': 400
            }), 400
        
        if not test_results_data:
            return jsonify({
                'error': 'No Valid Data',
                'message': '没有有效的数据行',
                'status_code': 400
            }), 400
        
        # 检查重复的测试ID
        existing_test_ids = set()
        duplicate_ids = []
        
        for result_data in test_results_data:
            test_id = result_data['test_id']
            if test_id in existing_test_ids:
                duplicate_ids.append(test_id)
            else:
                existing_test_ids.add(test_id)
        
        if duplicate_ids:
            return jsonify({
                'error': 'Duplicate Test IDs',
                'message': f'文件中存在重复的测试ID: {", ".join(duplicate_ids)}',
                'status_code': 400
            }), 400
        
        # 检查数据库中是否已存在
        existing_results = TestResult.query.filter(
            TestResult.test_id.in_(list(existing_test_ids))
        ).all()
        
        if existing_results:
            existing_ids = [r.test_id for r in existing_results]
            return jsonify({
                'error': 'Test IDs Already Exist',
                'message': f'以下测试ID已存在: {", ".join(existing_ids)}',
                'status_code': 409
            }), 409
        
        # 验证批次ID是否存在
        batch_ids = list(set([result['batch_id'] for result in test_results_data]))
        existing_batches = TestBatch.query.filter(
            TestBatch.id.in_(batch_ids),
            TestBatch.user_id == user.id
        ).all()
        existing_batch_ids = set([batch.id for batch in existing_batches])
        
        missing_batch_ids = [bid for bid in batch_ids if bid not in existing_batch_ids]
        if missing_batch_ids:
            return jsonify({
                'error': 'Batch IDs Not Found',
                'message': f'以下批次ID不存在: {", ".join(map(str, missing_batch_ids))}',
                'status_code': 400
            }), 400
        
        # 批量创建测试结果记录
        created_results = []
        for result_data in test_results_data:
            # 查找对应的电池
            battery = None
            if result_data.get('battery_id_str'):
                battery = Battery.query.filter_by(
                    battery_id=result_data['battery_id_str'],
                    user_id=user.id
                ).first()
            
            test_result = TestResult(
                test_id=result_data['test_id'],
                batch_id=result_data['batch_id'],
                battery_id=battery.id if battery else None,
                test_time=datetime.fromisoformat(result_data['test_time']),
                channel_number=result_data.get('channel_number'),
                voltage=result_data.get('voltage'),
                rs_value=result_data.get('rs_value'),
                rct_value=result_data.get('rct_value'),
                capacity=result_data.get('capacity'),
                thickness=result_data.get('thickness'),
                temperature=result_data.get('temperature'),
                test_result=result_data.get('test_result'),
                error_code=result_data.get('error_code')
            )
            db.session.add(test_result)
            created_results.append(test_result)
        
        db.session.commit()
        
        return jsonify({
            'message': f'成功导入 {len(created_results)} 条测试结果',
            'imported_count': len(created_results),
            'status_code': 201
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"导入测试结果错误: {str(e)}")
        return jsonify({
            'error': 'Import Failed',
            'message': '导入数据时发生错误',
            'status_code': 500
        }), 500

@data_bp.route('/export/test-results', methods=['GET'])
@jwt_required()
def export_test_results():
    """导出测试结果数据"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        # 获取查询参数
        batch_id = request.args.get('batch_id', type=int)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        test_result = request.args.get('test_result')
        
        # 构建查询
        query = TestResult.query.join(TestBatch).filter(TestBatch.user_id == user.id)
        
        if batch_id:
            query = query.filter(TestResult.batch_id == batch_id)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(TestResult.test_time >= start_dt)
            except ValueError:
                return jsonify({
                    'error': 'Invalid Date Format',
                    'message': '开始日期格式错误',
                    'status_code': 400
                }), 400
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                query = query.filter(TestResult.test_time <= end_dt)
            except ValueError:
                return jsonify({
                    'error': 'Invalid Date Format',
                    'message': '结束日期格式错误',
                    'status_code': 400
                }), 400
        
        if test_result:
            query = query.filter(TestResult.test_result == test_result)
        
        # 获取数据
        test_results = query.all()
        
        if not test_results:
            return jsonify({
                'error': 'No Data Found',
                'message': '没有找到符合条件的数据',
                'status_code': 404
            }), 404
        
        # 转换为字典格式
        results_data = []
        for result in test_results:
            result_dict = result.to_dict()
            # 添加电池ID字符串
            if result.battery:
                result_dict['battery_id'] = result.battery.battery_id
            results_data.append(result_dict)
        
        # 生成Excel文件
        exporter = ExcelExporter()
        excel_file = exporter.export_test_results(results_data)
        
        filename = f"测试结果导出_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        current_app.logger.error(f"导出测试结果错误: {str(e)}")
        return jsonify({
            'error': 'Export Failed',
            'message': '导出数据时发生错误',
            'status_code': 500
        }), 500

@data_bp.route('/export/statistics', methods=['GET'])
@jwt_required()
def export_statistics():
    """导出统计报告"""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'error': 'User Not Found',
                'message': '用户不存在',
                'status_code': 404
            }), 404
        
        # 获取查询参数
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # 构建查询
        query = TestResult.query.join(TestBatch).filter(TestBatch.user_id == user.id)
        
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date)
                query = query.filter(TestResult.test_time >= start_dt)
            except ValueError:
                return jsonify({
                    'error': 'Invalid Date Format',
                    'message': '开始日期格式错误',
                    'status_code': 400
                }), 400
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date)
                query = query.filter(TestResult.test_time <= end_dt)
            except ValueError:
                return jsonify({
                    'error': 'Invalid Date Format',
                    'message': '结束日期格式错误',
                    'status_code': 400
                }), 400
        
        # 计算统计信息
        all_results = query.all()
        total_tests = len(all_results)
        pass_tests = len([r for r in all_results if r.test_result == 'pass'])
        fail_tests = total_tests - pass_tests
        pass_rate = (pass_tests / total_tests * 100) if total_tests > 0 else 0
        
        # 每日统计
        from sqlalchemy import func, cast, Date
        daily_stats = db.session.query(
            cast(TestResult.test_time, Date).label('date'),
            func.count(TestResult.id).label('total'),
            func.sum(func.case([(TestResult.test_result == 'pass', 1)], else_=0)).label('pass_count'),
            func.sum(func.case([(TestResult.test_result == 'fail', 1)], else_=0)).label('fail_count')
        ).join(TestBatch).filter(TestBatch.user_id == user.id)
        
        if start_date:
            daily_stats = daily_stats.filter(TestResult.test_time >= start_dt)
        if end_date:
            daily_stats = daily_stats.filter(TestResult.test_time <= end_dt)
        
        daily_stats = daily_stats.group_by(cast(TestResult.test_time, Date)).all()
        
        daily_stats_list = []
        for stat in daily_stats:
            pass_rate_daily = (stat.pass_count / stat.total * 100) if stat.total > 0 else 0
            daily_stats_list.append({
                'date': stat.date.isoformat(),
                'total': stat.total,
                'pass_count': stat.pass_count,
                'fail_count': stat.fail_count,
                'pass_rate': pass_rate_daily
            })
        
        statistics = {
            'total_tests': total_tests,
            'pass_tests': pass_tests,
            'fail_tests': fail_tests,
            'pass_rate': pass_rate,
            'daily_stats': daily_stats_list
        }
        
        # 生成Excel文件
        exporter = ExcelExporter()
        excel_file = exporter.export_statistics_report(statistics)
        
        filename = f"统计报告_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        current_app.logger.error(f"导出统计报告错误: {str(e)}")
        return jsonify({
            'error': 'Export Failed',
            'message': '导出统计报告时发生错误',
            'status_code': 500
        }), 500

