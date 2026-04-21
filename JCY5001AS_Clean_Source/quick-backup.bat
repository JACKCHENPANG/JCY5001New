@echo off
echo 🚀 JCY5001AS 快速Git备份
echo ========================
echo 开始时间: %date% %time%
echo.

set "TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"

echo 🧹 清理临时文件...
REM 删除node_modules和其他大文件
if exist "JCY5001_Web_Frontend\node_modules" (
    echo 删除前端node_modules...
    rmdir /s /q "JCY5001_Web_Frontend\node_modules" 2>nul
)
if exist "JCY5001_Web_Frontend\dist" rmdir /s /q "JCY5001_Web_Frontend\dist" 2>nul
if exist "JCY5001_Web_Frontend\.vite" rmdir /s /q "JCY5001_Web_Frontend\.vite" 2>nul

REM 删除数据库文件
if exist "data\test_results.db" del /q "data\test_results.db" 2>nul
if exist "*.log" del /q "*.log" 2>nul

echo 📦 添加重要文件到Git...
REM 只添加源代码文件
git add *.py 2>nul
git add *.json 2>nul
git add *.md 2>nul
git add *.txt 2>nul
git add *.bat 2>nul
git add ui/ 2>nul
git add backend/ 2>nul
git add config/ 2>nul
git add utils/ 2>nul
git add algorithms/ 2>nul
git add 算法/ 2>nul
git add JCY5001_Server_Python/src/ 2>nul
git add JCY5001_Server_Python/requirements.txt 2>nul
git add JCY5001_Web_Frontend/src/ 2>nul
git add JCY5001_Web_Frontend/public/ 2>nul
git add JCY5001_Web_Frontend/package.json 2>nul
git add JCY5001_Web_Frontend/package-lock.json 2>nul
git add JCY5001_Web_Frontend/tsconfig.json 2>nul
git add JCY5001_Web_Frontend/vite.config.ts 2>nul
git add JCY5001_Web_Frontend/tailwind.config.js 2>nul
git add JCY5001_Web_Frontend/.env.example 2>nul
git add JCY5001_Web_Frontend/.env.local 2>nul
git add .gitignore 2>nul

echo 💾 创建提交...
git commit -m "JCY5001AS项目备份 - %TIMESTAMP% - 包含设备软件+前端+后端" 2>nul

echo 🌐 推送到GitHub...
git push origin main 2>nul

if %errorlevel% equ 0 (
    echo ✅ 备份成功！
    echo 📊 备份内容:
    echo    - JCY5001设备软件源代码
    echo    - Web前端项目 (不含node_modules)
    echo    - 后端服务器代码
    echo    - 配置文件和文档
    echo.
    echo 🔗 GitHub地址: https://github.com/JACKCHENPANG/JCY5001A
) else (
    echo ❌ 备份失败！
    echo 💡 可能的原因:
    echo    - 网络连接问题
    echo    - GitHub认证问题
    echo    - 仓库权限问题
)

echo.
echo 完成时间: %date% %time%
pause
