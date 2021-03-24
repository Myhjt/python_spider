
'''
TODO:目录和文件名需要改进
TODO:增加一个清晰度选则的功能
'''

import re,requests
from fake_useragent import  UserAgent
import os,time
import threading
import json
table = str.maketrans({
    "|":'#',
    '\\':'#',
    '\'':'#',
    '?':'#',
    '*':'#',
    '<':'#',
    '\"':'#',
    '>':'#',
    '+':'#',
    '[':'#',
    ']':'#',
    '/':'#'
})
title_list = [] # 标题列表
thread_list = [] # 线程列表
pNum = [] # 集数列表
MEDIA_TYPE = ['mp3','mp4','flv']
thread_nums = 10
hostPath = os.path.join(os.path.expanduser('~'),'Desktop','b站视频')
hostUrl = "https://www.bilibili.com/"
bangumi_referer = "https://www.bilibili.com/bangumi/play/"
video_referer = "https://www.bilibili.com/video/"
ffmpeg_path = "./ffmpeg/bin/ffmpeg"
# 会话对象
session = requests.Session()
# 用于请求视频json数据的headers
json_headers = {
    "host": "api.bilibili.com",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36 Edg/89.0.774.54",
    "Origin": "https://www.bilibili.com",
    "Referer": bangumi_referer,
    # "cookie": ""  会员视频要设置cookie
    }

# 用于请求一般网页的headers
html_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36 Edg/89.0.774.54",
    "Origin":"https://www.bilibili.com",
    "Referer":"https://www.bilibili.com/"
}

# 返回页面文本
def getPageInfo(html_url):
    """
    :param html_url:目标url
    :return:字符串，返回该url的文本形式
    """
    response = session.get(html_url, headers=html_headers,verify=False)
    html = response.text
    return html

# 从text从获取参数信息
def getParams(text):
    """
    :param text:html文本
    :return:返回一个params列表
    """
    paramsList = []
    global title_list
    params = {
        "bvid":"",
        "qn": "80",
        "type":"",
        "otype": "json",
        "fnver": "0",
        "fnval": "16",
        "session": ""
    }
    if avId[:2] != "av":
        rawData = re.findall(r'"epList":\[(.*?)\].*?',text)
        ep_ids = re.findall(r'"id":(.*?),.*?',rawData[0])
        aids = re.findall(r'"aid":(.*?),.*?',rawData[0])
        #标题
        titleNum = re.findall(r'"titleFormat":(.*?),.*?',rawData[0])
        title_list = re.findall(r'"longTitle":(.*?),.*?', rawData[0])
        for i in range(len(title_list)):
            print(str(i) +'---' + titleNum[i].strip() +' ' + title_list[i].strip())
        print("总共有{}集".format(len(ep_ids)-1))
        global pNum
        pNum = input("请输入你要下载的集数代号，以空格分开").strip().split()
        for i in pNum:
            params['ep_id'] = ep_ids[int(i)]
            params['aid'] = aids[int(i)]
            paramsList.append(params)
    else:
        rawData = re.findall(r'"pages":\[(.*?)\].*?',text)
        print(rawData[0])
        cids = re.findall(r'"cid":(.*?),.*?', rawData[0])
        title_list = re.findall(r'"part":(.*?),.*?', rawData[0])
        for i in range(len(title_list)):
            print(str(i) +'---' +' ' + title_list[i].strip())
        print("总共有{}集".format(len(title_list) + 1))
        pNum.extend(set(input("请输入你要下载的集数代号，以空格分开").split(' ')))
        for i in pNum:
            params["cid"] = cids[int(i)]
            params["avid"] = avId[2:]
            paramsList.append(params)
    return paramsList

# 获取番剧的json数据
def getBangumiJsonText(url,params):
    return session.get(url, headers=json_headers, params=params, verify=False).text

# 解析Json文本获取视频地址
def getVideoUrl(video_dict):
    videoUrl = video_dict["dash"]["video"][0]["baseUrl"]
    if videoUrl is None:
        print(videoUrl)
        print("错误,获取视频地址失败,错误位置-----getVideoUrl(text)")
        exit()
    else:
        return videoUrl

# 解析Json文本获取音频地址
def getAudioUrl(video_dict):
    audio_url= video_dict['dash']['audio'][0]['baseUrl']
    return audio_url

# 获取标题
def getVideoName(text):
    rawName = re.search(r'<title.*?>(.*?)</title>',text,re.S).group(1)
    index = rawName.rfind('_哔哩哔哩')
    return rawName[:index].translate(table)

# 获取资源文件的大小
def getResourceSize(url):
    return int(session.get(url,headers=html_headers).headers.get("Content-Length","0"))

