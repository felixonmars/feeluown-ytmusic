import re
from enum import Enum
from os import environ as env
from pathlib import Path
import subprocess
from typing import Union, Optional

import ytmusicapi


class YtItemType(Enum):
    songs = 'songs'
    videos = 'videos'
    albums = 'albums'
    artists = 'artists'
    playlists = 'playlists'


class Singleton(type):
    """ singleton metaclass """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class YtMusicService(metaclass=Singleton):
    """ Youtube music service """
    AUTH_FILE = Path.home() / '.FeelUOwn' / 'data' / 'ytmusic_header.json'

    def __init__(self):
        self.ytmusic: Optional[ytmusicapi.YTMusic] = None
        self.is_authed = False

    def init(self):
        if not self.is_authed and self.AUTH_FILE.exists():
            self.ytmusic = ytmusicapi.YTMusic(self.AUTH_FILE.as_posix())
            self.is_authed = True
        elif self.ytmusic is None:
            if self.AUTH_FILE.exists():
                self.ytmusic = ytmusicapi.YTMusic(self.AUTH_FILE.as_posix())
                self.is_authed = True
            else:
                self.ytmusic = ytmusicapi.YTMusic()
                self.is_authed = False

    def search(self, keyword: str, sfilter=YtItemType.songs):
        self.init()
        return self.ytmusic.search(keyword, sfilter.value)

    def detail(self, id_: str):
        self.init()
        return self.ytmusic.get_song(id_)

    def playlists(self):
        self.init()
        return self.ytmusic.get_library_playlists()

    def get_playlist(self, playlist_id, limit=200):
        self.init()
        return self.ytmusic.get_playlist(playlist_id, limit=limit)

    def artist_detail(self, id_: str):
        self.init()
        return self.ytmusic.get_artist(id_)


class YtMusicExtractor(metaclass=Singleton):
    MUSIC_DOMAIN = 'music.youtube.com'

    def __init__(self):
        ytdl = env.get('FUO_YTDL_PATH', 'youtube-dl')
        self.command = self.run_command('which', ytdl)
        self.audio_cache = dict()
        self.video_cache = dict()
        self.command_cache = dict()

    def run(self, *args, raw=False) -> Union[bytes, str]:
        cache_id = " ".join(args) + str(raw)
        if cache_id not in self.command_cache.keys():
            self.command_cache[cache_id] = self.run_command(self.command, *args, raw=raw)
        return self.command_cache[cache_id]

    @staticmethod
    def run_command(*args, raw=False) -> Union[bytes, str]:
        print(f'[Shell] Running: {" ".join(args)}')
        b = subprocess.check_output(args).strip()
        return b if raw else b.decode()

    def get_formats(self, vid: str):
        from fuo_ytmusic.schemas import YtdlFormat
        formats = []
        out: str = self.run('-F', f'https://{self.MUSIC_DOMAIN}/watch?v={vid}')
        for line in out.split('\n'):
            if re.match(r'\d+', line):
                formats.append(YtdlFormat.parse_line(line))
        return formats

    def get_url(self, vid: str):
        if vid not in self.audio_cache.keys():
            from fuo_ytmusic.schemas import YtdlExtract
            out: bytes = self.run('--print-json', '-s', '-f',
                                  f'{env.get("FUO_YTDL_VIDEO", "mp4/bestvideo")},'
                                  f'{env.get("FUO_YTDL_AUDIO", "bestaudio")}',
                                  f'https://{self.MUSIC_DOMAIN}/watch?v={vid}', raw=True)
            self.audio_cache[vid] = YtdlExtract.parse_raw(out.split(b'\n')[1]).url
        return self.audio_cache[vid]

    def get_mv(self, vid: str):
        if vid not in self.video_cache.keys():
            from fuo_ytmusic.schemas import YtdlExtract
            out: bytes = self.run('--print-json', '-s', '-f',
                                  f'{env.get("FUO_YTDL_VIDEO", "mp4/bestvideo")},'
                                  f'{env.get("FUO_YTDL_AUDIO", "bestaudio")}',
                                  f'https://{self.MUSIC_DOMAIN}/watch?v={vid}', raw=True)
            self.video_cache[vid] = YtdlExtract.parse_raw(out.split(b'\n')[0]).url
        return self.video_cache[vid]


if __name__ == '__main__':
    import json
    print(json.dumps(YtMusicService().get_playlist('VLPLFd1GuLx-VLz-jTU1GcvVJFz4mV1tWEaP')))
