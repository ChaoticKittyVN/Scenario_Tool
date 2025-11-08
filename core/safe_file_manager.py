# safe_file_manager.py
import os
import shutil
import time
from typing import List, Dict, Any

class SafeFileManager:
    """安全的文件操作管理器"""
    
    def __init__(self, dry_run=True, backup_existing=False):
        self.dry_run = dry_run  # 干跑模式，只显示将要执行的操作
        self.backup_existing = backup_existing  # 是否备份已存在的文件（默认不备份）
        self.operations = []  # 记录所有操作
        
    def copy_file(self, source_path: str, target_path: str, file_type: str = "未知类型") -> bool:
        """复制文件，带安全检查"""
        operation = {
            'type': 'copy',
            'source': source_path,
            'target': target_path,
            'file_type': file_type,
            'status': 'pending'
        }
        
        # 检查源文件是否存在
        if not os.path.exists(source_path):
            operation['status'] = 'failed'
            operation['error'] = '源文件不存在'
            self.operations.append(operation)
            return False
            
        # 检查目标文件是否已存在
        if os.path.exists(target_path):
            operation['status'] = 'skipped'
            operation['reason'] = '目标文件已存在，跳过'
            self.operations.append(operation)
            return True  # 不视为错误，只是跳过
            
        # 检查目标目录是否存在，不存在则创建
        target_dir = os.path.dirname(target_path)
        if not os.path.exists(target_dir):
            if not self.dry_run:
                os.makedirs(target_dir, exist_ok=True)
            operation['mkdir'] = target_dir
            
        # 执行复制
        if not self.dry_run:
            try:
                shutil.copy2(source_path, target_path)
                operation['status'] = 'success'
            except Exception as e:
                operation['status'] = 'failed'
                operation['error'] = str(e)
                return False
        else:
            operation['status'] = 'would_copy'
            
        self.operations.append(operation)
        return True
    
    def get_operation_summary(self) -> Dict[str, int]:
        """获取操作摘要"""
        status_counts = {}
        for op in self.operations:
            status = op['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total': len(self.operations),
            **status_counts
        }
    
    def print_operations(self):
        """打印所有操作"""
        status_icons = {
            'success': '✓',
            'would_copy': '→',
            'failed': '✗',
            'pending': '?',
            'skipped': '○'
        }
        
        for op in self.operations:
            icon = status_icons.get(op['status'], '?')
            print(f"{icon} {op['file_type']}: {os.path.basename(op['source'])}")
            
            if op['status'] == 'failed':
                print(f"    错误: {op['error']}")
            elif op['status'] == 'skipped':
                print(f"    跳过: {op['reason']}")
            elif op['status'] == 'would_copy':
                print(f"    将复制到: {os.path.basename(op['target'])}")
            elif op['status'] == 'success':
                print(f"    已复制到: {os.path.basename(op['target'])}")