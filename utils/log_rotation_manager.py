# -*- coding: utf-8 -*-
"""
日志轮转管理器
智能管理日志文件大小和轮转策略

Author: Jack
Date: 2025-01-09
"""

import os
import logging
import gzip
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

logger = logging.getLogger(__name__)


class LogRotationManager:
    """日志轮转管理器"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 配置参数
        self.max_file_size = 5 * 1024 * 1024  # 5MB
        self.backup_count = 5  # 保留5个备份文件
        self.compress_old_logs = True  # 压缩旧日志
        self.cleanup_days = 30  # 30天后删除旧日志
        
    def setup_rotating_logger(self, logger_name: str = "app") -> logging.Logger:
        """设置轮转日志记录器"""
        log_file = self.log_dir / f"{logger_name}.log"
        
        # 创建轮转文件处理器
        handler = RotatingFileHandler(
            log_file,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding='utf-8'
        )
        
        # 设置日志格式
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # 配置日志记录器
        app_logger = logging.getLogger(logger_name)
        app_logger.setLevel(logging.INFO)  # 默认INFO级别
        
        # 清除现有处理器
        app_logger.handlers.clear()
        app_logger.addHandler(handler)
        
        logger.info(f"✅ 日志轮转已设置: {log_file}")
        return app_logger
    
    def compress_old_logs(self):
        """压缩旧的日志文件"""
        try:
            for log_file in self.log_dir.glob("*.log.*"):
                if not log_file.name.endswith('.gz'):
                    compressed_file = log_file.with_suffix(log_file.suffix + '.gz')
                    
                    with open(log_file, 'rb') as f_in:
                        with gzip.open(compressed_file, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    # 删除原文件
                    log_file.unlink()
                    logger.info(f"🗜️ 压缩日志文件: {log_file} -> {compressed_file}")
                    
        except Exception as e:
            logger.error(f"压缩日志文件失败: {e}")
    
    def cleanup_old_logs(self):
        """清理过期的日志文件"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.cleanup_days)
            
            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_date.timestamp():
                    log_file.unlink()
                    logger.info(f"🗑️ 删除过期日志: {log_file}")
                    
        except Exception as e:
            logger.error(f"清理过期日志失败: {e}")
    
    def get_log_statistics(self) -> dict:
        """获取日志统计信息"""
        try:
            stats = {
                'total_files': 0,
                'total_size': 0,
                'compressed_files': 0,
                'uncompressed_files': 0,
                'oldest_log': None,
                'newest_log': None
            }
            
            log_files = list(self.log_dir.glob("*.log*"))
            stats['total_files'] = len(log_files)
            
            if log_files:
                # 计算总大小
                stats['total_size'] = sum(f.stat().st_size for f in log_files)
                
                # 统计压缩和未压缩文件
                for log_file in log_files:
                    if log_file.name.endswith('.gz'):
                        stats['compressed_files'] += 1
                    else:
                        stats['uncompressed_files'] += 1
                
                # 找到最新和最旧的日志
                file_times = [(f, f.stat().st_mtime) for f in log_files]
                file_times.sort(key=lambda x: x[1])
                
                stats['oldest_log'] = file_times[0][0].name
                stats['newest_log'] = file_times[-1][0].name
            
            return stats
            
        except Exception as e:
            logger.error(f"获取日志统计失败: {e}")
            return {}
    
    def optimize_current_log(self):
        """优化当前日志文件"""
        try:
            current_log = self.log_dir / "app.log"
            
            if current_log.exists():
                file_size = current_log.stat().st_size
                
                # 如果文件过大，强制轮转
                if file_size > self.max_file_size:
                    self._force_log_rotation(current_log)
                
                logger.info(f"📊 当前日志文件大小: {file_size / 1024 / 1024:.2f}MB")
                
        except Exception as e:
            logger.error(f"优化当前日志失败: {e}")
    
    def _force_log_rotation(self, log_file: Path):
        """强制日志轮转"""
        try:
            # 创建备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = log_file.with_name(f"{log_file.stem}_{timestamp}.log")
            
            # 移动当前日志文件
            shutil.move(str(log_file), str(backup_file))
            
            # 创建新的空日志文件
            log_file.touch()
            
            logger.info(f"🔄 强制日志轮转: {log_file} -> {backup_file}")
            
        except Exception as e:
            logger.error(f"强制日志轮转失败: {e}")
    
    def generate_log_report(self) -> str:
        """生成日志管理报告"""
        stats = self.get_log_statistics()
        
        if not stats:
            return "❌ 无法获取日志统计信息"
        
        total_size_mb = stats['total_size'] / 1024 / 1024
        
        report = [
            "📋 日志管理报告",
            "=" * 40,
            f"📁 日志文件总数: {stats['total_files']}",
            f"💾 总占用空间: {total_size_mb:.2f}MB",
            f"🗜️ 压缩文件数: {stats['compressed_files']}",
            f"📄 未压缩文件数: {stats['uncompressed_files']}",
            f"📅 最旧日志: {stats.get('oldest_log', 'N/A')}",
            f"🆕 最新日志: {stats.get('newest_log', 'N/A')}",
            "",
            "⚙️ 当前配置:",
            f"  • 最大文件大小: {self.max_file_size / 1024 / 1024}MB",
            f"  • 备份文件数: {self.backup_count}",
            f"  • 自动压缩: {'✅' if self.compress_old_logs else '❌'}",
            f"  • 清理周期: {self.cleanup_days}天",
            "=" * 40
        ]
        
        return "\n".join(report)
    
    def perform_maintenance(self):
        """执行日志维护任务"""
        logger.debug(f" 开始日志维护...")
        
        # 1. 优化当前日志
        self.optimize_current_log()
        
        # 2. 压缩旧日志
        if self.compress_old_logs:
            self.compress_old_logs()
        
        # 3. 清理过期日志
        self.cleanup_old_logs()
        
        # 4. 生成报告
        report = self.generate_log_report()
        logger.info(f"\n{report}")
        
        logger.info("✅ 日志维护完成")


def setup_optimized_logging():
    """设置优化的日志系统"""
    try:
        # 创建日志轮转管理器
        log_manager = LogRotationManager()
        
        # 设置轮转日志记录器
        app_logger = log_manager.setup_rotating_logger("app")
        
        # 执行维护任务
        log_manager.perform_maintenance()
        
        logger.info("✅ 优化日志系统设置完成")
        return log_manager
        
    except Exception as e:
        logger.error(f"设置优化日志系统失败: {e}")
        return None


def main():
    """主函数"""
    logger.info("🚀 开始日志系统优化...")
    
    log_manager = setup_optimized_logging()
    
    if log_manager:
        logger.info("✅ 日志系统优化完成！")
    else:
        logger.error("❌ 日志系统优化失败")


if __name__ == "__main__":
    main()
