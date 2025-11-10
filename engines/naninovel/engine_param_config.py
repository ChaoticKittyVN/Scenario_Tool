# naninovel引擎专用

# 格式配置字典
FORMAT_CONFIG = {
    "Note": {
        "category": "Note",
        "format": ";{value}"
    },
    "Music": {
        "category": "Audio",
        "format_stop": "@stopBgm wait:False",
        "format": '@bgm Music/{value}',
        "audio_behavior": True,
        "translate_type": "Music",
    },
    "Sound": {
        "category": "Audio",
        "format_stop": "@stopSound wait:False",
        "format": '@sfx SFX/{value}',
        "audio_behavior": True,
        "translate_type": "Sound",
    },
    "Ambience": {
        "category": "Audio",
        "format_stop": "@stopSound wait:False",
        "format": '@sfx SFX/{value} loop:True',
        "audio_behavior": True,
        "translate_type": "Ambience",
    },
    "Voice": {
        "category": "Audio",
        "format_stop": "@stopVoice",
        "format": '@voice {value}',
        "audio_behavior": True,
    },
    # 场景相关参数
    "Back": {
        "category": "Background",
        "translate_type": "Background",
    },
    "BackID": {
        "category": "Background",
        "translate_type": "Id",
        "format":"id:{value}"
    },
    "BackScale": {
        "category": "Background",
        "format":"sacle:{value}"
    },
    "BackPos": {
        "category": "Background",
        "format":"pos:{value}"
    },
    "BackVisible": {
        "category": "Background",
        "format":"visible:{value}"
    },
    "BackWait": {
        "category": "Background",
        "format":"wait:{value}"
    },
    "Dissolve": {
        "category": "Background",
        "translate_type": "Transition",
        "format":"dissolve:{value}"
    },
    "DissolveParam": {
        "category": "Background",
        "format":"params:{value}"
    },
    "BackTime": {
        "category": "Background",
        "format":"time:{value}"
    },
    # 立绘相关参数
    "Char": {
        "category": "Character",
        "translate_type": "Character",
        "format":"{value}.{varient}"
    },
    "Varient": {
        "category": "Character",
        "translate_type": "Varient"
    },
    "Pose": {
        "category": "Character",
        "translate_type": "Pose",
        "format":"pose:{value}"
    },
    "Position": {
        "category": "Character",
        "format":"position:{value}"
    },
    "Scale": {
        "category": "Character",
        "format":"scale:{value}"
    },
    "Visible": {
        "category": "Character",
        "format":"visible:{value}"
    },
    "Tint": {
        "category": "Character",
        "translate_type": "Tint",
        "format":"tint:{value}"
    },
    "Wait": {
        "category": "Character",
        "format":"wait:{value}"
    },
    "Time": {
        "category": "Character",
        "format":"time:{value}"
    },
    
    # 隐藏和转场相关参数
    "Hide": {
        "category": "Hide",
        "translate_type": "Character",
    },

    "HideWait":{
        "category": "Hide",
        "format":"wait:{value}"
    },

    "HideChars": {
        "category": "Hide",
    },

    "HideCharsWait": {
        "category": "Hide",
        "format":"wait:{value}"
    },
    "Transition": {
        "translate_type": "Transition",
    },
    
    # 文本相关参数
    "Printer": {
        "category": "Text",
    },
    "PrinterPos": {
        "category": "Text",
        "format":"pos:{value}"
    },
    "Speaker": {
        "category": "Text",
        "translate_type":"Speaker",
    },
    "Text": {
        "category": "Text",
    },
    "HidePrinter": {
        "category": "Text",
        "format": "@hidePrinter"
    }
}

PARAM_NAMES = []

for name,property in FORMAT_CONFIG.items():
    if "translate_type" in property or "translate_types" in property:
        PARAM_NAMES.append(name)