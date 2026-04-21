import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Select,
  Button,
  Table,
  Typography,
  Space,
  Checkbox,
  DatePicker,
  Input,
  Statistic,
  Tag,
  Drawer,
  Tabs,
  message,
  Spin
} from 'antd';
import {
  BarChartOutlined,
  SearchOutlined,
  ReloadOutlined,
  FilterOutlined,
  EyeOutlined,
  DownloadOutlined,
  LineChartOutlined
} from '@ant-design/icons';
import { getCurrentUser, hasPermission } from '../utils/auth';
import { analysisAPI } from '../services/api';
import DataExportModal from '../components/DataExportModal';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

interface TestResult {
  id: number;
  deviceId: string;
  batchId: string;
  cellType: string;
  channel: number;
  testTime: string;
  voltage: number;
  rs: number;
  rct: number;
  rsei: number;
  wImpedance: number;
  grade: string;
  result: 'pass' | 'fail';
  temperature: number;
  humidity: number;
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
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [testResults, setTestResults] = useState<TestResult[]>([]);
  const [filteredResults, setFilteredResults] = useState<TestResult[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [detailDrawerVisible, setDetailDrawerVisible] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<TestResult | null>(null);
  const [exportModalVisible, setExportModalVisible] = useState(false);
  
  // 筛选条件
  const [filters, setFilters] = useState<FilterConditions>({});
  const [devices, setDevices] = useState<string[]>([]);
  const [batches, setBatches] = useState<string[]>([]);
  const [cellTypes, setCellTypes] = useState<string[]>([]);
  
  // 统计数据
  const [statistics, setStatistics] = useState({
    totalTests: 0,
    passRate: 0,
    avgRs: 0,
    avgRct: 0,
    avgRsei: 0
  });

  const currentUser = getCurrentUser();

  // 获取测试数据
  const fetchTestResults = async () => {
    setLoading(true);
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // 模拟测试数据
      const mockData: TestResult[] = Array.from({ length: 50 }, (_, index) => ({
        id: index + 1,
        deviceId: `JCY5001A_${String(Math.floor(index / 10) + 1).padStart(3, '0')}`,
        batchId: `BATCH_${Math.floor(index / 8) + 1}`,
        cellType: ['21700', '18650', '26650'][index % 3],
        channel: (index % 8) + 1,
        testTime: dayjs().subtract(Math.floor(Math.random() * 30), 'day').format('YYYY-MM-DD HH:mm:ss'),
        voltage: 3.2 + Math.random() * 0.8,
        rs: 2.0 + Math.random() * 2.0,
        rct: 10.0 + Math.random() * 10.0,
        rsei: 1.0 + Math.random() * 2.0,
        wImpedance: 0.5 + Math.random() * 1.0,
        grade: ['A', 'B', 'C'][Math.floor(Math.random() * 3)],
        result: Math.random() > 0.1 ? 'pass' : 'fail',
        temperature: 20 + Math.random() * 10,
        humidity: 40 + Math.random() * 20
      }));
      
      setTestResults(mockData);
      setFilteredResults(mockData);
      
      // 提取筛选选项
      const uniqueDevices = [...new Set(mockData.map(item => item.deviceId))];
      const uniqueBatches = [...new Set(mockData.map(item => item.batchId))];
      const uniqueCellTypes = [...new Set(mockData.map(item => item.cellType))];
      
      setDevices(uniqueDevices);
      setBatches(uniqueBatches);
      setCellTypes(uniqueCellTypes);
      
      // 计算统计数据
      calculateStatistics(mockData);
      
    } catch (error) {
      console.error('获取测试数据失败:', error);
      message.error('获取测试数据失败');
    } finally {
      setLoading(false);
    }
  };

  // 计算统计数据
  const calculateStatistics = (data: TestResult[]) => {
    const totalTests = data.length;
    const passCount = data.filter(item => item.result === 'pass').length;
    const passRate = totalTests > 0 ? (passCount / totalTests) * 100 : 0;
    
    const avgRs = data.reduce((sum, item) => sum + item.rs, 0) / totalTests;
    const avgRct = data.reduce((sum, item) => sum + item.rct, 0) / totalTests;
    const avgRsei = data.reduce((sum, item) => sum + item.rsei, 0) / totalTests;
    
    setStatistics({
      totalTests,
      passRate,
      avgRs,
      avgRct,
      avgRsei
    });
  };

