from bilibili import bilibili
import asyncio
from configloader import ConfigLoader
import utils
import printer
from bilitimer import BiliTimer
import random
import re
import json

# 获取每日包裹奖励
async def Daily_bag():
    json_response = await bilibili.get_dailybag()
    # no done code
    printer.warn(json_response)
    for i in json_response['data']['bag_list']:
        printer.info([f'# 获得包裹 {i["bag_name"]}'])
    BiliTimer.call_after(Daily_bag, 21600)


# 签到功能
async def DoSign():
    # -500 done
    temp = await bilibili.get_dosign()
    printer.warn(temp)
    printer.info([f'# 签到状态: {temp["msg"]}'])
    if temp['code'] == -500 and '已' in temp['msg']:
        sleeptime = (utils.seconds_until_tomorrow() + 300)
    else:
        sleeptime = 350
    BiliTimer.call_after(DoSign, sleeptime)

# 领取每日任务奖励
async def Daily_Task():
    # -400 done/not yet
    json_response2 = await bilibili.get_dailytask()
    printer.warn(json_response2)
    printer.info([f'# 双端观看直播:  {json_response2["msg"]}'])
    if json_response2['code'] == -400 and '已' in json_response2['msg']:
        sleeptime = (utils.seconds_until_tomorrow() + 300)
    else:
        sleeptime = 350
    BiliTimer.call_after(Daily_Task, sleeptime)

async def Sign1Group(i1, i2):
    json_response = await bilibili.assign_group(i1, i2)
    if not json_response['code']:
        data = json_response['data']
        if data['status']:
            printer.info([f'# 应援团 {i1} 已应援过'])
        else:
            printer.info([f'# 应援团 {i1} 应援成功,获得{data["add_num"]}点亲密度'])

# 应援团签到
async def link_sign():
    json_rsp = await bilibili.get_grouplist()
    printer.warn(json_rsp)
    list_check = json_rsp['data']['list']
    for i in list_check:
        asyncio.ensure_future(Sign1Group(i['group_id'], i['owner_uid']))
    BiliTimer.call_after(link_sign, 21600)

async def send_expiring_gift():
    task_control = ConfigLoader().dic_user['task_control']
    if task_control['clean-expiring-gift']:
        argvs = await utils.fetch_bag_list(show=False)
        printer.warn(argvs)
        roomID = task_control['clean-expiring-gift2room']
        time_set = task_control['set-expiring-time']
        list_gift = []
        for i in argvs:
            left_time = i[3]
            # 剩余时间少于半天时自动送礼
            if left_time is not None and 0 < int(left_time) < time_set:
                list_gift.append(i[:3])
        if list_gift:
            print('发现即将过期的礼物', list_gift)
            if(len(list_gift) > 5):
                printer.warn(f'过期礼物{list_gift}')
            if task_control['clean_expiring_gift2all_medal']:
                print('正在投递其他勋章')
                list_medal = await utils.fetch_medal(show=False)
                list_gift = await full_intimate(list_gift, list_medal)
                
            print('正在清理过期礼物到指定房间')
            for i in list_gift:
                giftID = i[0]
                giftNum = i[1]
                bagID = i[2]
                await utils.send_gift_web(roomID, giftNum, bagID, giftID)
        else:
            print('未发现即将过期的礼物')

async def send_medal_gift():
    list_medal = []
    task_control = ConfigLoader().dic_user['task_control']
    if task_control['send2wearing-medal']:
        list_medal = await utils.WearingMedalInfo()
        if not list_medal:
            print('暂未佩戴任何勋章')
    if task_control['send2medal']:
        list_medal += await utils.fetch_medal(False, task_control['send2medal'])
    # print(list_medal)
    print('正在投递勋章')
    temp = await utils.fetch_bag_list(show=False)
    # print(temp)
    list_gift = []
    for i in temp:
        gift_id = int(i[0])
        left_time = i[3]
        if (gift_id not in [4, 3, 9, 10]) and left_time is not None:
            list_gift.append(i[:3])
    await full_intimate(list_gift, list_medal)

async def send_gift():
    await send_medal_gift()
    await send_expiring_gift()
    BiliTimer.call_after(send_gift, 21600)

async def full_intimate(list_gift, list_medal):
    json_res = await bilibili.gift_list()
    dic_gift = {j['id']: int(j['price'] / 100) for j in json_res['data']}
    for roomid, score_wanted, medal_name in list_medal:
        sum_score = 0
        for i in list_gift:
            gift_id, gift_num, bag_id = i
            price = dic_gift[gift_id]
            left_score = score_wanted - sum_score
            if price * gift_num <= left_score:
                num_wanted = gift_num
            elif left_score >= price:
                num_wanted = int(left_score / price)
            else:
                num_wanted = 0
            await utils.send_gift_web(roomid, num_wanted, bag_id, gift_id)
            i[1] -= num_wanted
            score = price * num_wanted
            sum_score += score
        printer.info([f'# 对{medal_name}共送出亲密度为{sum_score}的礼物'])
    return [i for i in list_gift if i[1]]


async def doublegain_coin2silver():
    if ConfigLoader().dic_user['task_control']['doublegain_coin2silver']:
        json_response0 = await bilibili.request_doublegain_coin2silver()
        json_response1 = await bilibili.request_doublegain_coin2silver()
        print(json_response0['msg'], json_response1['msg'])
    BiliTimer.call_after(doublegain_coin2silver, 21600)

