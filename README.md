# radioget

可以根据配置文件或命令行参数下载radiko [timeshift](http://radiko.jp/#!/timeshift)的音频，IP限制请自行解决，只提供proxy参数使用。

## 使用说明

URL: radiko.jp/#!/ts/station_id/start_at

#### 1. 计划任务型（隔日，即第二天下载前一天的内容）

```shell
{
    "name": "",
    "station_id": "",
    "start_at": "",
    "end_at": "",
    "encode": false,
    "save_dir": "",
    "proxy": ""
}

name: 下载文件的名字，选填  
station_id: 见URL，必填，如 LFR  
start_at: 广播开始时间，必填，如 005300  
end_at: 广播结束时间，必填，如 005800  
encode: 是否转码，需要ffmpeg的环境变量, true / false  
save_dir: 文件保存路径，默认当前目录，选填  
proxy: 设置代理地址，选填
```

#### 2. 单个下载型

命令行参数：
```shell
  -h, --help           show this help message and exit
  --station STATION    Station Name
  --start_at START_AT  Start Time 24-hour [20180829123000]
  --end_at END_AT      End Time 24-hour [20180829130000]
  --mp3                AAC to MP3
  --proxy PROXY        proxy address
  -s                   Specific radio

--start_at / --end_at 必须是带日期的完整时间，见 URL
-s 必须

如: python radioget.py -s --station LFR --start_at 20181002005300 --end_at 20181002005800 
```

## 其他说明

area_id.json 是官方[地区](http://radiko.jp/v3/station/region/full.xml)列表的精简版，如果你的代理IP提示禁止访问，可以查询是否被识别成其他地区。

## 辅助程序
[FFmpeg](http://www.ffmpeg.org/download.html)

## 参考
[rec_radiko_live](https://github.com/uru2/rec_radiko_live)