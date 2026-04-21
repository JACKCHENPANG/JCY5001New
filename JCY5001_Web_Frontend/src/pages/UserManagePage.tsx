import React, { useState, useEffect } from 'react';
import {
  Card,
  Table,
  Button,
  Space,
  Input,
  Select,
  Modal,
  Form,
  message,
  Typography,
  Row,
  Col,
  Tag,
  Tooltip,
  Popconfirm
} from 'antd';
import {
  UserOutlined,
  SearchOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  EyeOutlined,
  MailOutlined,
  KeyOutlined
} from '@ant-design/icons';
import { useAuth } from '../contexts/AuthContext';

const { Title, Text } = Typography;
const { Option } = Select;

interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user';
  status: 'active' | 'inactive';
  createdAt: string;
  lastLogin: string;
  deviceCount: number;
}

const UserManagePage: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [users, setUsers] = useState<User[]>([]);
  const [filteredUsers, setFilteredUsers] = useState<User[]>([]);
  const [searchText, setSearchText] = useState('');
  const [roleFilter, setRoleFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [form] = Form.useForm();

  // 获取用户列表
  const fetchUsers = async () => {
    setLoading(true);
    try {
      // 模拟API调用
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const mockUsers: User[] = [
        {
          id: '1',
          username: 'admin',
          email: 'admin@example.com',
          role: 'admin',
          status: 'active',
          createdAt: '2025-01-01 10:00:00',
          lastLogin: '2025-07-08 09:30:00',
          deviceCount: 1
        },
        {
          id: '2',
          username: 'user',
          email: 'user@example.com',
          role: 'user',
          status: 'active',
          createdAt: '2025-02-15 14:20:00',
          lastLogin: '2025-07-07 16:45:00',
          deviceCount: 1
        },
        {
          id: '4',
          username: 'jack',
          email: 'jack@example.com',
          role: 'user',
          status: 'active',
          createdAt: '2025-03-10 11:15:00',
          lastLogin: '2025-07-08 08:20:00',
          deviceCount: 1
        },
        {
          id: '5',
          username: 'test1',
          email: 'test1@example.com',
          role: 'user',
          status: 'inactive',
          createdAt: '2025-04-05 09:30:00',
          lastLogin: '2025-06-20 14:10:00',
          deviceCount: 0
        },
        {
          id: '6',
          username: 'test2',
          email: 'test2@example.com',
          role: 'user',
          status: 'active',
          createdAt: '2025-05-12 16:45:00',
          lastLogin: '2025-07-06 10:30:00',
          deviceCount: 0
        }
      ];
      
      setUsers(mockUsers);
      setFilteredUsers(mockUsers);
    } catch (error) {
      console.error('获取用户列表失败:', error);
      message.error('获取用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  // 搜索和过滤
  useEffect(() => {
    let filtered = users;

    // 搜索过滤
    if (searchText) {
      filtered = filtered.filter(user =>
        user.username.toLowerCase().includes(searchText.toLowerCase()) ||
        user.email.toLowerCase().includes(searchText.toLowerCase())
      );
    }

    // 角色过滤
    if (roleFilter !== 'all') {
      filtered = filtered.filter(user => user.role === roleFilter);
    }

    // 状态过滤
    if (statusFilter !== 'all') {
      filtered = filtered.filter(user => user.status === statusFilter);
    }

    setFilteredUsers(filtered);
  }, [users, searchText, roleFilter, statusFilter]);

  // 表格列定义
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      width: 120,
      render: (text: string) => (
        <div>
          <UserOutlined style={{ marginRight: 4, color: '#1890ff' }} />
          <Text strong>{text}</Text>
        </div>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      width: 200,
      render: (text: string) => (
        <div>
          <MailOutlined style={{ marginRight: 4, color: '#52c41a' }} />
          <Text>{text}</Text>
        </div>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 100,
      render: (role: string) => (
        <Tag color={role === 'admin' ? 'red' : 'blue'}>
          {role === 'admin' ? '管理员' : '普通用户'}
        </Tag>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={status === 'active' ? 'green' : 'default'}>
          {status === 'active' ? '活跃' : '禁用'}
        </Tag>
      ),
    },
    {
      title: '设备数量',
      dataIndex: 'deviceCount',
      key: 'deviceCount',
      width: 100,
      render: (count: number) => (
        <Text>{count} 台</Text>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'createdAt',
      key: 'createdAt',
      width: 150,
    },
    {
      title: '最后登录',
      dataIndex: 'lastLogin',
      key: 'lastLogin',
      width: 150,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record: User) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => handleViewUser(record)}
            />
          </Tooltip>
          <Tooltip title="编辑用户">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => handleEditUser(record)}
            />
          </Tooltip>
          <Tooltip title="重置密码">
            <Button
              type="text"
              icon={<KeyOutlined />}
              onClick={() => handleResetPassword(record)}
            />
          </Tooltip>
          {record.id !== user?.id && (
            <Popconfirm
              title="确定要删除这个用户吗？"
              description="删除后无法恢复，请谨慎操作。"
              onConfirm={() => handleDeleteUser(record)}
              okText="删除"
              cancelText="取消"
              okType="danger"
            >
              <Tooltip title="删除用户">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined />}
                />
              </Tooltip>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  // 处理函数
  const handleViewUser = (user: User) => {
    Modal.info({
      title: '用户详情',
      width: 600,
      content: (
        <div style={{ marginTop: '16px' }}>
          <Row gutter={[16, 16]}>
            <Col span={8}><Text strong>用户ID:</Text></Col>
            <Col span={16}>{user.id}</Col>
            <Col span={8}><Text strong>用户名:</Text></Col>
            <Col span={16}>{user.username}</Col>
            <Col span={8}><Text strong>邮箱:</Text></Col>
            <Col span={16}>{user.email}</Col>
            <Col span={8}><Text strong>角色:</Text></Col>
            <Col span={16}>
              <Tag color={user.role === 'admin' ? 'red' : 'blue'}>
                {user.role === 'admin' ? '管理员' : '普通用户'}
              </Tag>
            </Col>
            <Col span={8}><Text strong>状态:</Text></Col>
            <Col span={16}>
              <Tag color={user.status === 'active' ? 'green' : 'default'}>
                {user.status === 'active' ? '活跃' : '禁用'}
              </Tag>
            </Col>
            <Col span={8}><Text strong>绑定设备:</Text></Col>
            <Col span={16}>{user.deviceCount} 台</Col>
            <Col span={8}><Text strong>创建时间:</Text></Col>
            <Col span={16}>{user.createdAt}</Col>
            <Col span={8}><Text strong>最后登录:</Text></Col>
            <Col span={16}>{user.lastLogin}</Col>
          </Row>
        </div>
      ),
    });
  };

  const handleAddUser = () => {
    setEditingUser(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEditUser = (user: User) => {
    setEditingUser(user);
    form.setFieldsValue(user);
    setModalVisible(true);
  };

  const handleResetPassword = (user: User) => {
    Modal.confirm({
      title: '重置密码',
      content: `确定要重置用户 "${user.username}" 的密码吗？新密码将发送到用户邮箱。`,
      okText: '重置',
      cancelText: '取消',
      onOk: async () => {
        try {
          await new Promise(resolve => setTimeout(resolve, 1000));
          message.success('密码重置成功，新密码已发送到用户邮箱');
        } catch (error) {
          message.error('密码重置失败');
        }
      }
    });
  };

  const handleDeleteUser = async (user: User) => {
    try {
      await new Promise(resolve => setTimeout(resolve, 1000));
      const updatedUsers = users.filter(u => u.id !== user.id);
      setUsers(updatedUsers);
      setFilteredUsers(updatedUsers);
      message.success('用户删除成功');
    } catch (error) {
      message.error('用户删除失败');
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: '24px' }}>
          <Title level={4} style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
            <UserOutlined style={{ marginRight: '8px', color: '#1890ff' }} />
            用户管理
          </Title>
          <Text type="secondary">管理系统用户账号，维护用户权限和状态</Text>
        </div>

        {/* 搜索和过滤 */}
        <Row gutter={[16, 16]} style={{ marginBottom: '16px' }}>
          <Col xs={24} sm={12} md={8} lg={6}>
            <Input
              placeholder="搜索用户名或邮箱"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
            <Select
              placeholder="角色"
              value={roleFilter}
              onChange={setRoleFilter}
              style={{ width: '100%' }}
            >
              <Option value="all">全部角色</Option>
              <Option value="admin">管理员</Option>
              <Option value="user">普通用户</Option>
            </Select>
          </Col>
          <Col xs={12} sm={6} md={4} lg={3}>
            <Select
              placeholder="状态"
              value={statusFilter}
              onChange={setStatusFilter}
              style={{ width: '100%' }}
            >
              <Option value="all">全部状态</Option>
              <Option value="active">活跃</Option>
              <Option value="inactive">禁用</Option>
            </Select>
          </Col>
          <Col xs={24} sm={12} md={8} lg={12}>
            <Space style={{ float: 'right' }}>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchUsers}
                loading={loading}
              >
                刷新
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAddUser}
              >
                添加用户
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 用户表格 */}
        <Table
          columns={columns}
          dataSource={filteredUsers}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 个用户`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>
    </div>
  );
};

export default UserManagePage;
