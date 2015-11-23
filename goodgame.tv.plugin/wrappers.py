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
import os
import urlparse

try:
    import xbmc
    import xbmcaddon
    import xbmcgui
    import xbmcplugin

    addon_handle = int(sys.argv[1])
    xbmcplugin.setContent(addon_handle, 'movies')
    is_xbmc = True
except ImportError:
    is_xbmc = False


class GenericWrapper(object):
    _is_kodi = False

    def is_kodi(self):
        return self._is_kodi


class FakeWrapper(GenericWrapper):
    _is_kodi = False

    def add(self, *args, **kwargs):
        print('Item added: %s' % kwargs['title'])

    def commit(self, *args, **kwargs):
        pass

    def image(self, *args, **kwargs):
        pass


class KodiWrapper(GenericWrapper):
    _is_kodi = True

    def add(self, title, url, is_folder=True, image='DefaultFolder.png'):
        li = xbmcgui.ListItem(title, iconImage=image, thumbnailImage=image)
        self._add_to_dir(li, url, is_folder)

    # {
    #     'title': '[%sp] %s - %s' % (quality, author, title),
    #     'title2': title,
    #     'quality': quality,
    #     'author': author,
    #     'url': url,
    #     'viewers': viewers,
    #     'image': image
    # }
    def add_stream(self, stream):
        li = xbmcgui.ListItem(stream['title'])
        info = {
            'title': stream['title2'],
            'artist': list([stream['author']]),
            'plot': 'Plot'
        }
        li.setInfo(type=u'video', infoLabels=info)
        li.setLabel2(stream['author'])
        li.setArt({'poster': stream['image'], 'banner': stream['image'], 'icon': 'DefaultFolder.png',
                   'thumb': 'DefaultFolder.png'})
        self._add_to_dir(li, stream['url'], False)

    def _add_to_dir(self, li, url, is_folder):
        xbmcplugin.addDirectoryItem(
            handle=addon_handle,
            url=url,
            listitem=li,
            isFolder=is_folder)

    def view_mode(self, mode=500):
        xbmc.executebuiltin("Container.SetViewMode(%d)" % mode)

    def content_mode(self, mode='tvshows'):
        xbmcplugin.setContent(addon_handle, mode)

    def commit(self):
        xbmcplugin.endOfDirectory(addon_handle)

    def image(self, image_name):
        if image_name.startswith('http:'):
            return image_name

        plugin_id = 'goodgame.tv.plugin'
        addon = xbmcaddon.Addon(id=plugin_id)
        addon_path = (addon.getAddonInfo('path').decode('utf-8'))
        return xbmc.translatePath(
            os.path.join(addon_path, 'resources', 'media', image_name))


def get_kodi():
    if is_xbmc:
        return KodiWrapper()
    else:
        return FakeWrapper()


def get_game_tag(kodi):
    if kodi.is_kodi() is False:
        return 'starcraft-ii-heart-of-the-swarm'

    args = urlparse.parse_qs(sys.argv[2][1:])
    if 'tag' in args:
        return args['tag'][0]

    return False
