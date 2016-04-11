#! /usr/bin/python
# -*- coding: utf-8 -*-

import os
import urllib
from xbmcswift2 import Plugin, xbmc, xbmcgui
from resources.lib.loader import WebLoader
from resources.lib.parser import GGParser
import resources.lib.video as voder

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
        path =  plugin.url_for(game_info['type'], tag=game_info['tag'], page=1)
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

@plugin.route('/videos/<tag>/<page>')
def videos(tag = 'all', page=1):
    if tag == 'list':
        streams = parser.parse_games_vods()
        return compose_video_index(streams)

    elif tag == 'search':
        query = plugin.keyboard(heading=u'Поиск'.encode('utf-8', 'replace'))
        if query is None or len(str(query)) == 0:
            return

        streams = parser.search_videos(query, page)
        return compose_videos(streams)

    else:
        streams = parser.load_videos(tag, page)
        return compose_videos(streams)

@plugin.route('/search/<query>/<page>')
def search(query, page=1):
    streams = parser.search_videos(query, page)
    return compose_videos(streams)

def compose_video_index(list):
    items=[]
    for game_info in list:
        path =  plugin.url_for('videos', tag=game_info['tag'], page=1)
        items.append({'label': game_info['title'], 'path': path, 'thumbnail': game_info['cover']})
    plugin.set_content('movies')
    return plugin.finish(items=items, view_mode=VIEW_MODE_THUMBS)

def compose_videos(list):
    items=[]
    for vod in list:
        if vod['type'] == 'next':
            if vod['url']['tag'] == 'search':
                path = plugin.url_for('search', query=vod['url']['query'], page=vod['url']['page'])
            else:
                path = plugin.url_for('videos', tag=vod['url']['tag'], page=vod['url']['page'])
            items.append({
                'label': vod['title'],
                'path': path,
                'thumbnail': vod['image'],
                'is_playable': False
            })
        else:
            items.append({
                'label': vod['title'],
                'path': plugin.url_for('video', video_id=vod['id'], thumb=vod['image']),
                'thumbnail': vod['image'],
                # 'context_menu': build_context(stream),
                'info': {
                    'title': vod['title2'],
                    'genre': vod['title2'],
                    'director': vod['author'],
                    'plot': 'Plot',
                    'banner': vod['image'],
                    'poster': vod['image']
                 },
                'is_playable': False
            })
    plugin.set_content('movies')
    return plugin.finish(items=items, view_mode=VIEW_MODE_LIST)

@plugin.route('/video/<video_id>/<thumb>')
def video(video_id, thumb):
    videos = parser.load_video_page(video_id)
    return plugin.finish(items=compose_video(videos, thumb), view_mode=VIEW_MODE_LIST)

def compose_video(list, thumb):
    yt_vods = plugin.get_storage('yt_vods')
    tw_vods = plugin.get_storage('tw_vods')
    items = []
    for vod in list:
        if vod['type'] == voder.PLAYER_TYPE_YT:
            items.append({
                'label': vod['label'],
                'path': plugin.url_for('play', type = vod['type'], video_id=vod['id'], title=vod['label'].encode('utf-8'), img=vod['thumb']),
                'thumbnail': vod['thumb'],
                'is_playable': False
            })
            yt_vods[vod['id']] = vod['links']
        elif vod['type'] == voder.PLAYER_TYPE_GG:
            items.append({
                'label': vod['label'],
                'path': plugin.url_for('play', type = vod['type'], video_id=vod['path'], title=vod['label'].encode('utf-8'), img=thumb),
                'thumbnail': thumb,
                'is_playable': False
            })
        elif vod['type'] == voder.PLAYER_TYPE_TW:
            items.append({
                'label': vod['label'],
                'path': plugin.url_for('play', type = vod['type'], video_id=vod['id'], title=vod['label'].encode('utf-8'), img=thumb),
                'thumbnail': thumb,
                'is_playable': False
            })
            tw_vods[vod['id']] = vod['links']
    return items

@plugin.route('/play/<type>/<video_id>/<title>/<img>')
def play(type, video_id, title, img):
    if int(type) == voder.PLAYER_TYPE_YT:
        yt_vods = plugin.get_storage('yt_vods')
        if video_id in yt_vods:
            links = yt_vods[video_id]
            possibleChoices = []
            for link in links:
                possibleChoices.append(link['quality'])
            listitem =xbmcgui.ListItem(title, thumbnailImage=img)
            choice = xbmcgui.Dialog().select(u'Играть:', possibleChoices)
            if choice >= 0:
                xbmc.Player().play(links[choice]['url'], listitem)

    elif int(type) == voder.PLAYER_TYPE_GG:
        listitem =xbmcgui.ListItem(title, thumbnailImage=img)
        rtmpurl = 'rtmp://46.61.227.158:1940/vod/ app=vod/ playpath=%s' % (urllib.unquote(video_id))
        xbmc.Player().play(rtmpurl, listitem)

    elif int(type) == voder.PLAYER_TYPE_TW:
        tw_vods = plugin.get_storage('tw_vods')
        if video_id in tw_vods:
            links = tw_vods[video_id]
            possibleChoices = []
            for link in links:
                possibleChoices.append(link['quality'])
            listitem =xbmcgui.ListItem(title, thumbnailImage=img)
            choice = xbmcgui.Dialog().select(u'Играть:', possibleChoices)
            if choice >= 0:
                xbmc.Player().play(links[choice]['url'], listitem)

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