@echo off
echo 🚀 JCY5001AS Web平台重启脚本
echo ================================

echo 📋 当前配置信息:
if exist .env.local (
    echo ✅ 发现 .env.local 配置文件
    type .env.local
) else (
    echo ❌ 未找到 .env.local 配置文件
    echo 请先运行: node setup-server-config.js
    pause
    exit /b 1
)

echo.
echo 🔄 正在停止开发服务器...
taskkill /f /im node.exe 2>nul
timeout /t 2 >nul

echo 🧹 清除缓存...
if exist node_modules\.vite rmdir /s /q node_modules\.vite
if exist dist rmdir /s /q dist

echo 🔄 重新启动开发服务器...
echo 📡 服务器地址将使用 .env.local 中的配置
echo.

start cmd /k "npm run dev"

echo ✅ 开发服务器已启动
echo 💡 请在浏览器中访问: http://localhost:3000
echo 🔧 如果仍有问题，请访问: http://localhost:3000/connection-test.html
echo.
pause
