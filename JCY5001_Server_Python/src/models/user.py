from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

class User(db.Model):
    """用户模型"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(100), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(100))
    role = db.Column(db.String(20), default='user', nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    devices = db.relationship('Device', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    test_batches = db.relationship('TestBatch', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, username, email=None, password=None, company=None, role='user'):
        self.username = username
        self.email = email
        if password:
            self.set_password(password)
        self.company = company
        self.role = role
    
    def set_password(self, password):
        """设置密码哈希"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """验证密码"""
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """更新最后登录时间"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self, include_sensitive=False):
        """转换为字典"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'company': self.company,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_sensitive:
            data['password_hash'] = self.password_hash
        
        return data
    
    def has_permission(self, permission):
        """检查用户权限"""
        role_permissions = {
            'admin': ['read', 'write', 'delete', 'manage_users', 'manage_models'],
            'manager': ['read', 'write', 'delete'],
            'user': ['read', 'write'],
            'readonly': ['read']
        }
        
        return permission in role_permissions.get(self.role, [])
    
    def can_access_resource(self, resource_user_id):
        """检查是否可以访问特定用户的资源"""
        if self.role == 'admin':
            return True
        return self.id == resource_user_id
    
    @staticmethod
    def validate_role(role):
        """验证角色是否有效"""
        valid_roles = ['admin', 'manager', 'user', 'readonly']
        return role in valid_roles
    
    def __repr__(self):
        return f'<User {self.username}>'

class Device(db.Model):
    """设备模型"""
    __tablename__ = 'devices'
    
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    model = db.Column(db.String(50), default='JCY5001')
    firmware_version = db.Column(db.String(20))
    status = db.Column(db.String(20), default='active', nullable=False)
    last_sync = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    test_batches = db.relationship('TestBatch', backref='device', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, device_id, user_id, name, model='JCY5001', firmware_version=None):
        self.device_id = device_id
        self.user_id = user_id
        self.name = name
        self.model = model
        self.firmware_version = firmware_version
    
    def update_sync_time(self):
        """更新同步时间"""
        self.last_sync = datetime.utcnow()
        db.session.commit()
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'user_id': self.user_id,
            'name': self.name,
            'model': self.model,
            'firmware_version': self.firmware_version,
            'status': self.status,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def validate_status(status):
        """验证设备状态是否有效"""
        valid_statuses = ['active', 'inactive', 'maintenance']
        return status in valid_statuses
    
    def __repr__(self):
        return f'<Device {self.device_id}>'

class Battery(db.Model):
    """电池模型"""
    __tablename__ = 'batteries'
    
    id = db.Column(db.Integer, primary_key=True)
    battery_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    batch_number = db.Column(db.String(50), index=True)
    cell_type = db.Column(db.String(20))
    nominal_capacity = db.Column(db.Numeric(8, 2))  # mAh
    nominal_voltage = db.Column(db.Numeric(5, 3))   # V
    manufacturer = db.Column(db.String(100))
    production_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    test_results = db.relationship('TestResult', backref='battery', lazy='dynamic')
    
    def __init__(self, battery_id, batch_number=None, cell_type=None, 
                 nominal_capacity=None, nominal_voltage=None, 
                 manufacturer=None, production_date=None):
        self.battery_id = battery_id
        self.batch_number = batch_number
        self.cell_type = cell_type
        self.nominal_capacity = nominal_capacity
        self.nominal_voltage = nominal_voltage
        self.manufacturer = manufacturer
        self.production_date = production_date
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'battery_id': self.battery_id,
            'batch_number': self.batch_number,
            'cell_type': self.cell_type,
            'nominal_capacity': float(self.nominal_capacity) if self.nominal_capacity else None,
            'nominal_voltage': float(self.nominal_voltage) if self.nominal_voltage else None,
            'manufacturer': self.manufacturer,
            'production_date': self.production_date.isoformat() if self.production_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def validate_cell_type(cell_type):
        """验证电池类型是否有效"""
        valid_types = ['LFP', 'NMC', 'LCO', 'NCA', 'LTO']
        return cell_type in valid_types
    
    def __repr__(self):
        return f'<Battery {self.battery_id}>'

class TestBatch(db.Model):
    """测试批次模型"""
    __tablename__ = 'test_batches'
    
    id = db.Column(db.Integer, primary_key=True)
    batch_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    device_id = db.Column(db.Integer, db.ForeignKey('devices.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime)
    total_count = db.Column(db.Integer, default=0)
    pass_count = db.Column(db.Integer, default=0)
    fail_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='running', nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关系
    test_results = db.relationship('TestResult', backref='test_batch', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, batch_id, device_id, user_id, start_time, notes=None):
        self.batch_id = batch_id
        self.device_id = device_id
        self.user_id = user_id
        self.start_time = start_time
        self.notes = notes
    
    def update_statistics(self):
        """更新统计信息"""
        results = self.test_results.all()
        self.total_count = len(results)
        self.pass_count = sum(1 for r in results if r.test_result == 'pass')
        self.fail_count = sum(1 for r in results if r.test_result == 'fail')
        db.session.commit()
    
    def complete_batch(self):
        """完成批次"""
        self.end_time = datetime.utcnow()
        self.status = 'completed'
        self.update_statistics()
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'batch_id': self.batch_id,
            'device_id': self.device_id,
            'user_id': self.user_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'total_count': self.total_count,
            'pass_count': self.pass_count,
            'fail_count': self.fail_count,
            'pass_rate': round((self.pass_count or 0) / (self.total_count or 1) * 100, 2) if (self.total_count or 0) > 0 else 0,
            'status': self.status,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @staticmethod
    def validate_status(status):
        """验证批次状态是否有效"""
        valid_statuses = ['running', 'completed', 'failed', 'cancelled']
        return status in valid_statuses
    
    def __repr__(self):
        return f'<TestBatch {self.batch_id}>'

class TestResult(db.Model):
    """测试结果模型 - 扩展以匹配桌面软件数据结构"""
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    batch_id = db.Column(db.Integer, db.ForeignKey('test_batches.id'), nullable=False)
    battery_id = db.Column(db.Integer, db.ForeignKey('batteries.id'))
    channel_number = db.Column(db.Integer)
    battery_code = db.Column(db.String(100))   # 电池码
    test_start_time = db.Column(db.DateTime, nullable=False, index=True)
    test_end_time = db.Column(db.DateTime)
    test_duration = db.Column(db.Numeric(10, 3))  # 测试持续时间（秒）
    voltage = db.Column(db.Numeric(6, 3))      # V
    rs_value = db.Column(db.Numeric(8, 4))     # mΩ
    rct_value = db.Column(db.Numeric(8, 4))    # mΩ
    rsei_value = db.Column(db.Numeric(8, 4))   # mΩ - SEI膜电阻
    w_impedance = db.Column(db.Numeric(8, 4))  # W阻抗
    rs_grade = db.Column(db.Integer)           # Rs等级
    rct_grade = db.Column(db.Integer)          # Rct等级
    is_pass = db.Column(db.Boolean, nullable=False)  # 是否通过
    fail_reason = db.Column(db.Text)           # 失败原因
    test_mode = db.Column(db.String(50))       # 测试模式
    frequency_list = db.Column(db.Text)        # 频率列表(JSON)
    raw_data = db.Column(db.Text)              # 原始数据(JSON)
    outlier_result = db.Column(db.Text)        # 离群检测结果
    baseline_filename = db.Column(db.String(255))  # 基准文件名
    baseline_id = db.Column(db.Integer)        # 基准ID
    max_deviation_percent = db.Column(db.Numeric(8, 4))  # 最大偏差百分比
    frequency_deviations = db.Column(db.Text)  # 频率偏差(JSON)
    operator = db.Column(db.String(100))       # 操作员
    battery_type = db.Column(db.String(100))   # 电池类型
    battery_spec = db.Column(db.String(100))   # 电池规格
    batch_number = db.Column(db.String(100))   # 批次号
    rct_coefficient_of_variation = db.Column(db.Numeric(8, 4))  # Rct变异系数
    capacity_prediction = db.Column(db.Numeric(8, 2))  # 容量预测
    voltage_range_min = db.Column(db.Numeric(6, 3))    # 电压范围最小值
    voltage_range_max = db.Column(db.Numeric(6, 3))    # 电压范围最大值
    rs_range_min = db.Column(db.Numeric(8, 4))         # Rs范围最小值
    rs_range_max = db.Column(db.Numeric(8, 4))         # Rs范围最大值
    rct_range_min = db.Column(db.Numeric(8, 4))        # Rct范围最小值
    rct_range_max = db.Column(db.Numeric(8, 4))        # Rct范围最大值
    warburg_coefficient = db.Column(db.Numeric(10, 6)) # Warburg系数
    warburg_01hz = db.Column(db.Numeric(10, 6))        # 0.1Hz Warburg阻抗
    warburg_001hz = db.Column(db.Numeric(10, 6))       # 0.01Hz Warburg阻抗
    has_warburg_diffusion = db.Column(db.Boolean)      # 是否有Warburg扩散
    has_sei = db.Column(db.Boolean)                    # 是否有SEI膜
    sei_confidence = db.Column(db.Numeric(5, 4))       # SEI置信度
    double_layer_capacitance = db.Column(db.Numeric(10, 6))  # 双电层电容
    sei_capacitance = db.Column(db.Numeric(10, 6))     # SEI电容
    total_capacitance = db.Column(db.Numeric(10, 6))   # 总电容
    impedance_ratio = db.Column(db.Numeric(8, 4))      # 阻抗比(Rp/Rs)
    capacity = db.Column(db.Numeric(8, 2))     # Ah
    thickness = db.Column(db.Numeric(6, 3))    # mm
    temperature = db.Column(db.Numeric(5, 2))  # °C
    test_result = db.Column(db.String(10))     # pass/fail (兼容字段)
    error_code = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # 关系
    impedance_details = db.relationship('ImpedanceDetail', backref='test_result', lazy='dynamic', cascade='all, delete-orphan')
    
    def __init__(self, test_id, batch_id, test_start_time, battery_code=None, channel_number=None,
                 test_end_time=None, test_duration=None, voltage=None, rs_value=None, rct_value=None,
                 rsei_value=None, w_impedance=None, rs_grade=None, rct_grade=None, is_pass=False,
                 fail_reason=None, test_mode=None, frequency_list=None, raw_data=None,
                 outlier_result=None, baseline_filename=None, baseline_id=None,
                 max_deviation_percent=None, frequency_deviations=None, operator=None,
                 battery_type=None, battery_spec=None, batch_number=None,
                 rct_coefficient_of_variation=None, capacity_prediction=None,
                 voltage_range_min=None, voltage_range_max=None, rs_range_min=None,
                 rs_range_max=None, rct_range_min=None, rct_range_max=None,
                 warburg_coefficient=None, warburg_01hz=None, warburg_001hz=None,
                 has_warburg_diffusion=None, has_sei=None, sei_confidence=None,
                 double_layer_capacitance=None, sei_capacitance=None, total_capacitance=None,
                 impedance_ratio=None, capacity=None, thickness=None, temperature=None,
                 test_result=None, battery_id=None, error_code=None):
        self.test_id = test_id
        self.batch_id = batch_id
        self.battery_id = battery_id
        self.channel_number = channel_number
        self.battery_code = battery_code
        self.test_start_time = test_start_time
        self.test_end_time = test_end_time
        self.test_duration = test_duration
        self.voltage = voltage
        self.rs_value = rs_value
        self.rct_value = rct_value
        self.rsei_value = rsei_value
        self.w_impedance = w_impedance
        self.rs_grade = rs_grade
        self.rct_grade = rct_grade
        self.is_pass = is_pass
        self.fail_reason = fail_reason
        self.test_mode = test_mode
        self.frequency_list = frequency_list
        self.raw_data = raw_data
        self.outlier_result = outlier_result
        self.baseline_filename = baseline_filename
        self.baseline_id = baseline_id
        self.max_deviation_percent = max_deviation_percent
        self.frequency_deviations = frequency_deviations
        self.operator = operator
        self.battery_type = battery_type
        self.battery_spec = battery_spec
        self.batch_number = batch_number
        self.rct_coefficient_of_variation = rct_coefficient_of_variation
        self.capacity_prediction = capacity_prediction
        self.voltage_range_min = voltage_range_min
        self.voltage_range_max = voltage_range_max
        self.rs_range_min = rs_range_min
        self.rs_range_max = rs_range_max
        self.rct_range_min = rct_range_min
        self.rct_range_max = rct_range_max
        self.warburg_coefficient = warburg_coefficient
        self.warburg_01hz = warburg_01hz
        self.warburg_001hz = warburg_001hz
        self.has_warburg_diffusion = has_warburg_diffusion
        self.has_sei = has_sei
        self.sei_confidence = sei_confidence
        self.double_layer_capacitance = double_layer_capacitance
        self.sei_capacitance = sei_capacitance
        self.total_capacitance = total_capacitance
        self.impedance_ratio = impedance_ratio
        self.capacity = capacity
        self.thickness = thickness
        self.temperature = temperature
        self.test_result = test_result
        self.error_code = error_code
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'test_id': self.test_id,
            'batch_id': self.batch_id,
            'battery_id': self.battery_id,
            'channel_number': self.channel_number,
            'battery_code': self.battery_code,
            'test_start_time': self.test_start_time.isoformat() if self.test_start_time else None,
            'test_end_time': self.test_end_time.isoformat() if self.test_end_time else None,
            'test_duration': float(self.test_duration) if self.test_duration else None,
            'voltage': float(self.voltage) if self.voltage else None,
            'rs_value': float(self.rs_value) if self.rs_value else None,
            'rct_value': float(self.rct_value) if self.rct_value else None,
            'rsei_value': float(self.rsei_value) if self.rsei_value else None,
            'w_impedance': float(self.w_impedance) if self.w_impedance else None,
            'rs_grade': self.rs_grade,
            'rct_grade': self.rct_grade,
            'is_pass': self.is_pass,
            'fail_reason': self.fail_reason,
            'test_mode': self.test_mode,
            'frequency_list': self.frequency_list,
            'raw_data': self.raw_data,
            'outlier_result': self.outlier_result,
            'baseline_filename': self.baseline_filename,
            'baseline_id': self.baseline_id,
            'max_deviation_percent': float(self.max_deviation_percent) if self.max_deviation_percent else None,
            'frequency_deviations': self.frequency_deviations,
            'operator': self.operator,
            'battery_type': self.battery_type,
            'battery_spec': self.battery_spec,
            'batch_number': self.batch_number,
            'rct_coefficient_of_variation': float(self.rct_coefficient_of_variation) if self.rct_coefficient_of_variation else None,
            'capacity_prediction': float(self.capacity_prediction) if self.capacity_prediction else None,
            'voltage_range_min': float(self.voltage_range_min) if self.voltage_range_min else None,
            'voltage_range_max': float(self.voltage_range_max) if self.voltage_range_max else None,
            'rs_range_min': float(self.rs_range_min) if self.rs_range_min else None,
            'rs_range_max': float(self.rs_range_max) if self.rs_range_max else None,
            'rct_range_min': float(self.rct_range_min) if self.rct_range_min else None,
            'rct_range_max': float(self.rct_range_max) if self.rct_range_max else None,
            'warburg_coefficient': float(self.warburg_coefficient) if self.warburg_coefficient else None,
            'warburg_01hz': float(self.warburg_01hz) if self.warburg_01hz else None,
            'warburg_001hz': float(self.warburg_001hz) if self.warburg_001hz else None,
            'has_warburg_diffusion': self.has_warburg_diffusion,
            'has_sei': self.has_sei,
            'sei_confidence': float(self.sei_confidence) if self.sei_confidence else None,
            'double_layer_capacitance': float(self.double_layer_capacitance) if self.double_layer_capacitance else None,
            'sei_capacitance': float(self.sei_capacitance) if self.sei_capacitance else None,
            'total_capacitance': float(self.total_capacitance) if self.total_capacitance else None,
            'impedance_ratio': float(self.impedance_ratio) if self.impedance_ratio else None,
            'capacity': float(self.capacity) if self.capacity else None,
            'thickness': float(self.thickness) if self.thickness else None,
            'temperature': float(self.temperature) if self.temperature else None,
            'test_result': self.test_result,
            'error_code': self.error_code,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @staticmethod
    def validate_test_result(test_result):
        """验证测试结果是否有效"""
        valid_results = ['pass', 'fail']
        return test_result in valid_results
    
    def __repr__(self):
        return f'<TestResult {self.test_id}>'

class ImpedanceDetail(db.Model):
    """阻抗详情模型 - 扩展以匹配桌面软件数据结构"""
    __tablename__ = 'impedance_details'

    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test_results.id'), nullable=False)
    batch_id = db.Column(db.Integer, nullable=False)  # 批次ID
    channel_number = db.Column(db.Integer, nullable=False)  # 通道号
    battery_code = db.Column(db.String(100), nullable=False)  # 电池码
    test_timestamp = db.Column(db.String(50), nullable=False)  # 测试时间戳
    frequency = db.Column(db.Numeric(10, 2), nullable=False)  # Hz
    impedance_real = db.Column(db.Numeric(10, 6), nullable=False)  # 实部阻抗 mΩ
    impedance_imag = db.Column(db.Numeric(10, 6), nullable=False)  # 虚部阻抗 mΩ
    voltage = db.Column(db.Numeric(6, 3))      # 电压 V
    test_sequence = db.Column(db.Integer)      # 测试序列
    z_value = db.Column(db.Numeric(10, 6))     # Z值 mΩ
    baseline_z_value = db.Column(db.Numeric(10, 6))  # 基准Z值 mΩ
    deviation_percent = db.Column(db.Numeric(8, 4))  # 偏差百分比
    # 兼容字段
    z_real = db.Column(db.Numeric(10, 6))      # mΩ (兼容)
    z_imag = db.Column(db.Numeric(10, 6))      # mΩ (兼容)
    z_magnitude = db.Column(db.Numeric(10, 6)) # mΩ (兼容)
    phase_angle = db.Column(db.Numeric(8, 4))  # degrees (兼容)
    measurement_time = db.Column(db.DateTime)  # 测量时间 (兼容)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __init__(self, test_id, batch_id, channel_number, battery_code, test_timestamp,
                 frequency, impedance_real, impedance_imag, voltage=None, test_sequence=None,
                 z_value=None, baseline_z_value=None, deviation_percent=None,
                 z_real=None, z_imag=None, z_magnitude=None, phase_angle=None, measurement_time=None):
        self.test_id = test_id
        self.batch_id = batch_id
        self.channel_number = channel_number
        self.battery_code = battery_code
        self.test_timestamp = test_timestamp
        self.frequency = frequency
        self.impedance_real = impedance_real
        self.impedance_imag = impedance_imag
        self.voltage = voltage
        self.test_sequence = test_sequence
        self.z_value = z_value
        self.baseline_z_value = baseline_z_value
        self.deviation_percent = deviation_percent
        # 兼容字段
        self.z_real = z_real or impedance_real
        self.z_imag = z_imag or impedance_imag
        self.z_magnitude = z_magnitude
        self.phase_angle = phase_angle
        self.measurement_time = measurement_time
    
    def to_dict(self):
        """转换为字典"""
        return {
            'id': self.id,
            'test_id': self.test_id,
            'frequency': float(self.frequency) if self.frequency else None,
            'z_real': float(self.z_real) if self.z_real else None,
            'z_imag': float(self.z_imag) if self.z_imag else None,
            'z_magnitude': float(self.z_magnitude) if self.z_magnitude else None,
            'phase_angle': float(self.phase_angle) if self.phase_angle else None,
            'measurement_time': self.measurement_time.isoformat() if self.measurement_time else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<ImpedanceDetail test_id={self.test_id} freq={self.frequency}>'

