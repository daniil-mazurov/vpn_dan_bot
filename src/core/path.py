"""Путь к директории приложения"""

import os


def get_path():
    PATH = __file__
    for _ in range(3):
        PATH = os.path.dirname(PATH)
    return PATH

PATH = get_path()
"""PATH TO VPN_DAN_BOT"""
