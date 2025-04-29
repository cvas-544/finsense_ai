from admin_tools.keyword_manager import add_keyword_admin
import sys

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python -m admin_tools.add_keyword [expense|income] [word]")
        sys.exit(1)

    _, keyword_type, word = sys.argv
    add_keyword_admin(keyword_type, word)