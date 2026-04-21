import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Input, Card, message, Space } from 'antd';
import { useAuth } from '../contexts/AuthContext';

const TestLoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { login: authLogin, logout, isAuthenticated } = useAuth();

  const handleTestLogin = async () => {
    setLoading(true);
    
    try {
      // 直接设置token，不调用API
      const mockToken = 'test-token-' + Date.now();
      const mockUser = {
        id: '1',
        username: 'admin',
        email: 'admin@example.com',
        role: 'admin',
        company: '示例公司',
        department: '技术部',
        loginTime: new Date().toISOString(),
        permissions: ['device:read', 'device:write', 'data:read', 'data:export', 'user:manage']
      };

      // 使用AuthContext登录
      authLogin(mockToken, mockUser);

      message.success('登录成功！');

      // 跳转到仪表板
      navigate('/dashboard');
      
    } catch (error: any) {
      console.error('登录失败:', error);
      message.error('登录失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleClearStorage = () => {
    logout();
    message.info('已清除本地存储');
  };

  const checkStorage = () => {
    const token = localStorage.getItem('token');
    const user = localStorage.getItem('user');
    console.log('Token:', token);
    console.log('User:', user);
    message.info(`Token: ${token ? '存在' : '不存在'}`);
  };

  return (
    <div style={{ 
      minHeight: '100vh', 
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      background: '#f0f2f5'
    }}>
      <Card title="登录测试页面" style={{ width: 400 }}>
        <div style={{ marginBottom: 16 }}>
          认证状态: {isAuthenticated ? '已登录' : '未登录'}
        </div>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Button 
            type="primary" 
            loading={loading} 
            onClick={handleTestLogin}
            block
          >
            测试登录
          </Button>
          
          <Button onClick={handleClearStorage} block>
            清除存储
          </Button>
          
          <Button onClick={checkStorage} block>
            检查存储
          </Button>
          
          <Button onClick={() => navigate('/dashboard')} block>
            直接跳转仪表板
          </Button>
        </Space>
      </Card>
    </div>
  );
};

export default TestLoginPage;
