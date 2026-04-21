import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Form,
  Input,
  Button,
  Card,
  Typography,
  Space,
  message,
  Divider,
  Checkbox
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  DatabaseOutlined
} from '@ant-design/icons';
import { authAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const { Title, Text } = Typography;

interface LoginForm {
  username: string;
  password: string;
  remember: boolean;
}

const LoginPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();
  const { login } = useAuth();

  // 处理登录
  const handleLogin = async (values: LoginForm) => {
    setLoading(true);

    try {
      console.log('开始登录:', values.username);

      // 调用后端API进行登录
      const response = await authAPI.login(values.username, values.password);

      console.log('登录响应:', response);

      // 检查响应格式
      if (response.access_token && response.user) {
        // 使用AuthContext的login方法保存认证信息
        login(response.access_token, {
          id: response.user.id.toString(),
          username: response.user.username,
          email: response.user.email,
          role: response.user.role || 'user',
          company: response.user.company || '',
          department: response.user.department || '',
          loginTime: new Date().toISOString(),
          permissions: [] // 权限将在后续处理
        });

        message.success(`欢迎回来，${response.user.username}！`);

        // 跳转到仪表板
        navigate('/dashboard');
      } else {
        throw new Error('登录响应格式错误');
      }

    } catch (error: any) {
      console.error('登录失败:', error);
      message.error(error.message || '登录失败，请检查用户名和密码');
    } finally {
      setLoading(false);
    }
  };

  // 处理注册
  const handleRegister = () => {
    navigate('/register');
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <Card
        style={{
          width: '100%',
          maxWidth: 400,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
          borderRadius: '12px'
        }}
        bodyStyle={{ padding: '40px' }}
      >
        {/* Logo和标题 */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <Space direction="vertical" size="small">
            <DatabaseOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
            <Title level={2} style={{ margin: 0, color: '#1890ff' }}>
              JCY5001AS
            </Title>
            <Text type="secondary">电池阻抗测试系统</Text>
          </Space>
        </div>

        {/* 登录表单 */}
        <Form
          form={form}
          name="login"
          onFinish={handleLogin}
          autoComplete="off"
          size="large"
          initialValues={{
            username: 'admin',
            password: 'Admin123!',
            remember: true
          }}
        >
          <Form.Item
            name="username"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' }
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="用户名"
              autoComplete="username"
            />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' }
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="密码"
              autoComplete="current-password"
            />
          </Form.Item>

          <Form.Item name="remember" valuePropName="checked">
            <Checkbox>记住我</Checkbox>
          </Form.Item>

          <Form.Item style={{ marginBottom: '16px' }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{ height: '44px' }}
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <Divider>或</Divider>

        {/* 注册按钮 */}
        <Link to="/register">
          <Button
            type="default"
            block
            style={{ height: '44px' }}
          >
            注册新账户
          </Button>
        </Link>

        {/* 底部信息 */}
        <div style={{ textAlign: 'center', marginTop: '24px' }}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            © 2025 JCY5001AS 电池阻抗测试系统
          </Text>
        </div>

        {/* 测试账户提示 */}
        <div style={{ 
          marginTop: '16px', 
          padding: '12px', 
          background: '#f6f8fa', 
          borderRadius: '6px',
          border: '1px solid #e1e4e8'
        }}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            <strong>测试账户：</strong><br />
            管理员：admin / admin123<br />
            普通用户：user / user123
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default LoginPage;
