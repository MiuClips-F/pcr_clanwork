from hoshino import Service, R, priv
from hoshino.typing import CQEvent
import asyncio
import aiohttp
import re
import os

help = '''
[上传作业]
'''

sv = Service('pcr_clanwork', enable_on_default=True, visible=True)

BOSS = ['a1','a2','a3','a4','a5','a5-1','a5-2','b1','b2','b3','b4','b5','b5-1','b5-2','c1','c2','c3','c4','c5','c5-1','c5-2']

class clanwork():
    def __init__(self):
        self.upload_on = {}
        self.upload_image_on = {}
        self.user = {}
        self.work = {}
        self.state = {}
        self.name = {}

    def makedir(self, gid):
        for item in BOSS:
            RES = R.img(f'clanwork/{gid}/' + item)
            if not os.path.exists(RES.path):
                os.makedirs(RES.path)
            self.state[item] = len(os.listdir(RES.path)) // 2
        return self.state
    
    def turn_upload_on(self, gid):
        self.upload_on[gid] = True

    def turn_upload_off(self, gid):
        self.upload_on[gid] = False

    def turn_upload_image_on(self, gid):
        self.upload_image_on[gid] = True
    
    def turn_upload_image_off(self, gid):
        self.upload_image_on[gid] = False
    
    def set_user(self, gid):
        self.user[gid] = []
        self.work[gid] = {}

    def add_user(self, gid, uid):
        self.user[gid].append(uid)
        self.work[gid][uid] = {}

    def add_work_name(self, gid, msg):
        self.name[gid] = msg

    def get_work_name(self, gid):
        return self.name[gid]
    
    def get_user(self, gid):
        return self.user[gid][0]

    def get_on_off_upload_work(self, gid):
        return self.upload_on[gid] if self.upload_on.get(gid) is not None else False

    def get_on_off_upload_image(self, gid):
        return self.upload_image_on[gid] if self.upload_image_on.get(gid) is not None else False

cw = clanwork()

def get_list_num(gid, bossnum):
    workpath = R.img(f'clanwork/{gid}/{bossnum}').path
    path, dirs, files = next(os.walk(workpath))
    return workpath, len(files)

async def download(url, gid, bossnum):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as req:
                workpath, name = get_list_num(gid, bossnum)
                chunk = await req.read()
                open(os.path.join(f'{workpath}/{name + 1}.png'), 'wb').write(chunk)
                return True
    except Exception as e:
        print(e)
        return False

@sv.on_fullmatch('上传作业')
async def upload(bot, ev:CQEvent):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '仅限管理员上传作业', at_sender=True)
    if not os.path.exists(R.img(f'clanwork/{gid}').path):
        cw.makedir(gid)
    if cw.get_on_off_upload_work(gid):
        upuid = cw.get_user(gid)
        await bot.finish(ev, f'[CQ:at,qq={upuid}] 正在上传作业，请等待上传完毕', at_sender=True)
    uid = ev.user_id
    cw.turn_upload_on(gid)
    cw.set_user(gid)
    cw.add_user(gid, uid)
    await bot.send(ev, f'请在一分钟内上传指定BOSS作业，请输入boss\n例如：boss b1(代表二周目一王)\nboss b5-2（代表二周目五王狂暴）\n如果五王无狂暴，请输入boss b5', at_sender=True)
    await asyncio.sleep(60)
    

@sv.on_prefix('boss')
async def bossname(bot, ev:CQEvent):
    gid = ev.group_id
    uid = ev.user_id
    if cw.get_on_off_upload_work(gid) and cw.get_user(gid) == uid:
        msg = ev.message.extract_plain_text()
        await bot.send(ev, f'请上传{msg}作业图片', at_sender=True)
        cw.turn_upload_image_on(gid)
        cw.add_work_name(gid, msg)

@sv.on_message()
async def work(bot, ev:CQEvent):
    gid = ev.group_id
    uid = ev.user_id
    if cw.get_on_off_upload_image(gid) and cw.get_user(gid) == uid:
        ret = re.match(r"\[CQ:image,file=(.*),url=(.*)\]", str(ev.message))
        name = cw.get_work_name(gid)
        if not await download(ret.group(2), gid, name):
            await bot.finish(ev, '上传失败')
            cw.turn_upload_off(gid)
            cw.turn_upload_image_off(gid)
        await bot.send(ev, f'{name}作业上传完毕', an_sender=True)
        cw.turn_upload_off(gid)
        cw.turn_upload_image_off(gid)

@sv.on_fullmatch('关闭上传')
async def upload_off(bot, ev:CQEvent):
    gid = ev.group_id
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '为防止滥用，请联系群管理员关闭上传', at_sender=True)
    await bot.send(ev, '已强制关闭上传作业', at_sender=True)
    cw.turn_upload_off(gid)
    cw.turn_upload_image_off(gid)
    
@sv.on_prefix('查作业')
async def qwork(bot, ev:CQEvent):
    img = []
    gid = ev.group_id
    work = ev.message.extract_plain_text()
    cpath = R.img(f'clanwork/{gid}/{work}').path
    num = get_list_num(gid, work)[1]
    if num == 0:
        await bot.finish(ev, f'没有找到{work}的作业')
    for file in os.listdir(cpath):
        fnum = file[:-4]
        img.append(f'{fnum}：[CQ:image,file=file:///{cpath}/{file}]\n')
    msg = ''.join(img)
    await bot.send(ev, f'已找到{num}份{work}作业：\n{msg}', at_sender=True)

@sv.on_prefix('删作业')
async def dwork(bot, ev:CQEvent):
    gid = ev.group_id
    work = ev.message.extract_plain_text().split()
    if not priv.check_priv(ev, priv.ADMIN):
        await bot.finish(ev, '请联系群管理删除作业', at_sender=True)
    bossnum = work[0]
    listnum = work[1]
    path = R.img(f'clanwork/{gid}/{bossnum}/{listnum}.png').path
    os.remove(path)
    await bot.send(ev, f'已删除{bossnum}第{listnum}个作业', at_sender=True)
