#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import urllib, urllib2
import socket
import cookielib
import re

LOGIN_URL = 'http://goodgame.ru/ajax/login/'


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
    def __init__(self,cookie_dir):
        self.cookie_file = os.path.join(cookie_dir, '.cookies')
        self.cookie_jar = cookielib.LWPCookieJar(self.cookie_file)
        if not os.path.exists(self.cookie_file):
            self.cookie_jar.save()
        self.cookie_jar.revert()
        self.opener = Opener(handler=urllib2.HTTPCookieProcessor(self.cookie_jar))

    def load_page(self, url, data=None):
        self.cookie_jar.load()
        web_page = self.opener.get_page(url, data)

        search = re.findall('__DDOS_COOKIE=([a-z0-9]*);.*max-age=([0-9]+)', web_page)
        if search:
            ck = cookielib.Cookie(version=0, name='__DDOS_COOKIE', value=search[0][0], port=None, port_specified=False, domain='goodgame.ru', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=None, discard=True, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)
            self.add_ddos_cookie(ck)
            web_page = self.load_page(url, data)

        self.cookie_jar.save()
        return web_page

    def add_ddos_cookie(self, cookie):
        self.cookie_jar.set_cookie(cookie)

    def is_logged_in(self):
        for cookie in self.cookie_jar:
            if cookie.name == 'uid' and len(cookie.value) > 1:
                return True
        return False