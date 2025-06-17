import streamlit as st
import json
import os
from PIL import Image
from collections import defaultdict
from datetime import datetime
from tool_core import analyze_rooms, normalize_recent_stats, check_gim_trend, too_repeated

# ⚙️ Cấu hình giao diện
st.set_page_config(page_title="Tool Dự Đoán Phòng", page_icon="🔍")

# 🖼️ Sơ đồ phòng
image = Image.open(os.path.join(os.path.dirname(__file__), "Untitled.png"))
st.image(image, caption="📷 Mô phỏng hệ thống phòng", use_container_width=True)

# 📘 Tên phòng
room_data = {
    1: "Phòng Nhân Sự", 2: "Phòng Tài Vụ", 3: "Phòng Giám Sát", 4: "Văn Phòng",
    5: "Phòng Trò Chuyện", 6: "Nhà Kho", 7: "Phòng Họp", 8: "Phòng Giám Đốc"
}

# 🧠 Khởi tạo trạng thái
if "recent_rooms" not in st.session_state:
    st.session_state.recent_rooms = []
if "recent_stats" not in st.session_state:
    st.session_state.recent_stats = {i: -1 for i in range(1, 9)}
if "markov_map" not in st.session_state:
    st.session_state.markov_map = defaultdict(lambda: defaultdict(int))
if "suggested_history" not in st.session_state:
    st.session_state.suggested_history = []
if "build_history" not in st.session_state:
    st.session_state.build_history = []
if "build_boost_rounds" not in st.session_state:
    st.session_state.build_boost_rounds = 0

st.title("🔍 Tool Dự Đoán Phòng An Toàn")

# 🚦 Nếu chưa đủ dữ liệu khởi tạo (10 phòng đầu hoặc thống kê âm)
if len(st.session_state.recent_rooms) < 10 or any(v < 0 for v in st.session_state.recent_stats.values()):
    st.subheader("📥 Nhập 10 phòng sát thủ đã vào gần đây:")
    text_input = st.text_input("Nhập 10 số cách nhau bằng dấu cách (1–8):", "")

    st.subheader("📊 Nhập số lần mỗi phòng bị vào trong 100 trận:")
    cols = st.columns(4)
    stats_input = {}
    for idx, rid in enumerate(room_data):
        with cols[idx % 4]:
            stats_input[rid] = st.number_input(room_data[rid], min_value=0, max_value=100, value=12)

    if st.button("✅ Khởi tạo"):
        raw = text_input.strip()
        try:
            recent = list(map(int, raw.split()))
            if len(recent) != 10:
                st.error("❌ Phải nhập đúng 10 số.")
            elif not all(1 <= r <= 8 for r in recent):
                st.error("❌ Chỉ dùng số từ 1 đến 8.")
            else:
                st.session_state.recent_rooms = recent
                st.session_state.recent_stats = normalize_recent_stats(stats_input)
                st.success("✅ Khởi tạo thành công.")
                st.rerun()
        except ValueError:
            st.error("❌ Dữ liệu không hợp lệ. Nhập như: `1 2 3 4 5 6 7 8 1 2`")

# ✅ Nếu đã khởi tạo đủ
else:
    st.subheader("🔁 Nhập phòng sát thủ vừa vào:")
    new_room = st.number_input("Phòng mới:", min_value=1, max_value=8, step=1)

    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("➕ Thêm & Phân Tích"):
            # Cập nhật dữ liệu
            st.session_state.recent_rooms.append(new_room)
            if len(st.session_state.recent_rooms) > 10:
                st.session_state.recent_rooms.pop(0)
            st.session_state.recent_stats[new_room] += 1
            st.session_state.recent_stats = normalize_recent_stats(st.session_state.recent_stats)

            # Phân tích
            safest_room, safest_prob, probs = analyze_rooms(
                room_data,
                st.session_state.recent_rooms,
                st.session_state.recent_stats,
                st.session_state.markov_map
            )

            gim_level = check_gim_trend(st.session_state.recent_rooms, new_room)

            # Tránh lặp
            st.session_state.suggested_history.append(safest_room)
            if len(st.session_state.suggested_history) > 10:
                st.session_state.suggested_history.pop(0)
            if too_repeated(safest_room, st.session_state.suggested_history):
                for rid, _ in sorted(probs.items(), key=lambda x: x[1]):
                    if rid != safest_room and not too_repeated(rid, st.session_state.suggested_history):
                        safest_room = rid
                        safest_prob = 100 - probs[rid]
                        break

            # Gợi ý build
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
            if build >= 700 and len([b for b in st.session_state.build_history[-5:] if b < 700]) < 5:
                build = 300
            build = max(100, min(build, 1000))
            st.session_state.build_history.append(build)

            # Hiển thị kết quả
            st.success(f"🛡️ Phòng an toàn nhất: **{room_data[safest_room]}** ({safest_prob:.2f}%)")
            st.info(f"🎯 Đề xuất đặt: **{build} build**")

            # AI cảnh báo nếu có
            if os.path.exists("ai_deception_log.json"):
                with open("ai_deception_log.json") as f:
                    data = json.load(f)
                    st.warning("⚠️ AI có dấu hiệu đánh lừa!")
                    st.write(f"🕒 Phát hiện: `{data.get('last_deception_detected', '')}`")
                    st.write("📊 Cụm gần đây:", ", ".join(data.get("recent_clusters", [])))

            # Hiển thị xác suất
            st.markdown("### 📊 Xác suất an toàn:")
            for rid, prob in sorted(probs.items(), key=lambda x: x[1]):
                safe_percent = max(0, min(100, 100 - prob))
                st.write(f"**{room_data[rid]}** — {safe_percent:.2f}% an toàn")
                st.progress(safe_percent / 100)

    with col2:
        if st.button("🔁 Reset"):
            st.session_state.clear()
            st.rerun()

    # Hiển thị lịch sử
    st.markdown("### 🕓 Lịch sử gần đây:")
    st.write("🛑 Phòng đã vào:", [room_data[r] for r in st.session_state.recent_rooms])
    st.write("✅ Gợi ý gần đây:", [room_data[r] for r in st.session_state.suggested_history])
