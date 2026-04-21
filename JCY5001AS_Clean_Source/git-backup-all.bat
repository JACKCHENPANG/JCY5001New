@echo off
echo 🚀 JCY5001AS 项目Git备份脚本
echo ================================
echo 开始时间: %date% %time%
echo.

set "TIMESTAMP=%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TIMESTAMP=%TIMESTAMP: =0%"

echo 📋 备份计划:
echo 1. JCY5001设备软件 (当前目录)
echo 2. 前端项目 (JCY5001_Web_Frontend)
echo 3. 后端项目 (JCY5001_Server_Python)
echo.

REM ============================================
REM 1. 备份JCY5001设备软件 (主项目)
REM ============================================
echo 🔧 [1/3] 备份JCY5001设备软件...

REM 重置当前状态
git reset --hard HEAD 2>nul

REM 清理不需要的文件
echo 🧹 清理临时文件...
if exist "JCY5001_Web_Frontend\node_modules" rmdir /s /q "JCY5001_Web_Frontend\node_modules" 2>nul
if exist "JCY5001_Web_Frontend\dist" rmdir /s /q "JCY5001_Web_Frontend\dist" 2>nul
if exist "JCY5001_Web_Frontend\.vite" rmdir /s /q "JCY5001_Web_Frontend\.vite" 2>nul
if exist "data\test_results.db" del /q "data\test_results.db" 2>nul
if exist "*.log" del /q "*.log" 2>nul

REM 添加文件到Git
echo 📦 添加文件到Git...
git add . 2>nul

REM 创建提交
echo 💾 创建提交...
git commit -m "备份JCY5001设备软件 - %TIMESTAMP%" 2>nul

REM 推送到远程仓库
echo 🌐 推送到GitHub...
git push origin main 2>nul
if %errorlevel% equ 0 (
    echo ✅ JCY5001设备软件备份成功
) else (
    echo ❌ JCY5001设备软件备份失败
)

echo.

REM ============================================
REM 2. 创建前端项目仓库
REM ============================================
echo 🎨 [2/3] 创建前端项目仓库...

cd JCY5001_Web_Frontend

REM 检查是否已经是Git仓库
if not exist ".git" (
    echo 🔧 初始化Git仓库...
    git init 2>nul
    git remote add origin https://github.com/JACKCHENPANG/JCY5001_Web_Frontend.git 2>nul
)

REM 创建前端专用的.gitignore
echo 📝 创建.gitignore...
(
echo # 前端项目忽略文件
echo node_modules/
echo dist/
echo .vite/
echo build/
echo .env.local
echo .env.production
echo *.log
echo .DS_Store
echo Thumbs.db
echo .cache/
echo coverage/
echo .nyc_output/
echo .eslintcache
) > .gitignore

REM 添加文件
echo 📦 添加前端文件...
git add . 2>nul

REM 创建提交
echo 💾 创建前端提交...
git commit -m "JCY5001AS前端项目备份 - %TIMESTAMP%" 2>nul

REM 推送到远程仓库
echo 🌐 推送前端到GitHub...
git push -u origin main 2>nul
if %errorlevel% equ 0 (
    echo ✅ 前端项目备份成功
) else (
    echo ❌ 前端项目备份失败，可能需要先在GitHub创建仓库
)

cd ..
echo.

REM ============================================
REM 3. 创建后端项目仓库
REM ============================================
echo ⚙️ [3/3] 创建后端项目仓库...

cd JCY5001_Server_Python

REM 检查是否已经是Git仓库
if not exist ".git" (
    echo 🔧 初始化Git仓库...
    git init 2>nul
    git remote add origin https://github.com/JACKCHENPANG/JCY5001_Server_Python.git 2>nul
)

REM 创建后端专用的.gitignore
echo 📝 创建.gitignore...
(
echo # 后端项目忽略文件
echo __pycache__/
echo *.py[cod]
echo *$py.class
echo *.so
echo .Python
echo build/
echo develop-eggs/
echo dist/
echo downloads/
echo eggs/
echo .eggs/
echo lib/
echo lib64/
echo parts/
echo sdist/
echo var/
echo wheels/
echo *.egg-info/
echo .installed.cfg
echo *.egg
echo instance/
echo .webassets-cache
echo .env
echo .venv
echo env/
echo venv/
echo ENV/
echo env.bak/
echo venv.bak/
echo *.log
echo .DS_Store
echo Thumbs.db
echo *.db
echo *.sqlite
echo *.sqlite3
echo logs/
echo temp/
echo cache/
) > .gitignore

REM 添加文件
echo 📦 添加后端文件...
git add . 2>nul

REM 创建提交
echo 💾 创建后端提交...
git commit -m "JCY5001AS后端项目备份 - %TIMESTAMP%" 2>nul

REM 推送到远程仓库
echo 🌐 推送后端到GitHub...
git push -u origin main 2>nul
if %errorlevel% equ 0 (
    echo ✅ 后端项目备份成功
) else (
    echo ❌ 后端项目备份失败，可能需要先在GitHub创建仓库
)

cd ..
echo.

REM ============================================
REM 备份完成总结
REM ============================================
echo 🎉 备份完成总结
echo ================================
echo 完成时间: %date% %time%
echo.
echo 📊 备份状态:
echo ✅ JCY5001设备软件: https://github.com/JACKCHENPANG/JCY5001A
echo 🎨 前端项目: https://github.com/JACKCHENPANG/JCY5001_Web_Frontend
echo ⚙️ 后端项目: https://github.com/JACKCHENPANG/JCY5001_Server_Python
echo.
echo 💡 注意事项:
echo 1. 如果某个仓库备份失败，请先在GitHub创建对应的仓库
echo 2. 确保GitHub账户有推送权限
echo 3. 建议定期运行此脚本进行备份
echo.
echo 🔗 GitHub仓库地址:
echo - 主项目: git@github.com:JACKCHENPANG/JCY5001A.git
echo - 前端: git@github.com:JACKCHENPANG/JCY5001_Web_Frontend.git
echo - 后端: git@github.com:JACKCHENPANG/JCY5001_Server_Python.git
echo.

pause
