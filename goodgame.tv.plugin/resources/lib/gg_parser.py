#! /usr/bin/python
# -*- coding: utf-8 -*-

import os
import urllib
import urllib2
import socket
import cookielib
import httplib
import re
import json
import requests
from bs4 import BeautifulSoup

if __name__ == '__main__':
    # This is for testing purposes when the module is run from console.
    _cookie_dir = os.path.dirname(__file__)
else:
    import xbmc

    _cookie_dir = xbmc.translatePath('special://profile/addon_data/goodgame.tv.plugin').decode('utf-8')

GAMES_URL = 'http://goodgame.ru/channels/'
LOGIN_URL = 'http://goodgame.ru/ajax/login/'
ALL_STREAMS_JSON_URL = 'http://goodgame.ru/ajax/streams/selector/'
STREAM_DIRECT_URL = 'http://hls.goodgame.ru/hls/%s_%s.m3u8'
AVAILABLE_QUALITIES = [240, 480, 720, 1080]
FAV_STREAMS_URL = 'http://goodgame.ru/view/?q=/channels/favorites/'
ALL_STREAMS_URL = 'http://goodgame.ru/ajax/streams/channels/'
STREAMS_API_URL = 'http://goodgame.ru/api/getchannelsbygame?game=%s&fmt=json'
SUBSCRIBE_URL = 'http://goodgame.ru/ajax/subscribe/'
UNSUBSCRIBE_URL = 'http://goodgame.ru/ajax/unsubscribe/'


class Opener(object):
    headers = [('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:26.0) Gecko/20100101 Firefox/26.0'),
               ('Accept-Charset', 'UTF-8'),
               ('Accept', 'text/html'),
               ('Connection', 'keep-alive')]

    def __init__(self, handler=urllib2.BaseHandler(), host='http://goodgame.ru'):
        self.opener = urllib2.build_opener(handler)
        self.headers.append(('Host', host))
        self.opener.addheaders = self.headers

    def open(self, url, data=None):
        return self.opener.open(url, data)

    def get_page(self, url, data=None):
        try:
            session = self.opener.open(url, data)
        except (urllib2.URLError, socket.timeout) as ex:
            print 'webloader.Opener.get_page. Connection error'
            web_page = ''
        else:
            web_page = session.read().decode('utf-8', 'replace')
            session.close()
        return web_page


