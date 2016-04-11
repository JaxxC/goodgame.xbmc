#! /usr/bin/python
# -*- coding: utf-8 -*-

import re, urllib
import youtube
from resources.lib.twitch import TwitchVodParser

twitch = TwitchVodParser()
PLAYER_TYPE_GG = 1
PLAYER_TYPE_YT = 2
PLAYER_TYPE_TW = 3


def parse_players(soup, loader):
    players = soup.find_all('div', attrs={'class': 'block flash-player'})
    items = []
    gg_cnt = 0
    tw_cnt = 0
    for player in players:
        player_gg = player.find('object', attrs={'id': 'ggVideoPlayer'})
        if player_gg:
            items.append(process_player_gg(soup, player_gg, gg_cnt))
            gg_cnt+= 1
            continue

        player_yt = player.find('iframe', attrs={'src': re.compile('https:\/\/www.youtube.com\/embed.*')})
        if player_yt:
            items.append(process_player_yt(player_yt['src'], loader))
            continue

        player_tw = player.find('iframe', attrs={'src': re.compile('http:\/\/player.twitch.tv.*')})
        if player_tw:
            items.append(process_player_tw(player_tw['src'], soup, tw_cnt))
            tw_cnt+= 1
            continue
    return items

def process_player_gg(player, player_gg, cnt):
    title = player.find('h1').text
    src = player_gg.find('param', {'name': 'flashvars'})
    n = '[%s]' % cnt+1 if cnt>0  else ''
    return {
        'label': '[COLOR=FF300AEF][B][G][/B][/COLOR] [COLOR=FFB5A7FB]%s%s[/COLOR]' % (n,title),
        'id': '0',
        'path': src['value'].replace('src=//', ''),
        'thumb': ' ',
        'type': PLAYER_TYPE_GG
    }

def process_player_yt(url, loader):
    id = extract_yt_id(url)
    info = youtube.get_video_url('https://www.youtube.com/watch?v='+id, loader)
    return {
        'label': '[COLOR=FFC10D13][B][Y][/B][/COLOR] [COLOR=FFF89195]%s[/COLOR]' % (info['title']),
        'id': id,
        'links': info['urls'],
        'thumb': info['img'],
        'type': PLAYER_TYPE_YT
    }

def process_player_tw(url, player, cnt):
    id = extract_tw_id(url)
    info = twitch.get_vod(id);
    title = player.find('h1').text
    n = '[%s]' % str(cnt+1) if cnt>0  else ''
    return {
        'label': '[COLOR=FF511A64][B][T][/B][/COLOR] [COLOR=FFC57EDD]%s%s[/COLOR]' % (n,title),
        'id': id,
        'links': info,
        'thumb': ' ',
        'type': PLAYER_TYPE_TW
    }

def get_size(url):
    d = urllib.urlopen(url)
    print d.info()['Content-Length']

def extract_yt_id(url):
     id = re.search('https:\/\/www\.youtube\.com\/embed\/(.*)', url)
     return id.group(1)

def extract_tw_id(url):
     id = re.search('player\.twitch\.tv\/\?video=.(\d+)', url)
     return id.group(1)

