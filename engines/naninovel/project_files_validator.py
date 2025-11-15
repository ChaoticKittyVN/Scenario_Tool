from core.base_project_files_validator import BaseProjectFilesValidator
import pandas as pd
class NaninovelProjectFilesValidatorGenerator(BaseProjectFilesValidator):

    @property
    def source_path(self) -> str:
        """资源库路径"""
        return ""
        
    @property
    def project_path(self) -> str:
        """项目库路径"""
        return ""

    @property
    def path_dict(self) -> dict:
        """文件类型路径词典"""
        return {
            "Music": "Audio/Music/",
            "Back": "Background/MainBackground/",
            "Event": "Background/CG/",
        }

    @property
    def params_list(self) -> list:
        """需要抓取的参数类型"""
        return []
    
    def process_filenames(self, params):
        """
        从参数中提取文件名
        这个方法由子类实现，因为不同引擎的文件名提取逻辑可能不同
        
        Args:
            params: 参数字典
            
        Returns:
            List[str]: 提取出的文件名列表（不带扩展名）
        """
        filenames_by_type = {}

        # 安全地获取行数
        if not params:
            return filenames_by_type  # 如果参数为空，直接返回空字典
        
        row_count = len(list(params.values())[0])  # 获取第一个参数列的长度
        
        # 遍历每一行
        for i in range(row_count):
            if "Music" in params and not params["Music"][i] == "":
                music = params["Music"][i]
                if music != "停止":
                    filename = self.translator.translate("Music", music)
                    if "Music" not in filenames_by_type:
                        filenames_by_type["Music"] = set()
                    filenames_by_type["Music"].add(filename)
        
        # 将集合转换为列表
        for file_type in filenames_by_type:
            filenames_by_type[file_type] = sorted(list(filenames_by_type[file_type]))
        
        return filenames_by_type