"""
公开API路由
不需要认证的公开接口
"""

from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import and_, or_, desc

from extensions import db
from models.user import User, TestBatch, TestResult, Battery, ImpedanceDetail

public_bp = Blueprint('public', __name__)

@public_bp.route('/test-results', methods=['GET'])
def get_public_test_results():
    """获取公开的测试结果列表（不需要认证）"""
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        batch_id = request.args.get('batch_id', type=int)
        battery_id = request.args.get('battery_id', type=int)
        test_result = request.args.get('test_result')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        search = request.args.get('search')
        
        current_app.logger.info(f"公开API请求测试结果: page={page}, per_page={per_page}")
        
        # 构建查询 - 获取所有测试结果
        query = TestResult.query
        
        # 批次过滤
        if batch_id:
            query = query.filter(TestResult.batch_id == batch_id)
        
        # 电池过滤
        if battery_id:
            query = query.filter(TestResult.battery_id == battery_id)
        
        # 测试结果过滤
        if test_result:
            query = query.filter(TestResult.test_result == test_result)
        
        # 日期范围过滤
        if start_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                query = query.filter(TestResult.test_time >= start_dt)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                query = query.filter(TestResult.test_time <= end_dt)
            except ValueError:
                pass
        
        # 搜索过滤
        if search:
            search_filter = or_(
                TestResult.serial_number.ilike(f'%{search}%'),
                TestResult.batch_number.ilike(f'%{search}%')
            )
            query = query.filter(search_filter)
        
        # 按时间倒序排列
        query = query.order_by(desc(TestResult.test_time))
        
        # 分页
        pagination = query.paginate(
            page=page, 
            per_page=per_page, 
            error_out=False
        )
        
        # 格式化结果
        results = []
        for result in pagination.items:
            # 获取关联的电池信息
            battery = Battery.query.get(result.battery_id) if result.battery_id else None
            
            # 获取关联的批次信息
            batch = TestBatch.query.get(result.batch_id) if result.batch_id else None
            
            result_data = {
                'id': result.id,
                'device_id': batch.device_id if batch else 'Unknown',
                'test_time': result.test_time.isoformat() if result.test_time else None,
                'channel': result.channel_number,
                'voltage': float(result.voltage) if result.voltage else 0.0,
                'rs': float(result.rs) if result.rs else 0.0,
                'rct': float(result.rct) if result.rct else 0.0,
                'grade': result.grade or '',
                'status': result.test_result or '',
                'serial_number': result.serial_number or '',
                'batch_number': result.batch_number or '',
                'battery_type': batch.battery_type if batch else '',
                'battery_spec': batch.battery_spec if batch else '',
                'operator': batch.operator if batch else '',
                'w_impedance': float(result.w_impedance) if result.w_impedance else 0.0,
                'rsei_value': float(result.rsei_value) if result.rsei_value else 0.0,
                'rs_grade': result.rs_grade or '',
                'rct_grade': result.rct_grade or '',
                'fail_reason': result.fail_reason or ''
            }
            results.append(result_data)
        
        current_app.logger.info(f"返回 {len(results)} 条测试结果")
        
        return jsonify({
            'success': True,
            'data': results,
            'pagination': {
                'page': pagination.page,
                'pages': pagination.pages,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"获取公开测试结果失败: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'获取测试结果失败: {str(e)}',
            'status_code': 500
        }), 500

@public_bp.route('/health', methods=['GET'])
def public_health():
    """公开健康检查"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'JCY5001AS Public API'
    })

@public_bp.route('/stats', methods=['GET'])
def get_public_stats():
    """获取公开统计信息"""
    try:
        # 统计测试结果数量
        total_tests = TestResult.query.count()
        total_batches = TestBatch.query.count()
        total_batteries = Battery.query.count()
        
        # 最近的测试
        recent_test = TestResult.query.order_by(desc(TestResult.test_time)).first()
        
        stats = {
            'total_tests': total_tests,
            'total_batches': total_batches,
            'total_batteries': total_batteries,
            'last_test_time': recent_test.test_time.isoformat() if recent_test and recent_test.test_time else None
        }
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        current_app.logger.error(f"获取公开统计信息失败: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': f'获取统计信息失败: {str(e)}',
            'status_code': 500
        }), 500
