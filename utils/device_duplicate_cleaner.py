#!/usr/bin/env python3
"""
设备重复清理工具
用于检查和清理云端重复的设备ID
"""

import requests
import logging
import json
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DeviceDuplicateCleaner:
    """设备重复清理器"""
    
    def __init__(self, server_url: str = "https://ukukukukukukukuk.uk"):
        self.server_url = server_url
        self.session = requests.Session()
        self.access_token = None
        
        # 设置默认headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'JCY5001A-DeviceCleaner/1.0'
        })
    
    def authenticate(self, username: str = "admin", password: str = "Admin123!") -> bool:
        """认证获取访问令牌"""
        try:
            auth_url = f"{self.server_url}/api/auth/login"
            auth_data = {
                'username': username,
                'password': password
            }
            
            response = self.session.post(auth_url, json=auth_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get('access_token')
                
                # 更新session headers
                self.session.headers.update({
                    'Authorization': f'Bearer {self.access_token}'
                })
                
                logger.info("认证成功")
                return True
            else:
                logger.error(f"认证失败: HTTP {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"认证异常: {e}")
            return False
    
    def get_all_devices(self) -> List[Dict]:
        """获取所有设备列表"""
        try:
            devices_url = f"{self.server_url}/api/devices"
            response = self.session.get(devices_url, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                devices = result.get('devices', [])
                logger.info(f"获取到 {len(devices)} 个设备")
                return devices
            else:
                logger.error(f"获取设备列表失败: HTTP {response.status_code}, {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"获取设备列表异常: {e}")
            return []
    
    def find_duplicate_devices(self, devices: List[Dict]) -> Dict[str, List[Dict]]:
        """查找重复的设备"""
        device_groups = {}
        
        for device in devices:
            device_id = device.get('device_id', '')
            if device_id:
                if device_id not in device_groups:
                    device_groups[device_id] = []
                device_groups[device_id].append(device)
        
        # 只返回有重复的设备组
        duplicates = {k: v for k, v in device_groups.items() if len(v) > 1}
        
        logger.info(f"发现 {len(duplicates)} 个重复的设备ID")
        return duplicates
    
    def analyze_duplicates(self, duplicates: Dict[str, List[Dict]]) -> Dict:
        """分析重复设备的详细信息"""
        analysis = {
            'total_duplicate_groups': len(duplicates),
            'total_duplicate_devices': sum(len(devices) for devices in duplicates.values()),
            'details': []
        }
        
        for device_id, devices in duplicates.items():
            group_info = {
                'device_id': device_id,
                'device_short_id': device_id[:16] + '...' if len(device_id) > 16 else device_id,
                'count': len(devices),
                'devices': []
            }
            
            for device in devices:
                device_info = {
                    'id': device.get('id'),
                    'name': device.get('name'),
                    'model': device.get('model'),
                    'user_id': device.get('user_id'),
                    'created_at': device.get('created_at'),
                    'updated_at': device.get('updated_at'),
                    'status': device.get('status')
                }
                group_info['devices'].append(device_info)
            
            # 按创建时间排序，最新的在前
            group_info['devices'].sort(key=lambda x: x.get('created_at', ''), reverse=True)
            analysis['details'].append(group_info)
        
        return analysis
    
    def suggest_cleanup_plan(self, analysis: Dict) -> Dict:
        """建议清理方案"""
        cleanup_plan = {
            'keep_devices': [],
            'remove_devices': [],
            'summary': {
                'total_to_remove': 0,
                'total_to_keep': 0
            }
        }
        
        for group in analysis['details']:
            devices = group['devices']
            if len(devices) > 1:
                # 保留最新创建的设备
                keep_device = devices[0]  # 已按创建时间排序
                remove_devices = devices[1:]
                
                cleanup_plan['keep_devices'].append({
                    'device_id': group['device_id'],
                    'keep': keep_device,
                    'reason': '最新创建的设备'
                })
                
                for device in remove_devices:
                    cleanup_plan['remove_devices'].append({
                        'device_id': group['device_id'],
                        'remove': device,
                        'reason': '重复的旧设备'
                    })
        
        cleanup_plan['summary']['total_to_keep'] = len(cleanup_plan['keep_devices'])
        cleanup_plan['summary']['total_to_remove'] = len(cleanup_plan['remove_devices'])
        
        return cleanup_plan
    
    def execute_cleanup(self, cleanup_plan: Dict, dry_run: bool = True) -> Dict:
        """执行清理操作"""
        result = {
            'success': True,
            'removed_count': 0,
            'failed_count': 0,
            'errors': [],
            'dry_run': dry_run
        }
        
        if dry_run:
            logger.info("执行模拟清理（不会实际删除设备）")
            result['removed_count'] = len(cleanup_plan['remove_devices'])
            return result
        
        logger.info("开始执行实际清理操作")
        
        for item in cleanup_plan['remove_devices']:
            device = item['remove']
            device_db_id = device['id']
            
            try:
                # 删除设备
                delete_url = f"{self.server_url}/api/devices/{device_db_id}"
                response = self.session.delete(delete_url, timeout=30)
                
                if response.status_code in [200, 204]:
                    logger.info(f"成功删除重复设备: {device['name']} (ID: {device_db_id})")
                    result['removed_count'] += 1
                else:
                    error_msg = f"删除设备失败: HTTP {response.status_code}, {response.text}"
                    logger.error(error_msg)
                    result['errors'].append(error_msg)
                    result['failed_count'] += 1
                    
            except Exception as e:
                error_msg = f"删除设备异常: {e}"
                logger.error(error_msg)
                result['errors'].append(error_msg)
                result['failed_count'] += 1
                result['success'] = False
        
        return result
    
    def generate_report(self, analysis: Dict, cleanup_plan: Dict) -> str:
        """生成清理报告"""
        report = []
        report.append("=" * 60)
        report.append("设备重复检查和清理报告")
        report.append("=" * 60)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 概要信息
        report.append("概要信息:")
        report.append(f"  重复设备组数: {analysis['total_duplicate_groups']}")
        report.append(f"  重复设备总数: {analysis['total_duplicate_devices']}")
        report.append(f"  建议保留设备: {cleanup_plan['summary']['total_to_keep']}")
        report.append(f"  建议删除设备: {cleanup_plan['summary']['total_to_remove']}")
        report.append("")
        
        # 详细信息
        report.append("重复设备详情:")
        for group in analysis['details']:
            report.append(f"  设备ID: {group['device_short_id']}")
            report.append(f"  重复数量: {group['count']}")
            
            for i, device in enumerate(group['devices']):
                status = "【保留】" if i == 0 else "【删除】"
                report.append(f"    {status} {device['name']} (数据库ID: {device['id']})")
                report.append(f"         创建时间: {device['created_at']}")
                report.append(f"         用户ID: {device['user_id']}")
            report.append("")
        
        return "\n".join(report)


def main():
    """主函数"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("=== 设备重复清理工具 ===")
    
    # 创建清理器
    cleaner = DeviceDuplicateCleaner()
    
    # 认证
    if not cleaner.authenticate():
        print("❌ 认证失败，请检查服务器连接和凭据")
        return
    
    # 获取所有设备
    devices = cleaner.get_all_devices()
    if not devices:
        print("❌ 无法获取设备列表")
        return
    
    # 查找重复设备
    duplicates = cleaner.find_duplicate_devices(devices)
    if not duplicates:
        print("✅ 没有发现重复的设备")
        return
    
    # 分析重复设备
    analysis = cleaner.analyze_duplicates(duplicates)
    
    # 生成清理方案
    cleanup_plan = cleaner.suggest_cleanup_plan(analysis)
    
    # 生成报告
    report = cleaner.generate_report(analysis, cleanup_plan)
    print(report)
    
    # 询问是否执行清理
    print("\n" + "=" * 60)
    choice = input("是否执行清理操作？(y/N): ").strip().lower()
    
    if choice == 'y':
        # 先执行模拟清理
        print("\n执行模拟清理...")
        dry_result = cleaner.execute_cleanup(cleanup_plan, dry_run=True)
        print(f"模拟清理结果: 将删除 {dry_result['removed_count']} 个重复设备")
        
        # 确认执行实际清理
        confirm = input("\n确认执行实际清理？(y/N): ").strip().lower()
        if confirm == 'y':
            print("\n执行实际清理...")
            result = cleaner.execute_cleanup(cleanup_plan, dry_run=False)
            
            if result['success']:
                print(f"✅ 清理完成！成功删除 {result['removed_count']} 个重复设备")
            else:
                print(f"⚠️ 清理部分完成：成功 {result['removed_count']}，失败 {result['failed_count']}")
                for error in result['errors']:
                    print(f"   错误: {error}")
        else:
            print("取消实际清理操作")
    else:
        print("取消清理操作")


if __name__ == "__main__":
    main()
