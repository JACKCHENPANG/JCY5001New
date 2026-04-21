import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  message,
  Space,
  Tag,
  Popconfirm,
  Typography,
  Row,
  Col,
  Statistic
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  SyncOutlined,
  DatabaseOutlined,
  LinkOutlined,
  DisconnectOutlined
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';

const { Title, Text } = Typography;

interface Device {
  id: number;
  device_id: string;
  name: string;
  model: string;
  firmware_version?: string;
  status: 'active' | 'inactive' | 'maintenance';
  last_sync?: string;
  created_at: string;
}

interface DeviceForm {
  device_id: string;
  name: string;
  model: string;
  firmware_version?: string;
}

const DeviceBindingPage: React.FC = () => {
  const { user } = useAuth();
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingDevice, setEditingDevice] = useState<Device | null>(null);
  const [form] = Form.useForm();

  // 获取设备列表
  const fetchDevices = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('http://localhost:5002/api/devices/', {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        const result = await response.json();
        setDevices(result.devices || []);
      } else {
        message.error('获取设备列表失败');
      }
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

  // 添加/编辑设备
  const handleSubmit = async (values: DeviceForm) => {
    try {
      const token = localStorage.getItem('token');
      const url = editingDevice 
        ? `http://localhost:5002/api/devices/${editingDevice.id}`
        : 'http://localhost:5002/api/devices/';
      
      const method = editingDevice ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(values)
      });

      if (response.ok) {
        message.success(editingDevice ? '设备更新成功' : '设备绑定成功');
        setModalVisible(false);
        setEditingDevice(null);
        form.resetFields();
        fetchDevices();
      } else {
        const result = await response.json();
        message.error(result.message || '操作失败');
      }
    } catch (error) {
      console.error('设备操作失败:', error);
      message.error('设备操作失败');
    }
  };

  // 删除设备
  const handleDelete = async (deviceId: number) => {
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`http://localhost:5002/api/devices/${deviceId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });

      if (response.ok) {
        message.success('设备删除成功');
        fetchDevices();
      } else {
        const result = await response.json();
        message.error(result.message || '删除失败');
      }
    } catch (error) {
      console.error('删除设备失败:', error);
      message.error('删除设备失败');
    }
  };

  // 打开添加/编辑模态框
  const openModal = (device?: Device) => {
    if (device) {
      setEditingDevice(device);
      form.setFieldsValue(device);
    } else {
      setEditingDevice(null);
      form.resetFields();
    }
    setModalVisible(true);
  };

  // 状态标签颜色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'green';
      case 'inactive': return 'red';
      case 'maintenance': return 'orange';
      default: return 'default';
    }
  };

  // 状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'active': return '在线';
      case 'inactive': return '离线';
      case 'maintenance': return '维护中';
      default: return '未知';
    }
  };

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 80,
    },
    {
      title: '设备ID',
      dataIndex: 'device_id',
      key: 'device_id',
      render: (text: string) => <Text code>{text}</Text>
    },
    {
      title: '设备名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '型号',
      dataIndex: 'model',
      key: 'model',
    },
    {
      title: '固件版本',
      dataIndex: 'firmware_version',
      key: 'firmware_version',
      render: (text: string) => text || '-'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      )
    },
    {
      title: '最后同步',
      dataIndex: 'last_sync',
      key: 'last_sync',
      render: (text: string) => text ? new Date(text).toLocaleString() : '-'
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (text: string) => new Date(text).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record: Device) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => openModal(record)}
          >
            编辑
          </Button>
          <Popconfirm
            title="确定要删除这个设备吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 统计数据
  const stats = {
    total: devices.length,
    active: devices.filter(d => d.status === 'active').length,
    inactive: devices.filter(d => d.status === 'inactive').length,
    maintenance: devices.filter(d => d.status === 'maintenance').length,
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>
          <LinkOutlined /> 设备绑定管理
        </Title>
        <Text type="secondary">
          管理您的JCY5001AS设备，绑定新设备或编辑现有设备信息
        </Text>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="总设备数"
              value={stats.total}
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="在线设备"
              value={stats.active}
              valueStyle={{ color: '#3f8600' }}
              prefix={<LinkOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="离线设备"
              value={stats.inactive}
              valueStyle={{ color: '#cf1322' }}
              prefix={<DisconnectOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="维护中"
              value={stats.maintenance}
              valueStyle={{ color: '#d48806' }}
              prefix={<SyncOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 设备列表 */}
      <Card
        title="我的设备"
        extra={
          <Space>
            <Button
              icon={<SyncOutlined />}
              onClick={fetchDevices}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => openModal()}
            >
              绑定设备
            </Button>
          </Space>
        }
      >
        <Table
          columns={columns}
          dataSource={devices}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`,
          }}
        />
      </Card>

      {/* 添加/编辑设备模态框 */}
      <Modal
        title={editingDevice ? '编辑设备' : '绑定新设备'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingDevice(null);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="device_id"
            label="设备ID"
            rules={[
              { required: true, message: '请输入设备ID' },
              { pattern: /^[A-Za-z0-9_-]+$/, message: '设备ID只能包含字母、数字、下划线和连字符' }
            ]}
          >
            <Input 
              placeholder="请输入设备的唯一标识符"
              disabled={!!editingDevice}
            />
          </Form.Item>

          <Form.Item
            name="name"
            label="设备名称"
            rules={[{ required: true, message: '请输入设备名称' }]}
          >
            <Input placeholder="请输入设备名称" />
          </Form.Item>

          <Form.Item
            name="model"
            label="设备型号"
            initialValue="JCY5001A"
          >
            <Input placeholder="请输入设备型号" />
          </Form.Item>

          <Form.Item
            name="firmware_version"
            label="固件版本"
          >
            <Input placeholder="请输入固件版本（可选）" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingDevice ? '更新' : '绑定'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DeviceBindingPage;
