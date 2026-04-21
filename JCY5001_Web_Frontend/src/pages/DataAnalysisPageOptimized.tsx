import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Select,

  DatePicker,
  Row,
  Col,
  Typography,
  message,
  Tag,
  Divider,
  Form,
  Spin,
  Statistic,
  Tabs,

} from 'antd';
import {
  FilterOutlined,
  ExportOutlined,
  EyeOutlined,
  BarChartOutlined,
  ReloadOutlined,
  LineChartOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import { analysisAPI } from '../services/api';
import NyquistChart from '../components/NyquistChart';
import DataExportModal from '../components/DataExportModal';


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
  rsei?: number;
  temperature: number;
  result: string;
  grade?: string;
  errorCode: string;
  cellType: string;
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

interface FilterConditions {
  deviceId?: string;
  batchId?: string;
  cellType?: string;
  channels?: number[];
  dateRange?: [string, string];
  result?: string;
  searchText?: string;
}

const DataAnalysisPageOptimized: React.FC = () => {
  // 基础状态
  const [loading, setLoading] = useState(false);
  const [filteredResults, setFilteredResults] = useState<TestResult[]>([]);
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  
  // 筛选相关
  const [devices, setDevices] = useState<string[]>([]);
  const [batches, setBatches] = useState<string[]>([]);
  const [cellTypes, setCellTypes] = useState<string[]>([]);
  const [filters, setFilters] = useState<FilterConditions>({});
  
  // 选中的测试记录和明细数据
  const [selectedRecord, setSelectedRecord] = useState<TestResult | null>(null);
  const [impedanceDetails, setImpedanceDetails] = useState<ImpedanceDetail[]>([]);
  const [detailsLoading, setDetailsLoading] = useState(false);
  
  // 模态框
  const [exportModalVisible, setExportModalVisible] = useState(false);

  // 分页状态
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 20,
    total: 0,
    showSizeChanger: true,
    showQuickJumper: true,
    showTotal: (total: number, range: [number, number]) =>
      `显示 ${range[0]}-${range[1]} 条，共 ${total} 条数据`
  });

  // 统计数据
  const [statistics, setStatistics] = useState({
    totalTests: 0,
    passRate: 0,
    avgRs: 0,
    avgRct: 0,
    avgRsei: 0
  });

  // 获取测试数据
  const fetchTestResults = async (page: number = pagination.current, pageSize: number = pagination.pageSize) => {
    try {
      setLoading(true);
      const response = await analysisAPI.getTestResults({
        ...filters,
        page,
        per_page: pageSize
      });

      if (response.status_code === 200) {
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
          rsei: result.rsei,
          temperature: result.temperature,
          result: result.result,
          grade: result.grade,
          errorCode: result.error_code,
          cellType: result.cell_type
        }));
        
        setFilteredResults(formattedResults);
        calculateStatistics(formattedResults);

        // 更新分页信息
        setPagination(prev => ({
          ...prev,
          current: page,
          pageSize: pageSize,
          total: response.total || formattedResults.length
        }));
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

  // 获取阻抗明细数据
  const fetchImpedanceDetails = async (testResultId: number) => {
    try {
      setDetailsLoading(true);
      const response = await analysisAPI.getImpedanceDetails(testResultId);
      if (response.status_code === 200) {
        setImpedanceDetails(response.details || []);
      }
    } catch (error) {
      console.error('获取阻抗明细失败:', error);
      message.error('获取阻抗明细失败');
    } finally {
      setDetailsLoading(false);
    }
  };

  // 计算统计数据
  const calculateStatistics = (data: TestResult[]) => {
    const totalTests = data.length;
    const passCount = data.filter(item => item.result === 'pass').length;
    const passRate = totalTests > 0 ? (passCount / totalTests) * 100 : 0;
    
    const avgRs = totalTests > 0 ? data.reduce((sum, item) => sum + (item.rs || 0), 0) / totalTests : 0;
    const avgRct = totalTests > 0 ? data.reduce((sum, item) => sum + (item.rct || 0), 0) / totalTests : 0;
    const avgRsei = totalTests > 0 ? data.reduce((sum, item) => sum + (item.rsei || 0), 0) / totalTests : 0;
    
    setStatistics({
      totalTests,
      passRate,
      avgRs,
      avgRct,
      avgRsei
    });
  };

  // 应用筛选
  const applyFilters = () => {
    setPagination(prev => ({ ...prev, current: 1 })); // 重置到第一页
    fetchTestResults(1, pagination.pageSize);
  };

  // 重置筛选
  const resetFilters = () => {
    setFilters({});
    setPagination(prev => ({ ...prev, current: 1 })); // 重置到第一页
    fetchTestResults(1, pagination.pageSize);
  };

  // 处理分页变化
  const handleTableChange = (page: number, pageSize?: number) => {
    const newPageSize = pageSize || pagination.pageSize;
    setPagination(prev => ({
      ...prev,
      current: page,
      pageSize: newPageSize
    }));
    fetchTestResults(page, newPageSize);
  };

  // 选择测试记录
  const handleRecordSelect = (record: TestResult) => {
    setSelectedRecord(record);
    fetchImpedanceDetails(record.id);
  };

  // 导出数据
  const exportData = () => {
    if (selectedRowKeys.length === 0) {
      message.warning('请先选择要导出的数据');
      return;
    }
    setExportModalVisible(true);
  };

  useEffect(() => {
    fetchTestResults(1, pagination.pageSize);
    fetchFilterOptions();
  }, []);

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
      fixed: 'left' as const
    },
    {
      title: '测试ID',
      dataIndex: 'testId',
      key: 'testId',
      width: 120
    },
    {
      title: '设备ID',
      dataIndex: 'deviceId',
      key: 'deviceId',
      width: 120,
      filters: devices.map(device => ({ text: device, value: device })),
      onFilter: (value: any, record: TestResult) => record.deviceId === value
    },
    {
      title: '批次ID',
      dataIndex: 'batchId',
      key: 'batchId',
      width: 120
    },
    {
      title: '通道',
      dataIndex: 'channel',
      key: 'channel',
      width: 80
    },
    {
      title: '测试时间',
      dataIndex: 'testTime',
      key: 'testTime',
      width: 160
    },
    {
      title: '电压(V)',
      dataIndex: 'voltage',
      key: 'voltage',
      width: 100,
      render: (value: number) => value?.toFixed(3)
    },
    {
      title: 'Rs(mΩ)',
      dataIndex: 'rs',
      key: 'rs',
      width: 100,
      render: (value: number) => value?.toFixed(3)
    },
    {
      title: 'Rct(mΩ)',
      dataIndex: 'rct',
      key: 'rct',
      width: 100,
      render: (value: number) => value?.toFixed(3)
    },
    // Jack要求移除Rsei列显示
    // {
    //   title: 'Rsei(mΩ)',
    //   dataIndex: 'rsei',
    //   key: 'rsei',
    //   width: 100,
    //   render: (value: number) => value?.toFixed(3) || '-'
    // },
    {
      title: '温度(°C)',
      dataIndex: 'temperature',
      key: 'temperature',
      width: 100,
      render: (value: number) => value?.toFixed(1)
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
      )
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      fixed: 'right' as const,
      render: (_: any, record: TestResult) => (
        <Space>
          <Button
            type="link"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => handleRecordSelect(record)}
          >
            查看
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px', minHeight: '100vh', background: '#f5f5f5' }}>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>
          <Space>
            <BarChartOutlined />
            数据分析
          </Space>
        </Title>
        <Text type="secondary">电池阻抗测试数据分析与可视化 - 垂直布局优化</Text>
      </div>

      {/* 垂直线性布局 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

        {/* 第一部分：查询条件 */}
        <Card
          title={
            <Space>
              <FilterOutlined />
              查询条件
            </Space>
          }
          size="default"
          style={{ width: '100%' }}
        >
          <Row gutter={[16, 16]}>
            <Col xs={24} sm={12} md={6}>
              <Form.Item label="设备ID" style={{ marginBottom: '16px' }}>
                <Select
                  placeholder="选择设备"
                  allowClear
                  value={filters.deviceId}
                  onChange={(value) => setFilters({...filters, deviceId: value})}
                >
                  {devices.map(device => (
                    <Option key={device} value={device}>{device}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Form.Item label="批次ID" style={{ marginBottom: '16px' }}>
                <Select
                  placeholder="选择批次"
                  allowClear
                  value={filters.batchId}
                  onChange={(value) => setFilters({...filters, batchId: value})}
                >
                  {batches.map(batch => (
                    <Option key={batch} value={batch}>{batch}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Form.Item label="电芯类型" style={{ marginBottom: '16px' }}>
                <Select
                  placeholder="选择电芯类型"
                  allowClear
                  value={filters.cellType}
                  onChange={(value) => setFilters({...filters, cellType: value})}
                >
                  {cellTypes.map(type => (
                    <Option key={type} value={type}>{type}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Form.Item label="测试结果" style={{ marginBottom: '16px' }}>
                <Select
                  placeholder="选择测试结果"
                  allowClear
                  value={filters.result}
                  onChange={(value) => setFilters({...filters, result: value})}
                >
                  <Option value="pass">合格</Option>
                  <Option value="fail">不合格</Option>
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Form.Item label="通道" style={{ marginBottom: '16px' }}>
                <Select
                  mode="multiple"
                  placeholder="选择通道"
                  allowClear
                  value={filters.channels}
                  onChange={(value) => setFilters({...filters, channels: value})}
                >
                  {[1,2,3,4,5,6,7,8].map(ch => (
                    <Option key={ch} value={ch}>通道{ch}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Form.Item label="测试时间" style={{ marginBottom: '16px' }}>
                <RangePicker
                  style={{ width: '100%' }}
                  onChange={(dates) => {
                    if (dates) {
                      setFilters({
                        ...filters,
                        dateRange: [dates[0]!.format('YYYY-MM-DD'), dates[1]!.format('YYYY-MM-DD')]
                      });
                    } else {
                      setFilters({...filters, dateRange: undefined});
                    }
                  }}
                />
              </Form.Item>
            </Col>

            <Col xs={24} sm={12} md={6}>
              <Form.Item label=" " style={{ marginBottom: '16px' }}>
                <Space>
                  <Button onClick={resetFilters}>重置</Button>
                  <Button type="primary" icon={<FilterOutlined />} onClick={applyFilters}>
                    查询
                  </Button>
                </Space>
              </Form.Item>
            </Col>
          </Row>
        </Card>

        {/* 第二部分：查询结果表格 */}
        <Card
          title={
            <Space>
              <DatabaseOutlined />
              查询结果 ({pagination.total} 条)
            </Space>
          }
          extra={
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => fetchTestResults(pagination.current, pagination.pageSize)}
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
                导出 ({selectedRowKeys.length})
              </Button>
            </Space>
          }
          style={{ width: '100%' }}
        >
            {/* 统计概览 */}
            <Row gutter={[8, 8]} style={{ marginBottom: '8px' }}>
              <Col span={6}>
                <Statistic
                  title="总测试"
                  value={statistics.totalTests}
                  suffix="次"
                  valueStyle={{ fontSize: '16px' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="合格率"
                  value={statistics.passRate}
                  precision={1}
                  suffix="%"
                  valueStyle={{
                    fontSize: '16px',
                    color: statistics.passRate >= 90 ? '#3f8600' : '#cf1322'
                  }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="平均Rs"
                  value={statistics.avgRs}
                  precision={2}
                  suffix="mΩ"
                  valueStyle={{ fontSize: '16px' }}
                />
              </Col>
              <Col span={6}>
                <Statistic
                  title="平均Rct"
                  value={statistics.avgRct}
                  precision={2}
                  suffix="mΩ"
                  valueStyle={{ fontSize: '16px' }}
                />
              </Col>
            </Row>

            <Divider style={{ margin: '8px 0' }} />

          {/* 数据表格 */}
          <div style={{ minHeight: '500px' }}>
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
                ...pagination,
                onChange: handleTableChange,
                onShowSizeChange: handleTableChange,
              }}
              scroll={{ x: 1200 }}
              size="middle"
              onRow={(record) => ({
                onClick: () => handleRecordSelect(record),
                style: {
                  cursor: 'pointer',
                  backgroundColor: selectedRecord?.id === record.id ? '#e6f7ff' : undefined
                }
              })}
            />
          </div>
        </Card>

        {/* 第三部分：奈奎斯特图 */}
        <Card
          title={
            <Space>
              <LineChartOutlined />
              奈奎斯特图
              {selectedRecord && (
                <Text type="secondary">
                  - {selectedRecord.deviceId} CH{selectedRecord.channel}
                </Text>
              )}
            </Space>
          }
          style={{ width: '100%' }}
        >
          {selectedRecord ? (
            <Spin spinning={detailsLoading}>
              <div style={{ height: '400px' }}>
                <NyquistChart
                  data={impedanceDetails.map(detail => ({
                    frequency: detail.frequency,
                    real: detail.z_real,
                    imaginary: detail.z_imag,
                    magnitude: detail.z_magnitude,
                    phase: detail.phase_angle
                  }))}
                  title=""
                  height="400px"
                  showToolbar={true}
                  showFittedCurve={true}
                />
              </div>
            </Spin>
          ) : (
            <div style={{
              height: '400px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#fafafa',
              border: '1px dashed #d9d9d9',
              borderRadius: '6px'
            }}>
              <div style={{ textAlign: 'center', color: '#999' }}>
                <LineChartOutlined style={{ fontSize: '48px' }} />
                <div style={{ marginTop: '16px' }}>
                  请在查询结果中选择测试数据查看奈奎斯特图
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* 第四部分：测试明细数据 */}
        <Card
          title={
            <Space>
              <DatabaseOutlined />
              测试明细数据
              {selectedRecord && (
                <Text type="secondary">
                  - 测试ID: {selectedRecord.testId}
                </Text>
              )}
            </Space>
          }
          style={{ width: '100%' }}
        >
          {selectedRecord ? (
            <div style={{ minHeight: '400px' }}>
              <Tabs defaultActiveKey="basic" size="middle">
                <TabPane tab="基本信息" key="basic">
                  <Row gutter={[16, 16]}>
                    <Col span={8}>
                      <Text strong>测试ID:</Text> {selectedRecord.testId}
                    </Col>
                    <Col span={8}>
                      <Text strong>设备ID:</Text> {selectedRecord.deviceId}
                    </Col>
                    <Col span={8}>
                      <Text strong>批次ID:</Text> {selectedRecord.batchId}
                    </Col>
                    <Col span={8}>
                      <Text strong>通道:</Text> {selectedRecord.channel}
                    </Col>
                    <Col span={8}>
                      <Text strong>电压:</Text> {selectedRecord.voltage?.toFixed(3)} V
                    </Col>
                    <Col span={8}>
                      <Text strong>温度:</Text> {selectedRecord.temperature?.toFixed(1)} °C
                    </Col>
                    <Col span={8}>
                      <Text strong>Rs值:</Text> {selectedRecord.rs?.toFixed(3)} mΩ
                    </Col>
                    <Col span={8}>
                      <Text strong>Rct值:</Text> {selectedRecord.rct?.toFixed(3)} mΩ
                    </Col>
                    {selectedRecord.rsei && (
                      <Col span={8}>
                        <Text strong>Rsei值:</Text> {selectedRecord.rsei?.toFixed(3)} mΩ
                      </Col>
                    )}
                    <Col span={8}>
                      <Text strong>测试结果:</Text>
                      <Tag color={selectedRecord.result === 'pass' ? 'green' : 'red'} style={{ marginLeft: '4px' }}>
                        {selectedRecord.result === 'pass' ? '合格' : '不合格'}
                      </Tag>
                    </Col>
                    {selectedRecord.grade && (
                      <Col span={8}>
                        <Text strong>等级:</Text> {selectedRecord.grade}
                      </Col>
                    )}
                    <Col span={24}>
                      <Text strong>测试时间:</Text> {selectedRecord.testTime}
                    </Col>
                  </Row>
                </TabPane>

                <TabPane tab="阻抗数据" key="impedance">
                  <div style={{ height: '300px' }}>
                    <Table
                      columns={[
                        {
                          title: '频率(Hz)',
                          dataIndex: 'frequency',
                          key: 'frequency',
                          width: 120,
                          render: (value: number) => value.toFixed(2)
                        },
                        {
                          title: '实部(mΩ)',
                          dataIndex: 'z_real',
                          key: 'z_real',
                          width: 120,
                          render: (value: number) => value.toFixed(3)
                        },
                        {
                          title: '虚部(mΩ)',
                          dataIndex: 'z_imag',
                          key: 'z_imag',
                          width: 120,
                          render: (value: number) => value.toFixed(3)
                        },
                        {
                          title: '模值(mΩ)',
                          dataIndex: 'z_magnitude',
                          key: 'z_magnitude',
                          width: 120,
                          render: (value: number) => value.toFixed(3)
                        },
                        {
                          title: '相位(°)',
                          dataIndex: 'phase_angle',
                          key: 'phase_angle',
                          width: 120,
                          render: (value: number) => value.toFixed(1)
                        }
                      ]}
                      dataSource={impedanceDetails}
                      rowKey="id"
                      loading={detailsLoading}
                      pagination={{
                        pageSize: 10,
                        size: 'small',
                        showSizeChanger: true
                      }}
                      size="middle"
                      scroll={{ y: 250 }}
                    />
                  </div>
                </TabPane>
              </Tabs>
            </div>
          ) : (
            <div style={{
              height: '400px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#fafafa',
              border: '1px dashed #d9d9d9',
              borderRadius: '6px'
            }}>
              <div style={{ textAlign: 'center', color: '#999' }}>
                <DatabaseOutlined style={{ fontSize: '48px' }} />
                <div style={{ marginTop: '16px' }}>
                  请在查询结果中选择测试数据查看明细信息
                </div>
              </div>
            </div>
          )}
        </Card>

      </div>

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

export default DataAnalysisPageOptimized;
