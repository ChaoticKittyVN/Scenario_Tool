import pandas as pd
import os
from engines.naninovel import scenario_generator as sg
from core.engine_processor import EngineProcessor as ep
from tqdm import tqdm
from core.config import TARGET_PATH, OUTPUT_PATH, ENGINE_TYPE, get_engine_config, IGNORE_MODE, IGNORE_WORDS

def create_simple_processor():
    """创建简单的测试处理器"""
    import importlib
    from core.engine_processor import EngineProcessor
    from core.generator_loader import discover_generators
    
    # 临时导入配置
    engine_config_path = f"engines.{ENGINE_TYPE}.engine_param_config"
    engine_config = importlib.import_module(engine_config_path)
    format_config = engine_config.FORMAT_CONFIG
    from core.param_translator import ParamTranslator  # 假设有这个模块
    
    # 创建翻译器实例
    translator = ParamTranslator()  # 你可能需要根据实际情况初始化
    
    # 自动发现生成器，传入必需的参数
    generators = discover_generators(ENGINE_TYPE, format_config, translator)
    
    # 如果没有发现任何生成器，创建一个临时的
    if not generators:
        print("警告: 未发现任何生成器")
    
    # 创建处理器
    processor = EngineProcessor(generators, translator, None)
    processor.setup(format_config)
    
    return processor


def process_excel_file(file_path, output_path):
    """处理单个Excel文件"""
    try:
        processor = create_simple_processor()
        # 读取Excel文件
        test_file = pd.read_excel(file_path, sheet_name=None)
        sheet_names = list(test_file.keys())

        # 获取文件基本名（不含扩展名）
        file_basename = os.path.splitext(os.path.basename(file_path))[0]
        
        # 处理每个工作表
        for sheet in sheet_names:
            if sheet == '参数表':
                continue
                
            # 根据引擎类型确定输出文件扩展名
            if ENGINE_TYPE == "renpy":
                scenario_name = f"{sheet}.rpy" # f"{file_basename}_{sheet}.rpy"
            elif ENGINE_TYPE == "naninovel":
                # 为其他引擎预留
                scenario_name = f"{sheet}.nani" # f"{file_basename}_{sheet}.txt"
            else:
                # 为其他引擎预留
                scenario_name = f"{sheet}.txt" # f"{file_basename}_{sheet}.txt"
            
            # 检查结束标记
            if "Note" not in test_file[sheet].columns or "END" not in test_file[sheet]["Note"].tolist():
                print(f"工作表 {sheet} 不包含Note列或END标记，跳过")
                continue
                
            i = test_file[sheet]["Note"].tolist().index("END")
            j = 0
            out_put_list = []

            # ✅ 优化：批量提取需要处理的行数据，避免重复的iloc调用
            valid_indices = []
            for j in range(i):
                if test_file[sheet].iloc[j].get("Ignore") in IGNORE_WORDS and IGNORE_MODE:
                    continue
                valid_indices.append(j)

            # ✅ 优化：一次性获取所有需要处理的行
            if valid_indices:
                # 方法1：使用loc一次性获取所有行（推荐）
                valid_rows_df = test_file[sheet].loc[valid_indices]

            with tqdm(total=i, desc=f"处理 {file_basename} - {sheet}") as pbar:
                # ✅ 优化：批量处理，避免重复的DataFrame索引
                for idx in range(len(valid_rows_df)):
                    row_data = valid_rows_df.iloc[idx]  # 这个开销比从原始DataFrame获取小
                    out_put_list.extend(processor.process_row(row_data))
                    pbar.update(1)

            # 确保输出目录存在
            os.makedirs(output_path, exist_ok=True)
            
            # 根据引擎配置处理输出格式
            output_file_path = os.path.join(output_path, scenario_name)
            with open(output_file_path, "w", encoding="utf-8") as out_put:
                for line in out_put_list:
                    # Ren'Py 特定的缩进处理
                    if ENGINE_TYPE == "renpy":
                        if line.strip().startswith("label "):
                            out_put.write(line.strip() + "\n")
                        else:
                            out_put.write("    " + line.strip() + "\n")
                    else:
                        # 其他引擎的默认处理
                        out_put.write(line + "\n")
                        
            print(f"已生成: {output_file_path}")
            
    except Exception as e:
        print(f"处理文件 {file_path} 时出错: {e}")

def main():
    """主函数"""
    # 获取当前引擎配置
    engine_config = get_engine_config()
    
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
    
    print(f"找到 {len(excel_files)} 个Excel文件，开始处理...")
    
    # 处理每个Excel文件
    for excel_file in excel_files:
        file_path = os.path.join(TARGET_PATH, excel_file)
        print(f"\n处理文件: {excel_file}")
        process_excel_file(file_path, OUTPUT_PATH)
    
    print("\n所有文件处理完成")

if __name__ == "__main__":
    main()

