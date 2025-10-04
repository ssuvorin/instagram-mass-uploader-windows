import os

import tiktok_captcha_solver.selectors
from tiktok_captcha_solver.playwrightsolver import PlaywrightSolver

from tiktok_uploader.bot_integration import logger


class IconV3:
    IMAGE = ".captcha-verify-container .cap-relative img"
    SUBMIT_BUTTON = ".captcha-verify-container .TUXButton.TUXButton--primary"
    TEXT = ".captcha-verify-container span"
    UNIQUE_IDENTIFIER = ".captcha-verify-container"


def solve_captcha(page):
    logger.info('Solving captcha if present')
    sadcaptcha = PlaywrightSolver(page, os.environ.get('TIKTOK_SOLVER_API_KEY'))
    sadcaptcha.solve_captcha_if_present()