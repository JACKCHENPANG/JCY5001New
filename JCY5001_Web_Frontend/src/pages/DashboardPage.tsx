import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Statistic,
  Typography,
  Space,
  Button,
  Table,
  Tag,
  Progress,
  Alert,
  message
} from 'antd';
import {
  DatabaseOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SyncOutlined,
  ReloadOutlined,
  BarChartOutlined
} from '@ant-design/icons';
import { dashboardAPI } from '../services/api';
import { useRealTimeData } from '../hooks/useRealTimeData';
import RealTimeIndicator from '../components/RealTimeIndicator';

const { Title, Text } = Typography;

interface DashboardStats {
  totalDevices: number;
  onlineDevices: number;
  totalTests: number;
  passRate: number;
  todayTests: number;
  avgRs: number;
  avgRct: number;
}

interface RecentTest {
  id: number;
  deviceId: string;
  testTime: string;
  channel: number;
  result: 'pass' | 'fail';
  rs: number;
  rct: number;
}

const DashboardPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState<DashboardStats>({
    totalDevices: 0,
    onlineDevices: 0,
    totalTests: 0,
    passRate: 0,
    todayTests: 0,
    avgRs: 0,
    avgRct: 0
  });
  const [recentTests, setRecentTests] = useState<RecentTest[]>([]);

  // 实时数据更新
  const realTimeData = useRealTimeData({
    method: 'polling',
    pollingInterval: 30000, // 30秒更新一次
    autoStart: false, // 不自动启动，手动控制
    pollingApi: async () => {
      const [statsResponse, recentResponse] = await Promise.all([
        dashboardAPI.getStats(),
        dashboardAPI.getRecentTests(5)
      ]);
      return { stats: statsResponse, recent: recentResponse };
    },
    onDataReceived: (data) => {
      if (data.stats && data.stats.status_code === 200) {
        setStats({
          totalDevices: data.stats.total_devices,
          onlineDevices: data.stats.online_devices,
          totalTests: data.stats.total_tests,
          passRate: data.stats.pass_rate,
          todayTests: data.stats.today_tests,
          avgRs: data.stats.avg_rs,
          avgRct: data.stats.avg_rct
        });
      }

      if (data.recent && data.recent.status_code === 200) {
        const formattedTests = data.recent.recent_tests.map((test: any) => ({
          id: test.id,
          deviceId: test.device_id,
          testTime: new Date(test.test_time).toLocaleString('zh-CN'),
          channel: test.channel,
          result: test.result,
          rs: test.rs,
          rct: test.rct
        }));
        setRecentTests(formattedTests);
      }
    },
    onError: (error) => {
      console.error('实时数据更新失败:', error);
    }
  });

  // 获取仪表板数据
  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      // 获取统计数据
      const statsResponse = await dashboardAPI.getStats();
      if (statsResponse && statsResponse.status_code === 200) {
        setStats({
          totalDevices: statsResponse.total_devices,
          onlineDevices: statsResponse.online_devices,
          totalTests: statsResponse.total_tests,
          passRate: statsResponse.pass_rate,
          todayTests: statsResponse.today_tests,
          avgRs: statsResponse.avg_rs,
          avgRct: statsResponse.avg_rct
        });
      }

      // 获取最近测试数据
      const recentResponse = await dashboardAPI.getRecentTests(5);
      if (recentResponse && recentResponse.status_code === 200) {
        const formattedTests = recentResponse.recent_tests.map((test: any) => ({
          id: test.id,
          deviceId: test.device_id,
          testTime: new Date(test.test_time).toLocaleString('zh-CN'),
          channel: test.channel,
          result: test.result,
          rs: test.rs,
          rct: test.rct
        }));
        setRecentTests(formattedTests);
      }

    } catch (error: any) {
      console.error('获取仪表板数据失败:', error);
      message.error('获取仪表板数据失败: ' + (error.message || '未知错误'));

      // 设置默认数据以防止页面崩溃
      setStats({
        totalDevices: 0,
        onlineDevices: 0,
        totalTests: 0,
        passRate: 0,
        todayTests: 0,
        avgRs: 0,
        avgRct: 0
      });
      setRecentTests([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    // 启动实时数据更新
    realTimeData.start();

    // 清理函数
    return () => {
      realTimeData.stop();
    };
  }, []);

  // 最近测试表格列定义
  const recentTestColumns = [
    {
      title: '设备ID',
      dataIndex: 'deviceId',
      key: 'deviceId',
      width: 120,
    },
    {
      title: '测试时间',
      dataIndex: 'testTime',
      key: 'testTime',
      width: 150,
    },
    {
      title: '通道',
      dataIndex: 'channel',
      key: 'channel',
      width: 80,
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
      title: 'Rs (mΩ)',
      dataIndex: 'rs',
      key: 'rs',
      width: 100,
      render: (value: number) => value.toFixed(2),
    },
    {
      title: 'Rct (mΩ)',
      dataIndex: 'rct',
      key: 'rct',
      width: 100,
      render: (value: number) => value.toFixed(2),
    },
  ];

  return (
    <div>
      {/* 页面标题 */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <Title level={2}>
              <Space>
                <BarChartOutlined />
                仪表板
              </Space>
            </Title>
            <Text type="secondary">系统运行状态和数据概览</Text>
          </div>

          {/* 实时状态指示器 */}
          <RealTimeIndicator
            connected={realTimeData.connected}
            lastUpdate={realTimeData.lastUpdate}
            error={realTimeData.error}
            onRefresh={realTimeData.refresh}
          />
        </div>
      </div>

      {/* 系统状态提醒 */}
      <Alert
        message="系统运行正常"
        description="所有设备连接正常，数据同步正常"
        type="success"
        showIcon
        style={{ marginBottom: '24px' }}
      />

      {/* 统计卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="设备总数"
              value={stats.totalDevices}
              prefix={<DatabaseOutlined />}
              suffix="台"
            />
            <div style={{ marginTop: '8px' }}>
              <Text type="secondary">
                在线: {stats.onlineDevices} 台
              </Text>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="总测试次数"
              value={stats.totalTests}
              prefix={<CheckCircleOutlined />}
              suffix="次"
            />
            <div style={{ marginTop: '8px' }}>
              <Text type="secondary">
                今日: {stats.todayTests} 次
              </Text>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="合格率"
              value={stats.passRate}
              precision={1}
              suffix="%"
              valueStyle={{ color: stats.passRate >= 90 ? '#3f8600' : '#cf1322' }}
            />
            <div style={{ marginTop: '8px' }}>
              <Progress 
                percent={stats.passRate} 
                size="small" 
                showInfo={false}
                strokeColor={stats.passRate >= 90 ? '#52c41a' : '#ff4d4f'}
              />
            </div>
          </Card>
        </Col>
        
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="平均Rs值"
              value={stats.avgRs}
              precision={2}
              suffix="mΩ"
            />
            <div style={{ marginTop: '8px' }}>
              <Text type="secondary">
                平均Rct: {stats.avgRct.toFixed(2)} mΩ
              </Text>
            </div>
          </Card>
        </Col>
      </Row>

      {/* 设备状态和最近测试 */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <DatabaseOutlined />
                设备状态
              </Space>
            }
            extra={
              <Button
                type="text"
                icon={<ReloadOutlined />}
                onClick={realTimeData.refresh}
                loading={loading}
              >
                刷新
              </Button>
            }
          >
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <Progress
                type="circle"
                percent={Math.round((stats.onlineDevices / stats.totalDevices) * 100)}
                format={() => `${stats.onlineDevices}/${stats.totalDevices}`}
                strokeColor="#52c41a"
                size={120}
              />
              <div style={{ marginTop: '16px' }}>
                <Text strong>设备在线率</Text>
              </div>
            </div>
            
            <div style={{ marginTop: '16px' }}>
              <Row gutter={16}>
                <Col span={12}>
                  <div style={{ textAlign: 'center' }}>
                    <CheckCircleOutlined style={{ fontSize: '24px', color: '#52c41a' }} />
                    <div style={{ marginTop: '8px' }}>
                      <Text strong>{stats.onlineDevices}</Text>
                      <br />
                      <Text type="secondary">在线设备</Text>
                    </div>
                  </div>
                </Col>
                <Col span={12}>
                  <div style={{ textAlign: 'center' }}>
                    <CloseCircleOutlined style={{ fontSize: '24px', color: '#ff4d4f' }} />
                    <div style={{ marginTop: '8px' }}>
                      <Text strong>{stats.totalDevices - stats.onlineDevices}</Text>
                      <br />
                      <Text type="secondary">离线设备</Text>
                    </div>
                  </div>
                </Col>
              </Row>
            </div>
          </Card>
        </Col>
        
        <Col xs={24} lg={12}>
          <Card
            title={
              <Space>
                <SyncOutlined />
                最近测试
              </Space>
            }
            extra={
              <Button type="link" href="/analysis">
                查看更多
              </Button>
            }
          >
            <Table
              columns={recentTestColumns}
              dataSource={recentTests}
              rowKey="id"
              pagination={false}
              size="small"
              scroll={{ x: 600 }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default DashboardPage;
