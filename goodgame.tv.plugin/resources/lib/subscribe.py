# -*- coding: utf-8 -*-
# Name:        commands
# Author:      Roman V.M.
# Created:     15.02.2014
# Licence:     GPL v.3: http://www.gnu.org/copyleft/gpl.html

import sys
import gg_parser
# import xbmcvfs
import xbmcgui


def subscribe():
    print sys.argv
    if xbmcgui.Dialog().yesno(u'Внимание!', u'Подписаться на канал '+sys.argv[3]):
        gg_parser.subscribe(sys.argv[2], 1)
        xbmcgui.Dialog().ok(u'Внимание!', u'Вы подписались на канал '+sys.argv[3])


def unsubscribe():
    if xbmcgui.Dialog().yesno(u'Внимание!', u'Отписаться от канала '+sys.argv[3]):
        gg_parser.subscribe(sys.argv[2], 0)
        xbmcgui.Dialog().ok(u'Внимание!', u'Вы отписались от канала '+sys.argv[3])

if __name__ == '__main__':
    if sys.argv[1] == 'subscribe':
        subscribe()
    elif sys.argv[1] == 'unsubscribe':
        unsubscribe()
