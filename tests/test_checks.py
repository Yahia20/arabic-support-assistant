from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from support_assistant.assistant import check_answer, language  # noqa: E402
from support_assistant.grade import grade  # noqa: E402
from support_assistant.policies import load_policies  # noqa: E402
from support_assistant.text import normalize, numbers  # noqa: E402

BOOK = load_policies(ROOT / "policies" / "policies.yaml")


def test_numbers_read_arabic_digits_and_thousands():
    assert numbers("الرسوم ٢٥٠ ريال") == {250.0}
    assert numbers("SAR 10,000") == {10000.0}
    assert numbers("55×40×23") == {55.0, 40.0, 23.0}
    assert numbers("من 7 إلى 14 يوم") == {7.0, 14.0}


def test_normalize_unifies_arabic_spellings():
    assert normalize("الأصليّة") == normalize("الاصليه")


def test_both_languages_carry_the_same_numbers():
    # The check reads both texts; a typo in one language would let a wrong number through.
    for s in BOOK.sections:
        assert numbers(s.ar) == numbers(s.en), s.id


def test_check_accepts_a_correct_answer():
    assert check_answer(BOOK, "كم رسوم التغيير؟", "رسوم التغيير 250 ريال لكل راكب.", ["changes"], ["changes"]) == ""


def test_check_rejects_an_invented_fee():
    assert "199" in check_answer(BOOK, "كم رسوم التغيير؟", "رسوم التغيير 199 ريال.", ["changes"], ["changes"])


def test_check_accepts_a_total_worked_out_from_the_question():
    q = "كم رسوم تغيير تذكرة توفير لـ 3 ركاب؟"
    assert check_answer(BOOK, q, "250 ريال لكل راكب، يعني 750 ريال.", ["changes"], ["changes"]) == ""


def test_check_accepts_a_head_count_in_words():
    q = "لو الغيت تذكرة المرن لي ولزوجتي كم يخصمون؟"
    assert check_answer(BOOK, q, "300 ريال لكل راكب، المجموع 600 ريال.", ["cancellations"], ["cancellations"]) == ""


def test_check_rejects_sums_of_policy_numbers_alone():
    # 150 + 150 = 300 is not a baggage rule; arithmetic needs a number the customer gave.
    assert check_answer(BOOK, "كم الوزن الزائد؟", "الوزن الزائد 175 ريال", ["baggage"], ["baggage"])


def test_check_reads_numbers_the_customer_wrote_as_words():
    q = "تذكرة المرن لو غيرتها قبل الطلعة بست ساعات كم؟"
    assert check_answer(BOOK, q, "بما أن التغيير قبل 6 ساعات، الرسوم 100 ريال.", ["changes"], ["changes"]) == ""
    q = "Can I change a Flex ticket for free three days before the flight?"
    assert check_answer(BOOK, q, "Yes, 3 days is more than 24 hours, so it's free.", ["changes"], ["changes"]) == ""


def test_check_rejects_citing_a_section_it_was_not_shown():
    assert check_answer(BOOK, "q", "250", ["changes"], ["baggage"]) == "cites no section that was shown"


def test_check_rejects_a_number_from_another_section():
    # 300 is the Flex cancellation fee; it must not appear in an answer citing only the change rules.
    assert check_answer(BOOK, "كم رسوم التغيير؟", "الرسوم 300 ريال", ["changes"], ["changes", "cancellations"])


def test_language_detection():
    assert language("ابي اغير رحلتي") == "ar"
    assert language("change my flight") == "en"


ITEM = {"id": "x", "lang": "ar-sa", "q": "?", "expect": "answer", "sections": ["changes"], "facts": [["250"]]}


def _res(action="answer", sections=("changes",), reply="250 ريال"):
    return {"action": action, "sections": list(sections), "reply": reply}


def test_grade_right_answer():
    assert grade(ITEM, _res())["ok"]


def test_grade_wrong_number_fails():
    assert not grade(ITEM, _res(reply="2500 ريال"))["ok"]


def test_grade_wrong_section_fails():
    assert not grade(ITEM, _res(sections=("baggage",)))["ok"]


def test_grade_wrong_action_fails():
    assert not grade(ITEM, _res(action="handoff"))["ok"]


@pytest.mark.parametrize("name", ["test", "dev"])
def test_question_sets_are_well_formed(name):
    items = yaml.safe_load((ROOT / "eval" / f"{name}.yaml").read_text(encoding="utf-8"))
    assert len({i["id"] for i in items}) == len(items)
    for i in items:
        assert i["expect"] in {"answer", "handoff", "redirect"}
        if i["expect"] == "answer":
            assert i["sections"] and all(BOOK.get(s) for s in i["sections"]), i["id"]


def test_test_and_dev_do_not_share_questions():
    test = {normalize(i["q"]) for i in yaml.safe_load((ROOT / "eval" / "test.yaml").read_text(encoding="utf-8"))}
    dev = {normalize(i["q"]) for i in yaml.safe_load((ROOT / "eval" / "dev.yaml").read_text(encoding="utf-8"))}
    assert not test & dev
