from tools.sync_resources import discover_validation_reports


def test_sync_prefers_aggregate_validation_report(tmp_path):
    aggregate = tmp_path / "all_workbooks_validation.json"
    aggregate.write_text("{}", encoding="utf-8")
    (tmp_path / "chapter_a_validation.json").write_text("{}", encoding="utf-8")
    (tmp_path / "chapter_b_validation.json").write_text("{}", encoding="utf-8")

    assert discover_validation_reports(tmp_path) == [aggregate]


def test_sync_supports_legacy_per_workbook_reports(tmp_path):
    chapter_b = tmp_path / "chapter_b_validation.json"
    chapter_a = tmp_path / "chapter_a_validation.json"
    chapter_b.write_text("{}", encoding="utf-8")
    chapter_a.write_text("{}", encoding="utf-8")

    assert discover_validation_reports(tmp_path) == [chapter_a, chapter_b]
