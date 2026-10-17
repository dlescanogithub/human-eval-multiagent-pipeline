from __future__ import annotations

import json
from pathlib import Path

import pytest

from hemp.cli import main
from hemp.review.agreement_demo import build_panel, computation_demo, import_labels_csv


def test_computation_demo_is_a_labeled_synthetic_panel() -> None:
    report = computation_demo()
    assert report == computation_demo()
    assert report["label"] == "synthetic"
    assert report["status"] == "computation_demo"
    assert report["not_a_human_study"] is True
    assert int(str(report["n_items"])) >= 40
    disclaimer = str(report["disclaimer"])
    assert "synthetic" in disclaimer.lower()
    assert "not a human study" in disclaimer.lower()
    assert "demonstrate the metric code" in disclaimer
    raters = report["raters"]
    assert isinstance(raters, list)
    by_id = {str(row["rater_id"]): row for row in raters if isinstance(row, dict)}
    assert by_id["careful"]["design_match_rate"] == 0.90
    assert by_id["moderate"]["design_match_rate"] == 0.75
    assert by_id["noisy"]["design_match_rate"] == 0.55
    assert float(str(by_id["careful"]["realized_match_rate"])) > float(str(by_id["noisy"]["realized_match_rate"]))
    coefficients = report["coefficients"]
    assert isinstance(coefficients, dict)
    assert set(coefficients) == {
        "cohens_kappa_careful_moderate",
        "cohens_kappa_careful_noisy",
        "cohens_kappa_moderate_noisy",
        "fleiss_kappa",
        "krippendorff_alpha_nominal",
    }
    for payload in coefficients.values():
        assert isinstance(payload, dict)
        point = float(str(payload["point"]))
        low = float(str(payload["ci95_low"]))
        high = float(str(payload["ci95_high"]))
        assert -1.0 <= point <= 1.0
        assert -1.0 <= low <= high <= 1.0
        assert low <= point <= high
    with pytest.raises(ValueError):
        build_panel(4)


def test_template_csv_claims_no_agreement(repo_root: Path) -> None:
    report = import_labels_csv(repo_root / "fixtures" / "agreement" / "human_labels_template.csv")
    assert report["status"] == "empty"
    assert report["n_items"] == 0
    assert report["coefficients"] is None
    assert report["not_a_human_study"] is True
    assert "does not publish a real-agreement figure" in str(report["disclaimer"])


def test_csv_import_computes_without_calling_it_a_study(tmp_path: Path) -> None:
    path = tmp_path / "labels.csv"
    rows = ["item_id,rater_id,label"]
    for index in range(6):
        rows.append(f"item-{index},ada,pass")
        rows.append(f"item-{index},bea,{'pass' if index < 4 else 'fail'}")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    report = import_labels_csv(path)
    assert report["status"] == "computed_from_import"
    assert report["label"] == "imported"
    assert "does not publish a real-agreement figure" in str(report["disclaimer"])
    coefficients = report["coefficients"]
    assert isinstance(coefficients, dict)
    point = coefficients["cohens_kappa_first_two_raters"]
    assert isinstance(point, dict)
    assert -1.0 <= float(str(point["point"])) <= 1.0


def test_csv_import_rejects_a_ragged_table(tmp_path: Path) -> None:
    path = tmp_path / "ragged.csv"
    path.write_text("item_id,rater_id,label\na,r1,pass\nb,r1,pass\nb,r2,fail\n", encoding="utf-8")
    report = import_labels_csv(path)
    assert report["status"] == "ragged"
    assert report["coefficients"] is None


def test_csv_import_edge_cases(tmp_path: Path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="header"):
        import_labels_csv(empty)
    short = tmp_path / "short.csv"
    short.write_text("item_id,rater_id,label\na,r1,pass\na,r2,fail\n", encoding="utf-8")
    assert import_labels_csv(short)["status"] == "too_small"
    duplicate = tmp_path / "dup.csv"
    duplicate.write_text("item_id,rater_id,label\na,r1,pass\na,r1,fail\n", encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        import_labels_csv(duplicate)
    wide = tmp_path / "wide.csv"
    wide.write_text("item_id,rater_id,label\na,r1,pass,extra\n", encoding="utf-8")
    with pytest.raises(ValueError, match="each CSV row"):
        import_labels_csv(wide)


def test_agreement_commands(repo_root: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--root", str(repo_root), "agreement-demo"]) == 0
    text = capsys.readouterr().out
    assert "COMPUTATION DEMO" in text
    assert "n_items=48" in text
    assert "not a human study" in text
    template = "fixtures/agreement/human_labels_template.csv"
    assert main(["--root", str(repo_root), "agreement-import", "--csv", template]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "empty"
    assert payload["coefficients"] is None
    assert main(["--root", str(repo_root), "agreement-import", "--csv", "missing.csv"]) == 2


def test_csv_import_rejects_a_bad_header(tmp_path: Path) -> None:
    path = tmp_path / "bad.csv"
    path.write_text("id,person,value\n", encoding="utf-8")
    with pytest.raises(ValueError):
        import_labels_csv(path)
