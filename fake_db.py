import wordfreq
import json


WORDS = [
    {'en': 'outerwear', 'ru': 'верхняя одежда', 'grade': None},
    {'en': 'amusement park', 'ru': 'парк аттракционов', 'grade': None},
    {'en': 'gum', 'ru': 'жвачка', 'grade': None},
    {'en': 'vowel', 'ru': 'гласные буквы', 'grade': None},
    {'en': 'scissors', 'ru': 'ножницы', 'grade': None},
    {'en': 'diving', 'ru': 'дайвинг', 'grade': None},
    {'en': 'duodenum', 'ru': 'двенадцатиперстная кишка', 'grade': None},
    {'en': 'rare', 'ru': 'редкий', 'grade': None},
    {'en': 'behind', 'ru': 'за', 'grade': None},
    {'en': 'eat', 'ru': 'есть', 'grade': None}
]


def estimate_word_difficulty(word):
    freq = wordfreq.word_frequency(word, 'en')
    if freq > 0.001:
        return 1  # Очень легкий уровень
    elif freq > 0.0001:
        return 2  # Легкий уровень
    elif freq > 0.00001:
        return 3  # Ниже среднего уровня
    elif freq > 0.000001:
        return 4  # Средний уровень
    elif freq > 0.0000001:
        return 5  # Выше среднего уровня
    elif freq > 0.00000001:
        return 6  # Сложный уровень
    else:
        return 7  # Очень сложный уровень


def set_grades(words):
    for word in words:
        word['grade'] = estimate_word_difficulty(word['en'])


def save_to_file(words, filename):
    with open(filename, 'w') as f:
        json.dump(words, f, ensure_ascii=False, indent=4)


set_grades(WORDS)

save_to_file(WORDS, 'words.json')
