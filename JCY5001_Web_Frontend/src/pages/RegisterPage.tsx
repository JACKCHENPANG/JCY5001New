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
  Checkbox
} from 'antd';
import {
  UserOutlined,
  LockOutlined,
  MailOutlined,
  DatabaseOutlined,
  ArrowLeftOutlined
} from '@ant-design/icons';
import { register } from '../utils/auth';

const { Title, Text } = Typography;

interface RegisterForm {
  username: string;
  email?: string;
  password: string;
  confirmPassword: string;
  company?: string;
  agreement: boolean;
}

const RegisterPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  const navigate = useNavigate();

  // 处理注册
  const handleRegister = async (values: RegisterForm) => {
    setLoading(true);

    try {
      // 使用认证工具进行注册
      const response = await register({
        username: values.username,
        email: values.email || '',
        password: values.password,
        company: values.company || ''
      });

      message.success('注册成功！请使用新账户登录');

      // 跳转到登录页
      navigate('/login');

    } catch (error: any) {
      console.error('注册失败:', error);
      message.error(error.message || '注册失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  // 返回登录页
  const handleBackToLogin = () => {
    navigate('/login');
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
          maxWidth: 500,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
          borderRadius: '12px'
        }}
        bodyStyle={{ padding: '40px' }}
      >
        {/* 返回按钮 */}
        <div style={{ marginBottom: '16px' }}>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={handleBackToLogin}
          >
            返回登录
          </Button>
        </div>

        {/* Logo和标题 */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <Space direction="vertical" size="small">
            <DatabaseOutlined style={{ fontSize: '48px', color: '#1890ff' }} />
            <Title level={2} style={{ margin: 0, color: '#1890ff' }}>
              用户注册
            </Title>
            <Text type="secondary">创建JCY5001AS系统账户</Text>
          </Space>
        </div>

        {/* 注册表单 */}
        <Form
          form={form}
          name="register"
          onFinish={handleRegister}
          autoComplete="off"
          size="large"
          layout="vertical"
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' },
              { max: 20, message: '用户名最多20个字符' },
              { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线' }
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="请输入用户名"
            />
          </Form.Item>

          <Form.Item
            name="email"
            label="邮箱地址（选填）"
            rules={[
              { type: 'email', message: '请输入有效的邮箱地址' }
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="请输入邮箱地址（选填）"
            />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' },
              { max: 20, message: '密码最多20个字符' }
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="请输入密码"
            />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label="确认密码"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="请再次输入密码"
            />
          </Form.Item>

          <Form.Item
            name="company"
            label="公司名称（选填）"
          >
            <Input placeholder="请输入公司名称（选填）" />
          </Form.Item>

          <Form.Item
            name="agreement"
            valuePropName="checked"
            rules={[
              { 
                validator: (_, value) =>
                  value ? Promise.resolve() : Promise.reject(new Error('请同意用户协议'))
              }
            ]}
          >
            <Checkbox>
              我已阅读并同意 <a href="#" onClick={(e) => e.preventDefault()}>《用户协议》</a> 和 <a href="#" onClick={(e) => e.preventDefault()}>《隐私政策》</a>
            </Checkbox>
          </Form.Item>

          <Form.Item style={{ marginBottom: '16px' }}>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
              style={{ height: '44px' }}
            >
              注册账户
            </Button>
          </Form.Item>
        </Form>

        {/* 登录链接 */}
        <div style={{ textAlign: 'center', marginTop: '16px' }}>
          <Text type="secondary">
            已有账户？ <Link to="/login">立即登录</Link>
          </Text>
        </div>

        {/* 底部信息 */}
        <div style={{ textAlign: 'center', marginTop: '24px' }}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            © 2025 JCY5001AS 电池阻抗测试系统
          </Text>
        </div>
      </Card>
    </div>
  );
};

export default RegisterPage;
