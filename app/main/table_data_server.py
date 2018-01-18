#!/usr/bin/python
# -*- coding: UTF-8 -*-
from .mongo_service import MyMongo_executive,Case,CaseLogs
from .. import red
from .sqlhelper import find_the_first_day
from .backserver import CaseLog_DicToList,CaseInfoList,DateStrToDate
import datetime,json
import numpy as np
import pandas as pd
from mongoengine.queryset.visitor import Q
import queue,threading
from collections import defaultdict

#表格处理函数
class TableExcute():

    #初始化构建合同变和合同日志表
    def MongoCaseInit(self):
        start_date = find_the_first_day()
        mymon = MyMongo_executive()
        mymon.Case_init(start_date)
        mymon.CaseLog_inti_(start_date)

    def DailyQuest(self):
        now = datetime.datetime.now()
        now = now.replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday = now - datetime.timedelta(days=1)
        mymon = MyMongo_executive()
        mymon.Case_init(start_date=yesterday,end_date=now)
        mymon.CaseLog_inti_(start_date=yesterday,end_date=now)

    def CaseLogGet(self,start_date,end_date):
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date,hour=23,minute=59,seconds=59)
        logs = CaseLogs.objects(Q(date__gte=start_date) & Q(date__lte=end_date)).all()
        stactic = list(CaseLog_DicToList(event) for log in logs
                       for behave in log.events
                       for event in log.events[behave])
        stactic = sorted(stactic, key=lambda x: x[0], reverse=True)
        return stactic

    def CaseGet(self):
        startdate = datetime.datetime(2017, 7, 10, 8, 0, 0)
        enddate = datetime.datetime(2017, 7, 18, 8, 0, 0)
        cases = Case.objects(Q(start_date__gte=startdate) & Q(start_date__lte=enddate)).all()
        caseinfo_list = list(CaseInfoList(case) for case in cases)
        return caseinfo_list

    def Statistic_index(self,statistic_date,statistic_date_end,compare_date,compare_date_end):
        statistic_date = DateStrToDate(statistic_date)
        statistic_end_date  = DateStrToDate(statistic_date_end,hour=23,minute=59,seconds=59)
        compare_date = DateStrToDate(compare_date)
        compare_end_date = DateStrToDate(compare_date_end,hour=23,minute=59,seconds=59)
        events_frame = pd.read_msgpack(red.get('logs_data'))
        case_frame = pd.read_msgpack(red.get('case_data'))
        date_frame_statistic = events_frame[(events_frame['date']>=statistic_date)&(events_frame['date']<=statistic_end_date)]
        date_frame_compare = events_frame[(events_frame['date']>=compare_date)&(events_frame['date']<=compare_end_date)]

        data_excute = Data_Execute(events_frame,case_frame)
        que = queue.Queue()
        result_list = []

        t1 = threading.Thread(target=data_excute.index_stactic,args=(date_frame_statistic,1,que,statistic_date.strftime("%Y-%m-%d"),case_frame,True))
        t2 = threading.Thread(target=data_excute.index_stactic,args=(date_frame_compare,2,que,compare_date.strftime("%Y-%m-%d"),))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        while not que.empty():
            result_list.append(que.get())
        result_list=sorted(result_list,key=lambda x:x['data_name'])
        return result_list

    def Statistic_detail(self,start_date,end_date,type):
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date)
        date_frame = pd.read_msgpack(red.get('logs_data'))
        case_frame = pd.read_msgpack(red.get('case_data'))

        data_excute = Data_Execute(date_frame,case_frame)
        que = queue.Queue()
        result_list = []

        if int(type) == 1:#按日统计
            i=0
            thread_list = []
            while start_date<=end_date:
                start_date_end = start_date+datetime.timedelta(days=1)
                t1 = threading.Thread(target=data_excute.index_stactic,args=(date_frame[(date_frame['date']>=start_date)&(date_frame['date']<=start_date_end)],i,que,start_date.strftime("%Y-%m-%d"),case_frame,True,True))
                thread_list.append(t1)
                i+=1
                start_date+=datetime.timedelta(days=1)

        elif int(type) == 7:#按周统计
            i = 0
            thread_list =[]
            while start_date<=end_date:
                start_date_end = min(start_date + datetime.timedelta(days=7),end_date)
                t1 = threading.Thread(target=data_excute.index_stactic, args=(date_frame[(date_frame['date'] >= start_date) & (date_frame['date'] <= start_date_end)], i, que,
                '%s/%s'%(start_date.strftime("%Y-%m-%d"),start_date_end.strftime('%m-%d')), case_frame, True, True))
                thread_list.append(t1)
                i += 1
                start_date += datetime.timedelta(days=7)


        else: #按月统计
            i = 0
            thread_list = []
            while start_date <= end_date:
                start_date_end = min(start_date + datetime.timedelta(days=30), end_date)
                t1 = threading.Thread(target=data_excute.index_stactic, args=(
                date_frame[(date_frame['date'] >= start_date) & (date_frame['date'] <= start_date_end)], i, que,
                '%s/%s' % (start_date.strftime("%Y-%m-%d"), start_date_end.strftime('%m-%d')), case_frame, True, True))
                thread_list.append(t1)
                i += 1
                start_date += datetime.timedelta(days=30)

        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

        while not que.empty():
            result_list.append(que.get())
        result_list = sorted(result_list, key=lambda x: x['data_name'], reverse=True)
        return result_list

    #门店基本信息表处理函数
    def Statistic_by_shop(self,start_date,end_date):
        def shop_none_data(shop_name,date):
            new_none_data = {'date':date,'data_name':shop_name,
                'jinjian': 0, 'hetong': 0, 'loan': '%.2f' % 0, 'overtime': 0,
                'overtime_amount': '%.2f' % 0, 'waicui_amount': '%.2f' % 0,
                'principal_rate': '%.2f%%' % (0 * 100), 'interest_rate': '%.2f%%' % (0),
                'fee_rate': '%.2f%%' % (0 * 100), 'new':0,'renew':0,'recommend':0,'ontime':0,'advance':0,'waicui':0,'apply_pass':0,
                              'apply_rely':'0.00','approve_pass':0,'approve_rate':'0.00','recommend_amount':'0.00',
                              'goods':0}
            return new_none_data

        shop_reflect=json.loads(red.get('shop_data').decode())

        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date,23,59,59)
        date_frame = pd.read_msgpack(red.get('logs_data'))
        case_frame = pd.read_msgpack(red.get('case_data'))

        data = date_frame[(date_frame['date']>=start_date)&(date_frame['date']<=end_date)]

        shop_list = set(data['shop_id'].dropna(how='any'))
        data_excute = Data_Execute(date_frame,case_frame)
        result_dict = defaultdict(list)
        result_list = []
        date_index = "%s/%s"%(start_date.strftime('%Y-%m-%d'),end_date.strftime('%m-%d'))

        for shop in shop_list:
            shop_data = data_excute.detail_by_shop(table=data[data['shop_id']==shop],date_index=date_index,data_name=shop,case_frame=case_frame)
            shop_data['data_name']=shop_reflect[str(shop)]
            result_dict[int(shop)]=shop_data

        for shop_id in shop_reflect:
            if not result_dict[int(shop_id)]:
                result_list.append(shop_none_data(shop_reflect[shop_id],date_index))
            else:
                result_list.append(result_dict[int(shop_id)])

        return result_list

    #催收表处理
    def cuishou_by_shop(self,start_date,end_date):
        def cuishou(shop_name,date):
            none_data ={'date': date, 'data_name': shop_name, 'overtime_amount': '%.2f' % 0.0, 'overtime_num': 0,
             'waicui_num': 0, 'waicui_amount': '%.2f' % 0.0, 'overtime_rate': '%.2f' % 0.0,
             'diancui_waicui_rate': '%.2f' % 0.0,
             'waicui_end_num': 0, 'waicui_end_amount': '%.2f' % 0.0,'waicui_rate':'%.2f'%0.0}
            return none_data
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date)
        date_frame = pd.read_msgpack(red.get('logs_data'))
        case_frame = pd.read_msgpack(red.get('case_data'))
        shop_reflect = json.loads(red.get('shop_data').decode())
        result_dict = defaultdict(list)
        result_list = []
        date_index = "%s/%s" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%m-%d'))

        data = date_frame[(date_frame['date'] >= start_date) & (date_frame['date'] <= end_date)]
        data_excute = Data_Execute(date_frame=date_frame,cases_frame=case_frame)
        shop_list = set(data['shop_id'].dropna(how='any'))

        for shop in shop_list:
            shop_data = data_excute.cuishou_by_shop(table=data[data['shop_id']==shop],date_index=date_index,data_name=shop)
            shop_data['data_name']=shop_reflect[str(shop)]
            result_dict[int(shop)]=shop_data

        for shop_id in shop_reflect:
            if not result_dict[int(shop_id)]:
                result_list.append(cuishou(shop_reflect[shop_id],date_index))
            else:
                result_list.append(result_dict[int(shop_id)])
        return result_list

    #复审表处理
    def fushen_by_person(self,start_date,end_date):
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date,hour=23,minute=59,seconds=59)
        date_frame = pd.read_msgpack(red.get('logs_data'))
        case_frame = pd.read_msgpack(red.get('case_data'))

        data = date_frame[(date_frame['date'] >= start_date) & (date_frame['date'] <= end_date)]
        data_excute = Data_Execute(date_frame=date_frame, cases_frame=case_frame)
        fushen_events = data[data['behave'] == '复审审批']
        approvers = set(fushen_events['manipulator'].tolist())
        date_index = "%s/%s" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%m-%d'))
        result_list = []


        for approver in approvers:
            table = fushen_events[fushen_events['manipulator']==approver]
            statistic_data=data_excute.approve_by_person(table,date_index=date_index,data_name=approver)
            result_list.append(statistic_data)
        return result_list

    def apply_by_shop(self):
        start_date = datetime.datetime(2017,7,10)
        end_date = datetime.datetime(2017,10,15)
        shop_ids = [i for i in range(2,24)]
        date_frame = pd.read_msgpack(red.get('logs_data'))
        case_frame = pd.read_msgpack(red.get('case_data'))
        # shop_reflect = json.loads(red.get('shop_data').decode())

        data = date_frame[(date_frame['date'] >= start_date) & (date_frame['date'] <= end_date)]
        data_excute = Data_Execute(date_frame=date_frame, cases_frame=case_frame)
        date_index = "%s/%s" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%m-%d'))
        result_list = []

        apply_events = data[(data['behave']=='风控审批')&(data['shop_id'].isin(shop_ids))]
        apply_approvers = set(apply_events['manipulator'].dropna(how='any'))

        for apply_approver in apply_approvers:
            apply_by_person = apply_events[apply_events['manipulator'] == apply_approver]
            result_list.append(data_excute.apply_by_shop(apply_by_person,date_index=date_index,data_name=apply_approver))
        return result_list


    #中介信息
    def recommend_by_shop(self,start_date,end_date):
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date, hour=23, minute=59, seconds=59)
        date_frame = pd.read_msgpack(red.get('logs_data'))
        case_frame = pd.read_msgpack(red.get('case_data'))
        shop_reflect = json.loads(red.get('shop_data').decode())
        result_list = []

        data = date_frame[date_frame['date'] <= end_date]
        data_excute = Data_Execute(date_frame=date_frame, cases_frame=case_frame)
        date_index = "%s/%s" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%m-%d'))

        for shop_id in shop_reflect:
            shop_data = data_excute.recommend_by_shop(table=data[data['shop_id'] == int(shop_id)], date_index=date_index,data_name=shop_reflect[str(shop_id)],start_date=start_date)
            result_list.append(shop_data)
        return result_list




