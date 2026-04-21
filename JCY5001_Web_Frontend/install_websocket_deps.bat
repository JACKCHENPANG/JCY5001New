@echo off
echo Installing WebSocket dependencies...

cd /d "E:\Code\JCY5001_Web_Frontend"

echo Installing socket.io-client...
npm install socket.io-client

echo Installing additional dependencies...
npm install framer-motion

echo Dependencies installed successfully!
pause