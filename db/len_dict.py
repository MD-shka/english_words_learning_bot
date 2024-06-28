import json


def count_json_elements_by_grade(filename):
    with open(filename, 'r') as f:
        data = json.load(f)

        # Создаем словарь для подсчета элементов по каждому грейду
        grade_counts = {}

        # Проходим по всем элементам JSON
        for item in data:
            grade = item.get('grade')

            # Проверяем, есть ли уже такой грейд в словаре, иначе добавляем
            if grade in grade_counts:
                grade_counts[grade] += 1
            else:
                grade_counts[grade] = 1

        return grade_counts


# Пример использования
file_path = 'db/dictionary.json'
grade_counts = count_json_elements_by_grade(file_path)

# Выводим результаты
print(f"Количество элементов по каждому грейду в файле '{file_path}':")
for grade, count in grade_counts.items():
    print(f"Грейд {grade}: {count} элемент(ов)")
