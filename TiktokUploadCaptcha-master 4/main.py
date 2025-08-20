import json
import os
import random
import time

from playwright.sync_api import sync_playwright, Playwright

from src import logger
from src.dolphin.dolphin import Dolphin
from src.tiktok.auth import Auth
from src.tiktok.getCode import Email
from src.tiktok.upload import Uploader
from src.tiktok.video import Video
from src.telegram import send_message


def prepare_accounts(dolphin: Dolphin, playwright):
    accounts = dict()
    for i in os.listdir(os.path.abspath('accounts\\accounts_data')):
        with open(os.path.abspath('accounts\\accounts_data\\' + i + '\\config.json'), 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
        pr = dolphin.get_profile_by_name(i)
        if pr:
            accounts[i] = Auth(
                data['username'],
                data['password'],
                Email(data['email_username'], data['email_password']),
                pr,
                playwright)
    return accounts


def main(playwright: Playwright):
    send_message('Бот начал работу')
    d = Dolphin()

    start_time = 0
    try:
        with open(os.path.abspath('accounts\\config.json'), 'r', encoding='utf-8-sig') as f:
            cfg = json.load(f)

        accounts = prepare_accounts(dolphin=d, playwright=playwright)

        timer = 1
        start_time = time.time()
        for account in cfg['accounts']:
            try:
                # try:
                #     d.stop_profiles()
                # except:
                #     pass
                if os.path.exists(os.path.abspath(f'accounts\\accounts_data\\{account['name']}')):
                    uploader = Uploader(accounts[account['name']])
                    video = Video(name=account['video'], path=os.path.abspath(f'accounts\\videos\\{account['video']}'), description=account['title'])
                    uploader.upload_videos([video])
                    uploader.auth.profile.stop()
                    timer += 1
                    if timer == len(os.listdir(os.path.abspath('accounts\\accounts_data'))):
                        l = int(round((time.time() - start_time) // 60))
                        timer = 1
                        logger.info(f'All videos for this cycle uploaded, waiting for {30 - l} minutes')
                        if l < 30:
                            time.sleep(30 * 60)
            except:
                logger.log_err()
    except Exception as e:
        logger.log_err()
    finally:
        d.stop_profiles()
        t = round((time.time() - start_time) / 60, 2)
        videos_count = 0
        for i in cfg['accounts']:
            videos_count += len(i['video'])
        logger.info(f'Затраченое время: {str(t)} минут')
        logger.info(f'Скорость постинга: {str(round(videos_count / t, 2))} в/мин')
        send_message('Бот завершил работу')
        send_message(f'Затраченое время: {str(t)} минут')
        send_message(f'Скорость постинга: {str(round(videos_count / t, 2))} в/мин')


if __name__ == '__main__':
    # with sync_playwright() as playwright:
    #     main(playwright)
    import uvicorn
    from src.api import app

    uvicorn.run(app, host="0.0.0.0", port=8000)