'''
下载数据 指定    链接 名字 格式
@:param formType 
        - 1 代表下载MP4
        - 2 代表下载MP3
        - 3 代表下载flv
'''
def downloadData(tgtUrl,avName,form_type_num,fileName):
    typeName = MEDIA_TYPE[form_type_num]
    avName = avName.translate(table) # 去除文件名中的转义字符，以及文件夹明名中不允许的字符
    path = os.path.join(hostPath,avName)
    fileName = os.path.join(path,fileName+"."+typeName)
    # 不存在路径则创建文件夹
    if not os.path.exists(path):
        os.makedirs(path)
    # 存在文件夹判断是否下载过
    else:
        # 下载过直接返回
        if  os.path.exists(fileName):
            print("文件已存在")
            return
    nowData = 0
    res = session.get(tgtUrl, headers = html_headers, stream = True,verify=False)
    if res.status_code == 200:
        sumData = int(res.headers["Content-Length"])
        signal = chr(9632)  # 进度条的图形符号
        singleData = sumData/50  #将数据等分
        print("开始下载.....")
        t1 = time.time()
        with open(fileName,"wb") as f:
            for i in res.iter_content(1024):
                f.write(i)
                nowData+=len(i) # 更新已下载数据
                signalCount = int(nowData/singleData) # 设置符号块数量表示进度
                print("\t已下载{0:d}/{1:d}Mb[{2:}]进度---{3:.1f}%".format(nowData//(2**20),sumData//(2**20),
                                                                signal*signalCount+' '*(50-signalCount),
                                                                nowData/sumData*100))
        t = time.time() - t1
        print("用时:{0:.1f}秒,平均下载速度{1:.2f}Mb/s".format(t,sumData//(2**20)/t))
    else:
        print("下载{}{}请求失败".format(avName,typeName))
        print(res.status_code)

# 下载番剧
def spiderBangUmi():
    json_headers["Referer"] = "https://www.bilibili.com/bangumi/play/" + avId
    json_data_url = "https://api.bilibili.com/pgc/player/web/playurl"
    tgt_url = json_headers["Referer"]
    # 获取av页面信息
    html = getPageInfo(tgt_url)
    # 获取标题
    avName = getVideoName(html)
    # 获取参数列表
    paramsList = getParams(html)
    for index,params in enumerate(paramsList):
        avTitle = title_list[int(pNum[index])].translate(table)
        # 获取json文本
        json_text = json.loads(getBangumiJsonText(json_data_url,params))['result']
        # 下载数据
        video_url = getVideoUrl(json_text)
        if  type(video_url) is str:
            audio_url = getAudioUrl(json_text)
            if  video_url.find(r'u\0026'):
                video_url = video_url.replace(r'\u0026',"&")
            if audio_url.find(r'u\0026'):
                audio_url = audio_url.replace(r'\u0026', "&")
            downloadData(video_url,avName,1,avTitle) #下载视频文件
            downloadData(audio_url,avName,0,avTitle) #下载音频文件
            # 合并音画
            mergeVideoAndAudio(hostPath +avName+'/' ,avTitle,1,0)
        else:
            # 如果是.flv文件只下载视频
            nameList = []
            for j,url in enumerate(video_url):
                nameList.append(avTitle+str(j))

                downloadData(url, avName, 2,avTitle+str(j))
            mergeFlv(hostPath + avName + '/', nameList,0,1)

# 抓取普通的视频
def spiderAv():
    json_headers["Referer"] = video_referer + avId
    tgt_url = json_headers["Referer"]
    response = session.get(tgt_url,headers = html_headers)
    response.encoding = "utf-8"
    html = response.text
    avTitle = re.findall(r'<title.*?>(.*?)</title>',html,re.S)[0]  # 番剧名称
    pTitle = re.findall(r'"part":"(.*?)",',html) # 分集标题
    # 输出信息
    for index,i in enumerate(pTitle):
        print(str(index+1) +'---'+ i)

    # 对输入进行检查
    pList = input("请输入要下载的集数代号,以空格分开").split(' ')
    for p in pList:
        if int(p) not in range(1,len(pTitle)+1):
            pList.remove(p)
            print("不存在第{}集".format(p))
        else:
            params ={
                'p':p
            }
            name = pTitle[int(p)-1]
            # 获取目标网页信息
            tgtHtml = session.get(tgt_url,headers=html_headers,verify=False).text
            # 从网页中截取到嵌入其中的json数据
            raw_json = re.findall('"data":(.*?),"session',tgtHtml)[0]
            # 视频的json数据
            video_json = json.loads(raw_json)
            videoUrl = getVideoUrl(video_json)
            audioUrl = getAudioUrl(video_json)
            print("开始下载" + name)
            time.sleep(1)
            downloadData(audioUrl, avTitle, 0, name)
            # 如果不是.flv文件
            if re.findall(r'.*?\.flv.*?', videoUrl) is None:
                downloadData(videoUrl,avTitle,1,name)
            else:
                # 下载.flv文件
                downloadData(videoUrl, avTitle, 2, name)
            # 合并音频和视频
            Path = hostPath + avTitle + '/'
            mergeVideoAndAudio(Path, name,2,0)

# 合并视频和音频
def mergeVideoAndAudio(Path,name,video_type_num,audio_type_num):
    fileName = Path+"/"+name
    print("正在合并视频")
    cmd = '%s -y -i "%s.%s"  -i "%s.%s" -vcodec copy -acodec copy "%s.mp4"' % \
                (ffmpeg_path,fileName,MEDIA_TYPE[audio_type_num],fileName,MEDIA_TYPE[video_type_num],fileName+"_hjt")
    os.system(cmd)

# 显示菜单
def showMenu():
    """
        显示菜单，用户输入
    :return: 返回一个av号或者bv号
    """
    t = input("请输入av/Bv号")
    return t

if __name__ == '__main__':
    while True:
        avId = showMenu()
        if re.match(r"(av)|(bv).*?",avId,re.I):
            # 下载视频
            spiderAv()
        elif re.match(r"(ss)|(ep).*?",avId,re.I):
            # 下载番剧
            spiderBangUmi()
        else:
            print("请输入正确的番号")
