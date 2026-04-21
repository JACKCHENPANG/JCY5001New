/**
 * API服务类
 * 统一管理前端与后端的API通信
 */

import { message } from 'antd';
import { getCurrentUser, getToken } from '../utils/auth';

// API基础配置
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5002/api';

// 请求拦截器
const createApiRequest = async (url: string, options: RequestInit = {}) => {
  const token = getToken();
  
  const defaultHeaders: HeadersInit = {
    'Content-Type': 'application/json',
  };
  
  if (token) {
    defaultHeaders['Authorization'] = `Bearer ${token}`;
  }
  
  const config: RequestInit = {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  };
  
  try {
    const response = await fetch(`${API_BASE_URL}${url}`, config);
    
    // 处理认证失败 - 暂时禁用自动重定向，让组件自己处理
    if (response.status === 401) {
      console.warn('API请求401错误，但不自动重定向');
      // message.error('登录已过期，请重新登录');
      // 让调用方处理401错误
      throw new Error('Unauthorized');
    }
    
    // 处理其他错误
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.message || `HTTP ${response.status}: ${response.statusText}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error('API请求失败:', error);
    throw error;
  }
};

// 认证相关API
export const authAPI = {
  // 登录
  login: async (username: string, password: string) => {
    return createApiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  },
  
  // 注册
  register: async (userData: {
    username: string;
    email: string;
    phone: string;
    password: string;
    role: string;
    company: string;
    department?: string;
  }) => {
    return createApiRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },
  
  // 刷新令牌
  refreshToken: async (refreshToken: string) => {
    return createApiRequest('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },
  
  // 退出登录
  logout: async () => {
    return createApiRequest('/auth/logout', {
      method: 'POST',
    });
  },
};

// 仪表板相关API
export const dashboardAPI = {
  // 获取仪表板统计数据
  getStats: async () => {
    return createApiRequest('/web/dashboard/stats');
  },
  
  // 获取最近测试数据
  getRecentTests: async (limit: number = 10) => {
    return createApiRequest(`/web/recent-tests?limit=${limit}`);
  },
};

// 设备管理相关API
export const deviceAPI = {
  // 获取设备列表
  getDevices: async (params: {
    page?: number;
    per_page?: number;
    status?: string;
    search?: string;
  } = {}) => {
    const queryParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        queryParams.append(key, value.toString());
      }
    });
    
    return createApiRequest(`/web/devices/management?${queryParams.toString()}`);
  },
  
  // 获取设备详情
  getDevice: async (deviceId: string) => {
    return createApiRequest(`/devices/${deviceId}`);
  },
  
  // 创建设备
  createDevice: async (deviceData: {
    name: string;
    device_id: string;
    location: string;
    ip_address: string;
    status: string;
    version?: string;
  }) => {
    return createApiRequest('/devices', {
      method: 'POST',
      body: JSON.stringify(deviceData),
    });
  },
  
  // 更新设备
  updateDevice: async (deviceId: string, deviceData: any) => {
    return createApiRequest(`/devices/${deviceId}`, {
      method: 'PUT',
      body: JSON.stringify(deviceData),
    });
  },
  
  // 删除设备
  deleteDevice: async (deviceId: string) => {
    return createApiRequest(`/devices/${deviceId}`, {
      method: 'DELETE',
    });
  },
};

// 数据分析相关API
export const analysisAPI = {
  // 获取测试结果数据
  getTestResults: async (params: {
    page?: number;
    per_page?: number;
    device_id?: string;
    batch_id?: string;
    cell_type?: string;
    channels?: number[];
    start_date?: string;
    end_date?: string;
    result?: string;
    search?: string;
  } = {}) => {
    const queryParams = new URLSearchParams();
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== '') {
        if (key === 'channels' && Array.isArray(value)) {
          value.forEach(channel => queryParams.append('channels', channel.toString()));
        } else {
          queryParams.append(key, value.toString());
        }
      }
    });
    
    return createApiRequest(`/web/analysis/test-results?${queryParams.toString()}`);
  },
  
  // 获取筛选选项
  getFilterOptions: async () => {
    return createApiRequest('/web/analysis/filter-options');
  },
  
  // 获取阻抗明细数据
  getImpedanceDetails: async (testResultId: number) => {
    return createApiRequest(`/web/analysis/impedance-details/${testResultId}`);
  },
  
  // 导出数据
  exportData: async (params: {
    test_result_ids: number[];
    format: 'excel' | 'csv';
    fields?: string[];
  }) => {
    return createApiRequest('/data/export', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
};

// 图表分析相关API
export const chartAPI = {
  // 获取图表数据
  getChartData: async (testResultIds: number[]) => {
    return createApiRequest('/analysis/chart-data', {
      method: 'POST',
      body: JSON.stringify({ test_result_ids: testResultIds }),
    });
  },
  
  // 获取对比分析数据
  getComparisonData: async (params: {
    test_result_ids: number[];
    comparison_type: 'channel' | 'device' | 'batch';
  }) => {
    return createApiRequest('/analysis/comparison', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
};

// 公共API（无需认证）
export const publicAPI = {
  // 获取系统信息
  getSystemInfo: async () => {
    return createApiRequest('/public/system-info');
  },
  
  // 健康检查
  healthCheck: async () => {
    return fetch(`${API_BASE_URL.replace('/api', '')}/health`).then(res => res.json());
  },
  
  // 获取公共测试数据
  getPublicTestResults: async () => {
    return createApiRequest('/public/test-results');
  },
};

// 文件上传API
export const uploadAPI = {
  // 上传文件
  uploadFile: async (file: File, type: string = 'general') => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);
    
    const token = getToken();
    const headers: HeadersInit = {};
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    return fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers,
      body: formData,
    }).then(res => res.json());
  },
  
  // 下载文件
  downloadFile: async (fileId: string) => {
    const token = getToken();
    const headers: HeadersInit = {};
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    return fetch(`${API_BASE_URL}/download/${fileId}`, {
      method: 'GET',
      headers,
    });
  },
};

// WebSocket连接管理
export class WebSocketManager {
  private ws: WebSocket | null = null;
  private url: string;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 5000;
  
  constructor(endpoint: string = '/ws') {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    this.url = `${wsProtocol}//${wsHost}${endpoint}`;
  }
  
  connect(onMessage?: (data: any) => void, onError?: (error: Event) => void) {
    try {
      this.ws = new WebSocket(this.url);
      
      this.ws.onopen = () => {
        console.log('WebSocket连接已建立');
        this.reconnectAttempts = 0;
        
        // 发送认证信息
        const token = getToken();
        if (token) {
          this.send({ type: 'auth', token });
        }
      };
      
      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (onMessage) {
            onMessage(data);
          }
        } catch (error) {
          console.error('WebSocket消息解析失败:', error);
        }
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket错误:', error);
        if (onError) {
          onError(error);
        }
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket连接已关闭');
        this.attemptReconnect(onMessage, onError);
      };
      
    } catch (error) {
      console.error('WebSocket连接失败:', error);
    }
  }
  
  private attemptReconnect(onMessage?: (data: any) => void, onError?: (error: Event) => void) {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`尝试重连WebSocket (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      
      setTimeout(() => {
        this.connect(onMessage, onError);
      }, this.reconnectInterval);
    } else {
      console.error('WebSocket重连失败，已达到最大重试次数');
    }
  }
  
  send(data: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    } else {
      console.warn('WebSocket未连接，无法发送消息');
    }
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// 默认导出API对象
export default {
  auth: authAPI,
  dashboard: dashboardAPI,
  device: deviceAPI,
  analysis: analysisAPI,
  chart: chartAPI,
  public: publicAPI,
  upload: uploadAPI,
  WebSocketManager,
};
