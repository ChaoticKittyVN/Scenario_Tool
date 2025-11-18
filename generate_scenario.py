import pandas as pd
import os
from core.engine_processor import EngineProcessor
from tqdm import tqdm
from core.config import TARGET_PATH, OUTPUT_PATH, ENGINE_TYPE, get_engine_config, IGNORE_MODE, IGNORE_WORDS

def create_processor():
    """创建处理器实例"""
    
    from core.param_translator import ParamTranslator
    
    # 创建翻译器和上下文管理器实例
    translator = ParamTranslator()
    
    # 创建处理器 - 现在只需要传入引擎类型和依赖组件
    processor = EngineProcessor(ENGINE_TYPE, translator)
    processor.setup()
    
    return processor

# TODO 方法过大，需要解耦，读表部分需要改为使用目前名为param_extractor和data_reader的对象
def process_excel_file(file_path, output_path):
    """处理单个Excel文件"""
    try:
        processor = create_processor()
    
        # 读取Excel文件
        test_file = pd.read_excel(file_path, sheet_name=None, dtype=str)
        sheet_names = list(test_file.keys())

        # 获取文件基本名（不含扩展名）
        file_basename = os.path.splitext(os.path.basename(file_path))[0]
        
        # 处理每个工作表
        for sheet in sheet_names:
            if sheet == '参数表':
                continue
                
            # 根据引擎类型确定输出文件扩展名
            if ENGINE_TYPE == "renpy":
                scenario_name = f"{sheet}.rpy"
            elif ENGINE_TYPE == "naninovel":
                scenario_name = f"{sheet}.nani"
            else:
                scenario_name = f"{sheet}.txt"
            
            # 检查结束标记
            if "Note" not in test_file[sheet].columns or "END" not in test_file[sheet]["Note"].tolist():
                print(f"工作表 {sheet} 不包含Note列或END标记，跳过")
                continue
                
            i = test_file[sheet]["Note"].tolist().index("END")
            j = 0
            out_put_list = []

            # 批量提取需要处理的行数据
            valid_indices = []
            for j in range(i):
                if test_file[sheet].iloc[j].get("Ignore") in IGNORE_WORDS and IGNORE_MODE:
                    continue
                valid_indices.append(j)

            # 一次性获取所有需要处理的行
            if valid_indices:
                valid_rows_df = test_file[sheet].loc[valid_indices]

            with tqdm(total=len(valid_indices), desc=f"处理 {file_basename} - {sheet}") as pbar:
                # 批量处理
                for idx in range(len(valid_rows_df)):
                    row_data = valid_rows_df.iloc[idx]
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
                            out_put.write("    " + line + "\n")
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