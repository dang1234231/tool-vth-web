
import streamlit as st
import json
from collections import defaultdict
from tool_core import analyze_rooms, normalize_recent_stats
import os
from PIL import Image

image_path = os.path.join(os.path.dirname(__file__), "Untitled.png")
image = Image.open(image_path)
st.image(image, caption="📷 Mô phỏng hệ thống phòng", use_column_width=True)
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

st.set_page_config(page_title="Tool Dự Đoán Phòng", page_icon="🔍")

st.title("🔍 Tool Dự Đoán Phòng An Toàn")
st.markdown("*Dự đoán phòng an toàn nhất dựa trên lịch sử và thống kê 100 trận gần nhất.*")

# Nhập 10 phòng gần đây
st.markdown("### ✅ Nhập 10 phòng gần đây mà sát thủ đã vào:")
recent_input = st.text_input("Nhập 10 số cách nhau bằng dấu cách (giá trị từ 1 đến 8):", "")

# Nhập dữ liệu thống kê 100 trận
st.markdown("### ✅ Nhập thống kê số lần từng phòng bị vào trong 100 trận:")
default_stats = json.dumps({i: 12 for i in range(1, 9)}, indent=2)
stats_input = st.text_area("Nhập dạng JSON (ví dụ: {\"1\": 10, \"2\": 12, ...}):", value=default_stats, height=200)

# Nút phân tích
if st.button("🚀 Phân Tích"):
    try:
        # Xử lý chuỗi nhập
        recent_rooms = list(map(int, recent_input.strip().split()))
        if len(recent_rooms) != 10 or not all(1 <= r <= 8 for r in recent_rooms):
            st.error("❌ Bạn phải nhập đúng 10 số từ 1 đến 8.")
        else:
            recent_stats = json.loads(stats_input)
            recent_stats = {int(k): v for k, v in recent_stats.items()}
            recent_stats = normalize_recent_stats(recent_stats)

            # Phân tích kết quả
            safest_room, safest_prob, probs = analyze_rooms(
                room_data, recent_rooms, recent_stats, defaultdict(lambda: defaultdict(int))
            )

            st.success(f"🛡️ Phòng an toàn nhất: **{room_data[safest_room]}** ({safest_prob:.2f}% an toàn)")

            # Hiển thị xác suất
            st.markdown("### 📊 Xác suất an toàn của từng phòng:")
            for rid, prob in sorted(probs.items(), key=lambda x: x[1]):
                bar_value = 100 - prob
                st.write(f"**{room_data[rid]}** — {bar_value:.2f}% an toàn")
                st.progress(int(bar_value))

    except Exception as e:
        st.error(f"❌ Lỗi: {e}")
