"""Залишено для сумісності: старий запуск `python main.py` тепер викликає publish.py."""
import sys

from publish import main

if __name__ == "__main__":
    sys.exit(main())
