# 电池阻抗测试系统云端服务部署指南

## 快速开始

### 1. 环境要求
- Python 3.8+
- pip (Python包管理器)
- Git (可选)

### 2. 安装步骤

#### 步骤1: 下载项目
```bash
# 如果有Git
git clone <repository-url>
cd battery_impedance_api

# 或者直接下载解压项目文件夹
```

#### 步骤2: 创建虚拟环境
```bash
python -m venv venv

# Linux/Mac激活
source venv/bin/activate

# Windows激活
venv\Scripts\activate
```

#### 步骤3: 安装依赖
```bash
pip install -r requirements.txt
```

#### 步骤4: 配置环境变量
```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，设置必要的配置
```

#### 步骤5: 启动服务
```bash
python src/main.py
```

### 3. 访问服务
- API服务: http://localhost:5002
- API文档: http://localhost:5002/api
- 健康检查: http://localhost:5002/health

### 4. 默认账号
- 用户名: admin
- 密码: Admin123!

## 生产部署

### 使用Gunicorn
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5002 src.main:app
```

### 使用Docker
```bash
# 构建镜像
docker build -t battery-impedance-api .

# 运行容器
docker run -p 5002:5002 battery-impedance-api
```

## 故障排除

### 常见问题
1. **端口被占用**: 修改.env中的端口配置
2. **依赖安装失败**: 确保Python版本正确，使用虚拟环境
3. **数据库连接失败**: 检查数据库配置和权限

### 技术支持
- 邮箱: support@jcytest.com
- 文档: 查看项目文档文件夹

