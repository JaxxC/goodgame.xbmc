#! /usr/bin/python

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
ALL_STREAMS_URL = 'http://goodgame.ru/ajax/streams/channels/'
STREAM_DIRECT_URL = 'http://hls.goodgame.ru/hls/%s_%s.m3u8'
AVAILABLE_QUALITIES = [240, 480, 720, 1080]
FAV_STREAMS_URL = 'http://goodgame.ru/channels/favorites/'
STREAMS_API_URL = 'http://goodgame.ru/api/getchannelsbygame?game=%s&fmt=json'


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

    def loadPage(self, url, data=None):
        self.cookie_jar.load()
        web_page = self.opener.get_page(url, data)
        self.cookie_jar.save()
        return web_page

    def get_games(self):
        web_page = self.loadPage(GAMES_URL)
        soup = BeautifulSoup(web_page, "html.parser")
        games_div = soup.find('div', 'swiper-container')
        games = []
        if games_div is not None:
            games_cells = games_div.find_all('a')
            for game_cell in games_cells:
                try:
                    tag = re.findall('\/channels\/(.*?)\/', game_cell['href'], re.UNICODE)
                    if not tag:
                        tag = ['gg'];
                    image_tag = game_cell.find('img')
                    if image_tag is not None:
                        thumb = image_tag['src']
                    else:
                        thumb = ''
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

            for quality in AVAILABLE_QUALITIES:
                url = STREAM_DIRECT_URL % (stream_id, quality)
                if quality == 1080:
                    url = url.replace('_1080', '')
                if not self._is_stream_avaliable(url):
                    continue

                title = '[%sp] %s - %s' % (quality, data[id]['key'], data[id]['title'])
                image = data[id]['thumb'].replace('_240', '')

                streams.append({
                    'title': title,
                    'title2': data[id]['title'],
                    'quality': quality,
                    'author': data[id]['key'],
                    'url': url,
                    'viewers': data[id]['viewers'],
                    'image': image
                })
        return streams

    def get_streams_from_page(self, type='gg'):
        page = 1
        streams = []
        streams_cells = 1
        if type == 'gg':
            while streams_cells:
                postData = urllib.urlencode([('game', type), ('page', page)])
                web_page = self.loadPage(ALL_STREAMS_URL, postData)
                soup = BeautifulSoup(web_page, "html.parser")
                streams_cells = soup.find_all('li')
                streams = self.parse_allstreams_html(streams_cells, streams)
                page = page + 1
        else:
            web_page = self.loadPage(FAV_STREAMS_URL)
            soup = BeautifulSoup(web_page, "html.parser")
            streams_cells = soup.find_all('li', 'channel')
            streams = self.parse_favstreams_html(streams_cells)
        return streams

    def parse_allstreams_html(self, streams_cells, streams=[]):
        for stream_cell in streams_cells:
            try:
                if stream_cell['data-isgoodgame'] != '1':
                    continue

                stream_id = stream_cell['id'].replace('c', '')
                viewers = stream_cell.find('span', 'views').text.encode('utf-8')
                title = stream_cell.find('span', 'stream-name').text.encode('utf-8')
                author = stream_cell.find('span', 'streamer').text.encode('utf-8')
                image_tag = stream_cell.find('img')
                if image_tag is not None:
                    image = image_tag['src'].replace('_240', '')
                else:
                    image = ''
                for quality in AVAILABLE_QUALITIES:
                    url = STREAM_DIRECT_URL % (stream_id, quality)
                    if quality == 1080:
                        url = url.replace('_1080', '')
                    if not self._is_stream_avaliable(url):
                        continue

                    streams.append({
                        'title': '[%sp] %s - %s' % (quality, author, title),
                        'title2': title,
                        'quality': quality,
                        'author': author,
                        'url': url,
                        'viewers': viewers,
                        'image': image
                    })
            except TypeError:
                continue
        return streams

    def parse_favstreams_html(self, streams_cells):
        streams = []
        for stream_cell in streams_cells:
            try:
                if stream_cell.find('div', 'offline'):
                    return streams

                a = stream_cell.find('a', href="/")
                stream = re.findall('return obj_unsubscribe\(.*, (.*?),.*', a['onclick'], re.UNICODE)
                if stream:
                    stream_id = stream[0]
                else:
                    continue

                viewers = stream_cell.find('span', 'views').text.encode('utf-8')
                title = stream_cell.find('span', 'stream-name').text.encode('utf-8')
                author = stream_cell.find('span', 'streamer').text.encode('utf-8')
                image_tag = stream_cell.find('img')
                if image_tag is not None:
                    image = image_tag['src'].replace('_240', '')
                else:
                    image = ''
                for quality in AVAILABLE_QUALITIES:
                    url = STREAM_DIRECT_URL % (stream_id, quality)
                    if quality == 1080:
                        url = url.replace('_1080', '')
                    if not self._is_stream_avaliable(url):
                        continue

                    streams.append({
                        'title': '[%sp] %s - %s' % (quality, author, title),
                        'title2': title,
                        'quality': quality,
                        'author': author,
                        'url': url,
                        'viewers': viewers,
                        'image': image
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

    def login(self, nickname, password):
        if self.is_logged_in():
            return True

        loginData = [('nickname', nickname), ('password', password), ('remember', '1'), ('return', 'user')]
        postData = urllib.urlencode(loginData)
        result = self.loadPage(LOGIN_URL, postData)
        print self.cookie_jar
        return self.check_login_error(result)


loader = WebLoader()


def get_games(addon):
    loader.login(addon.getSetting('login_name'),addon.getSetting('login_password'))
    return loader.get_games()


def get_streams_from_page(game):
    return loader.get_streams_from_page(game)


def get_streams_from_api(game):
    return loader.get_streams_from_api(game)
