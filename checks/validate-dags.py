#!/usr/bin/env python3
"""
DAG Validation Script for BionicPRO
Проверяет синтаксис всех DAG файлов перед запуском Airflow
"""

import os
import sys
import importlib.util
import traceback
from pathlib import Path

def validate_dag_file(dag_path):
    """Проверяет синтаксис одного DAG файла"""
    print(f"🔍 Проверка: {dag_path}")

    try:
        # Загружаем модуль
        spec = importlib.util.spec_from_file_location("dag_module", dag_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Проверяем наличие DAG объекта
        dag_found = False
        for name in dir(module):
            obj = getattr(module, name)
            if hasattr(obj, '__class__') and obj.__class__.__name__ == 'DAG':
                print(f"  ✅ DAG найден: {obj.dag_id}")
                dag_found = True

        if not dag_found:
            print(f"  ⚠️  DAG объект не найден в файле")
            return False

        print(f"  ✅ Синтаксис корректный")
        return True

    except Exception as e:
        print(f"  ❌ Ошибка: {str(e)}")
        print(f"  📝 Детали:")
        traceback.print_exc()
        return False

def main():
    """Основная функция проверки"""
    script_dir = Path(__file__).parent
    dags_dir = script_dir.parent / "dags"

    print("=" * 50)
    print("  BionicPRO DAG Validation")
    print("=" * 50)
    print()

    if not dags_dir.exists():
        print(f"❌ Папка dags не найдена: {dags_dir}")
        return 1

    # Находим все .py файлы в папке dags
    dag_files = list(dags_dir.glob("*.py"))

    if not dag_files:
        print(f"❌ DAG файлы не найдены в: {dags_dir}")
        return 1

    print(f"📂 Найдено DAG файлов: {len(dag_files)}")
    print()

    # Проверяем каждый файл
    valid_count = 0
    for dag_file in dag_files:
        if validate_dag_file(dag_file):
            valid_count += 1
        print()

    # Результат
    print("=" * 50)
    print(f"📊 Результат: {valid_count}/{len(dag_files)} файлов прошли проверку")

    if valid_count == len(dag_files):
        print("🎉 Все DAG файлы корректны!")
        return 0
    else:
        print("❌ Есть ошибки в DAG файлах")
        return 1

if __name__ == "__main__":
    sys.exit(main())