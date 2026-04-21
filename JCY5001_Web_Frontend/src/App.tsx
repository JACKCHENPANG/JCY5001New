import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AuthProvider, useAuth } from './contexts/AuthContext';

// 导入页面组件
import LoginPage from './pages/LoginPage';
import TestLoginPage from './pages/TestLoginPage';
import RegisterPage from './pages/RegisterPage';
import DashboardPage from './pages/DashboardPage';
import DeviceManagePage from './pages/DeviceManagePage';
import DataAnalysisPageOptimized from './pages/DataAnalysisPageOptimized';
import ChartAnalysisPage from './pages/ChartAnalysisPage';
import UploadMonitorPage from './pages/UploadMonitorPage';
import MainLayout from './layouts/MainLayout';
import './App.css';

// 智能登录页面包装器
const LoginPageWrapper: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  // 如果正在加载，显示加载状态
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '16px'
      }}>
        正在加载...
      </div>
    );
  }

  // 如果已经认证，重定向到仪表板
  if (isAuthenticated) {
    console.log('LoginPageWrapper: 已认证，重定向到仪表板');
    return <Navigate to="/dashboard" replace />;
  }

  // 否则显示登录页面
  return <LoginPage />;
};

// 根路径重定向组件
const RootRedirect: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  // 如果正在加载，显示加载状态
  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '16px'
      }}>
        正在加载...
      </div>
    );
  }

  // 根据认证状态重定向
  return <Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />;
};

// 路由保护组件
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  console.log('ProtectedRoute: 检查认证状态', { isAuthenticated, isLoading });

  // 如果正在加载，显示加载状态
  if (isLoading) {
    console.log('ProtectedRoute: 正在加载认证状态...');
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        fontSize: '16px'
      }}>
        正在加载...
      </div>
    );
  }

  // 如果没有认证，重定向到登录页面
  if (!isAuthenticated) {
    console.log('ProtectedRoute: 未认证，重定向到登录页面');
    return <Navigate to="/login" replace />;
  }

  console.log('ProtectedRoute: 已认证，渲染子组件');
  return <>{children}</>;
};

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <AuthProvider>
        <Router>
        <Routes>
          {/* 登录页面 - 添加智能重定向 */}
          <Route path="/login" element={<LoginPageWrapper />} />

          {/* 测试登录页面 */}
          <Route path="/test-login" element={<TestLoginPage />} />

          {/* 注册页面 */}
          <Route path="/register" element={<RegisterPage />} />

          {/* 根路径重定向 */}
          <Route path="/" element={<RootRedirect />} />

          {/* 受保护的路由 - 平铺结构，避免嵌套路由问题 */}
          <Route path="/dashboard" element={
            <ProtectedRoute>
              <MainLayout>
                <DashboardPage />
              </MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/devices" element={
            <ProtectedRoute>
              <MainLayout>
                <DeviceManagePage />
              </MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/analysis" element={
            <ProtectedRoute>
              <MainLayout>
                <DataAnalysisPageOptimized />
              </MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/charts" element={
            <ProtectedRoute>
              <MainLayout>
                <ChartAnalysisPage />
              </MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/upload-monitor" element={
            <ProtectedRoute>
              <MainLayout>
                <UploadMonitorPage />
              </MainLayout>
            </ProtectedRoute>
          } />

          <Route path="/settings" element={
            <ProtectedRoute>
              <MainLayout>
                <div>系统设置页面开发中...</div>
              </MainLayout>
            </ProtectedRoute>
          } />

          {/* 404页面 */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
        </Router>
      </AuthProvider>
    </ConfigProvider>
  );
}

export default App;
