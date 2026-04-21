import React, { useRef, useState, useEffect } from 'react';
import { Card, Button, Space, Select, Tooltip, Switch, message, Table, Typography } from 'antd';
import {
  ReloadOutlined,
  DownloadOutlined,
  FullscreenOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

const { Option } = Select;
const { Text } = Typography;

interface TestData {
  id: number;
  deviceId: string;
  channel: number;
  testTime: string;
  rs: number;
  rct: number;
  rsei: number;
  voltage: number;
  result: 'pass' | 'fail';
}

interface DeviationData {
  channel: number;
  deviceId: string;
  rs: number;
  rct: number;
  rsei: number;
  rsDeviation: number;
  rctDeviation: number;
  rseiDeviation: number;
  testTime: string;
}

interface ZValueDeviationChartProps {
  data: TestData[];
  title?: string;
  width?: number | string;
  height?: number | string;
  showToolbar?: boolean;
  referenceChannel?: number;
  comparisonType?: 'channel' | 'device' | 'batch';
  onDeviationClick?: (deviation: DeviationData) => void;
}

const ZValueDeviationChart: React.FC<ZValueDeviationChartProps> = ({
  data = [],
  title = 'Z值偏差对比分析',
  width = '100%',
  height = 400,
  showToolbar = true,
  referenceChannel = 1,
  comparisonType = 'channel',
  onDeviationClick
}) => {
  const chartRef = useRef<ReactECharts>(null);
  const [selectedParameter, setSelectedParameter] = useState<'rs' | 'rct' | 'rsei'>('rs');
  const [showPercentage, setShowPercentage] = useState(true);
  const [referenceValue, setReferenceValue] = useState<number>(0);
  const [deviationData, setDeviationData] = useState<DeviationData[]>([]);
  const [showDataTable, setShowDataTable] = useState(false);

  // 生成模拟测试数据
  const generateMockData = (): TestData[] => {
    const devices = ['JCY5001A_001', 'JCY5001A_002', 'JCY5001A_003'];
    const mockData: TestData[] = [];
    
    devices.forEach((deviceId, deviceIndex) => {
      for (let channel = 1; channel <= 8; channel++) {
        // 基准值
        const baseRs = 2.5 + deviceIndex * 0.2;
        const baseRct = 12.0 + deviceIndex * 1.0;
        const baseRsei = 1.2 + deviceIndex * 0.1;
        
        // 添加通道间的偏差
        const channelVariation = (channel - 1) * 0.05 + (Math.random() - 0.5) * 0.3;
        
        mockData.push({
          id: deviceIndex * 8 + channel,
          deviceId,
          channel,
          testTime: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toLocaleString(),
          rs: baseRs + channelVariation,
          rct: baseRct + channelVariation * 3,
          rsei: baseRsei + channelVariation * 0.5,
          voltage: 3.2 + Math.random() * 0.8,
          result: Math.random() > 0.1 ? 'pass' : 'fail'
        });
      }
    });
    
    return mockData;
  };

  // 使用模拟数据或传入的数据
  const testData = data.length > 0 ? data : generateMockData();

  // 计算偏差数据
  const calculateDeviations = () => {
    if (testData.length === 0) return [];

    // 根据对比类型确定参考值
    let referenceData: TestData | undefined;
    
    if (comparisonType === 'channel') {
      // 以指定通道为参考
      referenceData = testData.find(item => item.channel === referenceChannel);
    } else if (comparisonType === 'device') {
      // 以第一个设备为参考
      referenceData = testData.find(item => item.deviceId === testData[0].deviceId);
    }

    if (!referenceData) {
      referenceData = testData[0];
    }

    const refValue = referenceData[selectedParameter];
    setReferenceValue(refValue);

    const deviations: DeviationData[] = testData.map(item => {
      const rsDeviation = showPercentage 
        ? ((item.rs - referenceData!.rs) / referenceData!.rs) * 100
        : item.rs - referenceData!.rs;
      
      const rctDeviation = showPercentage
        ? ((item.rct - referenceData!.rct) / referenceData!.rct) * 100
        : item.rct - referenceData!.rct;
      
      const rseiDeviation = showPercentage
        ? ((item.rsei - referenceData!.rsei) / referenceData!.rsei) * 100
        : item.rsei - referenceData!.rsei;

      return {
        channel: item.channel,
        deviceId: item.deviceId,
        rs: item.rs,
        rct: item.rct,
        rsei: item.rsei,
        rsDeviation,
        rctDeviation,
        rseiDeviation,
        testTime: item.testTime
      };
    });

    setDeviationData(deviations);
    return deviations;
  };

  useEffect(() => {
    calculateDeviations();
  }, [testData, selectedParameter, showPercentage, referenceChannel, comparisonType]);

  // ECharts配置
  const getChartOption = () => {
    const deviations = calculateDeviations();
    
    // 根据对比类型组织数据
    const categories = comparisonType === 'channel' 
      ? Array.from({ length: 8 }, (_, i) => `CH${i + 1}`)
      : [...new Set(deviations.map(d => d.deviceId))];

    const seriesData = categories.map(category => {
      const items = comparisonType === 'channel'
        ? deviations.filter(d => d.channel === parseInt(category.replace('CH', '')))
        : deviations.filter(d => d.deviceId === category);
      
      if (items.length === 0) return 0;
      
      // 取平均值或第一个值
      const avgDeviation = items.reduce((sum, item) => {
        return sum + item[`${selectedParameter}Deviation` as keyof DeviationData] as number;
      }, 0) / items.length;
      
      return avgDeviation;
    });

    // 计算颜色（基于偏差范围）
    const getColor = (value: number) => {
      const absValue = Math.abs(value);
      if (absValue <= 5) return '#52c41a'; // 绿色：偏差小
      if (absValue <= 15) return '#faad14'; // 黄色：偏差中等
      return '#ff4d4f'; // 红色：偏差大
    };

    return {
      title: {
        text: title,
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      grid: {
        left: '10%',
        right: '10%',
        bottom: '15%',
        top: '20%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: categories,
        name: comparisonType === 'channel' ? '通道' : '设备',
        nameLocation: 'middle',
        nameGap: 30,
        axisLine: {
          lineStyle: {
            color: '#666'
          }
        }
      },
      yAxis: {
        type: 'value',
        name: `${selectedParameter.toUpperCase()}偏差 ${showPercentage ? '(%)' : '(mΩ)'}`,
        nameLocation: 'middle',
        nameGap: 50,
        axisLine: {
          lineStyle: {
            color: '#666'
          }
        },
        splitLine: {
          show: true,
          lineStyle: {
            color: '#f0f0f0'
          }
        },
        // 添加零线
        axisPointer: {
          show: true,
          lineStyle: {
            color: '#999',
            type: 'dashed'
          }
        }
      },
      series: [
        {
          name: `${selectedParameter.toUpperCase()}偏差`,
          type: 'bar',
          data: seriesData.map((value, index) => ({
            value,
            itemStyle: {
              color: getColor(value)
            }
          })),
          barWidth: '60%',
          label: {
            show: true,
            position: 'top',
            formatter: (params: any) => {
              const value = params.value;
              return showPercentage ? `${value.toFixed(1)}%` : `${value.toFixed(2)}`;
            },
            fontSize: 12
          },
          tooltip: {
            formatter: (params: any) => {
              const categoryIndex = params.dataIndex;
              const category = categories[categoryIndex];
              const value = params.value;
              
              return `
                <div style="padding: 8px;">
                  <div><strong>${comparisonType === 'channel' ? '通道' : '设备'}:</strong> ${category}</div>
                  <div><strong>${selectedParameter.toUpperCase()}偏差:</strong> ${showPercentage ? value.toFixed(1) + '%' : value.toFixed(2) + 'mΩ'}</div>
                  <div><strong>参考值:</strong> ${referenceValue.toFixed(2)} mΩ</div>
                  <div><strong>状态:</strong> ${Math.abs(value) <= 5 ? '正常' : Math.abs(value) <= 15 ? '注意' : '异常'}</div>
                </div>
              `;
            }
          }
        }
      ],
      // 添加参考线（零偏差线）
      markLine: {
        data: [
          {
            yAxis: 0,
            lineStyle: {
              color: '#999',
              type: 'dashed',
              width: 2
            },
            label: {
              formatter: '零偏差线',
              position: 'end'
            }
          }
        ]
      },
      toolbox: {
        show: showToolbar,
        feature: {
          saveAsImage: {
            title: '保存图片',
            name: `z_deviation_${selectedParameter}_${Date.now()}`
          }
        },
        right: 20,
        top: 20
      }
    };
  };

  // 图表事件处理
  const onChartClick = (params: any) => {
    if (params.componentType === 'series') {
      const categoryIndex = params.dataIndex;
      const category = comparisonType === 'channel' 
        ? `CH${categoryIndex + 1}`
        : [...new Set(deviationData.map(d => d.deviceId))][categoryIndex];
      
      const relatedData = comparisonType === 'channel'
        ? deviationData.filter(d => d.channel === categoryIndex + 1)
        : deviationData.filter(d => d.deviceId === category);
      
      if (relatedData.length > 0 && onDeviationClick) {
        onDeviationClick(relatedData[0]);
      } else {
        message.info(`${comparisonType === 'channel' ? '通道' : '设备'}: ${category}, 偏差: ${params.value.toFixed(2)}${showPercentage ? '%' : 'mΩ'}`);
      }
    }
  };

  // 工具栏操作
  const handleDownload = () => {
    const chart = chartRef.current?.getEchartsInstance();
    if (chart) {
      const url = chart.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff'
      });
      
      const link = document.createElement('a');
      link.download = `z_deviation_${selectedParameter}_${Date.now()}.png`;
      link.href = url;
      link.click();
      
      message.success('图表已下载');
    }
  };

  // 偏差数据表格列
  const tableColumns = [
    {
      title: comparisonType === 'channel' ? '通道' : '设备',
      dataIndex: comparisonType === 'channel' ? 'channel' : 'deviceId',
      key: comparisonType === 'channel' ? 'channel' : 'deviceId',
      render: (value: any) => comparisonType === 'channel' ? `CH${value}` : value,
    },
    {
      title: `${selectedParameter.toUpperCase()}值 (mΩ)`,
      dataIndex: selectedParameter,
      key: selectedParameter,
      render: (value: number) => value.toFixed(2),
    },
    {
      title: `偏差 ${showPercentage ? '(%)' : '(mΩ)'}`,
      dataIndex: `${selectedParameter}Deviation`,
      key: 'deviation',
      render: (value: number) => (
        <span style={{ 
          color: Math.abs(value) <= 5 ? '#52c41a' : Math.abs(value) <= 15 ? '#faad14' : '#ff4d4f' 
        }}>
          {showPercentage ? `${value.toFixed(1)}%` : `${value.toFixed(2)}mΩ`}
        </span>
      ),
    },
    {
      title: '状态',
      key: 'status',
      render: (_, record: DeviationData) => {
        const deviation = Math.abs(record[`${selectedParameter}Deviation` as keyof DeviationData] as number);
        const status = deviation <= 5 ? 'success' : deviation <= 15 ? 'warning' : 'error';
        const text = deviation <= 5 ? '正常' : deviation <= 15 ? '注意' : '异常';
        return <span style={{ color: status === 'success' ? '#52c41a' : status === 'warning' ? '#faad14' : '#ff4d4f' }}>{text}</span>;
      },
    },
  ];

  return (
    <Card
      title={
        <Space>
          <span>{title}</span>
          <Tooltip title="Z值偏差分析用于对比不同通道或设备间的阻抗参数差异">
            <InfoCircleOutlined style={{ color: '#1890ff' }} />
          </Tooltip>
        </Space>
      }
      extra={
        showToolbar && (
          <Space>
            <Select
              value={selectedParameter}
              onChange={setSelectedParameter}
              style={{ width: 80 }}
              size="small"
            >
              <Option value="rs">Rs</Option>
              <Option value="rct">Rct</Option>
              <Option value="rsei">Rsei</Option>
            </Select>
            <Switch
              checked={showPercentage}
              onChange={setShowPercentage}
              size="small"
              checkedChildren="%"
              unCheckedChildren="mΩ"
            />
            <Button
              type="text"
              icon={<ReloadOutlined />}
              onClick={() => calculateDeviations()}
              size="small"
            />
            <Button
              type="text"
              icon={<DownloadOutlined />}
              onClick={handleDownload}
              size="small"
            />
            <Button
              type={showDataTable ? 'primary' : 'default'}
              size="small"
              onClick={() => setShowDataTable(!showDataTable)}
            >
              {showDataTable ? '隐藏表格' : '显示表格'}
            </Button>
          </Space>
        )
      }
      bodyStyle={{ padding: '16px' }}
    >
      <ReactECharts
        ref={chartRef}
        option={getChartOption()}
        style={{ width, height }}
        onEvents={{
          click: onChartClick
        }}
        opts={{
          renderer: 'canvas',
          useDirtyRect: false
        }}
      />
      
      {/* 统计信息 */}
      <div style={{ 
        marginTop: '8px', 
        fontSize: '12px', 
        color: '#666',
        textAlign: 'center'
      }}>
        参考值: {referenceValue.toFixed(2)} mΩ | 
        对比类型: {comparisonType === 'channel' ? '通道对比' : '设备对比'} | 
        参数: {selectedParameter.toUpperCase()} | 
        单位: {showPercentage ? '百分比' : '绝对值'}
      </div>

      {/* 偏差数据表格 */}
      {showDataTable && (
        <div style={{ marginTop: '16px' }}>
          <Table
            columns={tableColumns}
            dataSource={deviationData}
            rowKey={(record) => `${record.deviceId}_${record.channel}`}
            size="small"
            pagination={{ pageSize: 8 }}
            title={() => <Text strong>偏差数据详情</Text>}
          />
        </div>
      )}
    </Card>
  );
};

export default ZValueDeviationChart;