  // 应用筛选条件
  const applyFilters = () => {
    let filtered = testResults;
    
    // 设备筛选
    if (filters.deviceId) {
      filtered = filtered.filter(item => item.deviceId === filters.deviceId);
    }
    
    // 批次筛选
    if (filters.batchId) {
      filtered = filtered.filter(item => item.batchId === filters.batchId);
    }
    
    // 电芯类型筛选
    if (filters.cellType) {
      filtered = filtered.filter(item => item.cellType === filters.cellType);
    }
    
    // 通道筛选
    if (filters.channels && filters.channels.length > 0) {
      filtered = filtered.filter(item => filters.channels!.includes(item.channel));
    }
    
    // 日期范围筛选
    if (filters.dateRange) {
      const [startDate, endDate] = filters.dateRange;
      filtered = filtered.filter(item => {
        const testDate = dayjs(item.testTime);
        return testDate.isAfter(dayjs(startDate)) && testDate.isBefore(dayjs(endDate));
      });
    }
    
    // 结果筛选
    if (filters.result && filters.result !== 'all') {
      filtered = filtered.filter(item => item.result === filters.result);
    }
    
    // 文本搜索
    if (filters.searchText) {
      const searchLower = filters.searchText.toLowerCase();
      filtered = filtered.filter(item =>
        item.deviceId.toLowerCase().includes(searchLower) ||
        item.batchId.toLowerCase().includes(searchLower) ||
        item.cellType.toLowerCase().includes(searchLower)
      );
    }
    
    setFilteredResults(filtered);
    calculateStatistics(filtered);
    message.success(`筛选完成，共找到 ${filtered.length} 条记录`);
  };

  // 重置筛选条件
  const resetFilters = () => {
    setFilters({});
    setFilteredResults(testResults);
    calculateStatistics(testResults);
    message.info('筛选条件已重置');
  };

