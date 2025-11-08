import pandas as pd
import os
from tqdm import tqdm
from collections import defaultdict
from core.config import TARGET_PATH, OUTPUT_PATH, ENGINE_TYPE, get_engine_config, AUTO_COPY, DRY_RUN
from core.safe_file_manager import SafeFileManager

def create_validator():
    """创建文件验证器"""
    import importlib
    
    # 导入引擎配置
    engine_config_path = f"engines.{ENGINE_TYPE}.engine_param_config"
    engine_config = importlib.import_module(engine_config_path)
    format_config = engine_config.FORMAT_CONFIG

    # 创建验证器实例
    from core.param_translator import ParamTranslator 
    translator = ParamTranslator()
    
    # 根据引擎类型选择验证器
    if ENGINE_TYPE == "naninovel":
        from engines.naninovel.project_files_validator import NaninovelProjectFilesValidatorGenerator
        validator = NaninovelProjectFilesValidatorGenerator(format_config, translator)
    # elif ENGINE_TYPE == "renpy":
    #     from engines.renpy.project_files_validator import RenpyProjectFilesValidatorGenerator
    #     validator = RenpyProjectFilesValidatorGenerator(format_config, translator)
    else:
        raise ValueError(f"不支持的引擎类型: {ENGINE_TYPE}")
    
    return validator

def process_excel_file(file_path, output_path):
    """处理单个Excel文件进行文件验证"""
    try:
        validator = create_validator()
        test_file = pd.read_excel(file_path, sheet_name=None)
        file_basename = os.path.splitext(os.path.basename(file_path))[0]
        
        print(f"\n开始验证文件: {file_basename}")
        
        # 一站式调用完整验证流程
        validation_results = validator.complete_validation(test_file)
        
        # 生成报告（报告生成逻辑也需要相应调整以处理新的结果结构）
        report_data = validator.prepare_report_data(validation_results)
        print_comprehensive_report(report_data, file_basename)
        save_comprehensive_report(report_data, output_path, file_basename)

        # 交互式确认是否执行复制
        copy_plan = validator.generate_copy_plan(validation_results)
        if copy_plan:
            print(f"\n发现 {len(copy_plan)} 个需要复制的文件")
            
            # 显示复制计划预览
            print("\n复制计划预览:")
            for i, plan_item in enumerate(copy_plan, 1):
                print(f"  {i}. {plan_item['file_type']}: {plan_item['filename']}")
                print(f"     从: {plan_item['source_path']}")
                print(f"     到: {plan_item['target_path']}")
            
            # 询问用户确认
            if AUTO_COPY:
                response = 'y'
            else:
                response = input(f"\n是否执行复制操作? (y/N): ").strip().lower()
            if response == 'y':
                # 再次确认，特别是当不是干跑模式时
                
                if not DRY_RUN:
                    final_confirm = input("警告：这将实际复制文件！确认执行? (y/N): ").strip().lower()
                    if final_confirm != 'y':
                        print("已取消复制操作")
                        return
                
                # 创建文件管理器并执行复制
                file_manager = SafeFileManager(dry_run=DRY_RUN)
                
                for plan_item in copy_plan:
                    file_manager.copy_file(
                        plan_item['source_path'],
                        plan_item['target_path'],
                        plan_item['file_type']
                    )
                
                # 打印操作结果
                print(f"\n复制操作结果:")
                file_manager.print_operations()
                
                # 打印摘要
                summary = file_manager.get_operation_summary()
                print(f"\n操作摘要:")
                for status, count in summary.items():
                    if status != 'total':
                        status_display = {
                            'would_copy': '将复制',
                            'success': '成功',
                            'failed': '失败',
                            'skipped': '跳过'
                        }.get(status, status)
                        print(f"  {status_display}: {count}")
                print(f"  总计: {summary['total']}")
                
                if DRY_RUN:
                    print("\n注意: 当前为干跑模式，未实际执行复制操作")
            else:
                print("已跳过复制操作")
        else:
            print("\n没有需要复制的文件")

    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")
        import traceback
        traceback.print_exc()

