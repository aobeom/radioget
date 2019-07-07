# coding=utf-8
# @author AoBeom
# @create date 2018-10-04 13:33:50
# @modify date 2019-07-07 22:31:56
# @desc [radio]
import argparse
import base64
import json
import multiprocessing
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from multiprocessing.dummy import Pool

import requests

try:
    import queue
except ImportError:
    import Queue as queue


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36",
}
session = requests.Session()
session.headers.update(HEADERS)


class threadProcBar(object):
    def __init__(self, func, tasks, pool=multiprocessing.cpu_count()):
        self.func = func
        self.tasks = tasks

        self.bar_i = 0
        self.bar_len = 50
        self.bar_max = len(tasks)

        self.p = Pool(pool)
        self.q = queue.Queue()

    def __dosth(self, percent, task):
        if percent == self.bar_max:
            return self.done
        else:
            self.func(task)
            return percent

    def worker(self):
        process_bar = '[' + '>' * 0 + '-' * 0 + ']' + '%.2f' % 0 + '%' + '\r'
        sys.stdout.write(process_bar)
        sys.stdout.flush()
        pool = self.p
        for i, task in enumerate(self.tasks):
            try:
                percent = pool.apply_async(self.__dosth, args=(i, task))
                self.q.put(percent)
            except BaseException:
                break

    def process(self):
        pool = self.p
        while 1:
            result = self.q.get().get()
            if result == self.bar_max:
                self.bar_i = self.bar_max
            else:
                self.bar_i += 1
            num_arrow = int(self.bar_i * self.bar_len / self.bar_max)
            num_line = self.bar_len - num_arrow
            percent = self.bar_i * 100.0 / self.bar_max
            process_bar = '[' + '>' * num_arrow + '-' * \
                num_line + ']' + '%.2f' % percent + '%' + '\r'
            sys.stdout.write(process_bar)
            sys.stdout.flush()
            if result == self.bar_max-1:
                pool.terminate()
                break
        pool.join()
        self.__close()

    def __close(self):
        print('')


class mediaWorker(object):
    @classmethod
    def aac2mp3(cls, raw, save_name, save_dir):
        name_raw = raw
        name_mp3 = "{}.mp3".format(save_name)
        orig_audio = os.path.join(save_dir, name_raw)
        mp3_audio = os.path.join(save_dir, name_mp3)
        command = "ffmpeg -y -i {} {}".format(orig_audio, mp3_audio)
        os.system(command)
        return mp3_audio

    @classmethod
    def mp3tomp4(cls, audio_dir, cover_dir, cover_pix):
        output_path = audio_dir.replace(".mp3", ".mp4")
        command = 'ffmpeg -r 15 -f image2 -loop 1 -i "{cover}" -i "{audio}" -s {cover_pix} -pix_fmt yuvj420p -t 300 -vcodec libx264 "{output}"'.format(
            cover=cover_dir, audio=audio_dir, cover_pix=cover_pix, output=output_path)
        os.system(command)


class hlsWorker(object):
    def __init__(self):
        self.tmpdir = tempfile.mkdtemp(prefix="radiko_")

    def __isWindows(self):
        return 'Windows' in platform.system()

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
        total = len(videolist)
        # 将cmd的命令切割
        cut = 50
        part = total // cut
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
        r = session.get(url)
        with open(filename, "wb") as code:
            for chunk in r.iter_content(chunk_size=1024):
                code.write(chunk)

    def downloadAAC(self, dl_info):
        name = dl_info["name"]
        save_dir = dl_info["save_dir"]
        urls = dl_info["urls"]
        print("Total [{}]".format(str(len(urls))))
        media_prefix = self.tmpdir
        tmp_path = [os.path.join(media_prefix, str(index).zfill(8) + ".aac") for index, _ in enumerate(urls)]
        t = threadProcBar(self.__download, list(zip(urls, tmp_path)), 4)
        t.worker()
        t.process()
        return self.__mergeAAC(tmp_path, name, save_dir)

    # 合并音频
    def __mergeAAC(self, tmp_path, outname, save_dir):
        stream = ""
        outname = "{}.raw.aac".format(outname)
        videoput = os.path.join(save_dir, outname)
        if self.__isWindows():
            if len(tmp_path) >= 50:
                self.__longcmd(tmp_path, self.tmpdir, videoput)
            else:
                for v in tmp_path:
                    stream += os.path.join(self.tmpdir, v) + "+"
                videoin = stream[:-1]
                self.__concat("windows", videoin, videoput)
        else:
            for v in tmp_path:
                stream += os.path.join(self.tmpdir, v) + " "
            videoin = stream[:-1]
            self.__concat("linux", videoin, videoput)
        return outname


