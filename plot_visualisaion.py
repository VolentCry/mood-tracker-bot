import matplotlib.pyplot as plt
from add_mood_to_db import connect_db, get_all_moods

mood_map = {
    "positive": "Положительное 😊",
    "tired": "Усталое 😩",
    "sad": "Грустное 😢",
    "angry": "Злое 😠",
    "delighted": "Восхитительное 🤩",
    "irritated": "Раздражённое 😖",
    "calm": "Спокойное 🙂",
    "energetic": "Энергичное ⚡️",
    "anxious": "Тревожное 😰",
    "inspired": "Воодушевлённое 🤯",
    "bored": "Скучающее 🫠",
    "loving": "Влюблённое 🥰",
    "indifferent": "Безразличное 🥱",
    "scared": "Испуганное 😱",
    "proud": "Гордое 😎",
    "envious": "Завистливое 😒",
    "confused": "Растерянное 😓",
    "playful": "Игривое 😏",
    "focused": "Сосредоточенное 🤔",
    "sick": "Болезненное 🤧"
}

mood_map_counter = {
    "0": 0,
    "1": 0,
    "2": 0,
    "3": 0,
    "4": 0,
    "5": 0,
    "6": 0,
    "7": 0,
    "8": 0,
    "9": 0,
    "10": 0,
    "11": 0,
    "12": 0,
    "13": 0,
    "14": 0,
    "15": 0,
    "16": 0,
    "17": 0,
    "18": 0,
    "19": 0
}

conn = connect_db()
all_moods = get_all_moods(conn)
for record in all_moods:
    mood_map_counter[str(record[3])] += 1
conn.close()

value_list = []
name_of_mood_list = [] # Названия настроений, которых нет в БД
b = list(mood_map_counter.values())
for i in range(len(b)):
    if b[i] == 0:
        name_of_mood = list(mood_map.keys())[i]
        name_of_mood_list.append(name_of_mood)
    else: value_list.append(b[i])

labels_list = []
for j in mood_map.items():
    k, v = j
    if k in name_of_mood_list: pass
    else: labels_list.append(v)

vals = value_list
labels = [x[:-2] for x in labels_list]
fig, ax = plt.subplots()
ax.pie(vals, labels=labels, autopct='%1.1f%%')
ax.axis("equal")
plt.savefig(r'monthly chart\plot1.png', dpi=300)