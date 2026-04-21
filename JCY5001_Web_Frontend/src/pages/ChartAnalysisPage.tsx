import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Tabs,
  Button,
  Space,
  Select,
  Typography,
  Divider,
  message,
  Modal,
  Table
} from 'antd';
import {
  LineChartOutlined,
  BarChartOutlined,
  FullscreenOutlined,
  SwapOutlined,
  DownloadOutlined
} from '@ant-design/icons';
import NyquistChart from '../components/NyquistChart';
import ImpedanceSpectrumChart from '../components/ImpedanceSpectrumChart';
import ZValueDeviationChart from '../components/ZValueDeviationChart';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Option } = Select;

interface ImpedancePoint {
  frequency: number;
  real: number;
  imaginary: number;
  magnitude: number;
  phase: number;
}

interface TestData {
  id: number;
  deviceId: string;
  channel: number;
  testTime: string;
  impedanceData: ImpedancePoint[];
  rs: number;
  rct: number;
  rsei: number;
  voltage: number;
  result: 'pass' | 'fail';
}

const ChartAnalysisPage: React.FC = () => {
  const [selectedTest, setSelectedTest] = useState<TestData | null>(null);
  const [testDataList, setTestDataList] = useState<TestData[]>([]);
  const [compareMode, setCompareMode] = useState(false);
  const [selectedTests, setSelectedTests] = useState<TestData[]>([]);
  const [fullscreenChart, setFullscreenChart] = useState<string | null>(null);

  // 生成模拟测试数据
  const generateMockTestData = (): TestData[] => {
    return Array.from({ length: 10 }, (_, index) => {
      // 生成模拟阻抗数据
      const frequencies = [
        0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 
        1000, 2000, 5000, 7800
      ];
      
      const impedanceData: ImpedancePoint[] = frequencies.map(freq => {
        // 为不同测试添加一些变化
        const variation = 1 + (Math.random() - 0.5) * 0.2; // ±10%变化
        
        const Rs = 2.5 * variation;
        const Rsei = 1.2 * variation;
        const Csei = 0.001;
        const Rct = 12.0 * variation;
        const Cdl = 0.01;
        const W = 0.5 * variation;
        
        const omega = 2 * Math.PI * freq;
        
        // SEI膜阻抗
        const seiDenom = 1 + Math.pow(omega * Rsei * Csei, 2);
        const seiReal = Rsei / seiDenom;
        const seiImag = -omega * Rsei * Rsei * Csei / seiDenom;
        
        // 电荷转移阻抗
        const ctDenom = 1 + Math.pow(omega * Rct * Cdl, 2);
        const ctReal = Rct / ctDenom;
        const ctImag = -omega * Rct * Rct * Cdl / ctDenom;
        
        // Warburg阻抗
        const wReal = W / Math.sqrt(omega);
        const wImag = -W / Math.sqrt(omega);
        
        // 总阻抗
        const real = Rs + seiReal + ctReal + wReal;
        const imaginary = seiImag + ctImag + wImag;
        
        const magnitude = Math.sqrt(real * real + imaginary * imaginary);
        const phase = Math.atan2(imaginary, real) * 180 / Math.PI;
        
        return {
          frequency: freq,
          real,
          imaginary,
          magnitude,
          phase
        };
      });

      return {
        id: index + 1,
        deviceId: `JCY5001A_${String(Math.floor(index / 4) + 1).padStart(3, '0')}`,
        channel: (index % 8) + 1,
        testTime: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toLocaleString(),
        impedanceData,
        rs: impedanceData[0].real, // 高频实部近似为Rs
        rct: Math.max(...impedanceData.map(p => p.real)) - Math.min(...impedanceData.map(p => p.real)), // 近似Rct
        rsei: impedanceData.find(p => p.frequency >= 100)?.real || 0,
        voltage: 3.2 + Math.random() * 0.8,
        result: Math.random() > 0.1 ? 'pass' : 'fail'
      };
    });
  };

  useEffect(() => {
    const mockData = generateMockTestData();
    setTestDataList(mockData);
    setSelectedTest(mockData[0]); // 默认选择第一个测试
  }, []);

  // 处理测试选择
  const handleTestSelect = (testId: number) => {
    const test = testDataList.find(t => t.id === testId);
    if (test) {
      setSelectedTest(test);
    }
  };

  // 处理对比模式
  const handleCompareToggle = () => {
    setCompareMode(!compareMode);
    if (!compareMode) {
      setSelectedTests([]);
    }
  };

  // 处理对比测试选择
  const handleCompareSelect = (testIds: number[]) => {
    const tests = testDataList.filter(t => testIds.includes(t.id));
    setSelectedTests(tests);
  };

  // 处理全屏显示
  const handleFullscreen = (chartType: string) => {
    setFullscreenChart(chartType);
  };

  // 处理数据点击
  const handlePointClick = (point: ImpedancePoint) => {
    Modal.info({
      title: '阻抗数据详情',
      width: 500,
      content: (
        <div style={{ marginTop: '16px' }}>
          <Row gutter={[16, 8]}>
            <Col span={12}><Text strong>频率:</Text></Col>
            <Col span={12}>{point.frequency} Hz</Col>
            <Col span={12}><Text strong>实部 Z':</Text></Col>
            <Col span={12}>{point.real.toFixed(3)} mΩ</Col>
            <Col span={12}><Text strong>虚部 Z'':</Text></Col>
            <Col span={12}>{point.imaginary.toFixed(3)} mΩ</Col>
            <Col span={12}><Text strong>模值 |Z|:</Text></Col>
            <Col span={12}>{point.magnitude.toFixed(3)} mΩ</Col>
            <Col span={12}><Text strong>相位角 φ:</Text></Col>
            <Col span={12}>{point.phase.toFixed(1)}°</Col>
          </Row>
        </div>
      ),
    });
  };

  // 测试数据表格列
  const testTableColumns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '设备ID',
      dataIndex: 'deviceId',
      key: 'deviceId',
      width: 120,
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
      title: 'Rs (mΩ)',
      dataIndex: 'rs',
      key: 'rs',
      width: 80,
      render: (value: number) => value.toFixed(2),
    },
    {
      title: 'Rct (mΩ)',
      dataIndex: 'rct',
      key: 'rct',
      width: 80,
      render: (value: number) => value.toFixed(2),
    },
  ];

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>
          <Space>
            <LineChartOutlined />
            图表分析
          </Space>
        </Title>
        <Text type="secondary">电池阻抗数据可视化分析</Text>
      </div>

      <Row gutter={[16, 16]}>
        {/* 左侧：测试数据选择 */}
        <Col xs={24} lg={8}>
          <Card
            title="测试数据选择"
            extra={
              <Space>
                <Button
                  type={compareMode ? 'primary' : 'default'}
                  icon={<SwapOutlined />}
                  onClick={handleCompareToggle}
                  size="small"
                >
                  {compareMode ? '退出对比' : '对比模式'}
                </Button>
              </Space>
            }
            bodyStyle={{ padding: '12px' }}
          >
            {!compareMode ? (
              // 单选模式
              <div>
                <Text strong>选择测试:</Text>
                <Select
                  style={{ width: '100%', marginTop: '8px' }}
                  value={selectedTest?.id}
                  onChange={handleTestSelect}
                  placeholder="选择测试数据"
                >
                  {testDataList.map(test => (
                    <Option key={test.id} value={test.id}>
                      {test.deviceId} - CH{test.channel} - {test.testTime}
                    </Option>
                  ))}
                </Select>
                
                {selectedTest && (
                  <div style={{ marginTop: '16px' }}>
                    <Divider style={{ margin: '12px 0' }} />
                    <Row gutter={[8, 8]}>
                      <Col span={12}><Text strong>设备:</Text></Col>
                      <Col span={12}>{selectedTest.deviceId}</Col>
                      <Col span={12}><Text strong>通道:</Text></Col>
                      <Col span={12}>CH{selectedTest.channel}</Col>
                      <Col span={12}><Text strong>Rs:</Text></Col>
                      <Col span={12}>{selectedTest.rs.toFixed(2)} mΩ</Col>
                      <Col span={12}><Text strong>Rct:</Text></Col>
                      <Col span={12}>{selectedTest.rct.toFixed(2)} mΩ</Col>
                      <Col span={12}><Text strong>数据点:</Text></Col>
                      <Col span={12}>{selectedTest.impedanceData.length}</Col>
                    </Row>
                  </div>
                )}
              </div>
            ) : (
              // 对比模式
              <div>
                <Text strong>选择对比测试 (最多4个):</Text>
                <Select
                  mode="multiple"
                  style={{ width: '100%', marginTop: '8px' }}
                  value={selectedTests.map(t => t.id)}
                  onChange={handleCompareSelect}
                  placeholder="选择要对比的测试数据"
                  maxTagCount={2}
                >
                  {testDataList.map(test => (
                    <Option key={test.id} value={test.id} disabled={selectedTests.length >= 4 && !selectedTests.find(t => t.id === test.id)}>
                      {test.deviceId} - CH{test.channel}
                    </Option>
                  ))}
                </Select>
                
                {selectedTests.length > 0 && (
                  <div style={{ marginTop: '16px' }}>
                    <Divider style={{ margin: '12px 0' }} />
                    <Text strong>已选择 {selectedTests.length} 个测试:</Text>
                    {selectedTests.map(test => (
                      <div key={test.id} style={{ marginTop: '4px', fontSize: '12px' }}>
                        • {test.deviceId} - CH{test.channel}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </Card>

          {/* 测试数据表格 */}
          <Card title="测试数据列表" style={{ marginTop: '16px' }}>
            <Table
              columns={testTableColumns}
              dataSource={testDataList}
              rowKey="id"
              size="small"
              pagination={{ pageSize: 5 }}
              scroll={{ x: 500 }}
              onRow={(record) => ({
                onClick: () => {
                  if (!compareMode) {
                    handleTestSelect(record.id);
                  }
                },
                style: {
                  cursor: compareMode ? 'default' : 'pointer',
                  backgroundColor: selectedTest?.id === record.id ? '#e6f7ff' : undefined
                }
              })}
            />
          </Card>
        </Col>

        {/* 右侧：图表显示 */}
        <Col xs={24} lg={16}>
          <Tabs defaultActiveKey="nyquist" type="card">
            <TabPane
              tab={
                <Space>
                  <BarChartOutlined />
                  奈奎斯特图
                </Space>
              }
              key="nyquist"
            >
              <div style={{ position: 'relative' }}>
                <Button
                  type="text"
                  icon={<FullscreenOutlined />}
                  onClick={() => handleFullscreen('nyquist')}
                  style={{ position: 'absolute', top: 8, right: 8, zIndex: 10 }}
                />
                
                {!compareMode && selectedTest ? (
                  <NyquistChart
                    data={selectedTest.impedanceData}
                    title={`奈奎斯特图 - ${selectedTest.deviceId} CH${selectedTest.channel}`}
                    height={500}
                    showFittedCurve={true}
                    onPointClick={handlePointClick}
                  />
                ) : compareMode && selectedTests.length > 0 ? (
                  <div>
                    <Text strong>对比模式下的奈奎斯特图功能开发中...</Text>
                    {/* 这里可以实现多条曲线对比显示 */}
                  </div>
                ) : (
                  <div style={{ 
                    height: 500, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    background: '#fafafa',
                    border: '1px dashed #d9d9d9'
                  }}>
                    <div style={{ textAlign: 'center', color: '#999' }}>
                      <BarChartOutlined style={{ fontSize: '48px' }} />
                      <div style={{ marginTop: '16px' }}>
                        请选择测试数据查看奈奎斯特图
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </TabPane>

            <TabPane
              tab={
                <Space>
                  <LineChartOutlined />
                  阻抗谱图
                </Space>
              }
              key="spectrum"
            >
              <div style={{ position: 'relative' }}>
                <Button
                  type="text"
                  icon={<FullscreenOutlined />}
                  onClick={() => handleFullscreen('spectrum')}
                  style={{ position: 'absolute', top: 8, right: 8, zIndex: 10 }}
                />
                
                {!compareMode && selectedTest ? (
                  <ImpedanceSpectrumChart
                    data={selectedTest.impedanceData}
                    title={`阻抗谱图 - ${selectedTest.deviceId} CH${selectedTest.channel}`}
                    height={500}
                    chartType="both"
                    onPointClick={handlePointClick}
                  />
                ) : compareMode && selectedTests.length > 0 ? (
                  <div>
                    <Text strong>对比模式下的阻抗谱图功能开发中...</Text>
                    {/* 这里可以实现多条曲线对比显示 */}
                  </div>
                ) : (
                  <div style={{ 
                    height: 500, 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    background: '#fafafa',
                    border: '1px dashed #d9d9d9'
                  }}>
                    <div style={{ textAlign: 'center', color: '#999' }}>
                      <LineChartOutlined style={{ fontSize: '48px' }} />
                      <div style={{ marginTop: '16px' }}>
                        请选择测试数据查看阻抗谱图
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </TabPane>

            <TabPane
              tab={
                <Space>
                  <SwapOutlined />
                  Z值偏差分析
                </Space>
              }
              key="deviation"
            >
              <div style={{ position: 'relative' }}>
                <Button
                  type="text"
                  icon={<FullscreenOutlined />}
                  onClick={() => handleFullscreen('deviation')}
                  style={{ position: 'absolute', top: 8, right: 8, zIndex: 10 }}
                />

                <ZValueDeviationChart
                  data={testDataList}
                  title="Z值偏差对比分析"
                  height={500}
                  comparisonType="channel"
                  referenceChannel={1}
                />
              </div>
            </TabPane>
          </Tabs>
        </Col>
      </Row>

      {/* 全屏图表模态框 */}
      <Modal
        title={
          fullscreenChart === 'nyquist' ? '奈奎斯特图 - 全屏模式' :
          fullscreenChart === 'spectrum' ? '阻抗谱图 - 全屏模式' :
          'Z值偏差分析 - 全屏模式'
        }
        open={!!fullscreenChart}
        onCancel={() => setFullscreenChart(null)}
        width="90vw"
        style={{ top: 20 }}
        footer={[
          <Button key="download" icon={<DownloadOutlined />}>
            下载图片
          </Button>,
          <Button key="close" onClick={() => setFullscreenChart(null)}>
            关闭
          </Button>
        ]}
      >
        {fullscreenChart === 'nyquist' && selectedTest && (
          <NyquistChart
            data={selectedTest.impedanceData}
            title={`奈奎斯特图 - ${selectedTest.deviceId} CH${selectedTest.channel}`}
            height="70vh"
            showFittedCurve={true}
            onPointClick={handlePointClick}
          />
        )}
        {fullscreenChart === 'spectrum' && selectedTest && (
          <ImpedanceSpectrumChart
            data={selectedTest.impedanceData}
            title={`阻抗谱图 - ${selectedTest.deviceId} CH${selectedTest.channel}`}
            height="70vh"
            chartType="both"
            onPointClick={handlePointClick}
          />
        )}
        {fullscreenChart === 'deviation' && (
          <ZValueDeviationChart
            data={testDataList}
            title="Z值偏差对比分析 - 全屏模式"
            height="70vh"
            comparisonType="channel"
            referenceChannel={1}
          />
        )}
      </Modal>
    </div>
  );
};

export default ChartAnalysisPage;
