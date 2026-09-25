from typing import List


def average(numbers: List[float]) -> float:
    """Возвращает среднее значение списка чисел.

    :param numbers: список чисел
    :return: среднее арифметическое
    :raises ValueError: если список пуст
    """
    if not numbers:
        raise ValueError("Список чисел не может быть пустым")
    return sum(numbers) / len(numbers)