class radiko(object):
    def __init__(self):
        self.workdir = os.path.dirname(os.path.abspath(__file__))

        self.auth1_api = "https://radiko.jp/v2/api/auth1"
        self.auth2_api = "https://radiko.jp/v2/api/auth2"
        self.playlist_api = "https://radiko.jp/v2/api/ts/playlist.m3u8"

        self.real_area = None

    def __area_check(self):
        timestamp = str(int((time.time() + 3600) * 1000))
        check_url = 'http://radiko.jp/area?_={}'.format(timestamp)
        res = session.get(check_url)
        rule = r'document.write\(\'<span class="(.*?)">(.*?)</span>\'\);'
        keywork = re.findall(rule, res.text)
        if keywork:
            keywork = keywork[0]
            area_id = keywork[0]
            real_area = keywork[1]
            if area_id == "OUT":
                print("IP OUT, Radiko thinks you live in {}".format(real_area))
                exit()
            else:
                self.real_area = real_area
        else:
            print("Network Error")
            exit()

    def __cfg_read(self, config):
        if os.path.exists(config):
            with open(config, "r") as f:
                cfg = json.loads(f.read())
            not_null_para = ["station_id", "start_at", "end_at"]
            for i in not_null_para:
                if cfg.get(i) == "":
                    print("{} has no value".format(i))
                    exit()
            return cfg
        else:
            print("No config.json")
            exit()

    def __checkFileExist(self, file_name, save_dir):
        if not os.path.exists(save_dir):
            os.mkdir(save_dir)
        file_name = file_name + ".raw.aac"
        if file_name in os.listdir(save_dir):
            print("{} Already Exist.".format(file_name))
            exit()

    def cli_mode(self, station, start_at, end_at, proxy):
        cli_info = {}

        name = "Radiko.{}.{}.{}".format(station, start_at, end_at)
        save_dir = self.workdir

        if proxy:
            proxyinfo = {"http": "http://" + proxy, "https": "https://" + proxy}
            session.proxies.update(proxyinfo)

        self.__area_check()
        self.__checkFileExist(name, save_dir)

        urls = self.__get_aac_urls(station, start_at, end_at)

        cli_info = {
            "name": name,
            "save_dir": save_dir,
            "encode": "",
            "urls": urls
        }

        return cli_info

    def crond_mode(self, config):
        crond_info = {}
        cfg = self.__cfg_read(config)
        name = cfg["name"]
        station_id = cfg["station_id"]
        start_at = cfg["start_at"]
        end_at = cfg["end_at"]
        next_day = cfg["next_day"]
        encode = cfg["encode"]
        save_dir = cfg["save_dir"]
        cover_path = cfg["cover_path"]
        cover_pix = cfg["cover_pix"]
        proxy = cfg["proxy"]

        start_at = time.strftime('%Y%m%d' + cfg["start_at"], time.localtime(time.time()))
        end_at = time.strftime('%Y%m%d' + cfg["end_at"], time.localtime(time.time()))

        # crond 模式适用于隔日下载，如需当天放送当天下载请使用 cli 模式
        # next_day = true 指放送时间实际在第二天，故保存时间-1，请求则按实际时间
        # next_day = false 指放送时间就在当天，故保存时间和请求时间均-1
        if next_day:
            timestamp = time.strftime('%Y%m%d', time.localtime(time.time() - 86400))
            start_at = time.strftime('%Y%m%d' + cfg["start_at"], time.localtime(time.time()))
            end_at = time.strftime('%Y%m%d' + cfg["end_at"], time.localtime(time.time()))
        else:
            timestamp = time.strftime('%Y%m%d', time.localtime(time.time() - 86400))
            start_at = timestamp + cfg["start_at"]
            end_at = timestamp + cfg["end_at"]

        if int(start_at) > int(end_at):
            print("Time Error")
            exit()

        if name == "":
            name = "Radiko.{}.{}.{}".format(station_id, start_at, end_at)
        else:
            name = "{}.{}".format(timestamp, name)

        if proxy:
            proxyinfo = {"http": "http://" + proxy, "https": "https://" + proxy}
            session.proxies.update(proxyinfo)

        self.__area_check()
        if save_dir == "":
            save_dir == self.workdir

        self.__checkFileExist(name, save_dir)

        urls = self.__get_aac_urls(station_id, start_at, end_at)

        crond_info = {
            "name": name,
            "save_dir": save_dir,
            "cover_path": cover_path,
            "cover_pix": cover_pix,
            "encode": encode,
            "urls": urls
        }

        return crond_info

    def __get_aac_urls(self, station, start_at, end_at):
        # auth1
        header_auth1 = {}
        header_auth1["x-radiko-device"] = "pc"
        header_auth1["x-radiko-user"] = "dummy_user"
        header_auth1["x-radiko-app"] = "pc_html5"
        header_auth1["x-radiko-app-version"] = "0.0.1"
        auth1_res = session.get(self.auth1_api, headers=header_auth1)
        authtoken = auth1_res.headers["X-Radiko-AuthToken"]
        offset = auth1_res.headers["X-Radiko-KeyOffset"]
        length = auth1_res.headers["X-Radiko-KeyLength"]

        # key
        # player_url = "http://radiko.jp/apps/js/playerCommon.js"
        # player_text = session.get(player_url).read()
        # key_rule = re.compile(r'new RadikoJSPlayer\(\$audio\[0\], \'pc_html5\', \'(.*?)\', {')
        # authkey = key_rule.findall(player_text, re.S | re.M)[0]
        authkey = "bcd151073c03b352e1ef2fd66c32209da9ca0afa"
        authkey = authkey.encode(encoding='utf-8')
        with tempfile.TemporaryFile() as temp:
            temp.write(authkey)
            temp.seek(int(offset))
            buff = temp.read(int(length))
            partialkey = base64.b64encode(buff)

        # auth2
        header_auth2 = {}
        header_auth2["x-radiko-device"] = "pc"
        header_auth2["x-radiko-user"] = "dummy_user"
        header_auth2["x-radiko-authtoken"] = authtoken
        header_auth2["x-radiko-partialkey"] = partialkey
        auth2_res = session.get(self.auth2_api, headers=header_auth2)
        ip_status = auth2_res.status_code
        area = auth2_res.text.split(",")[0]
        # playlist
        header_play = {}
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
        m3u8_list_res = session.get(self.playlist_api, params=play_params, headers=header_play)
        ip_status = m3u8_list_res.status_code

        if ip_status == 200:
            m3u8_content = m3u8_list_res.text
            chunk_rule = r'http[s]?://.*?m3u8'
            m3u8_main_url_list = re.findall(chunk_rule, m3u8_content, re.S | re.M)
            m3u8_main_url = m3u8_main_url_list[0]
            media_rule = r'(http[s]?://.*?aac)'
            m3u8_main_res = session.get(m3u8_main_url)
            m3u8_main_content = m3u8_main_res.text
            aac_urls = re.findall(media_rule, m3u8_main_content, re.S | re.M)
            return aac_urls
        else:
            yourip = session.get("http://whatismyip.akamai.com/").text
            print("Scheduled time: {} - {}".format(start_at, end_at))
            print("IP Forbidden, Your IP: {}, Radiko Area Code: {}, Area: {}".format(yourip, area, self.real_area))
            exit()


