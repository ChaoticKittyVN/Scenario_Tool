# # naninovel引擎专用
# from engines.naninovel.param_processor import ParamProcessor
# import core.param_translator as translator
# from .engine_param_config import PARAM_GROUPS # 从同级目录的format_config导入

# # 参数列表定义
# note_audio_params = PARAM_GROUPS["note_audio"]
# background_params = PARAM_GROUPS["background"]
# character_params = PARAM_GROUPS["character"]
# hide_trans_params = PARAM_GROUPS["hide_trans"]
# text_command_params = PARAM_GROUPS["text_command"]

# # 初始化翻译器和参数处理器
# module_file = "param_config/param_mappings.py"
# translator = translator.ParamTranslator(module_file)
# processor = ParamProcessor(translator)

# # 抓取指定系列参数
# def params_generate(i: int, excel_dict: dict, params_list: list):
#     params = {}
#     for param in params_list:
#         params[param] = excel_dict.get(param)[i]
#     return params

# # 注释、音乐、清除图层指令生成
# def note_audio_generate(i: int, excel_dict: dict):
#     params = params_generate(i, excel_dict, note_audio_params)
#     results = []
    
#     for name, param in params.items():
#         result = processor.process_param(name, param)
#         if result:
#             results.append(result)
    
#     return results

# # 场景图片指令生成
# def scene_generate(i, excel_dict: dict):
#     params = params_generate(i, excel_dict, background_params)
#     return processor.process_composite(params, "background")

# # 立绘图片指令生成
# def figure_generate(i, excel_dict: dict):
#     params = params_generate(i, excel_dict, character_params)
#     return processor.process_composite(params, "character")

# # 隐藏、总转场效果指令生成
# def hide_trans_generate(i, excel_dict: dict):
#     params = params_generate(i, excel_dict, hide_trans_params)
#     return processor.process_composite(params, "hide_trans")

# # 文本指令生成
# def text_command_generate(i: int, excel_dict: dict):
#     params = params_generate(i, excel_dict, text_command_params)
#     return processor.process_composite(params, "text")

# def generate_all_commands(i, excel_dict):
#     """生成所有类型的命令"""
#     results = []
    
#     # 按顺序生成各种类型的命令
#     results.extend(note_audio_generate(i, excel_dict))
#     results.extend(scene_generate(i, excel_dict))
#     results.extend(figure_generate(i, excel_dict))
#     results.extend(hide_trans_generate(i, excel_dict))
#     results.extend(text_command_generate(i, excel_dict))
    
#     return results