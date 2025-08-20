import os
import json


def json_to_string(json_data):
    return f"{json_data['username']}:{json_data['password']}:{json_data['email_username']}:{json_data['email_password']}"

if __name__ == '__main__':
    result = ""
    for i in os.listdir('accounts\\accounts_data'):
        path_to_config = os.path.abspath(f'accounts\\accounts_data\\{i}\\config.json')
        with open(path_to_config, 'r') as f:
            s = json_to_string(json.load(f))
        result += s + '\n'
    with open('prepare_accounts\\accounts\\accounts.txt', 'w') as f:
        f.write(result)
