# -*- coding: utf-8 -*-
import time
import datetime

from tasks import config
from tasks import task_msg
from tasks.service.keno import *
from tasks.service.miss import *
from tasks.service.helpers import *
from tasks.utils.redis import redis_connt


class SelectPrevkeno(task_msg.Task):
    max_retries = 0
    default_retry_delay = 0

    def run(self, *args, **kwargs):
        count = 0
        issue = None
        NUM = kwargs['issue']
        print ('Select {}'.format(NUM))
        while not issue:
            count += 1
            if count > 60:
                return
            issue, lottery, frisbee, date = select_prevkeno(NUM)
        if lottery:
            print ('Set {}-{}'.format(lottery,date))
            nums = pc28_num(lottery.split(','))
            if str(NUM) == str(issue):
                set_keno(
                    issue=issue,
                    lottery=lottery,
                    frisbee=frisbee,
                    date=date,
                    pc_nums=nums,
                    pc_sum=sum(nums))
            

class NewPrevkeno(task_msg.Task):
    max_retries = 0
    default_retry_delay = 0

    def run(self, *args, **kwargs):
        
        # 执行时间逻辑
        if not IsRunTime('NewPrevkeno').verify():
            print ('NO Runing')
            return

        issue = None
        NUM = redis_connt.get('NEW_PREVKENO',default=0)
        if NUM:
            count = 0
            while True:
                count += 1
                issue, lottery, frisbee, date = select_prevkeno(NUM)
                if issue or count > 50:
                    break
            if lottery:
                nums = pc28_num(lottery.split(','))
                if str(NUM) <= str(issue):
                    NUM = issue
                    set_keno(
                        issue=issue,
                        lottery=lottery,
                        frisbee=frisbee,
                        date=date,
                        pc_nums=nums,
                        pc_sum=sum(nums))
                    print ('Set NewPrevkeno {}'.format(issue))
            else:
                task_msg.send_task('tasks.service.lottery.SelectPrevkeno',kwargs={"issue":NUM})

            last_prevkeno = redis_connt.get('NEW_PREVKENO',default=0)
            if (int(NUM)+1) > int(last_prevkeno):
                print ('Set NewPrevkeno Redis {}'.format(int(NUM)+1))
                # 更新 新的待获取期号
                redis_connt.set('NEW_PREVKENO',int(NUM)+1)
                redis_connt.expire('NEW_PREVKENO', 3600*24*7)
            else:
                print ('{}-{}'.format((int(NUM)+1),last_prevkeno))

class PrevkenoMiss(task_msg.Task):
    max_retries = 0
    default_retry_delay = 0

    def run(self, *args, **kwargs):
        try:
            print ('start prevkeno miss')
            prevkeno = Prevkeno()
            prevkeno.select_miss()
            print ('prevkeno miss end')
        except Exception as e:
            print (u'%s' % e)

class Test(task_msg.Task):
    max_retries = 0
    default_retry_delay = 0

    def run(self, *args, **kwargs):
        PAGE = int(redis_connt.get('PREVKENO_PAGE',default=15007))
        while PAGE:
            print (PAGE)
            try:
                last_keno = int(redis_connt.get('LAST_KENO',default=0))
                URL = 'http://www.bwlc.net/bulletin/prevkeno.html?page={}'.format(PAGE)
                data_list = get_prevkeno_list(URL)
                if data_list:
                    set_page = redis_connt.get('PREVKENO_PAGE',default=15007)
                    if int(set_page) == PAGE:
                        for data in data_list:
                            issue = data['issue']
                            lottery = data['lottery']
                            assert issue
                            if int(issue) == last_keno:
                                redis_connt.set('PREVKENO_PAGE',0)
                                break
                            nums = pc28_num(lottery.split(','))
                            set_keno(pc_nums=nums,pc_sum=sum(nums),**data)
                        PAGE -=1
                        redis_connt.set('PREVKENO_PAGE',PAGE)
            except Exception as e:
                print (URL)
                print (u'%s' % e)
