from __future__ import annotations

import pytest

from hemp.review.agreement import (
    cohens_kappa,
    fleiss_kappa,
    krippendorff_alpha_nominal,
)
from hemp.similarity import contains_term, jaccard, tokenize


def test_jaccard_edges() -> None:
    assert jaccard("", "") == 1.0
    assert jaccard("alpha", "") == 0.0
    assert jaccard("same words", "same words") == 1.0
    assert jaccard("alpha beta", "beta gamma") == pytest.approx(1 / 3)


def test_tokenize_and_term() -> None:
    assert tokenize("Hub-Rule 14") == ["hub", "rule", "14"]
    assert contains_term("the handoff token is set", "handoff token")
    assert not contains_term("a token is set", "handoff token")


def test_cohens_kappa_known_value() -> None:
    left = ["0", "0", "0", "0", "0", "1", "1", "1", "1", "1"]
    right = ["0", "0", "0", "0", "1", "1", "1", "1", "1", "1"]
    assert cohens_kappa(left, right) == pytest.approx(0.8)
    assert cohens_kappa(["a", "a"], ["a", "a"]) == 1.0


def test_fleiss_known_value() -> None:
    ratings = [
        ["Y", "Y", "Y"],
        ["Y", "Y", "N"],
        ["N", "N", "N"],
    ]
    assert fleiss_kappa(ratings) == pytest.approx(0.55)


def test_krippendorff_nominal() -> None:
    assert krippendorff_alpha_nominal([["A", "A"], ["B", "B"]]) == pytest.approx(1.0)
    assert krippendorff_alpha_nominal([["A", "B"], ["A", "B"]]) == pytest.approx(-0.5)
    assert krippendorff_alpha_nominal([["A", "A", None], ["B", "B", None]]) == pytest.approx(1.0)


def test_agreement_rejects_bad_shapes() -> None:
    with pytest.raises(ValueError):
        cohens_kappa(["a"], ["a", "b"])
    with pytest.raises(ValueError):
        fleiss_kappa([])
    with pytest.raises(ValueError):
        krippendorff_alpha_nominal([[None], [None]])
