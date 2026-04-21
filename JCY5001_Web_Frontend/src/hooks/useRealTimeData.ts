/**
 * 实时数据更新Hook
 * 支持WebSocket和轮询两种方式获取实时数据
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { message } from 'antd';
import { WebSocketManager } from '../services/api';

interface UseRealTimeDataOptions {
  // 更新方式：websocket 或 polling
  method?: 'websocket' | 'polling';
  // 轮询间隔（毫秒）
  pollingInterval?: number;
  // 是否自动开始
  autoStart?: boolean;
  // WebSocket端点
  wsEndpoint?: string;
  // 轮询API函数
  pollingApi?: () => Promise<any>;
  // 数据处理函数
  onDataReceived?: (data: any) => void;
  // 错误处理函数
  onError?: (error: any) => void;
  // 连接状态变化回调
  onConnectionChange?: (connected: boolean) => void;
}

interface UseRealTimeDataReturn {
  // 连接状态
  connected: boolean;
  // 最后更新时间
  lastUpdate: Date | null;
  // 开始实时更新
  start: () => void;
  // 停止实时更新
  stop: () => void;
  // 手动刷新
  refresh: () => void;
  // 错误信息
  error: string | null;
}

export const useRealTimeData = (options: UseRealTimeDataOptions): UseRealTimeDataReturn => {
  const {
    method = 'polling',
    pollingInterval = 30000, // 默认30秒
    autoStart = false,
    wsEndpoint = '/ws',
    pollingApi,
    onDataReceived,
    onError,
    onConnectionChange
  } = options;

  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsManagerRef = useRef<WebSocketManager | null>(null);
  const pollingTimerRef = useRef<NodeJS.Timeout | null>(null);
  const isActiveRef = useRef(false);

  // WebSocket消息处理
  const handleWebSocketMessage = useCallback((data: any) => {
    try {
      setLastUpdate(new Date());
      setError(null);
      
      if (onDataReceived) {
        onDataReceived(data);
      }
    } catch (err: any) {
      console.error('WebSocket数据处理失败:', err);
      setError(err.message || 'WebSocket数据处理失败');
      
      if (onError) {
        onError(err);
      }
    }
  }, [onDataReceived, onError]);

  // WebSocket错误处理
  const handleWebSocketError = useCallback((error: Event) => {
    console.error('WebSocket错误:', error);
    setConnected(false);
    setError('WebSocket连接错误');
    
    if (onConnectionChange) {
      onConnectionChange(false);
    }
    
    if (onError) {
      onError(error);
    }
  }, [onConnectionChange, onError]);

  // 轮询数据获取
  const pollData = useCallback(async () => {
    if (!isActiveRef.current || !pollingApi) {
      return;
    }

    try {
      const data = await pollingApi();
      setLastUpdate(new Date());
      setError(null);
      setConnected(true);

      if (onDataReceived) {
        onDataReceived(data);
      }

      if (onConnectionChange) {
        onConnectionChange(true);
      }
    } catch (err: any) {
      console.error('轮询数据获取失败:', err);
      setError(err.message || '数据获取失败');
      setConnected(false);

      if (onConnectionChange) {
        onConnectionChange(false);
      }

      if (onError) {
        onError(err);
      }
    }
  }, [pollingApi, onDataReceived, onError, onConnectionChange]);

  // 开始实时更新
  const start = useCallback(() => {
    if (isActiveRef.current) {
      return; // 已经在运行
    }

    isActiveRef.current = true;
    setError(null);

    if (method === 'websocket') {
      // 使用WebSocket
      if (!wsManagerRef.current) {
        wsManagerRef.current = new WebSocketManager(wsEndpoint);
      }
      
      wsManagerRef.current.connect(handleWebSocketMessage, handleWebSocketError);
      
      // WebSocket连接成功回调
      setTimeout(() => {
        if (wsManagerRef.current?.ws?.readyState === WebSocket.OPEN) {
          setConnected(true);
          if (onConnectionChange) {
            onConnectionChange(true);
          }
        }
      }, 1000);
      
    } else {
      // 使用轮询
      if (!pollingApi) {
        console.error('轮询模式需要提供pollingApi函数');
        setError('轮询模式配置错误');
        return;
      }
      
      // 立即执行一次
      pollData();
      
      // 设置定时器
      pollingTimerRef.current = setInterval(pollData, pollingInterval);
    }
  }, [method, wsEndpoint, pollingApi, pollingInterval, handleWebSocketMessage, handleWebSocketError, pollData, onConnectionChange]);

  // 停止实时更新
  const stop = useCallback(() => {
    isActiveRef.current = false;
    setConnected(false);
    setError(null);

    if (method === 'websocket') {
      // 断开WebSocket
      if (wsManagerRef.current) {
        wsManagerRef.current.disconnect();
        wsManagerRef.current = null;
      }
    } else {
      // 清除轮询定时器
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    }

    if (onConnectionChange) {
      onConnectionChange(false);
    }
  }, [method, onConnectionChange]);

  // 手动刷新
  const refresh = useCallback(() => {
    if (method === 'websocket') {
      // WebSocket模式下发送刷新请求
      if (wsManagerRef.current) {
        wsManagerRef.current.send({ type: 'refresh' });
      }
    } else {
      // 轮询模式下立即执行一次
      pollData();
    }
  }, [method, pollData]);

  // 自动开始
  useEffect(() => {
    if (autoStart) {
      start();
    }

    // 清理函数
    return () => {
      stop();
    };
  }, [autoStart, start, stop]);

  // 页面可见性变化处理
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        // 页面隐藏时暂停更新
        if (method === 'polling' && pollingTimerRef.current) {
          clearInterval(pollingTimerRef.current);
          pollingTimerRef.current = null;
        }
      } else {
        // 页面显示时恢复更新
        if (method === 'polling' && isActiveRef.current && !pollingTimerRef.current) {
          pollingTimerRef.current = setInterval(pollData, pollingInterval);
          // 立即刷新一次
          pollData();
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [method, pollData, pollingInterval]);

  // 网络状态变化处理
  useEffect(() => {
    const handleOnline = () => {
      if (isActiveRef.current) {
        // 网络恢复时重新开始
        setTimeout(() => {
          if (method === 'websocket') {
            start();
          } else {
            refresh();
          }
        }, 1000);
      }
    };

    const handleOffline = () => {
      setConnected(false);
      setError('网络连接断开');
      
      if (onConnectionChange) {
        onConnectionChange(false);
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [method, start, refresh, onConnectionChange]);

  return {
    connected,
    lastUpdate,
    start,
    stop,
    refresh,
    error
  };
};

// 实时数据状态指示器组件的类型定义
export interface RealTimeIndicatorProps {
  connected: boolean;
  lastUpdate: Date | null;
  error: string | null;
  onRefresh?: () => void;
}

// 注意：实际的RealTimeIndicator组件应该在单独的.tsx文件中实现
