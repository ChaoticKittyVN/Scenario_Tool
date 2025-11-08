# from core.base_sentence_generator import BaseSentenceGenerator

# class TextGenerator(BaseSentenceGenerator):

#     @property
#     def category(self):
#         return "Transition"

#     @property
#     def priority(self) -> int:
#         return 800

#     def process(self, data):
#         if not self.can_process(data):
#             return

#         results = []

#         # 处理全局转场效果
#         trans_with = data.get("TransWith")
#         if trans_with:
#             # 处理转场效果属性
#             trans_with = self.translator.translate("Transition", trans_with)
#             trans_with_atr = data.get("TransWithAtr")
#             if trans_with_atr:
#                 if trans_with == "dissolve":
#                     trans_with = f"Dissolve({trans_with_atr})"
#                 else:
#                     trans_with = f"{trans_with}({trans_with_atr})"
            
#             # 构建转场命令
#             result = f"with {trans_with}"
#             results.append(result)
        
#         return results