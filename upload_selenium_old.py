import time

from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By

from bot.src import logger
from bot.src.instagram_uploader import config


def upload_video(driver: WebDriver, video: str, title, location=None, mentions=None):
    logger.info(f'Now uploading video {video} with title {title}')

    title = title.encode('utf-8', 'ignore').decode('utf-8')
    if location:
        location = location.encode('utf-8', 'ignore').decode('utf-8')

    time.sleep(config['implicitly_wait'])

    new_post_button = WebDriverWait(driver, config['implicitly_wait']).until(
        EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['new_post_button']))
    )

    new_post_button.click()

    try:
        alternate_post_button = WebDriverWait(driver, config['implicitly_wait']).until(
            EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['alternate_post_button']))
        )
        alternate_post_button.click()
    except:
        pass

    time.sleep(config['implicitly_wait'])

    upload_button = WebDriverWait(driver, config['explicit_wait']).until(
        EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['upload_path']))
    )
    upload_button.send_keys(video)

    time.sleep(config['implicitly_wait'])

    try:
        WebDriverWait(driver, config['implicitly_wait']).until(
            EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['OK']))
        ).click()
        time.sleep(1)
    except:
        pass

    logger.info('Setting crop')

    select_crop = WebDriverWait(driver, config['implicitly_wait']).until(
        EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['select_crop']))
    )
    select_crop.click()
    original_crop = WebDriverWait(driver, config['implicitly_wait']).until(
        EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['original_crop']))
    )
    original_crop.click()
    select_crop.click()

    time.sleep(2)

    for _ in range(2):
        _next_page(driver)

    logger.info(f'Setting a description: {title}')

    try:
        description_field = WebDriverWait(driver, config['implicitly_wait']).until(
            EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['description_field']))
        )
        for i in title:
            description_field.send_keys(i)
            time.sleep(0.05)
    except Exception as e:
        print(e)

    time.sleep(2)

    if location:
        location = location.encode('utf-8', 'ignore').decode('utf-8')
        logger.info(f'Setting location {location}')
        location_field = WebDriverWait(driver, config['implicitly_wait']).until(
            EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['location_field']))
        )
        location_field.send_keys(location)
        first_location = WebDriverWait(driver, config['explicit_wait']).until(
            EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['first_location']))
        )
        first_location.click()
        time.sleep(2)
    if mentions:
        for mention in mentions:
            mention_field = driver.find_element(By.XPATH, config['selectors']['upload']['mentions_field'])
            mention_field.send_keys(mention)
            time.sleep(config['implicitly_wait'])
            first_mention = WebDriverWait(driver, config['explicit_wait']).until(
                EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['first_mention'].format(mention)))
            )
            first_mention.click()
        done_btn = WebDriverWait(driver, config['implicitly_wait']).until(
            EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['done_mentions']))
        )
        done_btn.click()
        time.sleep(2)

    WebDriverWait(driver, config['implicitly_wait']).until(
        EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['post_video']))
    ).click()

    try:
        WebDriverWait(driver, config['explicit_wait']).until(
            EC.presence_of_element_located((By.XPATH, config['selectors']['upload']['is_posted']))
        )
        logger.info(f'Video {video} successfully posted')
    except:
        logger.error(f'Video {video} is not posted')

    driver.refresh()


def _next_page(driver):
    time.sleep(3)
    next_page = WebDriverWait(driver, config['implicitly_wait']).until(
        EC.element_to_be_clickable((By.XPATH, config['selectors']['upload']['next']))
    )
    driver.execute_script('arguments[0].click()', next_page)


def upload_videos(driver: WebDriver, videos: list[dict]):
    for video in videos:
        upload_video(
            driver=driver,
            video=video['video_path'],
            title=video['title'] if video['title'] else video['video_path'],
            location=video['location'] if video['location'] else None,
            mentions=video['mentions'] if video['mentions'] else None
        )

    driver.close()

