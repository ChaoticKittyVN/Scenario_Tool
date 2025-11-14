import os
import sys
from core.param_updater import ParamUpdater
from core.config import PARAM_FILE, VARIENT_DATA_FILE

def main():
    """主函数"""
    print("开始更新参数映射和验证")
    
    # 检查参数文件是否存在
    param_files_exist = os.path.exists(PARAM_FILE)
    varient_files_exist = os.path.exists(VARIENT_DATA_FILE)
    
    updator = ParamUpdater()

    if not param_files_exist and not varient_files_exist:
        print("错误: 所有参数文件都不存在")
        print(f"检查的文件:")
        print(f"  - 基础参数: {PARAM_FILE}")
        print(f"  - 差分参数: {VARIENT_DATA_FILE}")
        return False
    
    # 阶段1: 生成基础参数映射
    base_mappings = {}
    if param_files_exist:
        print("\n=== 生成基础参数映射 ===")
        base_mappings = updator.generate_base_param_mappings()
        
        if base_mappings:
            total_mappings = sum(len(m) for m in base_mappings.values())
            print(f"✓ 成功生成 {total_mappings} 个基础参数映射")
            for param_name, mapping in base_mappings.items():
                print(f"  - {param_name}: {len(mapping)} 个映射")
        else:
            print("✗ 基础参数映射生成失败")
            if not varient_files_exist:
                return False  # 如果两个文件都失败才返回错误
    else:
        print("⚠ 警告: 基础参数文件不存在，跳过基础参数映射生成")
    
    # 阶段2: 生成差分参数映射
    varient_mappings = {}
    varient_params = []
    if varient_files_exist:
        print("\n=== 生成差分参数映射 ===")
        varient_mappings, varient_params = updator.generate_varient_param_mappings()
        
        if varient_mappings:
            total_varients = sum(len(m) for m in varient_mappings.values())
            print(f"✓ 成功生成 {total_varients} 个差分参数映射")
            print(f"✓ 共提取 {len(varient_params)} 个差分参数名")
            for character, mapping in varient_mappings.items():
                print(f"  - {character}: {len(mapping)} 个差分映射")
        else:
            print("✗ 差分参数映射生成失败")
            if not param_files_exist:
                return False  # 如果两个文件都失败才返回错误
    else:
        print("⚠ 警告: 差分参数文件不存在，跳过差分参数映射生成")
    
    # 阶段3: 更新验证数据（会同时使用基础参数和差分参数）
    print("\n=== 更新验证数据 ===")
    success = updator.validation_update()
    
    # 输出最终统计信息
    print("\n=== 更新完成统计 ===")
    if base_mappings:
        total_base = sum(len(m) for m in base_mappings.values())
        print(f"基础参数: {total_base} 个映射")
    
    if varient_mappings:
        total_varient = sum(len(m) for m in varient_mappings.values())
        print(f"差分参数: {total_varient} 个映射 ({len(varient_mappings)} 个角色)")
    
    if success:
        print("✓ 参数更新完成")
    else:
        print("✗ 参数更新失败")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)