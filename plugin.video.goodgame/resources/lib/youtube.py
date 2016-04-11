# s-*- coding: utf-8 -*-
# ------------------------------------------------------------
# pelisalacarta - XBMC Plugin
# Conector para Youtube
# http://blog.tvalacarta.info/plugin-xbmc/pelisalacarta/
# ------------------------------------------------------------
import urllib, re
import cgi

try:
    import simplejson as json
except ImportError:
    import json


def get_video_url(page_url, loader):
    data = loader.load_page(page_url)
    video_urls, img = scrapeWebPageForVideoLinks(data)
    video_urls.reverse()

    title = re.search('<meta property="og:title" content="(.*)">', data)
    return {
        'title': title.group(1),
        'urls': video_urls,
        'img': img
    }


def removeAdditionalEndingDelimiter(data):
    pos = data.find("};")
    if pos != -1:
        data = data[:pos + 1]
    return data


def normalizeUrl(self, url):
    if url[0:2] == "//":
        url = "http:" + url
    return url


def extractFlashVars(data):
    assets = 0
    flashvars = {}
    found = False

    for line in data.split("\n"):
        if line.strip().find(";ytplayer.config = ") > 0:
            found = True
            p1 = line.find(";ytplayer.config = ") + len(";ytplayer.config = ") - 1
            p2 = line.rfind(";")
            if p1 <= 0 or p2 <= 0:
                continue
            data = line[p1 + 1:p2]
            break
    data = removeAdditionalEndingDelimiter(data)

    if found:
        data = json.loads(data)
        if assets:
            flashvars = data["assets"]
        else:
            flashvars = data["args"]

    for k in ["html", "css", "js"]:
        if k in flashvars:
            flashvars[k] = normalizeUrl(flashvars[k])

    return flashvars


def scrapeWebPageForVideoLinks(data):
    fmt_value = {
        5: "240p h263 flv",
        18: "360p h264 mp4",
        22: "720p h264 mp4",
        26: "???",
        33: "???",
        34: "360p h264 flv",
        35: "480p h264 flv",
        37: "1080p h264 mp4",
        36: "3gpp",
        38: "720p vp8 webm",
        43: "360p h264 flv",
        44: "480p vp8 webm",
        45: "720p vp8 webm",
        46: "520p vp8 webm",
        59: "480 for rtmpe",
        78: "400 for rtmpe",
        82: "360p h264 stereo",
        83: "240p h264 stereo",
        84: "720p h264 stereo",
        85: "520p h264 stereo",
        100: "360p vp8 webm stereo",
        101: "480p vp8 webm stereo",
        102: "720p vp8 webm stereo",
        120: "hd720",
        121: "hd1080"
    }

    video_urls = []

    flashvars = extractFlashVars(data)
    if not flashvars.has_key(u"url_encoded_fmt_stream_map"):
        return video_urls

    for url_desc in flashvars[u"url_encoded_fmt_stream_map"].split(u","):
        url_desc_map = cgi.parse_qs(url_desc)
        if not (url_desc_map.has_key(u"url") or url_desc_map.has_key(u"stream")):
            continue

        try:
            key = int(url_desc_map[u"itag"][0])
            url = u""
            if url_desc_map.has_key(u"url"):
                url = urllib.unquote(url_desc_map[u"url"][0])
            elif url_desc_map.has_key(u"conn") and url_desc_map.has_key(u"stream"):
                url = urllib.unquote(url_desc_map[u"conn"][0])
                if url.rfind("/") < len(url) - 1:
                    url = url + "/"
                url = url + urllib.unquote(url_desc_map[u"stream"][0])
            elif url_desc_map.has_key(u"stream") and not url_desc_map.has_key(u"conn"):
                url = urllib.unquote(url_desc_map[u"stream"][0])

            if url_desc_map.has_key(u"sig"):
                url = url + u"&signature=" + url_desc_map[u"sig"][0]

            # links[key] = url
            video_urls.append({'quality': "(" + fmt_value[key] + ")", 'url': url})
        except:
            continue
    img = flashvars[u'iurl']
    return video_urls, img


def find_videos(data):
    encontrados = set()
    devuelve = []

    patronvideos = 'youtube.py(?:-nocookie)?\.com/(?:(?:(?:v/|embed/))|(?:(?:watch(?:_popup)?(?:\.php)?)?(?:\?|#!?)(?:.+&)?v=))?([0-9A-Za-z_-]{11})'  # '"http://www.youtube.com/v/([^"]+)"'
    matches = re.compile(patronvideos, re.DOTALL).findall(data)

    for match in matches:
        titulo = "[YouTube]"
        url = "http://www.youtube.py.com/watch?v=" + match

        if url != '':
            if url not in encontrados:
                devuelve.append([titulo, url, 'youtube.py'])
                encontrados.add(url)

    patronvideos = 'www.youtube.py.*?v(?:=|%3D)([0-9A-Za-z_-]{11})'
    matches = re.compile(patronvideos, re.DOTALL).findall(data)

    for match in matches:
        titulo = "[YouTube]"
        url = "http://www.youtube.py.com/watch?v=" + match

        if url not in encontrados:
            devuelve.append([titulo, url, 'youtube.py'])
            encontrados.add(url)

    # http://www.youtube.com/v/AcbsMOMg2fQ
    patronvideos = 'youtube.py.com/v/([0-9A-Za-z_-]{11})'
    matches = re.compile(patronvideos, re.DOTALL).findall(data)

    for match in matches:
        titulo = "[YouTube]"
        url = "http://www.youtube.py.com/watch?v=" + match

        if url not in encontrados:
            devuelve.append([titulo, url, 'youtube.py'])
            encontrados.add(url)

    return devuelve


def test():
    video_urls = get_video_url("http://www.youtube.py.com/watch?v=Kk-435429-M")
    return len(video_urls) > 0