def generate_file_type_section(file_type, details, output_func, is_console=True):
    """
    生成文件类型部分的报告
    
    Args:
        file_type: 文件类型名称
        details: 该文件类型的详细信息
        output_func: 输出函数（print或文件写入）
        is_console: 是否为控制台输出
    """
    output_func(f"{file_type}文件:")
    output_func("-" * 30)
    
    # 项目库状态
    output_func(f"  项目库: 找到 {len(details['project_found'])} / 缺失 {len(details['project_missing'])}")
    
    # 资源库状态
    output_func(f"  资源库: 找到 {len(details['source_found'])} / 缺失 {len(details['source_missing'])}")
    
    # 对比结果
    if details['missing_in_project_but_in_source']:
        label = "  项目库缺失但资源库存在" if is_console else "项目库缺失但资源库存在的文件:"
        output_func(f"{label} ({len(details['missing_in_project_but_in_source'])}):")
        for filename in sorted(details['missing_in_project_but_in_source']):
            if is_console:
                output_func(f"    ✗ {filename} -> {details['source_results'].get(filename)}")
            else:
                output_func(f"  {filename} -> {details['source_results'].get(filename)}")
    
    if details['missing_in_both']:
        label = "  两个库都缺失" if is_console else "两个库都缺失的文件:"
        output_func(f"{label} ({len(details['missing_in_both'])}):")
        for filename in sorted(details['missing_in_both']):
            if is_console:
                output_func(f"    ✗ {filename}")
            else:
                output_func(f"  {filename}")
    
    if details['inconsistent_files']:
        label = "  文件名不一致" if is_console else "文件名不一致的文件:"
        output_func(f"{label} ({len(details['inconsistent_files'])}):")
        for filename in sorted(details['inconsistent_files']):
            if is_console:
                output_func(f"    ! {filename}: 项目库={details['project_results'].get(filename)}, 资源库={details['source_results'].get(filename)}")
            else:
                output_func(f"  {filename}: 项目库={details['project_results'].get(filename)}, 资源库={details['source_results'].get(filename)}")
    
    # 文件详细状态（仅文件输出）
    if not is_console:
        output_func("所有文件详细状态:")
        for filename in sorted(details['filenames']):
            project_file = details['project_results'].get(filename)
            source_file = details['source_results'].get(filename)
            
            project_status = "✓" if project_file else "✗"
            source_status = "✓" if source_file else "✗"
            
            line = f"  {filename}: 项目库[{project_status}]"
            if project_file:
                line += f" -> {project_file}"
            
            line += " | 资源库[" + source_status + "]"
            if source_file:
                line += f" -> {source_file}"
            
            output_func(line)
    
    if not is_console:
        output_func("")

def generate_summary_section(summary, output_func, is_console=True):
    """
    生成汇总统计部分的报告
    
    Args:
        summary: 汇总统计信息
        output_func: 输出函数
        is_console: 是否为控制台输出
    """
    if is_console:
        output_func(f"\n汇总统计:")
        output_func("-" * 40)
    else:
        output_func(f"总统计:")
        output_func("-" * 30)
    
    output_func(f"总文件数: {summary['total_files']}")
    output_func(f"项目库: 找到 {summary['total_project_found']} | 缺失 {summary['total_project_missing']} | 完成率 {summary['project_completion_rate']:.1f}%")
    output_func(f"资源库: 找到 {summary['total_source_found']} | 缺失 {summary['total_source_missing']} | 完成率 {summary['source_completion_rate']:.1f}%")

def print_comprehensive_report(report_data, file_basename):
    """打印完整的验证报告"""
    file_type_details = report_data['file_type_details']
    summary = report_data['summary']
    
    print(f"\n{'='*60}")
    print(f"文件验证报告: {file_basename}")
    print(f"{'='*60}")
    
    for file_type, details in file_type_details.items():
        generate_file_type_section(file_type, details, print, is_console=True)
    
    generate_summary_section(summary, print, is_console=True)

def save_comprehensive_report(report_data, output_path, file_basename):
    """保存完整验证报告到文件"""
    file_type_details = report_data['file_type_details']
    summary = report_data['summary']
    
    os.makedirs(output_path, exist_ok=True)
    report_file = os.path.join(output_path, f"{file_basename}_validation_report.txt")
    
    with open(report_file, "w", encoding="utf-8") as f:
        def write_line(text):
            f.write(text + "\n")
        
        write_line(f"文件验证详细报告: {file_basename}")
        write_line("=" * 50)
        write_line("")
        
        for file_type, details in file_type_details.items():
            generate_file_type_section(file_type, details, write_line, is_console=False)
        
        generate_summary_section(summary, write_line, is_console=False)
    
    print(f"\n详细报告已保存至: {report_file}")


def main():
    """主函数"""
    
    # 确保目标路径存在
    if not os.path.exists(TARGET_PATH):
        print(f"错误: 目标路径不存在: {TARGET_PATH}")
        return
    
    # 获取所有Excel文件
    excel_files = [f for f in os.listdir(TARGET_PATH) 
                  if f.endswith('.xlsx') and not f.startswith('~')]
    
    if not excel_files:
        print(f"在 {TARGET_PATH} 中没有找到Excel文件")
        return
    
    print(f"找到 {len(excel_files)} 个Excel文件，开始文件验证...")
    
    # 处理每个Excel文件
    for excel_file in excel_files:
        file_path = os.path.join(TARGET_PATH, excel_file)
        process_excel_file(file_path, OUTPUT_PATH)
    
    print("\n所有文件验证完成")

if __name__ == "__main__":
    main()