#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志清理工具
用于清理测试产生的调试代码和优化日志输出

Author: Jack
Date: 2025-06-28
"""

import os
import re
import logging
from typing import List, Dict, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class LogCleanup:
    """日志清理工具"""
    
    def __init__(self, project_root: str):
        """
        初始化日志清理工具
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = Path(project_root)
        
        # 需要清理的调试日志模式
        self.debug_patterns = [
            r'logger\.debug\(f?"📊.*?\)',  # 统计调试日志
            r'logger\.info\(f?"📊.*?\)',   # 统计信息日志
            r'logger\.info\(f?"🔧.*?\)',   # 修复信息日志
            r'print\(f?".*调试.*?\)',      # 调试print语句
            r'print\(f?".*DEBUG.*?\)',     # DEBUG print语句
        ]
        
        # 需要优化的重复日志模式
        self.redundant_patterns = [
            r'logger\.info\(f?".*初始化完成.*?\)',  # 重复的初始化日志
            r'logger\.info\(f?".*管理器初始化.*?\)',  # 管理器初始化日志
            r'logger\.debug\(f?".*状态.*?\)',       # 状态调试日志
        ]
        
        # 排除的文件和目录
        self.exclude_patterns = [
            r'__pycache__',
            r'\.git',
            r'\.pytest_cache',
            r'logs',
            r'backup_.*',
            r'test_.*\.py',
            r'.*_test\.py',
        ]
        
        logger.debug("日志清理工具初始化完成")
    
    def scan_debug_logs(self) -> Dict[str, List[Dict]]:
        """
        扫描项目中的调试日志
        
        Returns:
            扫描结果字典
        """
        results = {
            'debug_logs': [],
            'redundant_logs': [],
            'files_scanned': 0,
            'total_issues': 0
        }
        
        try:
            # 遍历Python文件
            for py_file in self._get_python_files():
                results['files_scanned'] += 1
                
                # 扫描调试日志
                debug_issues = self._scan_file_for_debug(py_file)
                results['debug_logs'].extend(debug_issues)
                
                # 扫描重复日志
                redundant_issues = self._scan_file_for_redundant(py_file)
                results['redundant_logs'].extend(redundant_issues)
            
            results['total_issues'] = len(results['debug_logs']) + len(results['redundant_logs'])
            
            logger.info(f"扫描完成: {results['files_scanned']}个文件, {results['total_issues']}个问题")
            
        except Exception as e:
            logger.error(f"扫描调试日志失败: {e}")
        
        return results
    
    def clean_debug_logs(self, dry_run: bool = True) -> Dict[str, int]:
        """
        清理调试日志
        
        Args:
            dry_run: 是否为试运行模式
            
        Returns:
            清理统计信息
        """
        stats = {
            'files_processed': 0,
            'lines_removed': 0,
            'lines_modified': 0
        }
        
        try:
            scan_results = self.scan_debug_logs()
            
            if dry_run:
                self._print_scan_results(scan_results)
                return stats
            
            # 按文件分组处理
            files_to_process = self._group_issues_by_file(scan_results)
            
            for file_path, issues in files_to_process.items():
                if self._clean_file(file_path, issues):
                    stats['files_processed'] += 1
                    stats['lines_removed'] += len([i for i in issues if i['action'] == 'remove'])
                    stats['lines_modified'] += len([i for i in issues if i['action'] == 'modify'])
            
            logger.info(f"✅ 清理完成: {stats}")
            
        except Exception as e:
            logger.error(f"清理调试日志失败: {e}")
        
        return stats
    
    def _get_python_files(self) -> List[Path]:
        """获取所有Python文件"""
        python_files = []
        
        for root, dirs, files in os.walk(self.project_root):
            # 排除特定目录
            dirs[:] = [d for d in dirs if not any(re.match(pattern, d) for pattern in self.exclude_patterns)]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    # 排除特定文件
                    if not any(re.match(pattern, str(file_path)) for pattern in self.exclude_patterns):
                        python_files.append(file_path)
        
        return python_files
    
    def _scan_file_for_debug(self, file_path: Path) -> List[Dict]:
        """扫描文件中的调试日志"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for pattern in self.debug_patterns:
                    if re.search(pattern, line):
                        issues.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'type': 'debug',
                            'action': 'remove'
                        })
                        break
        
        except Exception as e:
            logger.debug(f"扫描文件{file_path}失败: {e}")
        
        return issues
    
    def _scan_file_for_redundant(self, file_path: Path) -> List[Dict]:
        """扫描文件中的重复日志"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for pattern in self.redundant_patterns:
                    if re.search(pattern, line):
                        issues.append({
                            'file': str(file_path),
                            'line': line_num,
                            'content': line.strip(),
                            'type': 'redundant',
                            'action': 'modify'
                        })
                        break
        
        except Exception as e:
            logger.debug(f"扫描文件{file_path}失败: {e}")
        
        return issues
    
    def _group_issues_by_file(self, scan_results: Dict) -> Dict[str, List[Dict]]:
        """按文件分组问题"""
        files_issues = {}
        
        all_issues = scan_results['debug_logs'] + scan_results['redundant_logs']
        
        for issue in all_issues:
            file_path = issue['file']
            if file_path not in files_issues:
                files_issues[file_path] = []
            files_issues[file_path].append(issue)
        
        return files_issues
    
    def _clean_file(self, file_path: str, issues: List[Dict]) -> bool:
        """清理单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # 按行号倒序排序，避免删除行时影响后续行号
            issues.sort(key=lambda x: x['line'], reverse=True)
            
            modified = False
            for issue in issues:
                line_idx = issue['line'] - 1  # 转换为0基索引
                
                if 0 <= line_idx < len(lines):
                    if issue['action'] == 'remove':
                        # 删除整行
                        del lines[line_idx]
                        modified = True
                    elif issue['action'] == 'modify':
                        # 修改为debug级别
                        original_line = lines[line_idx]
                        modified_line = original_line.replace('logger.info(', 'logger.debug(')
                        if modified_line != original_line:
                            lines[line_idx] = modified_line
                            modified = True
            
            if modified:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                logger.info(f"✅ 已清理文件: {file_path}")
                return True
        
        except Exception as e:
            logger.error(f"清理文件{file_path}失败: {e}")
        
        return False
    
    def _print_scan_results(self, results: Dict):
        """打印扫描结果"""
        print(f"\n📊 扫描结果:")
        print(f"  文件数量: {results['files_scanned']}")
        print(f"  重复日志: {len(results['redundant_logs'])}")
        print(f"  总问题数: {results['total_issues']}")
        
        if results['debug_logs']:
            for issue in results['debug_logs'][:5]:  # 只显示前5个
                print(f"  {issue['file']}:{issue['line']} - {issue['content'][:80]}...")
        
        if results['redundant_logs']:
            print(f"\n🔄 重复日志示例:")
            for issue in results['redundant_logs'][:5]:  # 只显示前5个
                print(f"  {issue['file']}:{issue['line']} - {issue['content'][:80]}...")


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python log_cleanup.py <project_root> [--clean]")
        return
    
    project_root = sys.argv[1]
    clean_mode = '--clean' in sys.argv
    
    cleanup = LogCleanup(project_root)
    
    if clean_mode:
        stats = cleanup.clean_debug_logs(dry_run=False)
        print(f"✅ 清理完成: {stats}")
    else:
        results = cleanup.scan_debug_logs()
        cleanup._print_scan_results(results)
        print("\n💡 使用 --clean 参数执行实际清理")


if __name__ == "__main__":
    main()
