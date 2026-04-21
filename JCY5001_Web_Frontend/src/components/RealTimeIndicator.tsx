import React from 'react';

interface RealTimeIndicatorProps {
  connected: boolean;
  lastUpdate: Date | null;
  error: string | null;
  onRefresh?: () => void;
}

const RealTimeIndicator: React.FC<RealTimeIndicatorProps> = ({ 
  connected, 
  lastUpdate, 
  error, 
  onRefresh 
}) => {
  const getStatusColor = () => {
    if (error) return '#ff4d4f';
    if (connected) return '#52c41a';
    return '#faad14';
  };

  const getStatusText = () => {
    if (error) return '连接错误';
    if (connected) return '实时连接';
    return '连接中...';
  };

  return (
    <div style={{ 
      display: 'flex', 
      alignItems: 'center', 
      gap: '8px',
      fontSize: '12px',
      color: '#666'
    }}>
      <div
        style={{
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          backgroundColor: getStatusColor(),
          animation: connected ? 'pulse 2s infinite' : 'none'
        }}
      />
      <span>{getStatusText()}</span>
      {lastUpdate && (
        <span>
          最后更新: {lastUpdate.toLocaleTimeString()}
        </span>
      )}
      {onRefresh && (
        <button
          onClick={onRefresh}
          style={{
            border: 'none',
            background: 'none',
            color: '#1890ff',
            cursor: 'pointer',
            fontSize: '12px'
          }}
        >
          刷新
        </button>
      )}
    </div>
  );
};

export default RealTimeIndicator;
