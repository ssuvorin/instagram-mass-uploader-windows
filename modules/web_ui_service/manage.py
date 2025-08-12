#!/usr/bin/env python
import os
import sys
from pathlib import Path

def main():
    # Ensure repo root is importable to load 'uploader' app
    repo_root = Path(__file__).resolve().parents[1].parent
    sys.path.append(str(repo_root))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'remote_ui.settings')
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main() 