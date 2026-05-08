"""
Naninovel Character Generator
生成角色相关命令
"""
from core.base_sentence_generator import BaseSentenceGenerator


class CharacterGenerator(BaseSentenceGenerator):
    """角色生成器"""

    animation_calculate_mode = True

    # 资源配置 - 用于资源验证
    resource_config = {
        "resource_type": "Character",
        "resource_category": "图片",
        "main_param": "Character",
        "part_params": ["Variant"],
        "separator": ".",
        "folder": "Characters/"
    }

    param_config = {
        "TransChar": {
            "translate_type": "TransitionType",
        },

        "Character": {
            "translate_type": "Character",
        },

        "Variant": {
            "translate_type": "Variant"
        },

        "Pose": {
            "translate_type": "Pose",
            "format": " pose:{value}"
        },

        "Position": {
            "format": " position:{value}"
        },

        "Scale": {
            "format": " scale:{value}"
        },

        "Visible": {
            "format": " visible:{value}"
        },

        "Tint": {
            "translate_type": "Tint",
            "format": " tint:{value}"
        },

        "Wait": {
            "format": " wait:true"
        },

        "Time": {
            "format": " time:{value}",
            "default": "0.5"
        },

        "CharAnim": {
            "translate_type": "Character",
        },

        "CharAnimParam": {
            "translate_type": "Animation"
        },

        "CharPose": {},

        "Xoffset": {},
        "Yoffset": {},

        "AnimRepeat": {},

        "CharAnimWait": {},

        "Transition": {},
    }


    pose_pos_mapping = {
        "中": {
            "x": 0,
            "y": 0
        },
        "左": {
            "x": -100,
            "y": 0
        },
        "右": {
            "x": 100,
            "y": 0
        },
    }

    animation_config = {
        "JumpUp": {
            "xoffset": 0,
            "yoffset": 50,
            "repeat": 1,
            "default_time": "0.3",
            "lines": [
                "    @char {char} position:{x},{y_plus_offset} time:{time}",
                "    @char {char} position:{x},{y} time:{time}"
            ],
            "end_line": "@await {anim}"
        },
        "ShakeHead": {
            "xoffset": 20,
            "yoffset": 0,
            "repeat": 1,
            "default_time": "0.3",
            "lines": [
                "    @char {char} position:{x_minus_offset},{y} time:{time}",
                "    @char {char} position:{x},{y} time:{time}",
                "    @char {char} position:{x_plus_offset},{y} time:{time}",
                "    @char {char} position:{x},{y} time:{time}"
            ],
            "end_line": "@await {anim}"
        },
    }

    def __init__(self, translator, engine_config):
        super().__init__(translator, engine_config)

        if self.animation_calculate_mode:
            self.char_pose_cache = {}


    @property
    def category(self):
        return "Character"

    @property
    def priority(self) -> int:
        return 300

    def process(self, data):
        """
        处理角色参数

        Args:
            data: 参数字典

        Returns:
            List[str]: 生成的角色命令
        """
        if not self.can_process(data):
            return None

        data = self.do_translate(data)

        """构建角色命令"""
        # 检查是否有足够的上下文生成角色命令
        char = self.get_value("Character", data)
        anim = self.get_value("CharAnimParam", data)

        if not char and not anim:
            return []
        
        lines = []
        trans = self.get_value("TransChar", data)

        if trans in ["block", "trans"] or self.exists_param("Transition", data):
            command = "    "
        else:
            command = ""

        if char == "hideAll":
            lines.append(f"{command}@hideChars")
            # 构建角色命令

        elif char:
            image = char

            if trans == "hide":
                command += "@hide "
            else:
                command += "@char "
                variant = self.get_value("Variant", data)

                # 使用variant_data时使用以下指令进行翻译
                # self.translator._translate_variant(variant,image)

                # 差分名，如有需要使用多参数组合
                image += f".{variant}"

            # 添加姿势
            pose = self.get_sentence("Pose", data)
            
            # 添加位置
            position = self.get_sentence("Position", data)
            
            # 添加缩放
            scale = self.get_sentence("Scale", data)
            
            # 添加可见性
            visible = self.get_sentence("Visible", data)
            
            # 添加色调
            tint = self.get_sentence("Tint", data)
            
            # 添加等待参数
            wait = self.get_sentence("Wait", data)

            line = (f"{command}{image}{pose}{position}{scale}{visible}{tint}{wait}")
            # 构建最终命令
            if trans == "trans":
                time = self.get_sentence("Time", data, use_default=True)
                lines.append(f"@trans{time}")
                lines.append("    @hideChars")
                lines.append(line)
            else:
                time = self.get_sentence("Time", data)
                lines.append(f"{line}{time}")

        if self.animation_calculate_mode:
            if self.exists_param("Pose", data):
                pose = self.get_value("Pose", data)
                self.char_pose_cache[char] = pose


        if anim:
            if self.animation_calculate_mode:

                anim = self.get_value("CharAnimParam", data)
                if self.exists_param("CharAnim", data):
                    char_anim = self.get_value("CharAnim", data)
                    if char_anim == "hideAll":
                        lines.append(f"@stop {anim}")
                else:
                    char_anim = char

                char_anim_pose = self.get_value("CharPose", data) if self.exists_param("CharPose", data) else self.char_pose_cache.get(char_anim, "Middle")

                x_offset = int(self.get_value("Xoffset", data)) if self.exists_param("Xoffset", data) else self.animation_config[anim]["xoffset"]
                y_offset = int(self.get_value("Yoffset", data)) if self.exists_param("Yoffset", data) else self.animation_config[anim]["yoffset"]

                positions = self.calculate_animation_positions(char_anim_pose, xoffset=x_offset, yoffset=y_offset)

                repeat_times = int(self.get_value("AnimRepeat", data)) if self.exists_param("AnimRepeat", data) else self.animation_config[anim]["repeat"]

                # 提前构建单次动画的命令列表（避免重复代码）
                anim_time = self.animation_config[anim].get("default_time", "0.1")
                single_commands = []
                for line_template in self.animation_config[anim]["lines"]:
                    single_commands.append(line_template.format(
                        char=char_anim,
                        x=positions['x'], y=positions['y'],
                        x_plus_offset=positions['x_plus_offset'], x_minus_offset=positions['x_minus_offset'],
                        y_plus_offset=positions['y_plus_offset'], y_minus_offset=positions['y_minus_offset'],
                        time=anim_time
                    ))

                # 添加动画启动命令
                if repeat_times == -1:
                    lines.append(f"@async {anim} loop:true")
                else:
                    lines.append(f"@async {anim}")

                # 添加动画命令组
                if repeat_times == -1 or repeat_times == 0:
                    # 播放一次（用于启动无限循环，或者原逻辑处理 0 次的情况）
                    lines.extend(single_commands)
                elif repeat_times > 0:
                    # 重复多次：直接将命令组列表重复 repeat_times 次
                    lines.extend(single_commands * repeat_times)

                # if "end_line" in self.animation_config[anim]:
                #     end_line = self.animation_config[anim]["end_line"].format(anim=anim)
                #     lines.append(end_line)
    
            else: 
                char_anim = self.get_value("CharAnim", data)
                if not char_anim:
                    char_anim = char
                
                anim = self.get_value("CharAnimParam", data)

                anim_wait = ""

                if self.exists_param("CharAnimWait", data):
                    anim_wait = " wait:true"

                lines.append(f"@animate {char} {anim}{anim_wait}")

        return lines
    
    def calculate_animation_positions(self, pose, xoffset=0, yoffset=0):
        """
        计算动画中使用的各种位置（包括正负偏移），使用 round 函数控制小数位数
        """
        # 获取基础位置坐标
        base_pos = self.pose_pos_mapping.get(pose, {"x": 0, "y": 0})
        base_x = base_pos["x"]
        base_y = base_pos["y"]

        # 计算带正负偏移的位置，使用 round 限制小数位数到3位
        x_plus_offset = round(base_x + xoffset, 3)
        x_minus_offset = round(base_x - xoffset, 3)
        y_plus_offset = round(base_y + yoffset, 3)
        y_minus_offset = round(base_y - yoffset, 3)

        # 返回包含所有位置的字典
        positions = {
            'x': base_x,
            'y': base_y,
            'x_plus_offset': x_plus_offset,
            'x_minus_offset': x_minus_offset,
            'y_plus_offset': y_plus_offset,
            'y_minus_offset': y_minus_offset
        }
        
        return positions
