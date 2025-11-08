from core.base_project_files_validator import BaseProjectFilesValidator

class NaninovelProjectFilesValidatorGenerator(BaseProjectFilesValidator):

    @property
    def source_path(self) -> str:
        """资源库路径"""
        return
        
    @property
    def project_path(self) -> str:
        """项目库路径"""
        return

    @property
    def path_dict(self) -> dict:
        """文件类型路径词典"""
        return

    def extract_filenames_from_params(self, params: dict[str, any]) -> list[str]:
        filename_list = []

        return filename_list