# renpy引擎专用
# 参数类型列表
PARAM_NAMES = ["Layer", "Transform", "Transition",
                "Speaker", "Figure", "Varient", "Animation",
                  "Background", "Event", 
                  "Movie", "Music", "Sound"]

# 参数组
PARAM_GROUPS = {
    "note_audio": ["Note", "SceneOnlayer", "Music", "Ambience", "Sound", "Voice"],
    "scene": ["UseScene", "Background", "Event", "EventAtr", "At", "Onlayer", "With", "WithAtr"],
    "figure": ['Show', 'ShowAtr0', 'ShowAtr1', 'ShowAtr2', 'ShowAtr3', 'ShowAt', 'ShowOnlayer', 'ShowWith', 'ShowWithAtr', 'ShowATL'],
    "hide_trans": ['Hide', 'HideOnlayer', 'HideWith', 'HideWithAtr', 'TransWith', 'TransWithAtr'],
    "text_command": ['WindowShow', 'Speaker', 'Text', 'WindowHide']
}
# 管道顺序列表
GENERATOR_PIPELINE = [
    "NoteAudioGenerator",
    "SceneGenerator", 
    "FigureGenerator",
    "HideTransGenerator",
    "TextGenerator"
]

# 格式配置字典
FORMAT_CONFIG = {
    "Note": {
        "category": "Note",
    },
    "Music": {
        "category": "Audio",
        "translate_type": "Music",
    },
    "Sound": {
        "category": "Audio",
        "translate_type": "Sound",
    },
    "Ambience": {
        "category": "Audio",
        "translate_type": "Ambience",
    },
    "Voice": {
        "category": "Audio",
        "audio_behavior": True,
    },

    "SceneOnlayer": {
        "category": "SceneClear",
        "translate_type": "Layer",
    },
    # 场景相关参数
    "UseScene": {
        "category": "Background",
    },
    "Background": {
        "category": "Background",
        "translate_type": "Background",
    },
    "Event": {
        "category": "Background",
        "translate_type": "Event",
    },
    "EventAtr": {
        "category": "Background",
    },
    "At": {
        "category": "Background",
        "translate_type": "Transform",
    },
    "Onlayer": {
        "category": "Background",
        "translate_type": "Layer",
    },
    "With": {
        "category": "Background",
        "translate_type": "Transition",
    },
    "WithAtr": {
        "category": "Background",
    },
    # 立绘相关参数
    "Show": {
        "category": "Figure",
        "translate_type": "Figure",
    },

    "ShowAtr0": {
        "category": "Figure",
        "translate_type": "Varient",
    },

    "ShowAtr1": {
        "category": "Figure",
    },

    "ShowAtr2": {
        "category": "Figure",
    },

    "ShowAtr3": {
        "category": "Figure",
    },

    "ShowAt": {
        "category": "Figure",
        "translate_type": "Transform",
    },

    "ShowOnlayer": {
        "category": "Figure",
        "translate_type": "Layer",
    },

    "ShowWith": {
        "category": "Figure",
        "translate_type": "Transition",
    },

    "ShowWithAtr": {
        "category": "Figure",
    },

    "ShowATL": {
        "category": "Figure",
        "translate_type": "Animation",
    },
    
    # 隐藏和转场相关参数
    "Hide": {
        "category": "Hide",
        "translate_types": ["Figure", "Background", "Event"],
        "default_type": "Figure"
    },

    "HideOnlayer": {
        "category": "Hide",
        "translate_type": "Layer",
    },

    "HideWith": {
        "category": "Hide",
        "translate_type": "Transition",
    },

    "HideWithAtr": {
        "category": "Hide",
    },

    "TransWith": {
        "category": "Transition",
        "translate_type": "Transition",
    },

    "TransWithAtr": {
        "category": "Transition",
    },
    
    # 文本相关参数
    "WindowShow": {
        "category": "Text",
        "format": "window show"
    },

    "Speaker": {
        "category": "Text",
        "translate_type": "Speaker",
    },

    "Text": {
        "category": "Text",
    },
    
    "WindowHide": {
        "category": "Text",
        "format": "window hide"
    }
}

