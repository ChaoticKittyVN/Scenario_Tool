"""
集成测试脚本
测试所有核心功能
"""
import sys
from pathlib import Path

def print_section(title):
    """打印测试章节标题"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_imports():
    """测试模块导入"""
    print_section("测试 1: 模块导入")

    try:
        # 核心模块
        from core.logger import get_logger
        from core.exceptions import ScenarioToolError
        from core.constants import WindowMode
        from core.config_manager import AppConfig
        from core.engine_registry import EngineRegistry
        from core.param_translator import ParamTranslator
        from core.base_sentence_generator import BaseSentenceGenerator
        from core.sentence_generator_manager import SentenceGeneratorManager
        from core.engine_processor import EngineProcessor

        # 引擎模块
        import engines.renpy
        import engines.naninovel

        print("[OK] 所有核心模块导入成功")
        return True
    except Exception as e:
        print(f"[ERROR] 模块导入失败: {e}")
        return False

def test_logger():
    """测试日志系统"""
    print_section("测试 2: 彩色日志系统")

    try:
        from core.logger import get_logger
        logger = get_logger()

        print("\n测试彩色日志输出:")
        logger.debug("这是 DEBUG 级别日志 - 青色")
        logger.info("这是 INFO 级别日志 - 绿色")
        logger.warning("这是 WARNING 级别日志 - 黄色")
        logger.error("这是 ERROR 级别日志 - 红色")
        logger.critical("这是 CRITICAL 级别日志 - 紫色")

        print("\n[OK] 日志系统测试通过")
        return True
    except Exception as e:
        print(f"[ERROR] 日志系统测试失败: {e}")
        return False

def test_config():
    """测试配置管理"""
    print_section("测试 3: 配置管理")

    try:
        from core.config_manager import AppConfig

        # 测试从文件加载配置
        config_path = Path("config.yaml")
        if not config_path.exists():
            print("[ERROR] config.yaml 文件不存在")
            return False

        config = AppConfig.from_file(config_path)
        print(f"[OK] 配置文件加载成功")
        print(f"    引擎类型: {config.engine.engine_type}")
        print(f"    输入目录: {config.paths.input_dir}")
        print(f"    输出目录: {config.paths.output_dir}")

        # 测试引擎切换
        print("\n测试引擎配置:")
        for engine_type in ["renpy", "naninovel"]:
            test_config = AppConfig.from_dict({
                "engine": {"engine_type": engine_type}
            })
            print(f"[OK] {engine_type} 引擎配置加载成功")

        return True
    except Exception as e:
        print(f"[ERROR] 配置管理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_engine_registry():
    """测试引擎注册表"""
    print_section("测试 4: 引擎注册表")

    try:
        from core.engine_registry import EngineRegistry

        # 导入引擎模块以触发注册
        import engines.renpy
        import engines.naninovel

        # 列出所有注册的引擎
        engines = EngineRegistry.list_engines()
        print(f"[OK] 已注册的引擎: {', '.join(engines)}")

        # 测试获取引擎信息
        for engine_name in engines:
            meta = EngineRegistry.get(engine_name)
            print(f"    - {meta.display_name}: {meta.file_extension}")

        return True
    except Exception as e:
        print(f"[ERROR] 引擎注册表测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_param_translator():
    """测试参数翻译器"""
    print_section("测试 5: 参数翻译器")

    try:
        from core.param_translator import ParamTranslator
        from pathlib import Path

        param_config_dir = Path("param_config")

        if not param_config_dir.exists():
            print("[SKIP] param_config 目录不存在，跳过测试")
            return True

        # ParamTranslator 在初始化时自动加载配置
        translator = ParamTranslator()
        print("[OK] 参数翻译器初始化成功")

        # 测试翻译功能
        available_types = translator.get_available_types()
        print(f"[OK] 可用参数类型: {len(available_types)} 个")

        # 测试单个翻译
        if available_types:
            test_type = available_types[0]
            params = translator.get_params_for_type(test_type)
            if params:
                test_param = params[0]
                result = translator.translate(test_type, test_param)
                print(f"[OK] 参数翻译测试通过")
            else:
                print(f"[OK] 参数翻译器功能正常")

        return True
    except Exception as e:
        print(f"[ERROR] 参数翻译器测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_exceptions():
    """测试异常系统"""
    print_section("测试 6: 异常系统")

    try:
        from core.exceptions import (
            ScenarioToolError, ConfigError, EngineError,
            GeneratorError, TranslationError, ExcelParseError,
            FileValidationError, EngineNotRegisteredError,
            InvalidParameterError
        )

        exception_classes = [
            ScenarioToolError, ConfigError, EngineError,
            GeneratorError, TranslationError, ExcelParseError,
            FileValidationError, EngineNotRegisteredError,
            InvalidParameterError
        ]

        print(f"[OK] 已定义 {len(exception_classes)} 个异常类:")
        for exc_class in exception_classes:
            print(f"    - {exc_class.__name__}")

        return True
    except Exception as e:
        print(f"[ERROR] 异常系统测试失败: {e}")
        return False

def test_constants():
    """测试常量管理"""
    print_section("测试 7: 常量管理")

    try:
        from core.constants import (
            WindowMode, SpecialSpeaker, SheetName, Marker
        )

        print("[OK] 常量枚举类:")
        print(f"    - WindowMode: {[m.value for m in WindowMode]}")
        print(f"    - SpecialSpeaker: {[s.value for s in SpecialSpeaker]}")
        print(f"    - SheetName: {[s.value for s in SheetName]}")
        print(f"    - Marker: {[m.value for m in Marker]}")

        return True
    except Exception as e:
        print(f"[ERROR] 常量管理测试失败: {e}")
        return False

def test_param_update():
    """测试参数映射更新"""
    print_section("测试 8: 参数映射更新")

    try:
        from core.config_manager import AppConfig
        from pathlib import Path

        # 检查参数文件是否存在
        config = AppConfig.from_file(Path("config.yaml"))
        engine_type = config.engine.engine_type
        param_file = Path(config.paths.param_config_dir) / f"param_data_{engine_type}.xlsx"

        if not param_file.exists():
            print(f"[SKIP] 参数文件不存在: {param_file}")
            return True

        # 导入 ParamUpdater
        import sys
        sys.path.insert(0, str(Path.cwd()))
        from update_param import ParamUpdater

        # 创建更新器并测试
        updater = ParamUpdater(config)
        print(f"[OK] ParamUpdater 初始化成功")

        # 测试读取参数文件
        mappings = updater.read_param_file(param_file)
        if mappings:
            print(f"[OK] 读取参数文件成功: {len(mappings)} 个工作表")
        else:
            print(f"[ERROR] 读取参数文件失败")
            return False

        # 检查生成的映射文件
        output_file = Path(config.paths.param_config_dir) / "param_mappings.py"
        if output_file.exists():
            print(f"[OK] 参数映射文件存在: {output_file.name}")
        else:
            print(f"[SKIP] 参数映射文件不存在（需要运行 update_param.py）")

        return True
    except Exception as e:
        print(f"[ERROR] 参数映射更新测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("  Scenario Tool - 集成测试")
    print("="*60)

    tests = [
        ("模块导入", test_imports),
        ("彩色日志系统", test_logger),
        ("配置管理", test_config),
        ("引擎注册表", test_engine_registry),
        ("参数翻译器", test_param_translator),
        ("异常系统", test_exceptions),
        ("常量管理", test_constants),
        ("参数映射更新", test_param_update),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n[ERROR] 测试 '{name}' 执行失败: {e}")
            results.append((name, False))

    # 打印测试总结
    print_section("测试总结")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\n总计: {passed}/{total} 测试通过\n")

    for name, result in results:
        status = "[OK]" if result else "[ERROR]"
        print(f"{status} {name}")

    print("\n" + "="*60)

    if passed == total:
        print("所有测试通过!")
        return 0
    else:
        print(f"有 {total - passed} 个测试失败")
        return 1

if __name__ == "__main__":
    sys.exit(main())
