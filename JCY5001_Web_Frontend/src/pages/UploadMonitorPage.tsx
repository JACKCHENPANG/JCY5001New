import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Button,
  Space,
  Progress,
  Alert,
  Tabs,
  Timeline,
  Badge,
  Tooltip,
  message,
  Modal,
  Form,
  Input,
  Switch,
  Select,
  Divider
} from 'antd';
import {
  CloudUploadOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  ClockCircleOutlined,
  SettingOutlined,
  ReloadOutlined,
  DeleteOutlined,
  EyeOutlined,
  WifiOutlined,
  DisconnectOutlined
} from '@ant-design/icons';
import { testResultsAPI } from '../services/api';

const { TabPane } = Tabs;
const { Option } = Select;

interface UploadStatus {
  id: string;
  device_id: string;
  status: 'pending' | 'uploading' | 'completed' | 'failed';
  progress: number;
  test_count: number;
  uploaded_count: number;
  failed_count: number;
  start_time: string;
  end_time?: string;
  error_message?: string;
}

interface DeviceStatus {
  device_id: string;
  device_name: string;
  online: boolean;
  last_seen: string;
  pending_uploads: number;
  total_tests: number;
  upload_rate: number;
}

const UploadMonitorPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [uploadStatuses, setUploadStatuses] = useState<UploadStatus[]>([]);
  const [deviceStatuses, setDeviceStatuses] = useState<DeviceStatus[]>([]);
  const [uploadHistory, setUploadHistory] = useState<any[]>([]);
  const [configModalVisible, setConfigModalVisible] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(30); // 秒

  // 模拟数据
  const mockUploadStatuses: UploadStatus[] = [
    {
      id: 'upload_001',
      device_id: 'JCY5001A_001',
      status: 'uploading',
      progress: 75,
      test_count: 20,
      uploaded_count: 15,
      failed_count: 0,
      start_time: '2025-01-07 14:30:00'
    },
    {
      id: 'upload_002',
      device_id: 'JCY5001A_002',
      status: 'completed',
      progress: 100,
      test_count: 50,
      uploaded_count: 48,
      failed_count: 2,
      start_time: '2025-01-07 13:15:00',
      end_time: '2025-01-07 13:45:00'
    },
    {
      id: 'upload_003',
      device_id: 'JCY5001A_003',
      status: 'failed',
      progress: 30,
      test_count: 10,
      uploaded_count: 3,
      failed_count: 7,
      start_time: '2025-01-07 12:00:00',
      error_message: '网络连接超时'
    }
  ];

  const mockDeviceStatuses: DeviceStatus[] = [
    {
      device_id: 'JCY5001A_001',
      device_name: '测试设备-001',
      online: true,
      last_seen: '2025-01-07 14:35:00',
      pending_uploads: 5,
      total_tests: 1250,
      upload_rate: 98.5
    },
    {
      device_id: 'JCY5001A_002',
      device_name: '测试设备-002',
      online: true,
      last_seen: '2025-01-07 14:34:00',
      pending_uploads: 0,
      total_tests: 2100,
      upload_rate: 99.2
    },
    {
      device_id: 'JCY5001A_003',
      device_name: '测试设备-003',
      online: false,
      last_seen: '2025-01-07 12:15:00',
      pending_uploads: 15,
      total_tests: 890,
      upload_rate: 95.8
    }
  ];

  const mockUploadHistory = [
    {
      time: '2025-01-07 14:30:00',
      device: 'JCY5001A_001',
      action: '开始上传批次数据',
      status: 'info'
    },
    {
      time: '2025-01-07 14:25:00',
      device: 'JCY5001A_002',
      action: '上传完成 - 48/50 成功',
      status: 'success'
    },
    {
      time: '2025-01-07 14:20:00',
      device: 'JCY5001A_001',
      action: '网络连接恢复',
      status: 'success'
    },
    {
      time: '2025-01-07 14:15:00',
      device: 'JCY5001A_003',
      action: '上传失败 - 网络超时',
      status: 'error'
    }
  ];

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (autoRefresh) {
      interval = setInterval(() => {
        loadData();
      }, refreshInterval * 1000);
    }
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [autoRefresh, refreshInterval]);

  const loadData = async () => {
    setLoading(true);
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 500));
      setUploadStatuses(mockUploadStatuses);
      setDeviceStatuses(mockDeviceStatuses);
      setUploadHistory(mockUploadHistory);
    } catch (error) {
      message.error('加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'success';
      case 'uploading': return 'processing';
      case 'failed': return 'error';
      case 'pending': return 'default';
      default: return 'default';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircleOutlined />;
      case 'uploading': return <SyncOutlined spin />;
      case 'failed': return <ExclamationCircleOutlined />;
      case 'pending': return <ClockCircleOutlined />;
      default: return <ClockCircleOutlined />;
    }
  };

  const uploadColumns = [
    {
      title: '设备ID',
      dataIndex: 'device_id',
      key: 'device_id',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)} icon={getStatusIcon(status)}>
          {status === 'completed' ? '已完成' :
           status === 'uploading' ? '上传中' :
           status === 'failed' ? '失败' : '等待中'}
        </Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'progress',
      key: 'progress',
      render: (progress: number, record: UploadStatus) => (
        <div style={{ width: 120 }}>
          <Progress 
            percent={progress} 
            size="small" 
            status={record.status === 'failed' ? 'exception' : 'normal'}
          />
          <div style={{ fontSize: '12px', color: '#666', marginTop: 2 }}>
            {record.uploaded_count}/{record.test_count} 条
          </div>
        </div>
      ),
    },
    {
      title: '开始时间',
      dataIndex: 'start_time',
      key: 'start_time',
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record: UploadStatus) => (
        <Space>
          <Tooltip title="查看详情">
            <Button type="text" icon={<EyeOutlined />} size="small" />
          </Tooltip>
          {record.status === 'failed' && (
            <Tooltip title="重试上传">
              <Button type="text" icon={<ReloadOutlined />} size="small" />
            </Tooltip>
          )}
          <Tooltip title="删除记录">
            <Button type="text" danger icon={<DeleteOutlined />} size="small" />
          </Tooltip>
        </Space>
      ),
    },
  ];

  const deviceColumns = [
    {
      title: '设备',
      key: 'device',
      render: (_, record: DeviceStatus) => (
        <Space>
          {record.online ? 
            <WifiOutlined style={{ color: '#52c41a' }} /> : 
            <DisconnectOutlined style={{ color: '#ff4d4f' }} />
          }
          <div>
            <div style={{ fontWeight: 'bold' }}>{record.device_name}</div>
            <div style={{ fontSize: '12px', color: '#666' }}>{record.device_id}</div>
          </div>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'online',
      key: 'online',
      render: (online: boolean) => (
        <Badge 
          status={online ? 'success' : 'error'} 
          text={online ? '在线' : '离线'} 
        />
      ),
    },
    {
      title: '待上传',
      dataIndex: 'pending_uploads',
      key: 'pending_uploads',
      render: (count: number) => (
        <Tag color={count > 0 ? 'orange' : 'green'}>
          {count} 条
        </Tag>
      ),
    },
    {
      title: '上传率',
      dataIndex: 'upload_rate',
      key: 'upload_rate',
      render: (rate: number) => (
        <Progress 
          percent={rate} 
          size="small" 
          format={percent => `${percent}%`}
        />
      ),
    },
    {
      title: '最后活动',
      dataIndex: 'last_seen',
      key: 'last_seen',
    },
  ];

  // 统计数据
  const totalDevices = deviceStatuses.length;
  const onlineDevices = deviceStatuses.filter(d => d.online).length;
  const totalPending = deviceStatuses.reduce((sum, d) => sum + d.pending_uploads, 0);
  const avgUploadRate = deviceStatuses.reduce((sum, d) => sum + d.upload_rate, 0) / totalDevices;

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
          <CloudUploadOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
          数据上传监控
        </h2>
        <p style={{ margin: '8px 0 0 0', color: '#666' }}>
          实时监控桌面设备的数据上传状态和同步进度
        </p>
      </div>

      {/* 控制栏 */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Button 
            type="primary" 
            icon={<ReloadOutlined />} 
            onClick={loadData}
            loading={loading}
          >
            刷新数据
          </Button>
          <Switch 
            checked={autoRefresh}
            onChange={setAutoRefresh}
            checkedChildren="自动刷新"
            unCheckedChildren="手动刷新"
          />
          {autoRefresh && (
            <Select
              value={refreshInterval}
              onChange={setRefreshInterval}
              style={{ width: 120 }}
            >
              <Option value={10}>10秒</Option>
              <Option value={30}>30秒</Option>
              <Option value={60}>1分钟</Option>
              <Option value={300}>5分钟</Option>
            </Select>
          )}
        </Space>
        <Button 
          icon={<SettingOutlined />} 
          onClick={() => setConfigModalVisible(true)}
        >
          监控配置
        </Button>
      </div>

      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: '24px' }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="在线设备"
              value={onlineDevices}
              suffix={`/ ${totalDevices}`}
              valueStyle={{ color: onlineDevices === totalDevices ? '#3f8600' : '#cf1322' }}
              prefix={<WifiOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="待上传数据"
              value={totalPending}
              suffix="条"
              valueStyle={{ color: totalPending > 0 ? '#fa8c16' : '#3f8600' }}
              prefix={<CloudUploadOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="平均上传率"
              value={avgUploadRate}
              precision={1}
              suffix="%"
              valueStyle={{ color: avgUploadRate > 95 ? '#3f8600' : '#fa8c16' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="活跃上传"
              value={uploadStatuses.filter(u => u.status === 'uploading').length}
              suffix="个"
              valueStyle={{ color: '#1890ff' }}
              prefix={<SyncOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 主要内容 */}
      <Tabs defaultActiveKey="uploads">
        <TabPane tab="上传状态" key="uploads">
          <Card title="当前上传任务" extra={
            <Badge count={uploadStatuses.filter(u => u.status === 'uploading').length} />
          }>
            <Table
              columns={uploadColumns}
              dataSource={uploadStatuses}
              rowKey="id"
              loading={loading}
              pagination={false}
              size="middle"
            />
          </Card>
        </TabPane>

        <TabPane tab="设备状态" key="devices">
          <Card title="设备连接状态">
            <Table
              columns={deviceColumns}
              dataSource={deviceStatuses}
              rowKey="device_id"
              loading={loading}
              pagination={false}
              size="middle"
            />
          </Card>
        </TabPane>

        <TabPane tab="上传历史" key="history">
          <Card title="上传活动日志">
            <Timeline>
              {uploadHistory.map((item, index) => (
                <Timeline.Item
                  key={index}
                  color={item.status === 'success' ? 'green' : 
                         item.status === 'error' ? 'red' : 'blue'}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <strong>{item.device}</strong> - {item.action}
                    </div>
                    <span style={{ color: '#666', fontSize: '12px' }}>
                      {item.time}
                    </span>
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
          </Card>
        </TabPane>
      </Tabs>

      {/* 配置弹窗 */}
      <Modal
        title="监控配置"
        open={configModalVisible}
        onCancel={() => setConfigModalVisible(false)}
        footer={[
          <Button key="cancel" onClick={() => setConfigModalVisible(false)}>
            取消
          </Button>,
          <Button key="save" type="primary">
            保存配置
          </Button>
        ]}
      >
        <Form layout="vertical">
          <Form.Item label="自动刷新间隔">
            <Select defaultValue={30} style={{ width: '100%' }}>
              <Option value={10}>10秒</Option>
              <Option value={30}>30秒</Option>
              <Option value={60}>1分钟</Option>
              <Option value={300}>5分钟</Option>
            </Select>
          </Form.Item>
          <Form.Item label="监控设备">
            <Select mode="multiple" placeholder="选择要监控的设备" style={{ width: '100%' }}>
              <Option value="JCY5001A_001">测试设备-001</Option>
              <Option value="JCY5001A_002">测试设备-002</Option>
              <Option value="JCY5001A_003">测试设备-003</Option>
            </Select>
          </Form.Item>
          <Form.Item label="告警设置">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>设备离线告警</span>
                <Switch defaultChecked />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>上传失败告警</span>
                <Switch defaultChecked />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>数据积压告警</span>
                <Switch defaultChecked />
              </div>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default UploadMonitorPage;
