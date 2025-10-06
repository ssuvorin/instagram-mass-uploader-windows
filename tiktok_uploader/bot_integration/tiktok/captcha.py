import os

from tiktok_captcha_solver.playwrightsolver import PlaywrightSolver

from tiktok_uploader.bot_integration import logger


def solve_captcha(page):
    logger.info('Solving captcha if present')
    sadcaptcha = PlaywrightSolver(page, os.environ.get('TIKTOK_SOLVER_API_KEY'))
    sadcaptcha.solve_captcha_if_present()