def opts():
    # radiko.jp/#!/ts/LFR/20181002005300"
    parser = argparse.ArgumentParser(description="Radiko Timefree download")
    subparsers = parser.add_subparsers(dest='cmd')

    # cli with console
    cli_parser = subparsers.add_parser('cli', help='Get the audio now')
    cli_parser.add_argument('--station', dest='station', action="store", help="Station Name", required=True)
    cli_parser.add_argument('--start_at', dest='start_at', action="store", help="Start Time 24-hour [20180829123000]", required=True)
    cli_parser.add_argument('--end_at', dest='end_at', action="store", help="End Time 24-hour [20180829130000]", required=True)
    cli_parser.add_argument('--mp3', dest='encode', action="store_true", default=False, help="AAC to MP3")
    cli_parser.add_argument('--proxy', dest='proxy', action="store", help="proxy address")

    # crond with config
    crond_parser = subparsers.add_parser('crond', help='Use config file')
    crond_parser.add_argument('--config', action='store', help='a config.json', required=True)

    return parser.parse_args()


def main():
    args = opts()
    cmd_type = args.cmd
    if cmd_type == "cli":
        station = args.station
        start_at = args.start_at
        end_at = args.end_at
        proxies = args.proxy
        encode = args.encode
        if int(start_at) > int(end_at):
            print("Time Error")
            exit()
        r = radiko()
        cli_info = r.cli_mode(station, start_at, end_at, proxies)
        hls = hlsWorker()
        raw = hls.downloadAAC(cli_info)
        if encode:
            name = cli_info["name"]
            save_dir = cli_info["save_dir"]
            mediaWorker.aac2mp3(raw, name, save_dir)
    elif cmd_type == "crond":
        r = radiko()
        config = args.config
        crond_info = r.crond_mode(config)
        encode = crond_info["encode"]
        hls = hlsWorker()
        raw = hls.downloadAAC(crond_info)
        if encode:
            name = crond_info["name"]
            save_dir = crond_info["save_dir"]
            cover_path = crond_info["cover_path"]
            cover_pix = crond_info["cover_pix"]
            mp3_path = mediaWorker.aac2mp3(raw, name, save_dir)
            if cover_path != "" and cover_pix != "":
                mediaWorker.mp3tomp4(mp3_path, cover_path, cover_pix)


if __name__ == "__main__":
    main()
