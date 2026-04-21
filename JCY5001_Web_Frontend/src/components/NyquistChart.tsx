import React from 'react';
import { Card } from 'antd';

interface ImpedancePoint {
  frequency: number;
  real: number;
  imaginary: number;
  magnitude: number;
  phase: number;
  channel?: number;
}

interface ChannelData {
  channel: number;
  data: ImpedancePoint[];
  color?: string;
  name?: string;
}

interface NyquistChartProps {
  data?: ImpedancePoint[];
  channelData?: ChannelData[];
  title?: string;
  width?: number | string;
  height?: number | string;
  showToolbar?: boolean;
  showFittedCurve?: boolean;
  onPointClick?: (point: ImpedancePoint) => void;
}

const NyquistChart: React.FC<NyquistChartProps> = ({
  data = [],
  channelData = [],
  title = '奈奎斯特图',
  width = '100%',
  height = 400,
  showToolbar = true,
  showFittedCurve = false,
  onPointClick
}) => {
  return (
    <Card title={title} style={{ width, height }}>
      <div style={{
        width: '100%',
        height: typeof height === 'number' ? height - 100 : '300px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#f5f5f5',
        border: '1px dashed #d9d9d9',
        borderRadius: '6px'
      }}>
        <div style={{ textAlign: 'center', color: '#999' }}>
          <div style={{ fontSize: '16px', marginBottom: '8px' }}>奈奎斯特图</div>
          <div style={{ fontSize: '12px' }}>图表组件正在维护中...</div>
        </div>
      </div>
    </Card>
  );
};

export default NyquistChart;
export type { ImpedancePoint, ChannelData, NyquistChartProps };
