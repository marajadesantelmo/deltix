import csv, sys
from collections import Counter, defaultdict
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")

filepath = r"C:\Users\facun\OneDrive\Documentos\GitHub\deltix\web_interactions.csv"

interactions = 0
sessions = set()
dates = []
user_messages = []
response_types = []
interactions_by_day = defaultdict(int)
sessions_by_day = defaultdict(set)

with open(filepath, encoding="utf-8", errors="replace") as f:
    reader = csv.DictReader(f)
    for row in reader:
        interactions += 1
        sessions.add(row["session_id"])
        ts = row["timestamp"]
        try:
            dt = datetime.fromisoformat(ts)
            day = dt.strftime("%Y-%m-%d")
        except:
            day = ts[:10]
        dates.append(ts)
        interactions_by_day[day] += 1
        sessions_by_day[day].add(row["session_id"])
        user_messages.append(row["user_message"].strip().lower())
        response_types.append(row["response_type"].strip())

print("=== TOTALS ===")
print(f"Total interactions: {interactions}")
print(f"Unique sessions: {len(sessions)}")

dates_sorted = sorted(dates)
print(f"First interaction: {dates_sorted[0]}")
print(f"Last interaction: {dates_sorted[-1]}")

print()
print("=== TOP 10 USER MESSAGES ===")
msg_counter = Counter(user_messages)
for msg, count in msg_counter.most_common(10):
    print(f"  {count:4d}x  {msg[:80]}")

print()
print("=== RESPONSE TYPE DISTRIBUTION ===")
rt_counter = Counter(response_types)
for rt, count in rt_counter.most_common():
    print(f"  {count:4d}x  {rt}")

print()
print("=== INTERACTIONS BY DAY ===")
for day in sorted(interactions_by_day.keys()):
    print(f"  {day}: {interactions_by_day[day]:4d} interactions, {len(sessions_by_day[day]):3d} unique sessions")
