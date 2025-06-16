
# tool_core.py - Logic gốc được tách từ toolvth.py để dùng lại trong bot
# (Rút gọn: loại bỏ input/output, chuyển sang hàm callable)

import json
from datetime import datetime
from collections import defaultdict

def get_cluster(room_id):
    clusters = {
        "trai": [2, 5, 6],
        "phai": [1, 4, 8],
        "giua": [3, 7]
    }
    for name, ids in clusters.items():
        if room_id in ids:
            return name
    return "khac"

def get_floor(room_id):
    if room_id in [1, 2, 3, 4]:
        return "tang1"
    elif room_id in [5, 6, 7, 8]:
        return "tang2"
    return "khac"

def count_floor_gim(recent_rooms):
    floor_count = {"tang1": 0, "tang2": 0}
    for room in recent_rooms:
        floor = get_floor(room)
        floor_count[floor] += 1
    return floor_count

def suggest_by_cluster(recent_rooms):
    cluster_count = {"trai": 0, "phai": 0, "giua": 0}
    for room in recent_rooms[-5:]:
        cluster = get_cluster(room)
        cluster_count[cluster] += 1
    return max(cluster_count, key=cluster_count.get)

def suggest_by_floor(recent_rooms):
    floor_count = {"tang1": 0, "tang2": 0}
    for room in recent_rooms[-5:]:
        floor = get_floor(room)
        floor_count[floor] += 1
    return max(floor_count, key=floor_count.get)

def detect_spam_rooms(recent_rooms):
    counts = {i: recent_rooms.count(i) for i in set(recent_rooms)}
    return [room for room, count in counts.items() if count >= 4]

def too_repeated(room_id, history, limit=3, window=5):
    return history[-window:].count(room_id) >= limit

def detect_ai_deception(recent_rooms):
    if len(recent_rooms) < 6:
        return False
    cluster_prev = [get_cluster(r) for r in recent_rooms[-6:-1]]
    cluster_last = get_cluster(recent_rooms[-1])
    return cluster_prev.count(cluster_last) == 0

def check_gim_trend(recent_rooms, current_room):
    if len(recent_rooms) < 3:
        return 0
    last3 = recent_rooms[-3:]
    if last3.count(current_room) == 3:
        return 3
    elif last3[-2:] == [current_room, current_room]:
        return 2
    return 0

def normalize_recent_stats(recent_stats):
    total = sum(recent_stats.values())
    if total <= 100:
        return recent_stats
    ratio = 100 / total
    for key in recent_stats:
        recent_stats[key] = max(0, round(recent_stats[key] * ratio))
    return recent_stats

def analyze_rooms(room_data, recent_rooms, recent_stats, markov_map):
    decay_weights = [2 ** (9 - i) for i in range(len(recent_rooms))]
    total_decay_weight = sum(decay_weights)
    room_counts = {room: 0 for room in room_data}
    for i, room in enumerate(recent_rooms):
        room_counts[room] += decay_weights[i]
    freq_recent = {room: room_counts[room] / total_decay_weight for room in room_data}

    if len(recent_rooms) >= 2:
        prev = recent_rooms[-2]
        curr = recent_rooms[-1]
        markov_map[prev][curr] += 1

    deception_mode = detect_ai_deception(recent_rooms)

    markov_score = defaultdict(float)
    if len(recent_rooms) >= 1:
        last_room = recent_rooms[-1]
        total_transit = sum(markov_map[last_room].values()) or 1
        for dest, count in markov_map[last_room].items():
            markov_score[dest] = count / total_transit

    cluster_pref = suggest_by_cluster(recent_rooms)
    floor_pref = suggest_by_floor(recent_rooms)
    spam_rooms = detect_spam_rooms(recent_rooms)
    floor_gim_count = count_floor_gim(recent_rooms)

    combined_scores = {}
    for room in room_data:
        score = 0.8 * freq_recent[room] + 0.2 * markov_score[room]

        if room in spam_rooms:
            score -= 0.2
        if deception_mode and get_cluster(room) == get_cluster(recent_rooms[-1]):
            score -= 0.1
        if get_cluster(room) == cluster_pref:
            score += 0.05
        if get_floor(room) == floor_pref:
            score += 0.05
        if floor_gim_count["tang1"] >= 6 and get_floor(room) == "tang2":
            score += 0.08
        elif floor_gim_count["tang2"] >= 6 and get_floor(room) == "tang1":
            score += 0.08

        if recent_stats.get(room, 0) < 10:
            score -= 0.15
        if recent_stats.get(room, 0) < 5:
            score -= 0.1

        combined_scores[room] = score

    probabilities = {room: min(combined_scores[room] * 100, 100) for room in combined_scores}
    safest_room = min(probabilities, key=probabilities.get)
    safest_room_prob = 100 - probabilities[safest_room]
    return safest_room, safest_room_prob, probabilities
