#! /usr/bin/python

import os
import urllib
import urllib2
import socket
import cookielib
import re
import hashlib
import base64
from bs4 import BeautifulSoup

if __name__ == '__main__':
    # This is for testing purposes when the module is run from console.
    _cookie_dir = os.path.dirname(__file__)
else:
    import xbmc

    _cookie_dir = xbmc.translatePath('special://profile/addon_data/plugin.video.goodgame').decode('utf-8')


class Opener(object):
    headers = [('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:26.0) Gecko/20100101 Firefox/26.0'),
               ('Accept-Charset', 'UTF-8'),
               ('Accept', 'text/html'),
               ('Connection', 'keep-alive')]

    def __init__(self, handler=urllib2.BaseHandler(), host='http://goodgame.ru'):
        self.opener = urllib2.build_opener(handler)
        self.headers.append('Host', host)
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

    def get_games(self, url, data=None):
        self.cookie_jar.load()
        web_page = self.opener.get_page(url, data)
        self.cookie_jar.save()
        soup = BeautifulSoup(web_page, "html.parser")
        games_div = soup.find('div', 'swiper-container')
        games = []
        if games_div is not None:
            games_cells = games_div.find_all('a')
            for game_cell in games_cells:
                try:
                    tag = re.findall('\/channels\/(.*?)\/', game_cell['href'], re.UNICODE)
                    if not tag:
                        tag = [''];
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
        return games;


loader = WebLoader()

def get_games(web_page):
    return loader.get_games(web_page)
