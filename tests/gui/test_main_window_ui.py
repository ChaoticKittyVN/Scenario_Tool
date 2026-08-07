import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMainWindow

from gui.ui.main_window import MainWindowUI


def application():
    return QApplication.instance() or QApplication([])


def test_param_page_exposes_full_and_scoped_update_actions():
    app = application()
    window = QMainWindow()
    ui = MainWindowUI()
    ui.setup_ui(window)

    assert ui.param_mappings_btn.text() == "仅生成映射文件"
    assert ui.param_sheet_btn.text() == "仅同步参数表"
    assert ui.param_update_btn.text() == "更新映射并同步参数表"
    assert ui.param_variant_mapping_btn.text() == "生成普通差分映射"
    assert ui.param_agent_variant_btn.text() == "生成 Agent 差分文档"
    assert ui.param_mappings_btn.objectName() == "secondaryButton"
    assert ui.param_sheet_btn.objectName() == "secondaryButton"
    assert ui.param_variant_mapping_btn.objectName() == "secondaryButton"
    assert ui.param_agent_variant_btn.objectName() == "secondaryButton"

    window.deleteLater()
    app.processEvents()
