import React, { useRef, useState } from 'react';
import { Card, Button, Space, Select, Tooltip, Switch, message } from 'antd';
import {
  ZoomInOutlined,
  ZoomOutOutlined,
  ReloadOutlined,
  DownloadOutlined,
  FullscreenOutlined
} from '@ant-design/icons';
import ReactECharts from 'echarts-for-react';

const { Option } = Select;

interface ImpedancePoint {
  frequency: number;
  real: number;
  imaginary: number;
  magnitude: number;
  phase: number;
}

interface ImpedanceSpectrumChartProps {
  data: ImpedancePoint[];
  title?: string;
  width?: number | string;
  height?: number | string;
  showToolbar?: boolean;
  chartType?: 'magnitude' | 'phase' | 'both';
  onPointClick?: (point: ImpedancePoint) => void;
}

const ImpedanceSpectrumChart: React.FC<ImpedanceSpectrumChartProps> = ({
  data = [],
  title = '阻抗谱图',
  width = '100%',
  height = 400,
  showToolbar = true,
  chartType = 'both',
  onPointClick
}) => {
  const chartRef = useRef<ReactECharts>(null);
  const [displayType, setDisplayType] = useState<'magnitude' | 'phase' | 'both'>(chartType);
  const [logScale, setLogScale] = useState(true);
  const [selectedFreqRange, setSelectedFreqRange] = useState<string>('all');

  // 生成模拟阻抗谱数据
  const generateMockData = (): ImpedancePoint[] => {
    const frequencies = [];
    // 生成对数分布的频率点
    for (let i = -2; i <= 4; i += 0.1) {
      frequencies.push(Math.pow(10, i));
    }
    
    return frequencies.map(freq => {
      // 模拟电池阻抗特性
      const Rs = 2.5;
      const Rsei = 1.2;
      const Csei = 0.001;
      const Rct = 12.0;
      const Cdl = 0.01;
      const W = 0.5;
      
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
  };

  // 使用模拟数据或传入的数据
  const impedanceData = data.length > 0 ? data : generateMockData();

  // 根据频率范围筛选数据
  const getFilteredData = () => {
    switch (selectedFreqRange) {
      case 'low':
        return impedanceData.filter(point => point.frequency <= 1);
      case 'mid':
        return impedanceData.filter(point => point.frequency > 1 && point.frequency <= 100);
      case 'high':
        return impedanceData.filter(point => point.frequency > 100);
      default:
        return impedanceData;
    }
  };

  // ECharts配置
  const getChartOption = () => {
    const filteredData = getFilteredData();
    
    const series = [];
    const yAxes = [];
    
    // 幅值数据系列
    if (displayType === 'magnitude' || displayType === 'both') {
      series.push({
        name: '阻抗模值 |Z|',
        type: 'line',
        yAxisIndex: 0,
        data: filteredData.map(point => [point.frequency, point.magnitude]),
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          color: '#1890ff',
          width: 2
        },
        itemStyle: {
          color: '#1890ff'
        },
        tooltip: {
          formatter: (params: any) => {
            const dataIndex = params.dataIndex;
            const point = filteredData[dataIndex];
            return `
              <div style="padding: 8px;">
                <div><strong>频率:</strong> ${point.frequency.toFixed(2)} Hz</div>
                <div><strong>阻抗模值:</strong> ${point.magnitude.toFixed(3)} mΩ</div>
                <div><strong>实部:</strong> ${point.real.toFixed(3)} mΩ</div>
                <div><strong>虚部:</strong> ${point.imaginary.toFixed(3)} mΩ</div>
              </div>
            `;
          }
        }
      });
      
      yAxes.push({
        type: 'value',
        name: '|Z| (mΩ)',
        position: 'left',
        scale: logScale,
        logBase: 10,
        nameTextStyle: {
          color: '#1890ff',
          fontSize: 14,
          fontWeight: 'bold'
        },
        axisLine: {
          lineStyle: {
            color: '#1890ff'
          }
        },
        axisLabel: {
          color: '#1890ff'
        },
        splitLine: {
          show: displayType === 'magnitude',
          lineStyle: {
            color: '#f0f0f0'
          }
        }
      });
    }
    
    // 相位数据系列
    if (displayType === 'phase' || displayType === 'both') {
      const yAxisIndex = displayType === 'both' ? 1 : 0;
      
      series.push({
        name: '相位角 φ',
        type: 'line',
        yAxisIndex,
        data: filteredData.map(point => [point.frequency, point.phase]),
        symbol: 'diamond',
        symbolSize: 6,
        lineStyle: {
          color: '#ff7875',
          width: 2
        },
        itemStyle: {
          color: '#ff7875'
        },
        tooltip: {
          formatter: (params: any) => {
            const dataIndex = params.dataIndex;
            const point = filteredData[dataIndex];
            return `
              <div style="padding: 8px;">
                <div><strong>频率:</strong> ${point.frequency.toFixed(2)} Hz</div>
                <div><strong>相位角:</strong> ${point.phase.toFixed(1)}°</div>
                <div><strong>阻抗模值:</strong> ${point.magnitude.toFixed(3)} mΩ</div>
              </div>
            `;
          }
        }
      });
      
      yAxes.push({
        type: 'value',
        name: 'φ (°)',
        position: displayType === 'both' ? 'right' : 'left',
        nameTextStyle: {
          color: '#ff7875',
          fontSize: 14,
          fontWeight: 'bold'
        },
        axisLine: {
          lineStyle: {
            color: '#ff7875'
          }
        },
        axisLabel: {
          color: '#ff7875'
        },
        splitLine: {
          show: displayType === 'phase',
          lineStyle: {
            color: '#f0f0f0'
          }
        }
      });
    }

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
        right: displayType === 'both' ? '15%' : '10%',
        bottom: '15%',
        top: '15%',
        containLabel: true
      },
      xAxis: {
        type: 'log',
        logBase: 10,
        name: '频率 (Hz)',
        nameLocation: 'middle',
        nameGap: 30,
        nameTextStyle: {
          fontSize: 14,
          fontWeight: 'bold'
        },
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
        axisLabel: {
          formatter: (value: number) => {
            if (value >= 1000) {
              return (value / 1000).toFixed(0) + 'k';
            } else if (value >= 1) {
              return value.toFixed(0);
            } else {
              return value.toFixed(2);
            }
          }
        }
      },
      yAxis: yAxes,
      legend: {
        data: series.map(s => s.name),
        bottom: 10,
        textStyle: {
          fontSize: 12
        }
      },
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        borderColor: '#ccc',
        borderWidth: 1,
        textStyle: {
          color: '#fff'
        }
      },
      toolbox: {
        show: showToolbar,
        feature: {
          dataZoom: {
            title: {
              zoom: '区域缩放',
              back: '缩放还原'
            }
          },
          restore: {
            title: '还原'
          },
          saveAsImage: {
            title: '保存图片',
            name: `impedance_spectrum_${Date.now()}`
          }
        },
        right: 20,
        top: 20
      },
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: 0
        }
      ],
      series
    };
  };

  // 图表事件处理
  const onChartClick = (params: any) => {
    if (params.componentType === 'series') {
      const dataIndex = params.dataIndex;
      const filteredData = getFilteredData();
      const point = filteredData[dataIndex];
      
      if (onPointClick) {
        onPointClick(point);
      } else {
        message.info(`频率: ${point.frequency.toFixed(2)} Hz, 阻抗: ${point.magnitude.toFixed(2)} mΩ, 相位: ${point.phase.toFixed(1)}°`);
      }
    }
  };

  // 工具栏操作
  const handleReset = () => {
    const chart = chartRef.current?.getEchartsInstance();
    if (chart) {
      chart.dispatchAction({
        type: 'restore'
      });
    }
  };

  const handleDownload = () => {
    const chart = chartRef.current?.getEchartsInstance();
    if (chart) {
      const url = chart.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff'
      });
      
      const link = document.createElement('a');
      link.download = `impedance_spectrum_${Date.now()}.png`;
      link.href = url;
      link.click();
      
      message.success('图表已下载');
    }
  };

  return (
    <Card
      title={
        <Space>
          <span>{title}</span>
          {showToolbar && (
            <>
              <Select
                value={displayType}
                onChange={setDisplayType}
                style={{ width: 120 }}
                size="small"
              >
                <Option value="magnitude">幅值</Option>
                <Option value="phase">相位</Option>
                <Option value="both">幅值+相位</Option>
              </Select>
              <Select
                value={selectedFreqRange}
                onChange={setSelectedFreqRange}
                style={{ width: 120 }}
                size="small"
              >
                <Option value="all">全频段</Option>
                <Option value="low">低频 (≤1Hz)</Option>
                <Option value="mid">中频 (1-100Hz)</Option>
                <Option value="high">高频 (&gt;100Hz)</Option>
              </Select>
            </>
          )}
        </Space>
      }
      extra={
        showToolbar && (
          <Space>
            <Tooltip title="对数坐标">
              <Switch
                checked={logScale}
                onChange={setLogScale}
                size="small"
                checkedChildren="Log"
                unCheckedChildren="Lin"
              />
            </Tooltip>
            <Tooltip title="重置">
              <Button
                type="text"
                icon={<ReloadOutlined />}
                onClick={handleReset}
                size="small"
              />
            </Tooltip>
            <Tooltip title="下载">
              <Button
                type="text"
                icon={<DownloadOutlined />}
                onClick={handleDownload}
                size="small"
              />
            </Tooltip>
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
      
      {/* 图表信息 */}
      <div style={{ 
        marginTop: '8px', 
        fontSize: '12px', 
        color: '#666',
        textAlign: 'center'
      }}>
        数据点数: {getFilteredData().length} | 
        显示类型: {displayType === 'magnitude' ? '幅值' : displayType === 'phase' ? '相位' : '幅值+相位'} | 
        坐标: {logScale ? '对数' : '线性'} | 
        频率范围: {selectedFreqRange === 'all' ? '全频段' : 
                  selectedFreqRange === 'low' ? '低频段' :
                  selectedFreqRange === 'mid' ? '中频段' : '高频段'}
      </div>
    </Card>
  );
};

export default ImpedanceSpectrumChart;
