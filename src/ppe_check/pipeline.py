"""End-to-end check-in pipeline: frames in → Report out."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import numpy as np

from .assign import detections_for_person
from .checks import (check_facemask, check_gloves, check_hair, check_hairnet,
                     check_nails, check_uniform)
from .rules import DEFAULT_RULES, load_rules, overall_status
from .types import Detection, Report


class PPEChecker:
    def __init__(self, weights: str, rules_path: Path = DEFAULT_RULES, device: Optional[str] = None):
        from ultralytics import YOLO  # imported lazily so tests don't need it

        self.model = YOLO(weights)
        self.device = device
        self.roles, self.th = load_rules(rules_path)

    def detect(self, frame: np.ndarray) -> List[Detection]:
        res = self.model.predict(frame, conf=self.th.review_below * 0.5,
                                 device=self.device, verbose=False)[0]
        names = res.names
        return [
            Detection(names[int(c)], float(p), tuple(map(float, b)))
            for b, p, c in zip(res.boxes.xyxy.tolist(), res.boxes.conf.tolist(), res.boxes.cls.tolist())
        ]

    def check(self, face_frame: np.ndarray, hands_frame: Optional[np.ndarray] = None,
              role: str = "kitchen", employee_id: str = "unknown") -> Report:
        """face_frame: employee facing camera. hands_frame: both hands shown (optional)."""
        if role not in self.roles:
            raise ValueError(f"unknown role '{role}', expected one of {list(self.roles)}")

        face_dets = detections_for_person(self.detect(face_frame))
        if hands_frame is not None:
            hand_img, hand_dets = hands_frame, detections_for_person(self.detect(hands_frame))
        else:
            hand_img, hand_dets = face_frame, face_dets

        results = {
            "facemask": check_facemask(face_dets, self.th),
            "hairnet": check_hairnet(face_dets, self.th),
            "hair": check_hair(face_frame, face_dets, self.th),
            "uniform": check_uniform(face_frame, face_dets, self.th),
            "gloves": check_gloves(hand_dets, self.th),
            "nails": check_nails(hand_img, hand_dets, self.th),
        }
        required = self.roles[role]
        overall, manual = overall_status(results, required)
        return Report(
            employee_id=employee_id,
            role=role,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            overall=overall,
            items={k: v for k, v in results.items() if k in required},
            manual_items=manual,
        )
