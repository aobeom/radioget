# radioget

可以根据配置文件或命令行参数下载radiko [timeshift](http://radiko.jp/#!/timeshift)的音频，IP限制请自行解决，只提供proxy参数使用。

## 使用说明

URL: radiko.jp/#!/ts/station_id/start_at  

#### 1. 计划任务型（隔日，即第二天下载前一天的内容）

```python
{
    "name": "",
    "station_id": "",
    "start_at": "",
    "end_at": "",
    "next_day": false,
    "encode": true,
    "save_dir": "",
    "cover_path": "",
    "cover_pix": "",
    "proxy": ""
}

字段说明：

name: 下载文件的名字，选填  
station_id: 见URL，必填，如 LFR  
start_at: 广播开始时间，必填，如 005300  
end_at: 广播结束时间，必填，如 005800  
encode: 是否转码，需要ffmpeg的环境变量, true / false  
next_day: 放送时间是否超过 24 时 true / false  
save_dir: 文件保存路径，默认当前目录，选填  
cover_path: 封面图片路径，选填，若设置将生成一图流视频
cover_pix: 封面分辨率，选填，同上
proxy: 设置代理地址，选填

python radioget.py crond --config config.json
```

#### 2. 单独下载

命令行参数：
```shell
  --station STATION    Station Name
  --start_at START_AT  Start Time 24-hour [20180829123000]
  --end_at END_AT      End Time 24-hour [20180829130000]
  --mp3                AAC to MP3
  --proxy PROXY        proxy address


start_at / end_at 必须是带日期的完整时间，见 URL

python radioget.py cli --station LFR --start_at 20181002005300 --end_at 20181002005800 
```

## 其他说明

+ crond 模式和 cli 模式默认情况只下载原始音频文件，除非设置 encode 为 true 或使用 --mp3 参数，其中 cli 模式不提供一图流视频转换

+ start_at 和 end_at 共同决定音频长度，可截取指定范围

+ 无法下载可能是IP限制或 start_at 和 end_at 区间错误

+ area_id.json 是官方[地区](http://radiko.jp/v3/station/region/full.xml)列表的精简版，如果你的代理IP提示禁止访问，可以查询是否被识别成其他地区。

## 辅助程序
[FFmpeg](http://www.ffmpeg.org/download.html)

## 参考
[rec_radiko_live](https://github.com/uru2/rec_radiko_live)