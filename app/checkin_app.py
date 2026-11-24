"""Check-in station demo.

    streamlit run app/checkin_app.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import streamlit as st
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ppe_check.pipeline import PPEChecker  # noqa: E402
from ppe_check.types import Status  # noqa: E402

ICON = {Status.PASS: "✅", Status.FAIL: "❌", Status.NEEDS_REVIEW: "⚠️", Status.NOT_CHECKED: "📝"}

st.set_page_config(page_title="PPE Hygiene Check", page_icon="🧤")
st.title("Staff Hygiene Check-in")

weights = st.sidebar.text_input("Detector weights", "runs/ppe_detector/weights/best.pt")
role = st.sidebar.selectbox("Role", ["kitchen", "barista", "cashier"])
employee_id = st.sidebar.text_input("Employee ID", "")


@st.cache_resource
def get_checker(path):
    return PPEChecker(path)


st.subheader("1. Face the camera")
face = st.camera_input("Face / upper body", key="face")
st.subheader("2. Show both hands, palms down")
hands = st.camera_input("Hands", key="hands")

if face and st.button("Run check", type="primary"):
    if not Path(weights).exists():
        st.error(f"Weights not found: {weights}. Train first with scripts/train_detector.py")
        st.stop()
    checker = get_checker(weights)
    to_np = lambda f: np.array(Image.open(f).convert("RGB"))[:, :, ::-1]  # RGB → BGR
    report = checker.check(to_np(face), to_np(hands) if hands else None,
                           role=role, employee_id=employee_id or "unknown")

    st.markdown(f"## {ICON[report.overall]} Overall: **{report.overall.value}**")
    for item, r in report.items.items():
        conf = f" ({r.confidence:.0%})" if r.confidence else ""
        st.write(f"{ICON[r.status]} **{item.capitalize()}**: {r.status.value}{conf} — {r.reason}")
    if report.manual_items:
        st.info("Check manually: " + ", ".join(report.manual_items))
    st.download_button("Download report (JSON)", json.dumps(report.to_dict(), indent=2),
                       file_name=f"report_{report.employee_id}_{report.timestamp}.json")