  // 查看详情
  const viewDetail = (record: TestResult) => {
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

  useEffect(() => {
    fetchTestResults();
  }, []);

  // 表格列定义
  const columns = [
    {
      title: '设备ID',
      dataIndex: 'deviceId',
      key: 'deviceId',
      width: 120,
      fixed: 'left' as const,
    },
    {
      title: '批次ID',
      dataIndex: 'batchId',
      key: 'batchId',
      width: 100,
    },
    {
      title: '电芯类型',
      dataIndex: 'cellType',
      key: 'cellType',
      width: 80,
    },
    {
      title: '通道',
      dataIndex: 'channel',
      key: 'channel',
      width: 60,
      align: 'center' as const,
    },
    {
      title: '测试时间',
      dataIndex: 'testTime',
      key: 'testTime',
      width: 150,
    },
    {
      title: '电压 (V)',
      dataIndex: 'voltage',
      key: 'voltage',
      width: 90,
      render: (value: number) => value.toFixed(3),
    },
    {
      title: 'Rs (mΩ)',
      dataIndex: 'rs',
      key: 'rs',
      width: 90,
      render: (value: number) => value.toFixed(2),
    },
    {
      title: 'Rct (mΩ)',
      dataIndex: 'rct',
      key: 'rct',
      width: 90,
      render: (value: number) => value.toFixed(2),
    },
    // Jack要求移除Rsei列显示
    // {
    //   title: 'Rsei (mΩ)',
    //   dataIndex: 'rsei',
    //   key: 'rsei',
    //   width: 90,
    //   render: (value: number) => value.toFixed(2),
    // },
    {
      title: '等级',
      dataIndex: 'grade',
      key: 'grade',
      width: 60,
      align: 'center' as const,
    },
    {
      title: '结果',
      dataIndex: 'result',
      key: 'result',
      width: 80,
      render: (result: string) => (
        <Tag color={result === 'pass' ? 'success' : 'error'}>
          {result === 'pass' ? '合格' : '不合格'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_, record: TestResult) => (
        <Space size="small">
          <Button
            type="text"
            icon={<EyeOutlined />}
            onClick={() => viewDetail(record)}
            size="small"
          >
            详情
          </Button>
          <Button
            type="text"
            icon={<LineChartOutlined />}
            size="small"
            onClick={() => navigate('/charts')}
          >
            图表
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
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

      {/* 统计概览 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="总测试次数"
              value={statistics.totalTests}
              suffix="次"
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="合格率"
              value={statistics.passRate}
              precision={1}
              suffix="%"
              valueStyle={{ color: statistics.passRate >= 90 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="平均Rs值"
              value={statistics.avgRs}
              precision={2}
              suffix="mΩ"
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="平均Rct值"
              value={statistics.avgRct}
              precision={2}
              suffix="mΩ"
            />
          </Card>
        </Col>
      </Row>

      {/* 筛选条件 */}
      <Card title="数据筛选" style={{ marginBottom: '16px' }}>
        <div className="filter-container">
          <Row gutter={[16, 16]} style={{ width: '100%' }}>
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
        
        <Row gutter={[16, 16]} style={{ marginTop: '16px' }}>
          <Col xs={24} sm={12} md={8}>
            <Text strong>通道选择:</Text>
            <div style={{ marginTop: '4px' }}>
              <Checkbox.Group
                options={Array.from({ length: 8 }, (_, i) => ({ label: `CH${i + 1}`, value: i + 1 }))}
                value={filters.channels}
                onChange={(values) => setFilters({ ...filters, channels: values as number[] })}
              />
            </div>
          </Col>
          
          <Col xs={24} sm={12} md={8}>
            <Text strong>日期范围:</Text>
            <RangePicker
              style={{ width: '100%', marginTop: '4px' }}
              value={filters.dateRange ? [dayjs(filters.dateRange[0]), dayjs(filters.dateRange[1])] : null}
              onChange={(dates) => {
                if (dates) {
                  setFilters({ 
                    ...filters, 
                    dateRange: [dates[0]!.format('YYYY-MM-DD'), dates[1]!.format('YYYY-MM-DD')] 
                  });
                } else {
                  setFilters({ ...filters, dateRange: undefined });
                }
              }}
            />
          </Col>
          
          <Col xs={24} sm={12} md={8}>
            <Text strong>搜索:</Text>
            <Input
              placeholder="搜索设备ID、批次ID等"
              prefix={<SearchOutlined />}
              style={{ marginTop: '4px' }}
              value={filters.searchText}
              onChange={(e) => setFilters({ ...filters, searchText: e.target.value })}
              allowClear
            />
          </Col>
        </Row>

        <Row>
          <Col span={24}>
            <div className="action-buttons" style={{ justifyContent: 'flex-end', marginTop: '16px' }}>
              <Button onClick={resetFilters}>
                重置
              </Button>
              <Button type="primary" icon={<FilterOutlined />} onClick={applyFilters}>
                应用筛选
              </Button>
            </div>
          </Col>
        </Row>
        </div>
      </Card>

      {/* 数据表格 */}
      <Card
        title={`测试数据 (${filteredResults.length} 条)`}
        extra={
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchTestResults}
              loading={loading}
            >
              刷新
            </Button>
            {hasPermission('data:export') && (
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                onClick={exportData}
                disabled={selectedRowKeys.length === 0}
              >
                导出选中
              </Button>
            )}
          </Space>
        }
      >
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
          <Tabs defaultActiveKey="basic">
            <TabPane tab="基本信息" key="basic">
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Text strong>设备ID:</Text>
                  <div>{selectedRecord.deviceId}</div>
                </Col>
                <Col span={12}>
                  <Text strong>批次ID:</Text>
                  <div>{selectedRecord.batchId}</div>
                </Col>
                <Col span={12}>
                  <Text strong>电芯类型:</Text>
                  <div>{selectedRecord.cellType}</div>
                </Col>
                <Col span={12}>
                  <Text strong>通道:</Text>
                  <div>{selectedRecord.channel}</div>
                </Col>
                <Col span={12}>
                  <Text strong>测试时间:</Text>
                  <div>{selectedRecord.testTime}</div>
                </Col>
                <Col span={12}>
                  <Text strong>测试结果:</Text>
                  <div>
                    <Tag color={selectedRecord.result === 'pass' ? 'success' : 'error'}>
                      {selectedRecord.result === 'pass' ? '合格' : '不合格'}
                    </Tag>
                  </div>
                </Col>
              </Row>
            </TabPane>
            
            <TabPane tab="阻抗数据" key="impedance">
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Text strong>电压 (V):</Text>
                  <div>{selectedRecord.voltage.toFixed(3)}</div>
                </Col>
                <Col span={12}>
                  <Text strong>Rs (mΩ):</Text>
                  <div>{selectedRecord.rs.toFixed(2)}</div>
                </Col>
                <Col span={12}>
                  <Text strong>Rct (mΩ):</Text>
                  <div>{selectedRecord.rct.toFixed(2)}</div>
                </Col>
                <Col span={12}>
                  <Text strong>Rsei (mΩ):</Text>
                  <div>{selectedRecord.rsei.toFixed(2)}</div>
                </Col>
                <Col span={12}>
                  <Text strong>W阻抗 (mΩ):</Text>
                  <div>{selectedRecord.wImpedance.toFixed(2)}</div>
                </Col>
                <Col span={12}>
                  <Text strong>等级:</Text>
                  <div>{selectedRecord.grade}</div>
                </Col>
              </Row>
            </TabPane>
            
            <TabPane tab="环境条件" key="environment">
              <Row gutter={[16, 16]}>
                <Col span={12}>
                  <Text strong>温度 (°C):</Text>
                  <div>{selectedRecord.temperature.toFixed(1)}</div>
                </Col>
                <Col span={12}>
                  <Text strong>湿度 (%):</Text>
                  <div>{selectedRecord.humidity.toFixed(1)}</div>
                </Col>
              </Row>
            </TabPane>
            
            <TabPane tab="图表分析" key="charts">
              <div style={{ textAlign: 'center', padding: '50px' }}>
                <LineChartOutlined style={{ fontSize: '48px', color: '#ccc' }} />
                <div style={{ marginTop: '16px', color: '#999' }}>
                  奈奎斯特图和阻抗谱图表功能开发中...
                </div>
              </div>
            </TabPane>
          </Tabs>
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
