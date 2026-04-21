import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Select,
  Input,
  DatePicker,
  Row,
  Col,
  Typography,
  Checkbox,
  Drawer,
  Tabs,
  Statistic,
  message,
  Tag,
  Divider,
  Form,
  Spin
} from 'antd';
import {
  SearchOutlined,
  FilterOutlined,
  ExportOutlined,
  EyeOutlined,
  BarChartOutlined,
  ReloadOutlined,
  LineChartOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import { getCurrentUser, hasPermission } from '../utils/auth';
import { analysisAPI } from '../services/api';
import DataExportModal from '../components/DataExportModal';
import NyquistChart from '../components/NyquistChart';
import dayjs from 'dayjs';

const { Option } = Select;
const { RangePicker } = DatePicker;
const { Text, Title } = Typography;
const { TabPane } = Tabs;

interface TestResult {
  id: number;
  testId: string;
  deviceId: string;
  batchId: string;
  channel: number;
  testTime: string;
  voltage: number;
  rs: number;
  rct: number;
  // Jack要求移除rsei字段
  // rsei?: number;
  temperature: number;
  result: string;
  grade?: string;
  errorCode: string;
  cellType: string;
  createdAt: string;
}

interface ImpedanceDetail {
  id: number;
  frequency: number;
  z_real: number;
  z_imag: number;
  z_magnitude: number;
  phase_angle: number;
  measurement_time: string;
}

interface FilterOptions {
  devices: string[];
  batches: string[];
  cellTypes: string[];
  channels: number[];
}

interface FilterConditions {
  deviceId?: string;
  batchId?: string;
  cellType?: string;
  channels?: number[];
  dateRange?: [string, string];
  result?: string;
  searchText?: string;
}

const DataAnalysisPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [filteredResults, setFilteredResults] = useState<TestResult[]>([]);
  const [devices, setDevices] = useState<string[]>([]);
  const [batches, setBatches] = useState<string[]>([]);
  const [cellTypes, setCellTypes] = useState<string[]>([]);
  const [filters, setFilters] = useState<FilterConditions>({});
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [rsGradeCount, setRsGradeCount] = useState<number>(3);  // 档位数量选择
  const [recalculatingGrades, setRecalculatingGrades] = useState(false);  // 重新计算档位的加载状态
  const [selectedRecord, setSelectedRecord] = useState<TestResult | null>(null);
  const [exportModalVisible, setExportModalVisible] = useState(false);

  // 获取测试数据
  const fetchTestResults = async () => {
    try {
      setLoading(true);
      const response = await analysisAPI.getTestResults();
      console.log('API响应:', response); // 添加调试日志

      if (response.status_code === 200) {
        // 修复：使用正确的字段名 'results' 而不是 'test_results'
        const results = response.results || [];
        const formattedResults = results.map((result: any) => ({
          id: result.id,
          testId: result.test_id,
          deviceId: result.device_id,
          batchId: result.batch_id,
          channel: result.channel,
          testTime: new Date(result.test_time).toLocaleString('zh-CN'),
          voltage: result.voltage,
          rs: result.rs,
          rct: result.rct,
          temperature: result.temperature,
          result: result.result,
          errorCode: result.error_code,
          cellType: result.cell_type,
          createdAt: result.test_time ? new Date(result.test_time).toLocaleString('zh-CN') : ''
        }));
        setTestResults(formattedResults);
        setFilteredResults(formattedResults);
      } else {
        console.warn('API返回非200状态码:', response.status_code);
        message.warning('获取数据时出现问题');
      }
    } catch (error) {
      console.error('获取测试数据失败:', error);
      message.error('获取测试数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 获取筛选选项
  const fetchFilterOptions = async () => {
    try {
      const response = await analysisAPI.getFilterOptions();
      if (response.status_code === 200) {
        setDevices(response.devices || []);
        setBatches(response.batches || []);
        setCellTypes(response.cell_types || []);
      }
    } catch (error) {
      console.error('获取筛选选项失败:', error);
    }
  };

  useEffect(() => {
    fetchTestResults();
    fetchFilterOptions();
  }, []);

  // 应用筛选
  const applyFilters = () => {
    let filtered = [...testResults];

    if (filters.deviceId) {
      filtered = filtered.filter(item => item.deviceId === filters.deviceId);
    }

    if (filters.batchId) {
      filtered = filtered.filter(item => item.batchId === filters.batchId);
    }

    if (filters.cellType) {
      filtered = filtered.filter(item => item.cellType === filters.cellType);
    }

    if (filters.channels && filters.channels.length > 0) {
      filtered = filtered.filter(item => filters.channels!.includes(item.channel));
    }

    if (filters.result && filters.result !== 'all') {
      filtered = filtered.filter(item => item.result === filters.result);
    }

    if (filters.searchText) {
      const searchText = filters.searchText.toLowerCase();
      filtered = filtered.filter(item =>
        item.deviceId.toLowerCase().includes(searchText) ||
        item.batchId.toLowerCase().includes(searchText) ||
        item.testId.toLowerCase().includes(searchText)
      );
    }

    setFilteredResults(filtered);
    message.success(`筛选完成，共找到 ${filtered.length} 条记录`);
  };

  // 重置筛选
  const resetFilters = () => {
    setFilters({});
    setFilteredResults(testResults);
    message.info('筛选条件已重置');
  };

  // 查看详情
  const viewDetails = (record: TestResult) => {
    setSelectedRecord(record);
    setDetailDrawerVisible(true);
  };

  // 导出数据
  const exportData = () => {
    if (!hasPermission('data:export')) {
      message.error('您没有数据导出权限');
      return;
    }
    
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的数据');
      return;
    }
    
    setExportModalVisible(true);
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
      title: '测试ID',
      dataIndex: 'testId',
      key: 'testId',
      width: 120,
    },
    {
      title: '设备ID',
      dataIndex: 'deviceId',
      key: 'deviceId',
      width: 100,
    },
    {
      title: '批次ID',
      dataIndex: 'batchId',
      key: 'batchId',
      width: 100,
    },
    {
      title: '通道',
      dataIndex: 'channel',
      key: 'channel',
      width: 80,
    },
    {
      title: '测试时间',
      dataIndex: 'testTime',
      key: 'testTime',
      width: 150,
    },
    {
      title: '电压(V)',
      dataIndex: 'voltage',
      key: 'voltage',
      width: 100,
      render: (value: number) => value?.toFixed(3),
    },
    {
      title: 'Rs(mΩ)',
      dataIndex: 'rs',
      key: 'rs',
      width: 100,
      render: (value: number) => value?.toFixed(3),
    },
    {
      title: 'Rct(mΩ)',
      dataIndex: 'rct',
      key: 'rct',
      width: 100,
      render: (value: number) => value?.toFixed(3),
    },
    {
      title: '温度(°C)',
      dataIndex: 'temperature',
      key: 'temperature',
      width: 100,
      render: (value: number) => value?.toFixed(1),
    },
    {
      title: '测试结果',
      dataIndex: 'result',
      key: 'result',
      width: 100,
      render: (value: string) => (
        <Tag color={value === 'pass' ? 'green' : 'red'}>
          {value === 'pass' ? '合格' : '不合格'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: TestResult) => (
        <Space size="small">
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => viewDetails(record)}
          >
            详情
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 页面标题 */}
      <div className="page-header">
        <div>
          <Title level={2}>
            <Space>
              <BarChartOutlined />
              数据分析
            </Space>
          </Title>
          <Text type="secondary">电池阻抗测试数据分析与可视化</Text>
        </div>
      </div>

      {/* 操作按钮 */}
      <Row style={{ marginBottom: '16px' }}>
        <Col span={24} style={{ textAlign: 'right' }}>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchTestResults}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              type="primary"
              icon={<ExportOutlined />}
              onClick={exportData}
              disabled={selectedRowKeys.length === 0}
            >
              导出数据 ({selectedRowKeys.length})
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 筛选条件 */}
      <Card title="数据筛选" style={{ marginBottom: '16px' }}>
        <Row gutter={[16, 16]}>
          <Col xs={24} sm={12} md={6}>
            <Text strong>设备选择:</Text>
            <Select
              placeholder="选择设备"
              style={{ width: '100%', marginTop: '4px' }}
              value={filters.deviceId}
              onChange={(value) => setFilters({ ...filters, deviceId: value })}
              allowClear
            >
              {devices.map(device => (
                <Option key={device} value={device}>{device}</Option>
              ))}
            </Select>
          </Col>
          
          <Col xs={24} sm={12} md={6}>
            <Text strong>批次选择:</Text>
            <Select
              placeholder="选择批次"
              style={{ width: '100%', marginTop: '4px' }}
              value={filters.batchId}
              onChange={(value) => setFilters({ ...filters, batchId: value })}
              allowClear
            >
              {batches.map(batch => (
                <Option key={batch} value={batch}>{batch}</Option>
              ))}
            </Select>
          </Col>
          
          <Col xs={24} sm={12} md={6}>
            <Text strong>电芯类型:</Text>
            <Select
              placeholder="选择电芯类型"
              style={{ width: '100%', marginTop: '4px' }}
              value={filters.cellType}
              onChange={(value) => setFilters({ ...filters, cellType: value })}
              allowClear
            >
              {cellTypes.map(type => (
                <Option key={type} value={type}>{type}</Option>
              ))}
            </Select>
          </Col>
          
          <Col xs={24} sm={12} md={6}>
            <Text strong>测试结果:</Text>
            <Select
              placeholder="选择测试结果"
              style={{ width: '100%', marginTop: '4px' }}
              value={filters.result}
              onChange={(value) => setFilters({ ...filters, result: value })}
              allowClear
            >
              <Option value="all">全部</Option>
              <Option value="pass">合格</Option>
              <Option value="fail">不合格</Option>
            </Select>
          </Col>
        </Row>
        
        <Row style={{ marginTop: '16px' }}>
          <Col span={24} style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={resetFilters}>
                重置
              </Button>
              <Button type="primary" icon={<FilterOutlined />} onClick={applyFilters}>
                应用筛选
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 数据表格 */}
      <Card title={`测试数据 (${filteredResults.length} 条)`}>
        <div className="responsive-table">
          <Table
            columns={columns}
            dataSource={filteredResults}
            rowKey="id"
            loading={loading}
            rowSelection={{
              selectedRowKeys,
              onChange: setSelectedRowKeys,
            }}
            pagination={{
              pageSize: 20,
              showSizeChanger: true,
              showQuickJumper: true,
              showTotal: (total, range) => `第 ${range[0]}-${range[1]} 条，共 ${total} 条`,
            }}
            scroll={{ x: 1400, y: 600 }}
            size="small"
          />
        </div>
      </Card>

      {/* 详情抽屉 */}
      <Drawer
        title="测试详情"
        placement="right"
        width={600}
        open={detailDrawerVisible}
        onClose={() => setDetailDrawerVisible(false)}
      >
        {selectedRecord && (
          <div>
            <p><strong>测试ID:</strong> {selectedRecord.testId}</p>
            <p><strong>设备ID:</strong> {selectedRecord.deviceId}</p>
            <p><strong>批次ID:</strong> {selectedRecord.batchId}</p>
            <p><strong>通道:</strong> {selectedRecord.channel}</p>
            <p><strong>测试时间:</strong> {selectedRecord.testTime}</p>
            <p><strong>电压:</strong> {selectedRecord.voltage?.toFixed(3)} V</p>
            <p><strong>Rs:</strong> {selectedRecord.rs?.toFixed(3)} mΩ</p>
            <p><strong>Rct:</strong> {selectedRecord.rct?.toFixed(3)} mΩ</p>
            <p><strong>温度:</strong> {selectedRecord.temperature?.toFixed(1)} °C</p>
            <p><strong>测试结果:</strong> 
              <Tag color={selectedRecord.result === 'pass' ? 'green' : 'red'}>
                {selectedRecord.result === 'pass' ? '合格' : '不合格'}
              </Tag>
            </p>
            <p><strong>错误代码:</strong> {selectedRecord.errorCode}</p>
            <p><strong>电芯类型:</strong> {selectedRecord.cellType}</p>
            <p><strong>创建时间:</strong> {selectedRecord.createdAt}</p>
          </div>
        )}
      </Drawer>

      {/* 数据导出模态框 */}
      <DataExportModal
        visible={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        selectedRowKeys={selectedRowKeys}
        exportType="test_results"
        title="导出测试结果"
      />
    </div>
  );
};

export default DataAnalysisPage;
