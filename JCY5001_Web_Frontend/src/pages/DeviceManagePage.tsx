import React, { useState, useEffect } from 'react';
import {
  Table,
  Card,
  Button,
  Space,
  Tag,
  Typography,
  Input,
  Select,
  Row,
  Col,
  Modal,
  Form,
  message,
  Tooltip,
  Badge
} from 'antd';
import {
  DatabaseOutlined,
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
  WifiOutlined,
  DisconnectOutlined
} from '@ant-design/icons';

const { Title, Text } = Typography;
const { Option } = Select;

interface Device {
  id: string;
  name: string;
  deviceId: string;
  status: 'online' | 'offline' | 'maintenance';
  location: string;
  lastSeen: string;
  totalTests: number;
  passRate: number;
  version: string;
  ipAddress: string;
}

const DeviceManagePage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [devices, setDevices] = useState<Device[]>([]);
  const [filteredDevices, setFilteredDevices] = useState<Device[]>([]);
  const [searchText, setSearchText] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [form] = Form.useForm();

  // 获取设备列表
  const fetchDevices = async () => {
    setLoading(true);
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const mockDevices: Device[] = [
        {
          id: '1',
          name: '生产线A-测试台1',
          deviceId: 'JCY5001A_001',
          status: 'online',
          location: '车间A-1号位',
          lastSeen: '2025-07-07 14:30:25',
          totalTests: 1250,
          passRate: 94.5,
          version: 'V0.80.20',
          ipAddress: '192.168.1.101'
        },
        {
          id: '2',
          name: '生产线A-测试台2',
          deviceId: 'JCY5001A_002',
          status: 'online',
          location: '车间A-2号位',
          lastSeen: '2025-07-07 14:28:15',
          totalTests: 980,
          passRate: 92.1,
          version: 'V0.80.20',
          ipAddress: '192.168.1.102'
        },
        {
          id: '3',
          name: '生产线B-测试台1',
          deviceId: 'JCY5001A_003',
          status: 'offline',
          location: '车间B-1号位',
          lastSeen: '2025-07-07 12:15:30',
          totalTests: 756,
          passRate: 89.3,
          version: 'V0.80.18',
          ipAddress: '192.168.1.103'
        },
        {
          id: '4',
          name: '质检部-标准台',
          deviceId: 'JCY5001A_004',
          status: 'maintenance',
          location: '质检部',
          lastSeen: '2025-07-07 09:45:12',
          totalTests: 2340,
          passRate: 96.8,
          version: 'V0.80.20',
          ipAddress: '192.168.1.104'
        }
      ];
      
      setDevices(mockDevices);
      setFilteredDevices(mockDevices);
      
    } catch (error) {
      console.error('获取设备列表失败:', error);
      message.error('获取设备列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  // 搜索和筛选
  useEffect(() => {
    let filtered = devices;
    
    // 状态筛选
    if (statusFilter !== 'all') {
      filtered = filtered.filter(device => device.status === statusFilter);
    }
    
    // 文本搜索
    if (searchText) {
      filtered = filtered.filter(device =>
        device.name.toLowerCase().includes(searchText.toLowerCase()) ||
        device.deviceId.toLowerCase().includes(searchText.toLowerCase()) ||
        device.location.toLowerCase().includes(searchText.toLowerCase())
      );
    }
    
    setFilteredDevices(filtered);
  }, [devices, searchText, statusFilter]);

  // 状态标签渲染
  const renderStatus = (status: string) => {
    const statusConfig = {
      online: { color: 'success', text: '在线', icon: <WifiOutlined /> },
      offline: { color: 'error', text: '离线', icon: <DisconnectOutlined /> },
      maintenance: { color: 'warning', text: '维护中', icon: <EditOutlined /> }
    };
    
    const config = statusConfig[status as keyof typeof statusConfig];
    return (
      <Tag color={config.color} icon={config.icon}>
        {config.text}
      </Tag>
    );
  };

  // 表格列定义
  const columns = [
    {
      title: '设备名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
      render: (text: string, record: Device) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.deviceId}
          </Text>
        </div>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: renderStatus,
    },
    {
      title: '位置',
      dataIndex: 'location',
      key: 'location',
      width: 150,
    },
    {
      title: 'IP地址',
      dataIndex: 'ipAddress',
      key: 'ipAddress',
      width: 130,
    },
    {
      title: '最后在线',
      dataIndex: 'lastSeen',
      key: 'lastSeen',
      width: 150,
    },
    {
      title: '测试统计',
      key: 'stats',
      width: 120,
      render: (_, record: Device) => (
        <div>
          <div>总数: {record.totalTests}</div>
          <div style={{ color: record.passRate >= 90 ? '#52c41a' : '#ff4d4f' }}>
            合格率: {record.passRate}%
          </div>
        </div>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
      width: 100,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record: Device) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewDevice(record)}
            />
          </Tooltip>
          <Tooltip title="编辑">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditDevice(record)}
            />
          </Tooltip>
          <Tooltip title="删除">
            <Button
              type="text"
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteDevice(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 处理设备操作
  const handleViewDevice = (device: Device) => {
    Modal.info({
      title: '设备详情',
      width: 600,
      content: (
        <div style={{ marginTop: '16px' }}>
          <Row gutter={[16, 8]}>
            <Col span={8}><Text strong>设备名称:</Text></Col>
            <Col span={16}>{device.name}</Col>
            <Col span={8}><Text strong>设备ID:</Text></Col>
            <Col span={16}>{device.deviceId}</Col>
            <Col span={8}><Text strong>状态:</Text></Col>
            <Col span={16}>{renderStatus(device.status)}</Col>
            <Col span={8}><Text strong>位置:</Text></Col>
            <Col span={16}>{device.location}</Col>
            <Col span={8}><Text strong>IP地址:</Text></Col>
            <Col span={16}>{device.ipAddress}</Col>
            <Col span={8}><Text strong>软件版本:</Text></Col>
            <Col span={16}>{device.version}</Col>
            <Col span={8}><Text strong>总测试次数:</Text></Col>
            <Col span={16}>{device.totalTests}</Col>
            <Col span={8}><Text strong>合格率:</Text></Col>
            <Col span={16}>{device.passRate}%</Col>
            <Col span={8}><Text strong>最后在线:</Text></Col>
            <Col span={16}>{device.lastSeen}</Col>
          </Row>
        </div>
      ),
    });
  };

  const handleEditDevice = (device: Device) => {
    setEditingDevice(device);
    form.setFieldsValue(device);
    setModalVisible(true);
  };

  const handleDeleteDevice = (device: Device) => {
    Modal.confirm({
      title: '确认删除',
      content: `确定要删除设备 "${device.name}" 吗？此操作不可恢复。`,
      okText: '删除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => {
        message.success('设备删除成功');
        fetchDevices();
      },
    });
  };

  const handleAddDevice = () => {
    setEditingDevice(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleModalOk = async () => {
    try {
      const values = await form.validateFields();
      console.log('设备信息:', values);
      
      message.success(editingDevice ? '设备更新成功' : '设备添加成功');
      setModalVisible(false);
      fetchDevices();
    } catch (error) {
      console.error('表单验证失败:', error);
    }
  };

  return (
    <div>
      {/* 页面标题 */}
      <div className="page-header">
        <div>
          <Title level={2}>
            <Space>
              <DatabaseOutlined />
              设备管理
            </Space>
          </Title>
          <Text type="secondary">管理和监控所有JCY5001AS测试设备</Text>
        </div>
      </div>

      {/* 搜索和筛选 */}
      <Card style={{ marginBottom: '16px' }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={8} md={6}>
            <Input
              placeholder="搜索设备名称、ID或位置"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={24} sm={6} md={4}>
            <Select
              placeholder="设备状态"
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: '100%' }}
            >
              <Option value="all">全部状态</Option>
              <Option value="online">在线</Option>
              <Option value="offline">离线</Option>
              <Option value="maintenance">维护中</Option>
            </Select>
          </Col>
          <Col xs={24} sm={10} md={14}>
            <div className="action-buttons" style={{ justifyContent: 'flex-end' }}>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchDevices}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAddDevice}
              >
                添加设备
              </Button>
            </div>
          </Col>
        </Row>
      </Card>

      {/* 设备列表 */}
      <Card>
        <div className="responsive-table">
          <Table
            columns={columns}
            dataSource={filteredDevices}
            rowKey="id"
            loading={loading}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total) => `共 ${total} 台设备`,
            }}
            scroll={{ x: 1200 }}
          />
        </div>
      </Card>

      {/* 添加/编辑设备模态框 */}
      <Modal
        title={editingDevice ? '编辑设备' : '添加设备'}
        open={modalVisible}
        onOk={handleModalOk}
        onCancel={() => setModalVisible(false)}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          style={{ marginTop: '16px' }}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="name"
                label="设备名称"
                rules={[{ required: true, message: '请输入设备名称' }]}
              >
                <Input placeholder="请输入设备名称" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="deviceId"
                label="设备ID"
                rules={[{ required: true, message: '请输入设备ID' }]}
              >
                <Input placeholder="请输入设备ID" />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="location"
                label="设备位置"
                rules={[{ required: true, message: '请输入设备位置' }]}
              >
                <Input placeholder="请输入设备位置" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="ipAddress"
                label="IP地址"
                rules={[
                  { required: true, message: '请输入IP地址' },
                  { pattern: /^(\d{1,3}\.){3}\d{1,3}$/, message: '请输入有效的IP地址' }
                ]}
              >
                <Input placeholder="请输入IP地址" />
              </Form.Item>
            </Col>
          </Row>
          
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="status"
                label="设备状态"
                rules={[{ required: true, message: '请选择设备状态' }]}
              >
                <Select placeholder="请选择设备状态">
                  <Option value="online">在线</Option>
                  <Option value="offline">离线</Option>
                  <Option value="maintenance">维护中</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="version"
                label="软件版本"
              >
                <Input placeholder="请输入软件版本" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default DeviceManagePage;
