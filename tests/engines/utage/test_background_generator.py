import unittest

import pandas as pd

from core.engine_processor import EngineProcessor
from core.scenario_state.effects import VisualEffectType, VisualStateEffect
from engines.utage.config import UtageConfig
from engines.utage.sentence_generators.background_generator import (
    BackgroundAction,
    BackgroundGenerator,
)


class StubTranslator:
    WAIT_TYPES = {
        "下同": "Add",
        "不等待": "NoWait",
    }

    def translate(self, param_type, value):
        if param_type == "WaitType":
            return self.WAIT_TYPES.get(value, value)
        return value

    def has_mapping(self, param_type, value):
        return False


class BackgroundGeneratorTest(unittest.TestCase):
    def setUp(self):
        self.translator = StubTranslator()
        self.generator = BackgroundGenerator(self.translator, UtageConfig())

    def test_displays_background_with_existing_optional_params(self):
        result = self.generator.process(
            {
                "Bg": "桂花林",
                "BgAtr": "夜",
                "BgLayer": "近景左",
                "BgX": "10",
                "BgY": "20",
                "WaitType": "下同",
            }
        )

        self.assertEqual(
            result,
            [
                {
                    "Command": "Bg",
                    "Arg1": "桂花林夜",
                    "Arg3": "近景左",
                    "Arg4": "10",
                    "Arg5": "20",
                    "WaitType": "Add",
                    "Arg6": "1",
                }
            ],
        )

    def test_resolves_display_once_for_rendering_and_state_analysis(self):
        operation = self.generator.resolve(
            {
                "Bg": "桂花林",
                "BgAtr": "夜",
                "BgLayer": "近景左",
                "BgX": "10",
                "BgY": "20",
                "WaitType": "下同",
            }
        )

        self.assertEqual(operation.action, BackgroundAction.SHOW)
        self.assertEqual(operation.resource_type, "Background")
        self.assertEqual(operation.resource, "桂花林夜")
        self.assertEqual(operation.layer, "近景左")
        self.assertEqual(operation.fade, "1")
        self.assertEqual(operation.wait_type, "Add")
        self.assertEqual(
            self.generator.render(operation),
            self.generator.process(
                {
                    "Bg": "桂花林",
                    "BgAtr": "夜",
                    "BgLayer": "近景左",
                    "BgX": "10",
                    "BgY": "20",
                    "WaitType": "下同",
                }
            ),
        )

    def test_emits_show_state_effect(self):
        context = {"sheet": "Scene01", "row": 12}

        effects = self.generator.state_effects(
            {
                "Bg": "桂花林",
                "BgAtr": "夜",
                "BgLayer": "近景左",
                "BgFade": "0.5",
            },
            context=context,
        )

        self.assertEqual(
            effects,
            [
                VisualStateEffect(
                    effect_type=VisualEffectType.SHOW,
                    resource_type="Background",
                    resource="桂花林夜",
                    layer="近景左",
                    transition_duration="0.5",
                    context=context,
                )
            ],
        )

    def test_hides_background_from_bg_context(self):
        result = self.generator.process(
            {
                "BgCommand": "隐藏",
                "Bg": "桂花林",
                "BgFade": "0.5",
            }
        )

        self.assertEqual(result, [{"Command": "BgOff", "Arg6": "0.5"}])

    def test_hides_event_from_event_context(self):
        result = self.generator.process(
            {
                "BgCommand": "隐藏",
                "BgEvent": "看日出",
            }
        )

        self.assertEqual(result, [{"Command": "BgEventOff", "Arg6": "1"}])

    def test_emits_hide_state_effect(self):
        effects = self.generator.state_effects(
            {
                "BgCommand": "隐藏",
                "BgEvent": "看日出",
            }
        )

        self.assertEqual(
            effects,
            [
                VisualStateEffect(
                    effect_type=VisualEffectType.HIDE,
                    resource_type="Event",
                    layer="BG",
                    transition_duration="1",
                )
            ],
        )

    def test_hide_requires_exactly_one_background_type(self):
        self.assertIsNone(self.generator.process({"BgCommand": "隐藏"}))
        self.assertIsNone(
            self.generator.process(
                {
                    "BgCommand": "隐藏",
                    "Bg": "桂花林",
                    "BgEvent": "看日出",
                }
            )
        )

    def test_changes_to_closeup_layer_with_keep_local(self):
        result = self.generator.process(
            {
                "BgCommand": "换图层",
                "BgLayer": "近景左",
                "WaitType": "不等待",
            }
        )

        self.assertEqual(
            result,
            [
                {
                    "Command": "ChangeLayer",
                    "Arg1": "BG",
                    "Arg2": "KeepLocal",
                    "Arg3": "近景左",
                    "WaitType": "NoWait",
                }
            ],
        )

    def test_changes_default_alias_back_to_bg_layer(self):
        result = self.generator.process(
            {
                "BgCommand": "换图层",
                "BgLayer": "默认",
                "BgFade": "3",
            }
        )

        self.assertEqual(
            result,
            [
                {
                    "Command": "ChangeLayer",
                    "Arg1": "BG",
                    "Arg2": "KeepLocal",
                    "Arg3": "BG",
                }
            ],
        )

    def test_emits_move_layer_state_effect(self):
        effects = self.generator.state_effects(
            {
                "BgCommand": "换图层",
                "BgLayer": "超近景",
                "WaitType": "不等待",
            }
        )

        self.assertEqual(
            effects,
            [
                VisualStateEffect(
                    effect_type=VisualEffectType.MOVE_LAYER,
                    resource_type="Background",
                    layer="超近景",
                    wait_type="NoWait",
                    preserve_local=True,
                )
            ],
        )

    def test_change_layer_takes_precedence_over_resource_cells(self):
        result = self.generator.process(
            {
                "BgCommand": "换图层",
                "Bg": "桂花林",
                "BgLayer": "超近景",
            }
        )

        self.assertEqual(
            result,
            [
                {
                    "Command": "ChangeLayer",
                    "Arg1": "BG",
                    "Arg2": "KeepLocal",
                    "Arg3": "超近景",
                }
            ],
        )

    def test_change_layer_requires_target_layer(self):
        self.assertIsNone(self.generator.process({"BgCommand": "换图层"}))
        self.assertEqual(self.generator.state_effects({"BgCommand": "换图层"}), [])

    def test_processor_routes_bg_command_to_background_generator(self):
        processor = EngineProcessor(
            "utage",
            self.translator,
            UtageConfig(),
            generator_categories=["Background"],
        )
        processor.setup()

        result = processor.process_row(
            pd.Series(
                {
                    "BgCommand": "换图层",
                    "BgLayer": "默认",
                }
            )
        )

        self.assertEqual(
            result,
            [
                {
                    "Command": "ChangeLayer",
                    "Arg1": "BG",
                    "Arg2": "KeepLocal",
                    "Arg3": "BG",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