class WebLoader():
    def __init__(self):
        self.cookie_file = os.path.join(_cookie_dir, '.cookies')
        self.cookie_jar = cookielib.LWPCookieJar(self.cookie_file)
        if not os.path.exists(self.cookie_file):
            self.cookie_jar.save()
        self.cookie_jar.revert()
        self.opener = Opener(handler=urllib2.HTTPCookieProcessor(self.cookie_jar))

    def set_addon(self, addon):
        self.addon = addon
        min_quality = int(self.addon.getSetting('min_quality'))
        min_index = AVAILABLE_QUALITIES.index(min_quality)
        max_quality = int(self.addon.getSetting('max_quality'))
        max_index = AVAILABLE_QUALITIES.index(max_quality) + 1
        if max_index < min_index:
            max_index = min_index
        self.available_qualities = AVAILABLE_QUALITIES[min_index:max_index]

    def loadPage(self, url, data=None):
        self.cookie_jar.load()
        web_page = self.opener.get_page(url, data)
        self.cookie_jar.save()
        return web_page

    def get_games(self):
        web_page = self.loadPage(GAMES_URL)
        search = re.findall('__DDOS_COOKIE=([a-z0-9]*);.*max-age=([0-9]+)', web_page)
        if search:
            self.add_ddos_cookie(search)
            web_page = self.loadPage(GAMES_URL)
        soup = BeautifulSoup(web_page, "html.parser")
        games_div = soup.find('div', 'swiper-container')
        games = []
        if games_div is not None:
            games_cells = games_div.find_all('a')
            for game_cell in games_cells:
                try:
                    tag = re.findall('\/channels\/(.*?)\/', game_cell['href'], re.UNICODE)
                    image_tag = game_cell.find('img')

                    if image_tag is not None:
                        thumb = image_tag['src']
                    else:
                        thumb = ''

                    if not tag:
                        tag = ['popular'];
                        title = u'Популярные'.encode('utf-8')
                    else:
                        title = game_cell.find('div').text.encode('utf-8')
                except TypeError:
                    continue
                else:
                    games.append({'cover': thumb, 'tag': tag[0], 'title': title})
        return games

    def get_streams_from_api(self, game):
        streams = []
        data = requests.get(STREAMS_API_URL % game)
        data = data.json()

        for id in data:
            stream_id = self._extract_id(data[id]['embed'])
            if not stream_id:
                continue

            for quality in self.available_qualities:
                url = STREAM_DIRECT_URL % (stream_id, quality)
                if quality == 1080:
                    url = url.replace('_1080', '')
                if not self._is_stream_avaliable(url):
                    continue

                title = self.make_title(quality, data[id]['key'], data[id]['title'])
                image = data[id]['thumb'].replace('_240', '')

                streams.append({
                    'title': title,
                    'title2': data[id]['title'],
                    'quality': quality,
                    'author': data[id]['key'],
                    'url': url,
                    'viewers': data[id]['viewers'],
                    'image': image,
                    'type': 'stream',
                    'stream_id': stream_id
                })
        return streams

    def get_streams_from_page(self, type='popular', page=1):
        if type == 'popular':
            streams = self.load_page_streams_popular(page)
        elif type == 'rest':
            streams = self.load_page_streams_rest(page)
        else:
            web_page = self.loadPage(FAV_STREAMS_URL)
            search = re.findall('__DDOS_COOKIE=([a-z0-9]*);.*max-age=([0-9]+)', web_page)
            if search:
                self.add_ddos_cookie(search)
                web_page = self.loadPage(FAV_STREAMS_URL)
            soup = BeautifulSoup(web_page, "html.parser")
            streams_cells = soup.find_all('li', 'channel')
            streams = self.parse_favstreams_html(streams_cells)
        return streams

    def load_page_streams_popular(self, page):
        postData = urllib.urlencode([('page', page), ('tab', 'popular')])
        result = self.loadPage(ALL_STREAMS_JSON_URL, postData)
        result = json.loads(result)
        streams = self.parse_allstreams(result['streams'])

        if result['more']:
            streams.append(self.next_page(page, 'popular'))
        return streams

    def load_page_streams_rest(self, page):
        postData = urllib.urlencode([('game', 'rest'), ('page', page)])
        web_page = self.loadPage(ALL_STREAMS_URL, postData)
        soup = BeautifulSoup(web_page, "html.parser")
        streams_cells = soup.find_all('li')
        streams = self.parse_reststreams_html(streams_cells)

        if len(streams_cells) == 40:
            streams.append(self.next_page(page, 'rest'))
        return streams

    def next_page(self, page, game):
        return {
            'title': '[COLOR=FFD02090]' + u"Следующая страница".encode('utf-8') + '[/COLOR]',
            'url': {
                'tag': game,
                'page': str(int(page) + 1),
            },
            'type': 'next'
        }

    def make_title(self, quality, author, title):
        return '[COLOR=FFFFFF00][%sp][/COLOR][COLOR=FF00BFFF][B] %s[/B][/COLOR] - %s' % (quality, author, title)

    def parse_allstreams(self, allstreams):
        streams = []
        for stream in allstreams:
            try:
                stream_id = stream['streamkey']
                viewers = stream['viewers']
                title = stream['title'].encode('utf-8')
                author = stream['streamer'].encode('utf-8')
                image_tag = stream['preview']
                if image_tag is not None:
                    image = image_tag.replace('_240', '')
                else:
                    image = ''

                if stream['premium']:
                    qualities_list = self.available_qualities
                else:
                    qualities_list = [1080]

                for quality in qualities_list:
                    url = STREAM_DIRECT_URL % (stream_id, quality)
                    if quality == 1080:
                        url = url.replace('_1080', '')
                    if not self._is_stream_avaliable(url):
                        continue

                    streams.append({
                        'title': self.make_title(quality, author, title),
                        'title2': title,
                        'quality': quality,
                        'author': author,
                        'url': url,
                        'viewers': viewers,
                        'image': image,
                        'type': 'stream',
                        'stream_id': stream_id
                    })
            except TypeError:
                continue
        return streams

    def parse_reststreams_html(self, streams_cells):
        streams = []
        for stream_cell in streams_cells:
            try:
                if stream_cell['data-isgoodgame'] != '1':
                    continue

                stream_id = re.sub('^c', '', stream_cell['id'])
                viewers = stream_cell.find('span', 'views').text.encode('utf-8')
                title = stream_cell.find('span', 'stream-name').text.encode('utf-8')
                author = stream_cell.find('span', 'streamer').text.encode('utf-8')
                image_tag = stream_cell.find('img')
                if image_tag is not None:
                    image = image_tag['src'].replace('_240', '')
                else:
                    image = ''
                for quality in self.available_qualities:
                    url = STREAM_DIRECT_URL % (stream_id, quality)
                    if quality == 1080:
                        url = url.replace('_1080', '')
                    if not self._is_stream_avaliable(url):
                        continue

                    streams.append({
                        'title': self.make_title(quality, author, title),
                        'title2': title,
                        'quality': quality,
                        'author': author,
                        'url': url,
                        'viewers': viewers,
                        'image': image,
                        'type': 'stream',
                        'stream_id': stream_id
                    })
            except TypeError:
                continue
        return streams

    def parse_favstreams_html(self, streams_cells):
        streams = []
        for stream_cell in streams_cells:
            try:
                if stream_cell.find('div', 'offline'):
                    continue

                stream_id = re.sub('^c', '', stream_cell['id'])

                viewers = stream_cell.find('span', 'views').text.encode('utf-8')
                title = stream_cell.find('span', 'stream-name').text.encode('utf-8')
                author = stream_cell.find('span', 'streamer').text.encode('utf-8')
                image_tag = stream_cell.find('img')
                if image_tag is not None:
                    image = image_tag['src'].replace('_240', '')
                else:
                    image = ''
                for quality in self.available_qualities:
                    url = STREAM_DIRECT_URL % (stream_id, quality)
                    if quality == 1080:
                        url = url.replace('_1080', '')
                    if not self._is_stream_avaliable(url):
                        continue

                    streams.append({
                        'title': self.make_title(quality, author, title),
                        'title2': title,
                        'quality': quality,
                        'author': author,
                        'url': url,
                        'viewers': viewers,
                        'image': image,
                        'type': 'fav',
                        'stream_id': stream_id
                    })
            except TypeError:
                continue
        return streams

    def _extract_id(self, src):
        data = re.search('.*player\?(\w*)\\"', src)
        if not data:
            return False
        return data.group(1)

    def _is_stream_avaliable(self, url):
        c = httplib.HTTPConnection('hls.goodgame.ru')
        c.request("HEAD", url)
        if c.getresponse().status == 200:
            return True
        return False

    def is_logged_in(self):
        for cookie in self.cookie_jar:
            if cookie.name == 'uid' and len(cookie.value) > 1:
                return True
        return False

    def check_login_error(self, result):
        result = json.loads(result)
        return (result['code'] == 1 or result['code'] == 4)

    def add_ddos_cookie(self, search):
        ck = cookielib.Cookie(version=0, name='__DDOS_COOKIE', value=search[0][0], port=None, port_specified=False,
                                  domain='goodgame.ru', domain_specified=False, domain_initial_dot=False, path='/',
                                  path_specified=True, secure=False, expires=None, discard=True, comment=None,
                                  comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
        self.cookie_jar.set_cookie(ck)

    def login(self):
        if self.is_logged_in():
            return True

        loginData = [('nickname', self.addon.getSetting('login_name')),
                     ('password', self.addon.getSetting('login_password')), ('remember', '1'), ('return', 'user')]
        postData = urllib.urlencode(loginData)
        result = self.loadPage(LOGIN_URL, postData)
        return self.check_login_error(result)

    def subscribe(self, channelId):
        postData = urllib.urlencode([('obj', channelId), ('obj_type', 7)])
        self.loadPage(SUBSCRIBE_URL, postData)

    def unsubscribe(self, channelId):
        postData = urllib.urlencode([('obj', channelId), ('obj_type', 7)])
        self.loadPage(UNSUBSCRIBE_URL, postData)


loader = WebLoader()


def set_addon(addon):
    loader.set_addon(addon)


def get_games():
    loader.login()
    return loader.get_games()


def get_streams_from_page(game, page):
    return loader.get_streams_from_page(game, page)


def get_streams_from_api(game):
    return loader.get_streams_from_api(game)


def subscribe(channelId, sub=1):
    if sub:
        loader.subscribe(channelId)
    else:
        loader.unsubscribe(channelId)
