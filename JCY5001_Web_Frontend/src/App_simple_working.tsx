import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';

// 简单的测试组件
const TestLogin = () => (
  <div style={{ padding: '50px', textAlign: 'center' }}>
    <h1>登录页面</h1>
    <p>这是一个简化的登录页面</p>
  </div>
);

const TestDashboard = () => (
  <div style={{ padding: '50px', textAlign: 'center' }}>
    <h1>仪表板</h1>
    <p>这是一个简化的仪表板页面</p>
  </div>
);

// 路由保护组件
const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = localStorage.getItem('token');
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

function App() {
  return (
    <ConfigProvider locale={zhCN}>
      <Router>
        <Routes>
          {/* 登录页面 */}
          <Route path="/login" element={<TestLogin />} />

          {/* 受保护的路由 */}
          <Route path="/" element={
            <ProtectedRoute>
              <TestDashboard />
            </ProtectedRoute>
          }>
            {/* 默认重定向到仪表板 */}
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<TestDashboard />} />
          </Route>

          {/* 404页面 */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </Router>
    </ConfigProvider>
  );
}

export default App;
