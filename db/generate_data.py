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

        sql_query = (f"INSERT INTO dictionary (word, translation, grade_id) "
                     f"SELECT '{word}', '{translation}', grade_id "
                     f"FROM grades WHERE grade_id = '{grade}';\n")

        sql_f.write(sql_query)
