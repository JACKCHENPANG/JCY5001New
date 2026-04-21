import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Layout,
  Menu,
  Avatar,
  Dropdown,
  Typography,
  Space,
  Button,
  theme,
  message
} from 'antd';
import {
  DashboardOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  CloudUploadOutlined,
  SettingOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined
} from '@ant-design/icons';
import { hasPermission } from '../utils/auth';
import { useAuth } from '../contexts/AuthContext';

const { Header, Sider, Content } = Layout;
const { Title } = Typography;

interface MainLayoutProps {
  children?: React.ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuVisible, setMobileMenuVisible] = useState(false);
  const [isMobile, setIsMobile] = useState(window.innerWidth <= 768);
  const { user: currentUser, logout: authLogout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const {
    token: { colorBgContainer },
  } = theme.useToken();

  // 监听窗口大小变化
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth <= 768;
      setIsMobile(mobile);
      if (!mobile) {
        setMobileMenuVisible(false);
      }
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  // 用户信息现在从AuthContext获取，不需要手动更新

  // 菜单项配置（基于权限过滤）
  const menuItems = [
    {
      key: '/dashboard',
      icon: <DashboardOutlined />,
      label: '仪表板',
    },
    {
      key: '/devices',
      icon: <DatabaseOutlined />,
      label: '设备管理',
      permission: 'device:read'
    },
    {
      key: '/analysis',
      icon: <BarChartOutlined />,
      label: '数据分析',
      permission: 'data:read'
    },
    {
      key: '/upload-monitor',
      icon: <CloudUploadOutlined />,
      label: '上传监控',
      permission: 'data:read'
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: '系统设置',
      permission: 'system:read'
    },
  ].filter(item => !item.permission || hasPermission(item.permission));

  // 用户下拉菜单
  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人资料',
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
    },
  ];

  // 处理菜单点击
  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key);
    // 移动端点击菜单后关闭菜单
    if (isMobile) {
      setMobileMenuVisible(false);
    }
  };

  // 切换移动端菜单
  const toggleMobileMenu = () => {
    if (isMobile) {
      setMobileMenuVisible(!mobileMenuVisible);
    } else {
      setCollapsed(!collapsed);
    }
  };

  // 处理用户菜单点击
  const handleUserMenuClick = ({ key }: { key: string }) => {
    if (key === 'logout') {
      // 使用AuthContext退出登录
      authLogout();
      message.success('已退出登录');
      navigate('/login');
    } else if (key === 'profile') {
      // 跳转到个人资料页
      navigate('/profile');
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* 移动端遮罩层 */}
      {isMobile && mobileMenuVisible && (
        <div
          className="mobile-overlay"
          onClick={() => setMobileMenuVisible(false)}
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 999
          }}
        />
      )}

      {/* 侧边栏 */}
      <Sider
        trigger={null}
        collapsible
        collapsed={isMobile ? false : collapsed}
        width={isMobile ? 280 : 200}
        style={{
          background: colorBgContainer,
          boxShadow: '2px 0 8px 0 rgba(29,35,41,.05)',
          position: isMobile ? 'fixed' : 'relative',
          left: isMobile ? (mobileMenuVisible ? 0 : -280) : 'auto',
          top: 0,
          bottom: 0,
          zIndex: 1000,
          transition: isMobile ? 'left 0.3s ease' : 'none'
        }}
      >
        {/* Logo区域 */}
        <div style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: (isMobile || !collapsed) ? 'flex-start' : 'center',
          padding: (isMobile || !collapsed) ? '0 24px' : 0,
          borderBottom: '1px solid #f0f0f0'
        }}>
          <DatabaseOutlined style={{ fontSize: '24px', color: '#1890ff' }} />
          {(isMobile || !collapsed) && (
            <Title level={4} style={{ margin: '0 0 0 12px', color: '#1890ff' }}>
              JCY5001AS
            </Title>
          )}
        </div>

        {/* 导航菜单 */}
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0, marginTop: 16 }}
        />
      </Sider>

      {/* 主内容区域 */}
      <Layout style={{ marginLeft: isMobile ? 0 : 'auto' }}>
        {/* 顶部导航栏 */}
        <Header style={{
          padding: isMobile ? '0 16px' : '0 24px',
          background: colorBgContainer,
          borderBottom: '1px solid #f0f0f0',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: isMobile ? 'fixed' : 'relative',
          top: 0,
          left: 0,
          right: 0,
          zIndex: 100
        }}>
          {/* 左侧：折叠按钮 */}
          <Button
            type="text"
            icon={isMobile ? <MenuUnfoldOutlined /> : (collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />)}
            onClick={toggleMobileMenu}
            style={{
              fontSize: '16px',
              width: 64,
              height: 64,
            }}
          />

          {/* 右侧：用户信息 */}
          <Space>
            <span style={{ color: '#666' }}>欢迎回来，</span>
            <Dropdown
              menu={{
                items: userMenuItems,
                onClick: handleUserMenuClick,
              }}
              placement="bottomRight"
            >
              <Space style={{ cursor: 'pointer' }}>
                <Avatar size="small" icon={<UserOutlined />} />
                <span>{currentUser?.username || '用户'}</span>
              </Space>
            </Dropdown>
          </Space>
        </Header>

        {/* 页面内容 */}
        <Content style={{
          margin: isMobile ? '16px 8px' : '24px',
          padding: isMobile ? '16px' : '24px',
          background: colorBgContainer,
          borderRadius: '8px',
          minHeight: isMobile ? 'calc(100vh - 80px)' : 'calc(100vh - 112px)',
          marginTop: isMobile ? '64px' : '0',
          overflow: 'auto'
        }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
