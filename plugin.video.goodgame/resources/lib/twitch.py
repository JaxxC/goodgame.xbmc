#! /usr/bin/python
# -*- coding: utf-8 -*-

import requests
import json
import random
import m3u8

USHER_API_LIVE = 'http://usher.twitch.tv/api/channel/hls/{channel}.m3u8?player=twitchweb' +\
    '&token={token}&sig={sig}&$allow_audio_only=true&allow_source=true' + \
    '&type=any&p={random}'
LIVE_TOKEN_API = 'http://api.twitch.tv/api/channels/{channel}/access_token'
USHER_API_VOD = 'http://usher.twitch.tv/vod/{vod_id}?nauthsig={sig}&nauth={token}&allow_source=true'
VOD_TOKEN_API = 'http://api.twitch.tv/api/vods/{vod}/access_token'

class TwitchParser():
    def __init__(self, channel, available_qualities):
        self.channel = channel
        self.qualities = available_qualities
        self.urls = []
        m3u8 = self.get_live_stream(channel)
        self.set_video_urls(m3u8)

    def get_token_and_signature(self, channel):
        url = LIVE_TOKEN_API.format(channel=channel)
        r = requests.get(url)
        txt = r.text
        data = json.loads(txt)
        sig = data['sig']
        token = data['token']
        return token, sig

    def get_live_stream(self, channel):
        token, sig = self.get_token_and_signature(channel)
        r = random.randint(0,1E7)
        data = json.loads(token)
        url = USHER_API_LIVE.format(channel=data['channel'], sig=sig, token=token, random=r)
        r = requests.get(url)
        m3u8_obj = m3u8.loads(r.text)
        return m3u8_obj

    def set_video_urls(self, m3u8_obj):
        # premium =  len(m3u8_obj.playlists) > 1
        for p in m3u8_obj.playlists:
            si = p.stream_info
            bandwidth = si.bandwidth/(1024)
            quality = p.media[0].name
            resolution = si.resolution if si.resolution else (1920,1080)
            uri = p.uri
            if resolution[1] in self.qualities or quality == u'Source':
                self.urls.append({'url': uri, 'quality': quality, 'bandwidth': bandwidth, 'resolution': resolution[1]})

    def get_quality(self, quality):
        return self.urls[quality]

    def get_qualities(self):
        return self.urls


class TwitchVodParser():

    def get_token_and_signature(self, vod):
        url = VOD_TOKEN_API.format(vod=vod)
        r = requests.get(url)
        data = json.loads(r.text)
        return data['token'], data['sig']

    def get_vod(self, vod_id):
        urls = []
        token, sig = self.get_token_and_signature(vod_id)
        quality_playlist_url = USHER_API_VOD.format(vod_id=vod_id, sig=sig, token=token)
        variant_playlist = m3u8.load(quality_playlist_url)
        for p in variant_playlist.playlists:
            quality = p.media[0].name
            uri = p.uri
            urls.append({'url': uri, 'quality': quality})
        return urls