#! /usr/bin/python
# -*- coding: utf-8 -*-

import urllib
import httplib
import re
import json
import requests
from bs4 import BeautifulSoup
from twitch import TwitchParser


GAMES_URL = 'http://goodgame.ru/channels/'
LOGIN_URL = 'http://goodgame.ru/ajax/login/'
ALL_STREAMS_JSON_URL = 'http://goodgame.ru/ajax/streams/selector/'
STREAM_DIRECT_URL = 'http://hls.goodgame.ru/hls/%s_%s.m3u8'
STREAM_SOURCE_URL = 'http://hls.goodgame.ru/hls/%s.m3u8'
FAV_STREAMS_URL = 'http://goodgame.ru/view/?q=/channels/favorites/'
ALL_STREAMS_URL = 'http://goodgame.ru/ajax/streams/channels/'
STREAMS_API_URL = 'http://api2.goodgame.ru/v2/streams?game=%s&page=%s'
CHANNELS_API_URL = 'http://api2.goodgame.ru/v2/streams/%s'


class GGParser:
    def __init__(self, plugin, loader):
        self.plugin = plugin
        self.loader = loader
        self.twitch_enabled = self.plugin.get_setting('p_twitch') == 'true'
        self.source_only = self.plugin.get_setting('q_best') == 'true'
        self.set_qualities()

    def set_qualities(self):
        self.gg_qualities = []
        self.twitch_qualities = []
        if self.source_only:
            self.gg_qualities.append(1080)
            self.twitch_qualities.append(1080)
        else:
            if  self.plugin.get_setting('q_mobile') == 'true':
                self.gg_qualities.append(240)
                self.twitch_qualities.append(266)
            if self.plugin.get_setting('q_low') == 'true':
                if 240 not in self.gg_qualities:
                    self.gg_qualities.append(240)
                self.twitch_qualities.append(360)
            if self.plugin.get_setting('q_medium') == 'true':
                self.gg_qualities.append(480)
                self.twitch_qualities.append(480)
            if self.plugin.get_setting('q_high') == 'true':
                self.gg_qualities.append(720)
                self.twitch_qualities.append(720)
            if self.plugin.get_setting('q_high') == 'true':
                self.gg_qualities.append(1080)
                self.twitch_qualities.append(1080)

    def parse_games(self):
        web_page = self.loader.load_page(GAMES_URL)
        soup = BeautifulSoup(web_page, "html.parser")
        games_div = soup.find('div', 'swiper-container')
        games = []

        games.append({'cover': self.local_media('gm_all-translations_poster.jpg'), 'tag': 'all', 'title': u'Все стримы'})
        if games_div is not None:
            games_cells = games_div.find_all('a')
            for game_cell in games_cells:
                try:
                    tag = re.findall('\/channels\/(.*?)\/', game_cell['href'], re.UNICODE)
                    if tag:
                        title = game_cell.find('div').text
                        image_tag = game_cell.find('img')

                        if image_tag is not None:
                            thumb = image_tag['src']
                        else:
                            thumb = ''
                        games.append({'cover': thumb, 'tag': tag[0], 'title': title})
                except TypeError:
                    continue

        return games

    def load_page_streams_apiv2(self, game='', page=1):
        data = requests.get(STREAMS_API_URL % (game, page))
        data = data.json()
        streams = self.parse_streams_apiv2(data['_embedded']['streams'])
        if data['page'] < data['page_count']:
            if game=='':
                game = 'all'
            streams.append(self.next_page(data['page'], game))
        return streams

    def parse_streams_apiv2(self, data):
        streams = []
        for stream in data:
            stream_id = stream['channel']['gg_player_src']
            if stream_id == False:
                stream_id = str(stream['channel']['id'])

            if stream['channel']['player_type'] == 'Premium':
                for quality in self.gg_qualities:
                    if quality == 1080:
                        url = STREAM_SOURCE_URL % (stream_id)
                    else:
                        url = STREAM_DIRECT_URL % (stream_id, quality)
                    item= self.build_stream_item(stream_id, quality, stream['channel'], url)
                    streams.append(item)

            elif stream['channel']['player_type'] == 'GoodGame':
                url = STREAM_SOURCE_URL % (stream_id)
                quality = u'Source'
                item= self.build_stream_item(stream_id, quality, stream['channel'], url)
                streams.append(item)

            elif stream['channel']['player_type'] == 'Twitch' and self.twitch_enabled:
                twitch_stream = TwitchParser(self.extract_twitch_id(stream['channel']['embed']), self.twitch_qualities)
                twitch_qualities =twitch_stream.get_qualities()
                for quality in twitch_qualities:
                    item= self.build_stream_item(stream_id, quality['quality'], stream['channel'], quality['url'])
                    streams.append(item)

        return streams

    def build_stream_item(self, stream_id, quality, stream, url, type='stream'):
        if re.search('goodgame.ru',url):
            platform= 'G'
        else:
            platform= 'T'

        return {
                    'id': stream_id,
                    'title': self.make_title(quality, stream['key'], stream['title'], platform),#'%sp' % quality
                    'title2': stream['title'],
                    'quality': quality,
                    'author': stream['key'],
                    'url': url,
                    # 'viewers': stream['viewers'],
                    'image': stream['thumb'].replace('_240', ''),
                    'poster':stream['img'],
                    'type': type
                }

    def load_page_streams_favourite(self):
        web_page = self.loader.load_page(FAV_STREAMS_URL)
        soup = BeautifulSoup(web_page, "html.parser")
        streams_cells = soup.find_all('li', 'channel')
        streams = self.parse_streams_favourite(streams_cells)
        return streams

    def parse_streams_favourite(self, streams_cells):
        streams = []
        for stream_cell in streams_cells:
            try:
                if stream_cell.find('div', 'offline'):
                    break

                stream_id = re.sub('^c', '', stream_cell['id'])
                image_tag = stream_cell.find('img')
                if image_tag is not None:
                    image = image_tag['src']
                else:
                    image = ''

                if re.search('goodgame.ru',image):
                    stream = {
                        'title': stream_cell.find('span', 'stream-name').text,
                        'key': stream_cell.find('span', 'streamer').text,
                        'viewers': stream_cell.find('span', 'views').text,
                        'thumb': image,
                        'img': image
                    }
                    if stream_cell.find('a','premium'):
                        for quality in self.gg_qualities:
                            if quality == 1080:
                                url = STREAM_SOURCE_URL % (stream_id)
                            else:
                                url = STREAM_DIRECT_URL % (stream_id, quality)
                            item= self.build_stream_item(stream_id, quality, stream, url, type='fav')
                            streams.append(item)
                    else:
                        url = STREAM_SOURCE_URL % (stream_id)
                        quality = u'Source'
                        item= self.build_stream_item(stream_id, quality, stream, url, type='fav')
                        streams.append(item)
                else:
                    channel_url = stream_cell.find('a', 'streamer-link')
                    channel_name = re.search('channel\/(.*)\/', channel_url['href'])
                    stream_api = self.get_channel_apiv2(channel_name.group(1))
                    if stream_api['channel']['player_type'] == 'Twitch' and self.twitch_enabled:
                        twitch_stream = TwitchParser(self.extract_twitch_id(stream_api['channel']['embed']), self.twitch_qualities)
                        twitch_qualities =twitch_stream.get_qualities()
                        for quality in twitch_qualities:
                            item= self.build_stream_item(stream_id, quality['quality'], stream_api['channel'], quality['url'], type='fav')
                            streams.append(item)
                    else:
                        continue
            except TypeError:
                continue
        return streams

    def load_page_streams_rest(self, page, tag):
        postData = urllib.urlencode([('game', 'rest'), ('page', page)])
        web_page = self.loader.load_page(ALL_STREAMS_URL, postData)
        soup = BeautifulSoup(web_page, "html.parser")
        streams_cells = soup.find_all('li')
        streams = self.parse_streams_rest(streams_cells)

        if len(streams_cells) == 40:
            streams.append(self.next_page(page, 'rest'))
        return streams

    def parse_streams_rest(self, streams_cells):
        streams = []
        for stream_cell in streams_cells:
            try:
                stream_id = re.sub('^c', '', stream_cell['id'])
                image_tag = stream_cell.find('img')
                if stream_cell['data-isgoodgame'] == '1':
                    if image_tag is not None:
                        image = image_tag['src'].replace('_240', '')
                    else:
                        image = ''
                    stream = {
                        'title': stream_cell.find('span', 'stream-name').text,
                        'key': stream_cell.find('span', 'streamer').text,
                        'viewers': stream_cell.find('span', 'views').text,
                        'thumb': image,
                        'img': image
                    }
                    if stream_cell['data-ispremium'] != '1':
                        url = STREAM_SOURCE_URL % (stream_id)
                        quality = u'Source'
                        item= self.build_stream_item(stream_id, quality, stream, url)
                        streams.append(item)
                    else:
                        for quality in self.gg_qualities:
                            if quality == 1080:
                                url = STREAM_SOURCE_URL % (stream_id)
                            else:
                                url = STREAM_DIRECT_URL % (stream_id, quality)
                            item= self.build_stream_item(stream_id, quality, stream, url)
                            streams.append(item)
                else:
                    channel_url = stream_cell.find('a', 'streamer-link')
                    channel_name = re.search('channel\/(.*)\/', channel_url['href'])
                    stream_api = self.get_channel_apiv2(channel_name.group(1))
                    if stream_api['channel']['player_type'] == 'Twitch' and self.twitch_enabled:
                        twitch_stream = TwitchParser(self.extract_twitch_id(stream_api['channel']['embed']), self.twitch_qualities)
                        twitch_qualities =twitch_stream.get_qualities()
                        for quality in twitch_qualities:
                            item= self.build_stream_item(stream_id, quality['quality'], stream_api['channel'], quality['url'])
                            streams.append(item)
                    else:
                        continue

            except TypeError:
                continue
        return streams

    def next_page(self, page, game):
        return {
            'title': '[COLOR=FFD02090]' +u"Следующая страница" + '[/COLOR]',
            'url': {
                'tag': game,
                'page': str(int(page) + 1),
            },
            'image': '',
            'type': 'next'
        }

    def make_title(self, quality, author, title, platform):
        if platform == 'T':
            color = '9400D3'
        else:
            color = '0000FF'
        return '[COLOR=FF%s][B][%s][/B][/COLOR][COLOR=FFFFFF00][%s][/COLOR][COLOR=FF00BFFF][B] %s[/B][/COLOR] - %s' % (color, platform,quality, author, title)

    def local_media(self, file):
        addon_id = self.plugin._addon.getAddonInfo('id')
        return 'special://home/addons/%s/resources/media/%s' % (addon_id, file)

    def _extract_id(self, src):
        data = re.search('.*player\?(\w*)\\"', src)
        if data:
            return 'gg', data.group(1)

        data = re.search('.*\/?channel=(\w*)\\"', src)
        if data:
            print u'Twitch'
            return 'tw', data.group(1)

        # data = re.search('.*\/embed\.php\?c=(\w*)&', src)
        # if data:
        #     print u'Cybergame'
        #     return 'cg', data.group(1)

        return False, False

    def extract_twitch_id(self, src):
        data = re.search('.*\/?channel=(\w*)\\"', src)
        return data.group(1)

    # http://api.cybergame.tv/p/embed.php?c=ladychimera&w=100pc&h=100pc&type=embed
    # http://stream1.cybergame.tv:8080/premium2/%s.m3u8
    # http://st.cybergame.tv:8080/live2/pzn.m3u8
    # http://stream2.cybergame.tv:8080/live2/pzn.m3u8
    def extract_cg_id(self, src):
        data = re.search('\/embed.php\?c=(\w*)&"', src)
        return data.group(1)

    def get_channel_apiv2(self, channel_id):
        data = requests.get(CHANNELS_API_URL % channel_id)
        data = data.json()
        return data

    def check_login_error(self, result):
        result = json.loads(result)
        return (result['code'] == 1 or result['code'] == 4)

    def login(self):
        if self.loader.is_logged_in():
            return True

        loginData = [('nickname', self.plugin.get_setting('login_name')),
                     ('password', self.plugin.get_setting('login_password')), ('remember', '1'), ('return', 'user')]
        postData = urllib.urlencode(loginData)
        result = self.loader.load_page(LOGIN_URL, postData)
        return self.check_login_error(result)

