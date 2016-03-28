#! /usr/bin/python
# -*- coding: utf-8 -*-

import sys, urllib
from loader import WebLoader
import xbmcgui, xbmcvfs, xbmc

SUBSCRIBE_URL = 'http://goodgame.ru/ajax/subscribe/'
UNSUBSCRIBE_URL = 'http://goodgame.ru/ajax/unsubscribe/'


def subscribe():
    loader = get_loader()
    if xbmcgui.Dialog().yesno(u'Внимание!', u'Подписаться на канал '+sys.argv[3]):
        postData = urllib.urlencode([('obj', sys.argv[2]), ('obj_type', 7)])
        loader.load_page(SUBSCRIBE_URL, postData)
        xbmcgui.Dialog().ok(u'Внимание!', u'Вы подписались на канал '+sys.argv[3])

def unsubscribe():
    loader = get_loader()
    if xbmcgui.Dialog().yesno(u'Внимание!', u'Отписаться от канала '+sys.argv[3]):
        postData = urllib.urlencode([('obj', sys.argv[2]), ('obj_type', 7)])
        loader.load_page(UNSUBSCRIBE_URL, postData)
        xbmcgui.Dialog().ok(u'Внимание!', u'Вы отписались от канала '+sys.argv[3])

def delete_cookies():
    if xbmcgui.Dialog().yesno(u'Внимание!', u'Действительно удалить cookies?'):
        xbmcvfs.delete('special://profile/addon_data/plugin.video.goodgame/.cookies')

def get_loader():
    _cookie_dir = xbmc.translatePath('special://userdata/addon_data/plugin.video.goodgame')
    loader = WebLoader(_cookie_dir)
    return loader


if __name__ == '__main__':
    if sys.argv[1] == 'subscribe':
        subscribe()
    elif sys.argv[1] == 'unsubscribe':
        unsubscribe()
    elif sys.argv[1] == 'delcookies':
        delete_cookies()
