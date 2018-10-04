# coding=utf-8
# @author AoBeom
# @create date 2018-10-04 13:33:50
# @modify date 2018-10-04 22:20:04
# @desc [description]
import argparse
import base64
import json
import os
import platform
import re
import subprocess
import tempfile
import time

import requests

from packages.threadpb import threadProcBar


class radiko(object):
    def __init__(self, crond=True, proxies=None):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
        }
        self.workdir = os.path.dirname(os.path.abspath(__file__))

        self.auth1_api = "https://radiko.jp/v2/api/auth1"
        self.auth2_api = "https://radiko.jp/v2/api/auth2"
        self.playlist_api = "https://radiko.jp/v2/api/ts/playlist.m3u8"

        self.tmpdir = tempfile.mkdtemp()

        self.requests = requests.Session()

        if crond:
            self.cfg = self.__checkCfg()
            proxycfg = self.cfg["proxy"]
            if proxycfg:
                proxyinfo = {"http": "http://" + proxycfg, "https": "https://" + proxycfg}
                self.requests.proxies = proxyinfo
            if self.cfg["save_dir"] == "":
                self.save_dir = self.workdir
            else:
                self.save_dir = self.cfg["save_dir"]
            if self.cfg["name"] == "":
                self.save_name = "Radiko"
            else:
                self.save_name = self.cfg["name"]
            if self.cfg["encode"]:
                self.isEncode = True
                self.__checkEncode()
            else:
                self.isEncode = False
        else:
            if proxies:
                proxyinfo = {"http": "http://" + proxies, "https": "https://" + proxies}
                self.requests.proxies = proxyinfo
            self.save_dir = self.workdir
            self.save_name = "Radiko"
            self.isEncode = False

        self.audio_path = ""
        self.timestamp = ""

    def __isWindows(self):
        return 'Windows' in platform.system()

    def __checkFileExist(self):
        if not os.path.exists(self.save_dir):
            os.mkdir(self.save_dir)
        check_name = "{d}.raw.aac".format(d=self.timestamp)
        save_list = os.listdir(self.save_dir)
        if check_name in save_list:
            print("{} Already Exist.".format(check_name))
            exit()

    def __checkCfg(self):
        config = os.path.join(self.workdir, "config.json")
        if os.path.exists(config):
            with open(config, "r") as config:
                cfg = json.loads(config.read())
                for key, value in cfg.items():
                    if key not in ["save_dir", "name", "proxy"]:
                        if value == "":
                            print("{} has no value".format(key))
                            exit()
            return cfg
        else:
            print("No config.json")
            exit()

    def __checkEncode(self):
        prog_ffmpeg = subprocess.Popen("ffmpeg -version", stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        result = prog_ffmpeg.stderr.read()
        if result:
            print("FFMPEG NOT FOUND.")
            exit()

    def __concat(self, ostype, inputv, outputv):
        if ostype == "windows":
            os.system("copy /B " + inputv + " " + outputv + " >nul 2>nul")
        elif ostype == "linux":
            os.system("cat " + inputv + " >" + outputv)

    # windows特殊处理
    def __longcmd(self, videolist, videofolder, videoput):
        videolist = videolist
        totle = len(videolist)
        # 将cmd的命令切割
        cut = 50
        part = totle / cut
        parts = []
        temp = []
        for v in videolist:
            temp.append(v)
            if len(temp) == cut:
                parts.append(temp)
                temp = []
            if len(parts) == part:
                parts.append(temp)
        outputs = []
        for index, p in enumerate(parts):
            stream = ""
            outputname = "out_" + str(index + 1) + ".aac"
            outputpath = os.path.join(videofolder, outputname)
            outputs.append(outputpath)
            for i in p:
                stream += os.path.join(self.tmpdir, i) + "+"
            videoin = stream[:-1]
            self.__concat("windows", videoin, outputpath)
        flag = ""
        for output in outputs:
            flag += output + "+"
        videoin_last = flag[:-1]
        self.__concat("windows", videoin_last, videoput)

    def __download(self, para):
        url = para[0]
        filename = para[1]
        r = self.requests.get(url, headers=self.headers)
        with open(filename, "wb") as code:
            for chunk in r.iter_content(chunk_size=1024):
                code.write(chunk)

    def getAACURLs(self, station=None, start_at=None, end_at=None):
        if start_at is None and end_at is None and station is None:
            start_at = time.strftime('%Y%m%d' + self.cfg["start_at"], time.localtime(time.time()))
            end_at = time.strftime('%Y%m%d' + self.cfg["end_at"], time.localtime(time.time()))
            station = self.cfg["station_id"]
            self.timestamp = time.strftime('%Y%m%d', time.localtime(time.time() - 86400))
        else:
            time_tag = "{}.{}.{}".format(station, start_at, end_at)
            self.timestamp = time_tag
        self.__checkFileExist()
        # auth1
        header_auth1 = self.headers.copy()
        header_auth1["x-radiko-device"] = "pc"
        header_auth1["x-radiko-user"] = "dummy_user"
        header_auth1["x-radiko-app"] = "pc_html5"
        header_auth1["x-radiko-app-version"] = "0.0.1"
        auth1_res = self.requests.get(self.auth1_api, headers=header_auth1)
        authtoken = auth1_res.headers["X-Radiko-AuthToken"]
        offset = auth1_res.headers["X-Radiko-KeyOffset"]
        length = auth1_res.headers["X-Radiko-KeyLength"]

        # key
        # player_url = "http://radiko.jp/apps/js/playerCommon.js"
        # player_text = self.requests.get(player_url, headers=self.headers).read()
        # key_rule = re.compile(r'new RadikoJSPlayer\(\$audio\[0\], \'pc_html5\', \'(.*?)\', {')
        # authkey = key_rule.findall(player_text, re.S | re.M)[0]
        authkey = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"
        with tempfile.TemporaryFile() as temp:
            temp.write(authkey)
            temp.seek(int(offset))
            buff = temp.read(int(length))
            partialkey = base64.b64encode(buff)

        # auth2
        header_auth2 = self.headers.copy()
        header_auth2["x-radiko-device"] = "pc"
        header_auth2["x-radiko-user"] = "dummy_user"
        header_auth2["x-radiko-authtoken"] = authtoken
        header_auth2["x-radiko-partialkey"] = partialkey
        auth2_res = self.requests.get(self.auth2_api, headers=header_auth2)
        ip_status = auth2_res.status_code
        area = auth2_res.text.split(",")[0]
        # playlist
        header_play = self.headers.copy()
        header_play["X-Radiko-AreaId"] = area
        header_play["X-Radiko-AuthToken"] = authtoken

        play_params = {
            "station_id": station,
            "start_at": start_at,
            "ft": start_at,
            "end_at": end_at,
            "to": end_at,
            "l": "15",
            "type": "b"
        }
        m3u8_list_res = self.requests.get(self.playlist_api, params=play_params, headers=header_play)
        ip_status = m3u8_list_res.status_code
        if ip_status == 200:
            m3u8_content = m3u8_list_res.text
            chunk_rule = r'http[s]?://.*?m3u8'
            m3u8_main_url_list = re.findall(chunk_rule, m3u8_content, re.S | re.M)
            m3u8_main_url = m3u8_main_url_list[0]
            media_rule = r'(http[s]?://.*?aac)'
            m3u8_main_res = self.requests.get(m3u8_main_url, headers=self.headers)
            m3u8_main_content = m3u8_main_res.text
            aac_urls = re.findall(media_rule, m3u8_main_content, re.S | re.M)
            return aac_urls
        else:
            yourip = self.requests.get("http://whatismyip.akamai.com/").text
            print("IP Forbidden, Your IP: {}, Radiko Area Code: {}".format(yourip, area))
            exit()

    def downloadAAC(self, urls, thread):
        total = len(urls)
        print("Total [{}]".format(str(total)))
        media_prefix = self.tmpdir
        media_path = [os.path.join(media_prefix, str(index).zfill(8) + ".aac") for index, _ in enumerate(urls)]
        t = threadProcBar(self.__download, list(zip(urls, media_path)), thread)
        t.worker()
        t.process()
        self.__mergeAAC(media_path)

    # 合并音频
    def __mergeAAC(self, media_path):
        stream = ""
        outname = "{d}.raw.aac".format(d=self.timestamp)
        videoput = os.path.join(self.save_dir, outname)
        if self.__isWindows():
            if len(media_path) > 50:
                self.__longcmd(media_path, self.tmpdir, videoput)
            else:
                for v in media_path:
                    stream += os.path.join(self.tmpdir, v) + "+"
                videoin = stream[:-1]
                self.__concat("windows", videoin, videoput)
        else:
            for v in media_path:
                stream += os.path.join(self.tmpdir, v) + " "
            videoin = stream[:-1]
            self.__concat("linux", videoin, videoput)

    def aac2mp3(self, name=None):
        name_raw = "{d}.raw.aac".format(d=self.timestamp)
        name_mp3 = "{d}.{name}.mp3".format(
            d=self.timestamp, name=self.save_name)
        orig_audio = os.path.join(self.save_dir, name_raw)
        mp3_audio = os.path.join(self.save_dir, name_mp3)
        self.audio_path = mp3_audio
        command = "ffmpeg -y -i {} {}".format(orig_audio, mp3_audio)
        os.system(command)

    def mp3tomp4(self, name=None):
        cover = os.path.join(self.save_dir, "cover.png")
        cover_pix = "480x300"
        outname = "{d}.{name}.mp4".format(
            d=self.timestamp, name=self.save_name)
        save_path = os.path.join(self.save_dir, outname)
        command = 'ffmpeg -r 15 -f image2 -loop 1 -i "{cover}" -i "{audio}" -s {cover_pix} -pix_fmt yuvj420p -t 300 -vcodec libx264 "{output}"'.format(
            cover=cover, audio=self.audio_path, cover_pix=cover_pix, output=save_path)
        os.system(command)


def opts():
    # radiko.jp/#!/ts/LFR/20181002005300"
    paras = argparse.ArgumentParser(description="Radiko Timefree download")
    paras.add_argument('--station', dest='station', action="store", help="Station Name")
    paras.add_argument('--start_at', dest='start_at', action="store", help="Start Time 24-hour [20180829123000]")
    paras.add_argument('--end_at', dest='end_at', action="store", help="End Time 24-hour [20180829130000]")
    paras.add_argument('--mp3', dest='tomp3', action="store_true", default=False, help="AAC to MP3")
    paras.add_argument('--proxy', dest='proxy', action="store", help="proxy address")
    paras.add_argument('-s', dest='specific', action="store_true", default=False, help="Specific radio")
    args = paras.parse_args()
    return args


def main():
    args = opts()
    station = args.station
    start_at = args.start_at
    end_at = args.end_at
    specific = args.specific
    proxies = args.proxy
    tomp3 = args.tomp3

    r = radiko(crond=not specific, proxies=proxies)
    if specific:
        if station is None or start_at is None or end_at is None:
            print("No station / start_at / end_at")
            exit()
        else:
            urls = r.getAACURLs(station, start_at, end_at)
    else:
        urls = r.getAACURLs()

    r.downloadAAC(urls, 4)
    if r.isEncode or tomp3:
        r.aac2mp3()
        # r.mp3tomp4()


if __name__ == "__main__":
    main()