async def sliver2coin():
    if ConfigLoader().dic_user['task_control']['silver2coin']:
        # 403 done
        # json_response1 = await bilibili.silver2coin_app()
        
        json_response = await bilibili.silver2coin_web()
        printer.info([f'#  {json_response["msg"]}'])
        
        if json_response['code'] == 403 and '最多' in json_response['msg']:
            finish_web = True
        else:
            finish_web = False

        if finish_web:
            sleeptime = (utils.seconds_until_tomorrow() + 300)
            BiliTimer.call_after(sliver2coin, sleeptime)
            return
        else:
            BiliTimer.call_after(sliver2coin, 350)
            return

    BiliTimer.call_after(sliver2coin, 21600)

async def GetVideoExp(list_topvideo):
    print('开始获取视频观看经验')
    aid = random.choice(list_topvideo)
    cid = await utils.GetVideoCid(aid)
    await bilibili().Heartbeat(aid, cid)

async def GiveCoinTask(coin_remain, list_topvideo):
    i = 0
    while coin_remain > 0:
        i += 1
        if i > 20:
            print('本次可投票视频获取量不足')
            return
        aid = random.choice(list_topvideo)
        rsp = await utils.GiveCoin2Av(aid, 1)
        if rsp is None:
            break
        elif rsp:
            coin_remain -= 1

async def GetVideoShareExp(list_topvideo):
    print('开始获取视频分享经验')
    aid = random.choice(list_topvideo)
    await bilibili().DailyVideoShare(aid)

async def BiliMainTask():
    task_control = ConfigLoader().dic_user['task_control']
    login, watch_av, num, share_av = await utils.GetRewardInfo()
    if task_control['fetchrule'] == 'bilitop':
        list_topvideo = await utils.GetTopVideoList()
    else:
        list_topvideo = await utils.fetch_uper_video(task_control['mid'])
    if (not login) or not watch_av:
        await GetVideoExp(list_topvideo)
    coin_sent = num / 10
    coin_set = min(task_control['givecoin'], 5)
    coin_remain = coin_set - coin_sent
    await GiveCoinTask(coin_remain, list_topvideo)
    if not share_av:
        await GetVideoShareExp(list_topvideo)
    # b站傻逼有记录延迟，3点左右成功率高一点
    BiliTimer.call_after(BiliMainTask, utils.seconds_until_tomorrow() + 10800)


async def check(id):
    # 3放弃
    # 2 否 voterule
    # 4 删除 votedelete
    # 1 封杀 votebreak
    text_rsp = await bilibili().req_check_voted(id)
    pattern = re.compile(r'\((.+)\)')
    match = pattern.findall(text_rsp)
    temp = json.loads(match[0])
    data = temp['data']
    votebreak = data['voteBreak']
    voteDelete = data['voteDelete']
    voteRule = data['voteRule']
    voted = votebreak+voteDelete+voteRule
    percent = (voteRule / voted) if voted else 0
    
    print(f'\"{data["originContent"]}\"')
    print('该案件目前已投票', voted)
    print('认为言论合理比例', percent)
    return voted, percent
    
    
def judge_case(voted, percent):
    vote = None
    if voted >= 300:
        # 认为这里可能出现了较多分歧，抬一手
        if percent >= 0.4:
            vote = 2
        elif percent <= 0.25:
            vote = 4
    elif voted >= 150:
        if percent >= 0.9:
            vote = 2
        elif percent <= 0.1:
            vote = 4
    elif voted >= 50:
        if percent >= 0.97:
            vote = 2
        elif percent <= 0.03:
            vote = 4
    # 抬一手
    if vote is None and voted >= 400:
        vote = 2
        
    return vote
               
async def judge():
    num_case = 0
    num_voted = 0
    while True:
        temp = await bilibili().req_fetch_case()
        if not temp['code']:
            id = temp['data']['id']
            num_case += 1
        else:
            print('本次未获取到案件')
            break
        
        wait_time = 0
        min_percent = 1
        max_percent = 0
        while True:
            voted, percent = await check(id)
            vote = judge_case(voted, percent)
            if voted >= 50:
                min_percent = min(min_percent, percent)
                max_percent = max(max_percent, percent)
                print('统计投票波动情况', max_percent, min_percent)
            
            if vote is not None:
                break
            elif wait_time >= 1200:
                print('进入二次判定')
                # 如果case判定中，波动很小，则表示趋势基本一致
                if 0 <= max_percent - min_percent <= 0.1 and voted > 200:
                    future_voted = voted + 100
                    vote0 = judge_case(future_voted, max_percent)
                    vote1 = judge_case(future_voted, min_percent)
                    vote = vote0 if vote0 == vote1 else None
                print('二次判定结果', vote)
                break
            else:
                sleep_time = 180 if voted < 300 else 60
                printer.info([f'案件{id}暂时无法判定，在{sleep_time}后重新尝试'], True)
                await asyncio.sleep(sleep_time)
                wait_time += sleep_time
        
        if vote is None:
            num_voted -= 1
            vote = 3
        print('该案件的投票决策', id, vote)
        json_rsp = await bilibili().req_vote_case(id, vote)
        if not json_rsp['code']:
            print('该案件的投票结果', id, '投票成功')
            num_voted += 1
        else:
            print('该案件的投票结果', id, '投票失败，请反馈作者')
        
        print('______________________________________________')
    
    printer.info([f'风纪委员会共获取{num_case}件案例，其中有效投票{num_voted}件'], True)
    BiliTimer.call_after(judge, 3600)
        

def init():
    BiliTimer.call_after(sliver2coin, 0)
    BiliTimer.call_after(doublegain_coin2silver, 0)
    BiliTimer.call_after(DoSign, 0)
    BiliTimer.call_after(Daily_bag, 0)
    BiliTimer.call_after(Daily_Task, 0)
    BiliTimer.call_after(link_sign, 0)
    BiliTimer.call_after(send_gift, 0)
    BiliTimer.call_after(BiliMainTask, 0)
    BiliTimer.call_after(judge, 0)
    
