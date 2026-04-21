/**
 * 用户认证和权限管理工具
 */

export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user' | 'operator' | 'viewer';
  company: string;
  department?: string;
  loginTime: string;
  permissions: string[];
}

export interface LoginResponse {
  user: User;
  token: string;
  refreshToken: string;
  expiresIn: number;
}

// 角色权限配置
export const ROLE_PERMISSIONS = {
  admin: [
    'device:read',
    'device:write',
    'device:delete',
    'data:read',
    'data:write',
    'data:export',
    'user:read',
    'user:write',
    'user:delete',
    'system:read',
    'system:write'
  ],
  operator: [
    'device:read',
    'device:write',
    'data:read',
    'data:write',
    'data:export'
  ],
  user: [
    'device:read',
    'data:read',
    'data:export'
  ],
  viewer: [
    'device:read',
    'data:read'
  ]
};

/**
 * 获取当前用户信息
 */
export const getCurrentUser = (): User | null => {
  try {
    const userStr = localStorage.getItem('user');
    if (!userStr) return null;
    
    const user = JSON.parse(userStr);
    
    // 添加权限信息
    user.permissions = ROLE_PERMISSIONS[user.role as keyof typeof ROLE_PERMISSIONS] || [];
    
    return user;
  } catch (error) {
    console.error('获取用户信息失败:', error);
    return null;
  }
};

/**
 * 获取认证令牌
 */
export const getToken = (): string | null => {
  return localStorage.getItem('token');
};

/**
 * 检查用户是否已登录
 */
export const isAuthenticated = (): boolean => {
  const token = getToken();
  const user = getCurrentUser();
  return !!(token && user);
};

/**
 * 检查用户是否有指定权限
 */
export const hasPermission = (permission: string): boolean => {
  const user = getCurrentUser();
  if (!user) return false;
  
  return user.permissions.includes(permission);
};

/**
 * 检查用户是否有指定角色
 */
export const hasRole = (role: string): boolean => {
  const user = getCurrentUser();
  if (!user) return false;
  
  return user.role === role;
};

/**
 * 检查用户是否是管理员
 */
export const isAdmin = (): boolean => {
  return hasRole('admin');
};

/**
 * 登录
 */
export const login = async (username: string, password: string): Promise<LoginResponse> => {
  try {
    // 这里应该调用实际的登录API
    // const response = await fetch('/api/auth/login', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ username, password })
    // });
    
    // 模拟登录API调用
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // 模拟登录响应
    const mockResponse: LoginResponse = {
      user: {
        id: '1',
        username,
        email: `${username}@example.com`,
        role: username === 'admin' ? 'admin' : 'user',
        company: '示例公司',
        department: '技术部',
        loginTime: new Date().toISOString(),
        permissions: ROLE_PERMISSIONS[username === 'admin' ? 'admin' : 'user']
      },
      token: 'mock-jwt-token-' + Date.now(),
      refreshToken: 'mock-refresh-token-' + Date.now(),
      expiresIn: 3600
    };
    
    // 保存到本地存储
    localStorage.setItem('user', JSON.stringify(mockResponse.user));
    localStorage.setItem('token', mockResponse.token);
    localStorage.setItem('refreshToken', mockResponse.refreshToken);
    
    return mockResponse;
    
  } catch (error) {
    console.error('登录失败:', error);
    throw new Error('登录失败，请检查用户名和密码');
  }
};

/**
 * 注册
 */
export const register = async (userData: {
  username: string;
  email?: string;
  password: string;
  company?: string;
}): Promise<{ success: boolean; message: string }> => {
  try {
    // 调用实际的注册API
    const response = await fetch('http://localhost:5002/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.message || '注册失败');
    }

    return {
      success: true,
      message: data.message || '注册成功'
    };

  } catch (error: any) {
    console.error('注册失败:', error);
    throw new Error(error.message || '注册失败，请稍后重试');
  }
};

/**
 * 退出登录
 */
export const logout = (): void => {
  localStorage.removeItem('user');
  localStorage.removeItem('token');
  localStorage.removeItem('refreshToken');
  
  // 可以在这里调用后端的登出API
  // fetch('/api/auth/logout', { method: 'POST' });
};

/**
 * 刷新令牌
 */
export const refreshToken = async (): Promise<string | null> => {
  try {
    const refreshTokenValue = localStorage.getItem('refreshToken');
    if (!refreshTokenValue) return null;
    
    // 这里应该调用实际的刷新令牌API
    // const response = await fetch('/api/auth/refresh', {
    //   method: 'POST',
    //   headers: { 'Content-Type': 'application/json' },
    //   body: JSON.stringify({ refreshToken: refreshTokenValue })
    // });
    
    // 模拟刷新令牌
    const newToken = 'mock-jwt-token-refreshed-' + Date.now();
    localStorage.setItem('token', newToken);
    
    return newToken;
    
  } catch (error) {
    console.error('刷新令牌失败:', error);
    logout(); // 刷新失败时退出登录
    return null;
  }
};

/**
 * 检查令牌是否即将过期
 */
export const isTokenExpiringSoon = (): boolean => {
  // 这里应该解析JWT令牌的过期时间
  // 简化实现：假设令牌1小时后过期，提前10分钟刷新
  const user = getCurrentUser();
  if (!user) return false;
  
  const loginTime = new Date(user.loginTime).getTime();
  const now = Date.now();
  const expireTime = loginTime + 60 * 60 * 1000; // 1小时
  const refreshThreshold = 10 * 60 * 1000; // 10分钟
  
  return (expireTime - now) < refreshThreshold;
};

/**
 * 权限检查装饰器（用于组件）
 */
export const withPermission = (permission: string) => {
  return (WrappedComponent: any) => {
    return (props: any) => {
      if (!hasPermission(permission)) {
        return null; // 简化处理，避免JSX语法问题
      }

      return WrappedComponent(props);
    };
  };
};

/**
 * 角色检查装饰器（用于组件）
 */
export const withRole = (role: string) => {
  return (WrappedComponent: any) => {
    return (props: any) => {
      if (!hasRole(role)) {
        return null; // 简化处理，避免JSX语法问题
      }

      return WrappedComponent(props);
    };
  };
};
