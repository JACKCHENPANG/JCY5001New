#!/bin/bash

# JCY5001AS Web平台部署脚本
# 作者: Jack
# 日期: 2025-07-06

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装，请先安装Docker Compose"
        exit 1
    fi
    
    # 检查Git
    if ! command -v git &> /dev/null; then
        log_error "Git未安装，请先安装Git"
        exit 1
    fi
    
    log_success "系统依赖检查完成"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p logs/nginx
    mkdir -p logs/backend
    mkdir -p uploads
    mkdir -p nginx/ssl
    mkdir -p monitoring/grafana/dashboards
    mkdir -p monitoring/grafana/datasources
    mkdir -p backups
    
    log_success "目录创建完成"
}

# 生成SSL证书
generate_ssl_cert() {
    log_info "生成SSL证书..."
    
    if [ ! -f "nginx/ssl/cert.pem" ]; then
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=CN/ST=Beijing/L=Beijing/O=JCY5001AS/CN=localhost"
        
        log_success "SSL证书生成完成"
    else
        log_info "SSL证书已存在，跳过生成"
    fi
}

# 设置环境变量
setup_environment() {
    log_info "设置环境变量..."
    
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# JCY5001AS Web平台环境配置
JWT_SECRET_KEY=$(openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
POSTGRES_PASSWORD=jcy5001_password
REDIS_PASSWORD=redis_password

# 数据库配置
DATABASE_URL=postgresql://jcy5001:jcy5001_password@postgres:5432/jcy5001_db
REDIS_URL=redis://:redis_password@redis:6379/0

# 应用配置
FLASK_ENV=production
NODE_ENV=production
REACT_APP_API_URL=https://localhost/api
REACT_APP_WS_URL=wss://localhost/socket.io

# 监控配置
GRAFANA_ADMIN_PASSWORD=admin123
EOF
        log_success "环境变量文件创建完成"
    else
        log_info "环境变量文件已存在"
    fi
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    # 构建后端镜像
    log_info "构建后端镜像..."
    docker build -t jcy5001-backend:latest ../JCY5001_Server_Python/
    
    # 构建前端镜像
    log_info "构建前端镜像..."
    docker build -t jcy5001-frontend:latest ../JCY5001_Web_Frontend/
    
    log_success "Docker镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 启动数据库和缓存服务
    log_info "启动基础服务..."
    docker-compose up -d postgres redis
    
    # 等待数据库启动
    log_info "等待数据库启动..."
    sleep 10
    
    # 运行数据库迁移
    log_info "运行数据库迁移..."
    docker-compose run --rm backend python -m flask db upgrade
    
    # 启动应用服务
    log_info "启动应用服务..."
    docker-compose up -d backend frontend nginx
    
    # 启动监控服务（可选）
    if [ "$1" = "--with-monitoring" ]; then
        log_info "启动监控服务..."
        docker-compose up -d prometheus grafana
    fi
    
    log_success "服务启动完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    # 检查后端服务
    for i in {1..30}; do
        if curl -f http://localhost:5000/api/health &> /dev/null; then
            log_success "后端服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "后端服务健康检查失败"
            return 1
        fi
        sleep 2
    done
    
    # 检查前端服务
    for i in {1..30}; do
        if curl -f http://localhost:3000 &> /dev/null; then
            log_success "前端服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "前端服务健康检查失败"
            return 1
        fi
        sleep 2
    done
    
    # 检查Nginx服务
    for i in {1..30}; do
        if curl -f http://localhost/health &> /dev/null; then
            log_success "Nginx服务健康检查通过"
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Nginx服务健康检查失败"
            return 1
        fi
        sleep 2
    done
    
    log_success "所有服务健康检查通过"
}

# 显示部署信息
show_deployment_info() {
    log_success "JCY5001AS Web平台部署完成！"
    echo ""
    echo "访问地址："
    echo "  前端应用: https://localhost"
    echo "  API文档: https://localhost/api/docs"
    echo "  健康检查: https://localhost/health"
    echo ""
    echo "管理地址："
    echo "  Grafana监控: http://localhost:3001 (admin/admin123)"
    echo "  Prometheus: http://localhost:9090"
    echo ""
    echo "常用命令："
    echo "  查看日志: docker-compose logs -f [service]"
    echo "  重启服务: docker-compose restart [service]"
    echo "  停止服务: docker-compose down"
    echo "  备份数据: ./backup.sh"
    echo ""
}

# 主函数
main() {
    echo "========================================"
    echo "    JCY5001AS Web平台自动部署脚本"
    echo "========================================"
    echo ""
    
    check_dependencies
    create_directories
    generate_ssl_cert
    setup_environment
    build_images
    start_services $1
    health_check
    show_deployment_info
    
    log_success "部署完成！"
}

# 脚本入口
if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  --with-monitoring    启用监控服务"
    echo "  --help, -h          显示帮助信息"
    echo ""
    exit 0
fi

main $1