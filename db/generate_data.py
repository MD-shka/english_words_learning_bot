import json
import os

script_dir = os.path.dirname(__file__)
words_file_path = os.path.join(script_dir, 'dictionary.json')

with open(words_file_path, 'r') as f:
    dictionary = json.load(f)

with open('/docker-entrypoint-initdb.d/data.sql', 'w') as sql_f:
    for entry in dictionary:
        word = entry["word"]
        translation = entry["translation"]
        grade = entry["grade"]
        sql_query = (f"INSERT INTO dictionary (word, translation, grade) VALUES "
                     f"('{word}', '{translation}', {grade});\n")
        sql_f.write(sql_query)

with open('/docker-entrypoint-initdb.d/words.json', 'r') as f:
    dictionary = json.load(f)

with open('/docker-entrypoint-initdb.d/data.sql', 'w') as sql_f:
    for entry in dictionary:
        word = entry["en"]
        translation = entry["ru"]
        grade = entry["grade"]
        sql_query = (f"INSERT INTO dictionary (word, translation, grade) VALUES "
                     f"('{word}', '{translation}', {grade});\n")
        sql_f.write(sql_query)
