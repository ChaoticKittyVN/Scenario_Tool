from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd
import os
import glob

class BaseProjectFilesValidator(ABC):
    """项目文件验证器基类"""

    def __init__(self, format_config, translator):
        self.format_config = format_config
        self.translator = translator

    @property
    @abstractmethod
    def source_path(self) -> str:
        """资源库路径"""
        pass
        
    @property
    @abstractmethod
    def project_path(self) -> str:
        """项目库路径"""
        pass

    @property
    @abstractmethod
    def path_dict(self) -> dict:
        """文件类型路径词典"""
        pass

    @property
    @abstractmethod
    def params_list(self) -> list:
        """需要抓取的参数类型"""
        pass

    @abstractmethod
    def process_filenames(self, params: Dict[str, Any]) -> Dict[str, List[str]]:
        """
        从参数中提取文件名并按类型分类
        
        Args:
            params: 参数字典 {列名: [值列表]}
            
        Returns:
            Dict[str, List[str]]: 按文件类型分类的文件名字典
        """
        pass

    def do_translate(self, row_data : dict):
        new_data = row_data
        for name,value in row_data.items():
            translate_type = self.format_config.get(name).get("translate_type")

            if translate_type:
                new_value = self.translator.translate(translate_type, value)
                new_data[name] = new_value

            elif self.format_config.get(name).get("translate_types"):
                for translate_type in self.format_config.get(name).get("translate_types"):
                    if value in self.translator.mappings[translate_type]:
                        new_value = self.translator.translate(translate_type, value)
                        new_data[name] = new_value
                        break
            else:
                continue

        return new_data   

    def get_int(self, num : str):
        num = str(num)
        try:
            return int(float(num))
        except:
            print(f"警告：{num}不是支持的数字格式") 
            return num  

    def is_same_list(self, source_list: list, project_list: list) -> bool:
        """比较两个列表是否相同（忽略顺序）"""
        return sorted(source_list) == sorted(project_list)

    def _search_files(self, base_path: str, filenames: List[str], file_types: List[str] = None) -> Dict[str, str]:
        """
        通用文件搜索方法
        
        Args:
            base_path: 基础路径（资源库或项目库）
            filenames: 文件名列表（不带扩展名）
            file_types: 要搜索的文件类型列表
            
        Returns:
            Dict[str, str]: 文件名映射 {原始文件名: 带扩展名的完整文件名}
        """
        result = {}
        
        if file_types is None:
            file_types = list(self.path_dict.keys())
        
        for filename in filenames:
            if not filename:
                continue
                
            found_file = self._find_file(base_path, filename, file_types)
            result[filename] = found_file

        return result

    def _find_file(self, base_path: str, filename: str, file_types: List[str]) -> str:
        """
        在指定路径中查找文件
        
        Args:
            base_path: 基础路径
            filename: 文件名（不带扩展名）
            file_types: 要搜索的文件类型列表
            
        Returns:
            str: 找到的完整文件名，如果未找到返回None
        """
        for file_type in file_types:
            if file_type not in self.path_dict:
                continue
                
            search_dir = os.path.join(base_path, self.path_dict[file_type])
            if not os.path.exists(search_dir):
                continue
                
            pattern = os.path.join(search_dir, f"{filename}.*")
            matching_files = glob.glob(pattern)
            
            for file_path in matching_files:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                if base_name.lower() == filename.lower():
                    return os.path.basename(file_path)
        
        return None

    def search_files_in_source(self, filenames: List[str], file_types: List[str] = None) -> Dict[str, str]:
        """
        在资源库中搜索文件
        
        Args:
            filenames: 文件名列表（不带扩展名）
            file_types: 要搜索的文件类型列表
            
        Returns:
            Dict[str, str]: 文件名映射 {原始文件名: 带扩展名的完整文件名}
        """
        return self._search_files(self.source_path, filenames, file_types)

    def search_files_in_project(self, filenames: List[str], file_types: List[str] = None) -> Dict[str, str]:
        """
        在项目库中搜索文件
        
        Args:
            filenames: 文件名列表（不带扩展名）
            file_types: 要搜索的文件类型列表
            
        Returns:
            Dict[str, str]: 文件名映射 {原始文件名: 带扩展名的完整文件名}
        """
        return self._search_files(self.project_path, filenames, file_types)


    def extract_column_data_for_validation(self, sheet_data, sheet_name):
        """
        提取列数据供验证器处理
        """
        if "Note" not in sheet_data.columns or "END" not in sheet_data["Note"].tolist():
            print(f"工作表 {sheet_name} 不包含Note列或END标记，跳过")
            return {}
        
        end_index = sheet_data["Note"].tolist().index("END")
        column_data = {}
        
        target_columns = self.params_list
        
        print(f"  提取列数据: {', '.join(target_columns)}")

        for column in target_columns:
            if column not in sheet_data.columns:
                continue

            column_values = sheet_data[column].iloc[:end_index].tolist()
            column_data[column] = [str(x) if pd.notna(x) else "" for x in column_values]
            
            print(f"    {column}: 提取了 {len(column_values)} 个值")
        
        return column_data

    def validate_files_by_type(self, files_by_type):
        """
        按文件类型验证文件
        
        Args:
            validator: 文件验证器
            files_by_type: 按类型分类的文件字典
            
        Returns:
            Dict[str, Dict[str, str]]: 验证结果 {文件类型: {文件名: 完整文件名}}
        """
        validation_results = {}
        
        print("\n在资源库中搜索文件...")
        
        for file_type, filenames in files_by_type.items():
            print(f"  验证 {file_type} 文件...")
            
            # 在资源库中搜索这类文件
            search_results = self.search_files_in_source(filenames, [file_type])
            
            validation_results[file_type] = search_results
            
            # 统计
            found_count = sum(1 for result in search_results.values() if result)
            print(f"    {file_type}: {len(filenames)} 个文件中找到 {found_count} 个")
        
        return validation_results
    
    def complete_validation(self, excel_data):
        """完整的验证流程（一站式调用）"""
        files_by_type = self.extract_filenames_from_excel(excel_data)
        project_results = self.validate_in_project(files_by_type)
        source_results = self.validate_in_source(files_by_type)
        comparison = self.compare_validations(project_results, source_results)
        
        return {
            'files_by_type': files_by_type,
            'project_validation': project_results,
            'source_validation': source_results,
            'comparison': comparison
        }
    
    def extract_filenames_from_excel(self, excel_data):
        """
        从Excel数据中提取文件名
        
        Args:
            excel_data: 读取的Excel数据 {sheet_name: DataFrame}
            
        Returns:
            Dict[str, List[str]]: 按文件类型分类的文件名字典
        """
        from collections import defaultdict
        
        all_files_by_type = defaultdict(list)
        sheet_names = list(excel_data.keys())
        
        for sheet in sheet_names:
            if sheet == '参数表':  # 跳过参数表
                continue
                
            print(f"\n处理工作表: {sheet}")
            
            # 使用现有的方法提取列数据
            extracted_data = self.extract_column_data_for_validation(excel_data[sheet], sheet)
            
            # 使用现有的方法处理文件名
            filenames_by_type = self.process_filenames(extracted_data)

            # 合并结果
            for file_type, filenames in filenames_by_type.items():
                all_files_by_type[file_type].extend(filenames)
        
        # 去重
        for file_type in all_files_by_type:
            all_files_by_type[file_type] = list(set(all_files_by_type[file_type]))
        
        return dict(all_files_by_type)

    def validate_in_project(self, files_by_type):
        """在项目库中验证文件"""
        validation_results = {}
        for file_type, filenames in files_by_type.items():
            if filenames:
                search_results = self.search_files_in_project(filenames, [file_type])
                validation_results[file_type] = search_results
        return validation_results
    
    def validate_in_source(self, files_by_type):
        """在资源库中验证文件"""
        validation_results = {}
        for file_type, filenames in files_by_type.items():
            if filenames:
                search_results = self.search_files_in_source(filenames, [file_type])
                validation_results[file_type] = search_results
        return validation_results
    
    def compare_validations(self, project_results, source_results):
        """对比项目库和资源库的验证结果"""
        comparison = {}
        
        for file_type in project_results:
            project_files = project_results[file_type]
            source_files = source_results.get(file_type, {})
            
            # 找出项目库缺失但资源库存在的文件
            missing_in_project_but_in_source = [
                filename for filename, project_file in project_files.items()
                if not project_file and source_files.get(filename)
            ]
            
            # 找出两个库都缺失的文件
            missing_in_both = [
                filename for filename, project_file in project_files.items()
                if not project_file and not source_files.get(filename)
            ]
            
            # 找出文件名不一致的情况
            inconsistent_files = [
                filename for filename, project_file in project_files.items()
                if project_file and source_files.get(filename) and 
                   project_file != source_files[filename]
            ]
            
            comparison[file_type] = {
                'missing_in_project_but_in_source': missing_in_project_but_in_source,
                'missing_in_both': missing_in_both,
                'inconsistent_files': inconsistent_files
            }
        
        return comparison
    

    def prepare_report_data(self, validation_results):
        """
        准备报告数据，提取和计算所有需要的信息
        
        Args:
            validation_results: 完整的验证结果
            
        Returns:
            Dict: 包含所有报告数据的字典
        """
        # 从验证结果中提取各个部分
        files_by_type = validation_results.get('files_by_type', {})
        project_validation = validation_results.get('project_validation', {})
        source_validation = validation_results.get('source_validation', {})
        comparison = validation_results.get('comparison', {})
        
        # 准备详细数据
        file_type_details = {}
        total_files = 0
        total_project_found = 0
        total_source_found = 0
        
        for file_type in files_by_type:
            filenames = sorted(files_by_type[file_type])
            project_results = project_validation.get(file_type, {})
            source_results = source_validation.get(file_type, {})
            comp_results = comparison.get(file_type, {})
            
            # 项目库状态
            project_found = [f for f in filenames if project_results.get(f)]
            project_missing = [f for f in filenames if not project_results.get(f)]
            
            # 资源库状态
            source_found = [f for f in filenames if source_results.get(f)]
            source_missing = [f for f in filenames if not source_results.get(f)]
            
            # 对比结果
            missing_in_project_but_in_source = comp_results.get('missing_in_project_but_in_source', [])
            missing_in_both = comp_results.get('missing_in_both', [])
            inconsistent_files = comp_results.get('inconsistent_files', [])
            
            file_type_details[file_type] = {
                'filenames': filenames,
                'project_found': project_found,
                'project_missing': project_missing,
                'source_found': source_found,
                'source_missing': source_missing,
                'missing_in_project_but_in_source': missing_in_project_but_in_source,
                'missing_in_both': missing_in_both,
                'inconsistent_files': inconsistent_files,
                'project_results': project_results,
                'source_results': source_results
            }
            
            total_files += len(filenames)
            total_project_found += len(project_found)
            total_source_found += len(source_found)
        
        # 计算汇总统计
        total_project_missing = total_files - total_project_found
        total_source_missing = total_files - total_source_found
        
        summary = {
            'total_files': total_files,
            'total_project_found': total_project_found,
            'total_source_found': total_source_found,
            'total_project_missing': total_project_missing,
            'total_source_missing': total_source_missing,
            'project_completion_rate': (total_project_found/total_files*100) if total_files > 0 else 0,
            'source_completion_rate': (total_source_found/total_files*100) if total_files > 0 else 0
        }
        
        return {
            'file_type_details': file_type_details,
            'summary': summary
        }
    
    def generate_copy_plan(self, validation_results: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        生成文件复制计划
        
        Args:
            validation_results: 完整的验证结果
            
        Returns:
            List[Dict]: 复制计划，包含源路径、目标路径等信息
        """
        copy_plan = []
        comparison = validation_results.get('comparison', {})
        source_validation = validation_results.get('source_validation', {})
        
        for file_type, comp_results in comparison.items():
            # 找出项目库缺失但资源库存在的文件
            missing_files = sorted(comp_results.get('missing_in_project_but_in_source', []))
            
            for filename in missing_files:
                source_filename = source_validation[file_type].get(filename)
                if source_filename:
                    source_path = os.path.join(
                        self.source_path, 
                        self.path_dict[file_type], 
                        source_filename
                    )
                    target_path = os.path.join(
                        self.project_path,
                        self.path_dict[file_type],
                        source_filename
                    )
                    
                    copy_plan.append({
                        'file_type': file_type,
                        'filename': filename,
                        'source_path': source_path,
                        'target_path': target_path,
                        'source_filename': source_filename
                    })
        
        return copy_plan