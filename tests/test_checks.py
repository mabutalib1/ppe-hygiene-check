from ppe_check.assign import detections_for_person
from ppe_check.checks import check_facemask, check_gloves, check_hairnet
from ppe_check.rules import overall_status
from ppe_check.types import Detection, ItemResult, Status, Thresholds

TH = Thresholds(passing=0.6, review_below=0.4)


def d(label, conf, box=(10, 10, 20, 20)):
    return Detection(label, conf, box)


def test_mask_pass():
    assert check_facemask([d("mask", 0.9)], TH).status == Status.PASS


def test_incorrect_mask_fails():
    r = check_facemask([d("mask", 0.5), d("incorrect_mask", 0.8)], TH)
    assert r.status == Status.FAIL and r.reason == "incorrect_mask"


def test_low_conf_needs_review():
    assert check_hairnet([d("hairnet", 0.3)], TH).status == Status.NEEDS_REVIEW


def test_missing_evidence_needs_review():
    assert check_hairnet([], TH).status == Status.NEEDS_REVIEW


def test_gloves_two_hands_pass():
    assert check_gloves([d("glove", 0.9), d("glove", 0.8)], TH).status == Status.PASS


def test_gloves_bare_hand_fails():
    assert check_gloves([d("glove", 0.9), d("bare_hand", 0.7)], TH).status == Status.FAIL


def test_gloves_one_hand_review():
    assert check_gloves([d("glove", 0.9)], TH).status == Status.NEEDS_REVIEW


def test_assign_drops_other_people():
    dets = [
        d("person", 0.9, (0, 0, 100, 200)),        # employee (largest)
        d("person", 0.9, (300, 0, 340, 80)),      # someone in background
        d("mask", 0.9, (40, 20, 60, 40)),
        d("no_mask", 0.9, (310, 10, 330, 30)),    # background person's face
    ]
    labels = [x.label for x in detections_for_person(dets)]
    assert labels == ["mask"]


def test_overall_fail_wins():
    res = {
        "facemask": ItemResult("facemask", Status.PASS, 0.9),
        "gloves": ItemResult("gloves", Status.FAIL, 0.9),
        "nails": ItemResult("nails", Status.NOT_CHECKED),
    }
    overall, manual = overall_status(res, ["facemask", "gloves", "nails"])
    assert overall == Status.FAIL and manual == ["nails"]


def test_overall_pass_lists_manual_items():
    res = {"facemask": ItemResult("facemask", Status.PASS, 0.9),
           "uniform": ItemResult("uniform", Status.NOT_CHECKED)}
    overall, manual = overall_status(res, ["facemask", "uniform"])
    assert overall == Status.PASS and manual == ["uniform"]
