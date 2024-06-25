import wordfreq
import json


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


def convert_and_filter_words(input_filename, output_filename):
    with open(input_filename, 'r') as f:
        words_list = [line.strip() for line in f.readlines() if line.strip()]

    words_json = []
    for word in words_list:
        grade = estimate_word_difficulty(word)
        if grade <= 6:
            words_json.append({
                'en': word,
                'ru': None,
                'grade': grade
            })

    with open(output_filename, 'w') as f:
        json.dump(words_json, f, ensure_ascii=False, indent=4)


convert_and_filter_words('raw_words.txt', 'db/dictionary.json')