#========================================================================================


#数据统计函数
class Data_Execute:
    def __init__(self,date_frame = None,cases_frame =None):
        self.none_data = {'date':None,'data_name':None,
                'jinjian': 0, 'hetong': 0, 'loan': '%.2f' % 0, 'overtime': 0,
                'overtime_amount': '%.2f' % 0, 'waicui_amount': '%.2f' % 0,
                'principal_rate': '%.2f%%' % (0 * 100), 'interest_rate': '%.2f%%' % (0),
                'fee_rate': '%.2f%%' % (0 * 100),'new':0,'renew':0,'recommend':0,'ontime':0,'advance':0,'waicui':0,'apply_pass':0,
                              'apply_rely':'0.00','approve_pass':0,'approve_rate':'0.00','recommend_amount':'0.00',
                              'goods':0}
        self.date_frame = date_frame
        self.cases_frame = cases_frame

    #进件计算
    def apply_info(self,table):
        apply = table[table['behave'] == '风控审批'].drop_duplicates(['case_id'])
        jinjian = len(apply)  # 进件量

        apply_success = apply[apply['message']=='通过']
        apply_su_num = len(apply_success)
        return apply, jinjian,apply_success,apply_su_num

    #放款计算
    def loan_info(self,table):
        loan = table[table['behave'] == '放款'].drop_duplicates(['case_id'])
        loan_amount = np.array(
            list(map(lambda x: x['实际放款金额'] if '发送成功' in x['message'] else 0, loan['message'])))  # 发送成功的数据才算作放款
        hetong = len(loan_amount)  # 合同量
        fangkuan = loan_amount.sum()  # 放款总数
        return loan_amount, hetong, fangkuan

    #逾期计算
    def overtime_info(self,table):
        overtime = table[table['behave'].str.contains('电催') | table['behave'].str.contains('外催')]
        yuqi = len(overtime.drop_duplicates(['case_id']))  # 逾期数
        overtime_amount = np.array(list(message['金额'] for message in overtime['message']))
        yuqi_amount = overtime_amount.sum()  # 逾期款数

        waicui = overtime[overtime['behave'] == '外催']
        index_waicui = len(waicui.drop_duplicates(['case_id']))  # 外催数
        waicui_amount_data = np.array(list(message['金额'] for message in waicui['message']))
        waicui_amount = waicui_amount_data.sum()  # 外催总额
        return yuqi, yuqi_amount, index_waicui, waicui_amount

    #到期计算
    def payment_info(self,table):
        payment_case = table[table['behave'] == '到期']
        payment_case = payment_case.drop_duplicates(['case_id', 'manipulator'])
        payment_list = payment_case['message'].tolist()
        if payment_list:
            payment_data = pd.DataFrame(payment_list)
            principal_rate = payment_data['本期已还本金'].sum() / payment_data['本期应还本金'].sum()  # 本金还款率
            interest_rate = payment_data['本期已还利息'].sum() / payment_data['本期应还利息'].sum()  # 利息还款率
            fee_rate = payment_data['本期已还费用'].sum() / payment_data['本期应还费用'].sum()  # 费用还款率
        else:
            principal_rate, interest_rate, fee_rate = 0.0, 0.0, 0.0
        return principal_rate, interest_rate, fee_rate

    #催收计算
    def cuishou_info(self,table):
        shop_event_approve=table[(table['behave']=='复审审批')&(table['message'].str.contains('通过'))]
        approve_cases = shop_event_approve['case_id'].tolist()
        overtime_cases = self.date_frame[(self.date_frame['behave'].isin(['外催', '电催'])) & (self.date_frame['case_id'].isin(approve_cases))]
        overtime_amount = pd.DataFrame(overtime_cases['message'].tolist())['金额'].sum() if overtime_cases['message'].tolist() else 0.0 # 逾期总额
        overtime_num = len(set(overtime_cases['case_id']))# 逾期总数

        waicui_case = overtime_cases[overtime_cases['behave']=='外催']
        waicui_num= len(set(waicui_case['case_id']))  # 外催数
        waicui_amount = pd.DataFrame(waicui_case['message'].tolist())['金额'].sum() if waicui_case['message'].tolist() else 0.0# 外催金额
        waicui_rate = waicui_num / len(approve_cases)  # 外催比
        cases = self.cases_frame[self.cases_frame['case_id'].isin(set(waicui_case['case_id']))]
        cases_amount = cases['amount'].sum() if not cases.empty else 0.0# 单量总金额
        waicui_amount_rate = waicui_amount / cases_amount if cases_amount else 0.0 # 外催金额比

        overtime_rate = overtime_num / len(approve_cases) if approve_cases else 0.0 # 逾期比
        diancui_waicui_rate = waicui_num / overtime_num if overtime_num else 0.0  # 电催移交比

        approve_case = pd.merge(shop_event_approve, self.cases_frame, how='left', on='case_id')
        f = lambda x: True if x['status'][10] >= 1 and x['status'][-1] == 1 else False
        waicui_end_case = approve_case[approve_case.apply(f,axis=1)]
        waicui_end_num=len(waicui_end_case)  # 外催结清单量
        waicui_end_amount = waicui_end_case['amount'].sum()  if not waicui_end_case.empty else 0.0# 外催结清金额
        return overtime_amount,overtime_num,waicui_num,waicui_amount,overtime_rate,diancui_waicui_rate,waicui_end_num,waicui_end_amount,waicui_rate,waicui_amount_rate

    #复审信息计算
    def approve_info(self,table):
        approves = table[table['behave']=='复审审批']
        approve_num = len(approves)  # 风控批件量
        approve_success_cases = approves[approves['message'].str.contains('通过')==True]
        approve_success_num = len(approve_success_cases)  # 复审批件量
        approve_dely = approve_num-approve_success_num#复审拒件量
        approve_retry = len(approve_success_cases[approve_success_cases['message']=='退单通过'])#退单通过量

        # cases = person_approves['case_id'].tolist()
        # person_applys = self.date_frame[(self.date_frame['behave'] == '风控审批') & (self.date_frame['case_id'].isin(cases))]
        # apply_approve_table = pd.merge(person_applys, person_approves, on='case_id')
        # apply_approve_table['exhaust_time'] = apply_approve_table['date_y'] - apply_approve_table['date_x']
        # exhaust_time_mean_info =apply_approve_table['exhaust_time'].mean().seconds
        # approve_hour, approve_minute, approve_seconds = exhaust_time_mean_info // 3600, exhaust_time_mean_info % 3600 // 60, exhaust_time_mean_info % 60
        # exhaust_time_mean = "%s时%s分%s秒"%(approve_hour,approve_minute,approve_seconds)#平均审核时间

        return approve_num,approve_success_num,approve_dely,approve_retry

    #中介单信息
    def recommned_info(self,table,start_date):
        approve_events = table[(table['behave']=='复审审批')&(table['message'].str.contains('通过'))]
        approve_cases = set(approve_events['case_id'])
        recommend_num_entire=len(set(self.cases_frame[self.cases_frame['case_id'].isin(approve_cases)]['recommend_name'].dropna(how='any')))#总中介数
        table_new=table[table['date']>=start_date]
        approve_cases_new = set(table_new['case_id'])
        cases =self.cases_frame[self.cases_frame['case_id'].isin(approve_cases_new)]
        recommend_num_new = len(set(cases['recommend_name'].dropna(how='any')))#新中介数量
        recommend_case = cases[~cases['recommend_name'].isnull()]
        recommend = len(recommend_case)  # 推荐单量
        recommend_amount = recommend_case['amount'].sum() if recommend != 0 else 0.0  # 推荐单量金额
        recommend_fee = recommend_case['recommend_fee'].sum() if recommend !=0 else 0.0#中介费用
        return recommend_num_entire,recommend_num_new,recommend,recommend_amount,recommend_fee



    #总览统计函数
    def index_stactic(self,date_frame,data_name,que,date_index,case_frame=None,is_index=False,is_detail=False):
        if not date_frame.empty:
            statistic_data,apply = self.fundamental_data_excute(date_frame,date_index,data_name)

            if is_index:#如果是主统计表
                statistic_data,case_frame = self.index_data_excute(apply,statistic_data,case_frame)
                if is_detail:#如果是详细统计表(详细信息表需要主统计表数据)
                    statistic_data = self.detail_data_execute(date_frame,statistic_data,case_frame)
        else:
            statistic_data = self.none_data
            statistic_data['date'],statistic_data['data_name']=date_index,data_name
        que.put(statistic_data)
        return que

    def fundamental_data_excute(self,table,date_index,data_name):

        apply, jinjian,apply_success,apply_su_num = self.apply_info(table)
        loan_amount, hetong, fangkuan = self.loan_info(table)
        yuqi, yuqi_amount, index_waicui, waicui_amount = self.overtime_info(table)
        principal_rate, interest_rate, fee_rate = self.payment_info(table)

        statistic_data = {'date': date_index, 'data_name': data_name,
                          'jinjian': jinjian, 'hetong': hetong, 'loan': '%.2f' % fangkuan, 'overtime': yuqi,
                          'overtime_amount': '%.2f' % yuqi_amount, 'waicui_amount': '%.2f' % waicui_amount,
                          'principal_rate': '%.2f%%' % (principal_rate * 100),
                          'interest_rate': '%.2f%%' % (interest_rate * 100),
                          'fee_rate': '%.2f%%' % (fee_rate * 100), 'waicui': index_waicui}
        return statistic_data,apply

    def index_data_excute(self,limit,statistic_data,case_frame):
        case_id_list = list(set(limit['case_id']))  # case_id_list
        case_frame = case_frame[case_frame['case_id'].isin(case_id_list)]

        case_num=len(case_frame)
        new = len(case_frame[case_frame['is_renew_case']==0])
        renew = case_num - new
        recommend_case = case_frame[~case_frame['recommend_name'].isnull()]
        recommend = len(recommend_case)#推荐单量
        recommned_amount = recommend_case['amount'].sum() if recommend!=0 else 0.0#推荐单量金额
        ontime = len(case_frame[case_frame['status_code']=='A2'])
        advance = len(case_frame[case_frame['status_code']=='A3'])

        statistic_data['new'],statistic_data['renew'],statistic_data['recommend'],statistic_data['ontime'],statistic_data['advance'],statistic_data['recommend_amount']=\
        new,renew,recommend,ontime,advance,'%.2f'%float(recommned_amount)
        return statistic_data,case_frame

    def detail_data_execute(self,table,statistic_data,case_frame):

        def goods_num(case_frame):
            goods = 0#有效单量
            for case in case_frame['status']:
                if case[3] >= 4 and case[10] == 0:
                    goods += 1
            return goods

        if not table.empty:
            apply, jinjian, apply_success, apply_su_num = self.apply_info(table)
            approve_num, approve_success_num, approve_dely,approve_retry = self.approve_info(table)
            goods = goods_num(case_frame)
        else:
            apply, jinjian, apply_success, apply_su_num =0,0,0,0
            approve_num, approve_success_num, approve_dely, approve_retry = 0,0,0,0
            goods= 0

        statistic_data['apply_pass'],statistic_data['apply_rely'],statistic_data['approve_pass'],statistic_data['approve_rate'] = apply_su_num,'%.2f'%((jinjian-apply_su_num)/jinjian if jinjian else 0.0),approve_success_num,'%.2f'%(approve_success_num/approve_num if approve_num else 0.0)
        statistic_data['goods']=goods

        return statistic_data


    #门店基本信息统计计算
    def detail_by_shop(self,table,date_index,data_name,case_frame):
        if not table.empty:
            statistic_data, apply = self.fundamental_data_excute(table, date_index, data_name)
            statistic_data,case_frame = self.index_data_excute(apply, statistic_data,case_frame)
            statistic_data = self.detail_data_execute(table, statistic_data, case_frame)
        else:
            statistic_data = self.none_data
            statistic_data['date'], statistic_data['data_name'] = date_index, data_name
        return statistic_data

    #门店催收信息统计计算
    def cuishou_by_shop(self,table,date_index,data_name):
        if not table.empty:
            overtime_amount, overtime_num, waicui_num, waicui_amount, overtime_rate,\
            diancui_waicui_rate, waicui_end_num, waicui_end_amount,waicui_rate,waicui_amount_rate=self.cuishou_info(table)
            statistic_data = {'date':date_index,'data_name':data_name,'overtime_amount':'%.2f'%float(overtime_amount),'overtime_num':overtime_num,
                              'waicui_num':waicui_num,'waicui_amount':'%.2f'%waicui_amount,'overtime_rate':'%.2f'%overtime_rate,'diancui_waicui_rate':'%.2f'%diancui_waicui_rate,
                              'waicui_end_num':waicui_end_num,'waicui_end_amount':'%.2f'%waicui_end_amount,'waicui_rate':'%.2f'%waicui_rate}
        else:
            statistic_data = {'date':date_index,'data_name':data_name,'overtime_amount':'%.2f'%0.0,'overtime_num':0,
                              'waicui_num':0,'waicui_amount':'%.2f'%0.0,'overtime_rate':'%.2f'%0.0,'diancui_waicui_rate':'%.2f'%0.0,
                              'waicui_end_num':0,'waicui_end_amount':'%.2f'%0.0,'waicui_rate':'%.2f'%0.0}
        return statistic_data

    def approve_by_person(self,table,date_index,data_name):
        if not table.empty:
            overtime_amount, overtime_num, waicui_num, waicui_amount, overtime_rate, \
            diancui_waicui_rate, waicui_end_num, waicui_end_amount, waicui_rate,waicui_amount_rate = self.cuishou_info(table)
            approve_num, approve_success_num, approve_dely,approve_retry = self.approve_info(table)
            statistic_data = {
                'date':date_index,'data_name':data_name,'approve_num':approve_num,'approve_success_num':approve_success_num,'approve_dely':approve_dely,
                'exhaust_time_mean':None,'waicui_num':waicui_num,'waicui_amount':'%.2f'%waicui_amount,'waicui_rate':'%.2f'%waicui_rate,
                'waicui_amount_rate':'%.2f'%waicui_amount_rate,'overtime_num':overtime_num,'overtime_rate':'%.2f'%overtime_rate}
        else:
            statistic_data = {
                'date': date_index, 'data_name': data_name, 'approve_num': 0,
                'approve_success_num': 0,'approve_dely':0,
                'exhaust_time_mean': None, 'waicui_num': 0,
                'waicui_amount': '%.2f' % 0.0, 'waicui_rate': '%.2f' % 0.0,
                'waicui_amount_rate': '%.2f'%0.0, 'overtime_num': 0, 'overtime_rate': '%.2f'%0.0}
        return statistic_data

    def recommend_by_shop(self,table,start_date,date_index,data_name):
        if not table.empty:
            recommend_num_entire, recommend_num_new, recommend, recommend_amount, recommend_fee = self.recommned_info(table,start_date)
            overtime_amount, overtime_num, waicui_num, waicui_amount, overtime_rate, \
            diancui_waicui_rate, waicui_end_num, waicui_end_amount, waicui_rate, waicui_amount_rate = self.cuishou_info(table)
            principal_rate, interest_rate, fee_rate = self.payment_info(table)
            statistic_data ={ 'date':date_index,'data_name':data_name,'recommend_num_entire':recommend_num_entire,'recommend_num_new':recommend_num_new,
                              'recommend':recommend,'recommend_amount':'%.2f'%recommend_amount,'recommend_fee':'%.2f'%recommend_fee,'overtime_num':overtime_num,
                              'overtime_amount':'%.2f'%overtime_amount,'waicui_num':waicui_num,'waicui_amount':"%.2f"%waicui_amount,'principal_rate':'%.2f'%principal_rate
                              }
        else:
            statistic_data = {'date': date_index, 'data_name': data_name, 'recommend_num_entire': 0,
                              'recommend_num_new': 0,
                              'recommend': 0, 'recommend_amount': '%.2f' % 0.0,
                              'recommend_fee': '%.2f' % 0.0, 'overtime_num': 0,
                              'overtime_amount': '%.2f' % 0.0, 'waicui_num':0,'waicui_amount': "%.2f" % 0.0,
                              'principal_rate': '%.2f' % 0.0
                              }
        return statistic_data

    def apply_by_shop(self,table,date_index,data_name):
        if not table.empty:
            apply, jinjian, apply_success,apply_su_num = self.apply_info(table)
            cases = set(apply_success['case_id'])
            approve_events = self.date_frame[(self.date_frame['behave'] == '复审审批') & (self.date_frame['case_id'].isin(cases))]
            approve_num, approve_success_num, approve_dely,approve_retry = self.approve_info(approve_events)
            overtime_amount, overtime_num, waicui_num, waicui_amount, overtime_rate, \
            diancui_waicui_rate, waicui_end_num, waicui_end_amount, waicui_rate, waicui_amount_rate = self.cuishou_info(approve_events)
            statistic_data={'date':date_index,'data_name':data_name,'jinjian':jinjian,'apply_su_num':apply_su_num,'approve_success_num':approve_success_num,
                            'approve_dely_rate':'%.2f'%(approve_dely/approve_num if approve_num else 0.0),'approve_rate':'%.2f'%(approve_success_num/apply_su_num if apply_su_num else 0.0),
                            'waicui_num':waicui_num,'waicui_amount':'%.2f'%waicui_amount,'approve_retry':approve_retry,'approve_retry_rate':'%.2f'%(approve_retry/apply_su_num if apply_su_num else 0.0)
            }
        else:
            statistic_data={'date':date_index,'data_name':data_name,'jinjian':0,'apply_su_num':0,'approve_success_num':0,
                            'approve_dely_rate':'%.2f'%0.0,'approve_rate':'%.2f'%0.0,'waicui_num':0,'waicui_amount':'%.2f'%0.0,
                            'approve_retry':0,'approve_retry_rate':'%.2f'%0.0}

        return statistic_data







