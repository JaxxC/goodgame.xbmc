#! /usr/bin/python
# -*- coding: utf-8 -*-

import os
import urllib
from xbmcswift2 import Plugin, xbmc
from resources.lib.loader import WebLoader
from resources.lib.parser import GGParser

plugin = Plugin()

_cookie_dir = xbmc.translatePath('special://profile/addon_data/plugin.video.goodgame')

loader = WebLoader(_cookie_dir)
parser = GGParser(plugin, loader)
parser.login()

VIEW_MODE_LIST = '50'
VIEW_MODE_THUMBS = '500'

@plugin.route('/')
def index():
    games = parser.parse_games()
    return compose_index(games)

def compose_index(list):
    items=[]
    for game_info in list:
        path =  plugin.url_for('streams', tag=game_info['tag'], page=1)
        items.append({'label': game_info['title'], 'path': path, 'thumbnail': game_info['cover']})
    plugin.set_content('movies')
    return plugin.finish(items=items, view_mode=VIEW_MODE_THUMBS)

@plugin.route('/streams/<tag>/<page>')
def streams(tag = 'all', page=1):
    if tag == 'favorites':
        streams = parser.load_page_streams_favourite()
    elif tag == 'rest':
        streams = parser.load_page_streams_rest(page, tag)
    elif tag == 'all':
        streams = parser.load_page_streams_apiv2('', page)
    else:
        streams = parser.load_page_streams_apiv2(tag)
    return compose_streams(streams)

def compose_streams(list):
    items=[]
    for stream in list:
        if stream['type'] == 'next':
            items.append({
                'label': stream['title'],
                'path': plugin.url_for('streams', tag=stream['url']['tag'], page=stream['url']['page']),
                'thumbnail': stream['image'],
                'is_playable': False
            })
        else:
            items.append({
                'label': stream['title'],
                'path': stream['url'],
                'thumbnail': stream['image'],
                'context_menu': build_context(stream),
                'info': {
                    'title': stream['title2'],
                    'genre': stream['title2'],
                    'director': stream['author'],
                    'plot': 'Plot',
                    'banner': stream['image'],
                    'poster': stream['image']
                 },
                'is_playable': True
            })
    plugin.set_content('movies')
    return plugin.finish(items=items, view_mode=VIEW_MODE_LIST)

def build_context(stream):
    print stream
    addon_path = plugin.addon.getAddonInfo('path').decode('utf-8')
    if stream['type'] == 'fav':
        context = u'RunScript({addon_path}/resources/lib/commands.py,unsubscribe,{stream_id},{author})'.format(addon_path=addon_path,
                                                                                                                stream_id=urllib.quote_plus(stream['id'].encode('utf-8')),
                                                                                                                author=stream['author'].encode('utf-8'))
        return [( u'Отписаться', context)]
    else:
        context = u'RunScript({addon_path}/resources/lib/commands.py,subscribe,{stream_id},{author})'.format(addon_path=addon_path,
                                                                                                                stream_id=urllib.quote_plus(stream['id'].encode('utf-8')),
                                                                                                                author=stream['author'].encode('utf-8'))
        return [( u'Подписаться', context)]

if __name__ == '__main__':
    plugin.run()