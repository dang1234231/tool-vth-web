import streamlit as st
import json
import os
from PIL import Image
from collections import defaultdict
from datetime import datetime
from tool_core import analyze_rooms, normalize_recent_stats, check_gim_trend, too_repeated, get_cluster

# --- Setup ban đầu ---
st.set_page_config(page_title="Tool Dự Đoán Phòng", page_icon="🔍")
image_path = os.path.join(os.path.dirname(__file__), "Untitled.png")
image = Image.open(image_path)
st.image(image, caption="📷 Mô phỏng hệ thống phòng", use_container_width=True)

room_data = {
    1: "Phòng Nhân Sự",
    2: "Phòng Tài Vụ",
    3: "Phòng Giám Sát",
    4: "Văn Phòng",
    5: "Phòng Trò Chuyện",
    6: "Nhà Kho",
    7: "Phòng Họp",
    8: "Phòng Giám Đốc"
}

# --- Khởi tạo trạng thái ---
if "recent_rooms" not in st.session_state:
    st.session_state.recent_rooms = []
if "recent_stats" not in st.session_state:
    st.session_state.recent_stats = {i: 12 for i in range(1, 9)}
if "markov_map" not in st.session_state:
    st.session_state.markov_map = defaultdict(lambda: defaultdict(int))
if "suggested_history" not in st.session_state:
    st.session_state.suggested_history = []
if "build_history" not in st.session_state:
    st.session_state.build_history = []
if "build_boost_rounds" not in st.session_state:
    st.session_state.build_boost_rounds = 0

st.title("🔍 Tool Dự Đoán Phòng An Toàn (Web)")

# --- Nhập phòng mới ---
new_room = st.number_input("🔢 Nhập phòng sát thủ vừa vào (1–8):", min_value=1, max_value=8, step=1)

col1, col2 = st.columns([1, 3])
with col1:
    if st.button("➕ Thêm & Phân Tích"):
        # Cập nhật lịch sử phòng
        st.session_state.recent_rooms.append(new_room)
        if len(st.session_state.recent_rooms) > 10:
            st.session_state.recent_rooms.pop(0)

        # Cập nhật thống kê
        st.session_state.recent_stats[new_room] = st.session_state.recent_stats.get(new_room, 0) + 1
        st.session_state.recent_stats = normalize_recent_stats(st.session_state.recent_stats)

        # Phân tích
        safest_room, safest_prob, probabilities = analyze_rooms(
            room_data,
            st.session_state.recent_rooms,
            st.session_state.recent_stats,
            st.session_state.markov_map
        )

        gim_level = check_gim_trend(st.session_state.recent_rooms, new_room)

        # Tránh gợi ý lặp nhiều lần
        st.session_state.suggested_history.append(safest_room)
        if len(st.session_state.suggested_history) > 10:
            st.session_state.suggested_history.pop(0)
        if too_repeated(safest_room, st.session_state.suggested_history):
            alt_rooms = sorted(probabilities.items(), key=lambda x: x[1])
            for rid, _ in alt_rooms:
                if rid != safest_room and not too_repeated(rid, st.session_state.suggested_history):
                    safest_room = rid
                    safest_prob = 100 - probabilities[rid]
                    break

        # Tính build đề xuất
        build = round(safest_prob / 10) * 100
        if new_room == safest_room:
            st.session_state.build_boost_rounds = 2
        if st.session_state.build_boost_rounds > 0:
            build += 200
            st.session_state.build_boost_rounds -= 1
        if gim_level == 2:
            build = min(build, 300)
        elif gim_level == 3:
            build = 100

        LARGE_BUILD = 700
        SMALL_COUNT_REQUIRED = 5
        recent_small = [b for b in st.session_state.build_history[-SMALL_COUNT_REQUIRED:] if b < LARGE_BUILD]
        if build >= LARGE_BUILD and len(recent_small) < SMALL_COUNT_REQUIRED:
            build = 300

        build = max(100, min(build, 1000))
        st.session_state.build_history.append(build)

        # --- Hiển thị kết quả ---
        st.success(f"🛡️ Phòng an toàn nhất: **{room_data[safest_room]}** ({safest_prob:.2f}% an toàn)")
        st.info(f"🎯 Đề xuất đặt: **{build} build**")

        # Hiển thị cảnh báo AI nếu có log
        if os.path.exists("ai_deception_log.json"):
            with open("ai_deception_log.json", "r") as f:
                data = json.load(f)
                st.warning("⚠️ AI có dấu hiệu đánh lừa gần đây!")
                st.write(f"🕒 Phát hiện: `{data.get('last_deception_detected', '')}`")
                st.write("📊 Chuỗi cụm gần đây:", ", ".join(data.get("recent_clusters", [])))

        # Hiển thị xác suất
        st.markdown("### 📊 Xác suất an toàn các phòng:")
        for rid, prob in sorted(probabilities.items(), key=lambda x: x[1]):
            safe_percent = max(0, min(100, 100 - prob))
            st.write(f"**{room_data[rid]}** — {safe_percent:.2f}% an toàn")
            st.progress(safe_percent)

with col2:
    if st.button("🔁 Reset"):
        st.session_state.clear()
        st.rerun()

# Hiển thị lịch sử nhanh
st.markdown("### 🕓 Lịch sử gần đây:")
st.write("🛑 Phòng đã vào:", [room_data[r] for r in st.session_state.recent_rooms])
st.write("✅ Gợi ý gần đây:", [room_data[r] for r in st.session_state.suggested_history])
