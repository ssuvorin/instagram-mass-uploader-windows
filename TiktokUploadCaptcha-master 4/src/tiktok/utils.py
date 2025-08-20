import os
import shutil


def delete_video(name):
    os.remove(os.path.abspath(__file__).replace('src\\tiktok\\utils.py', f'videos\\{name}'))

def delete_title(title):
    with open(os.path.abspath(f'titles\\titles.txt'), 'r', encoding='utf-8') as f:
        lines = f.readlines()
    modified_lines = [line for line in lines if line.strip() != title]
    with open(os.path.abspath(f'titles\\titles.txt'), 'w', encoding='utf-8') as f:
        f.writelines(modified_lines)

def delete_profile(name):
    if os.path.exists(os.path.abspath(f'accounts\\accounts_data\\{name}')):
        shutil.rmtree(os.path.abspath(f'accounts\\accounts_data\\{name}'))
