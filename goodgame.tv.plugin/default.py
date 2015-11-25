#!/usr/bin/env python
# Copyright (c) 2015 Niko Yakovlev <vegasq@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import re
import os
import requests
import httplib
import urllib

from wrappers import get_kodi
from wrappers import get_game_tag

from xbmcswift2 import Plugin
# Create xbmcswift2 plugin instance.
plugin = Plugin()
addon_path = plugin.addon.getAddonInfo('path').decode('utf-8')

# Import custom modules.
sys.path.append(os.path.join(addon_path, 'resources', 'lib'))
import gg_parser

class GGKodi(object):
    DEBUG = False

    idselector = '.*player\?(\w*)\\"'

    def __init__(self, kodi):
        self._kodi = kodi
        gg_parser.set_addon(plugin.addon)

    def set_game(self, game):
        self.game = game

    def _build_url(self, query):
        return sys.argv[0] + '?' + urllib.urlencode(query)

    def _is_stream_avaliable(self, url):
        c = httplib.HTTPConnection('hls.goodgame.ru')
        c.request("HEAD", url)
        if c.getresponse().status == 200:
            return True
        return False

    def create_main_menu(self):
        avaliable_games = gg_parser.get_games()
        for game_info in avaliable_games:
            self._kodi.add(
                title=game_info['title'],
                url=self._build_url(game_info),
                image=self._kodi.image(game_info['cover'])
            )
        self._kodi.view_mode(500)
        self._kodi.commit()

    def create_streams_menu(self):
        if self.game == 'gg' or self.game == 'favorites':
            streams = gg_parser.get_streams_from_page(self.game)
        else:
            streams = gg_parser.get_streams_from_api(self.game)

        for stream in streams:
            self._kodi.add_stream(stream)

        self._kodi.view_mode(560)
        self._kodi.commit()



if __name__ == '__main__':
    kodi_wrapper = get_kodi()
    game_tag = get_game_tag(kodi_wrapper)
    ggk = GGKodi(kodi_wrapper)

    if game_tag is False:
        ggk.create_main_menu()
    else:
        ggk.set_game(game_tag)
        ggk.create_streams_menu()
