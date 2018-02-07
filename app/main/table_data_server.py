#!/usr/bin/python
# -*- coding: UTF-8 -*-
from .mongo_service import Case,CaseLogs
from .. import red
from .backserver import CaseInfoList,DateStrToDate,log_datelist
import datetime,json
import numpy as np
import pandas as pd
from mongoengine.queryset.visitor import Q
from collections import defaultdict

#表格处理函数
class TableExcute():
    def load_logs_message(self,start_date,end_date):
        logs_date_list = log_datelist(start_date,end_date)
        date_frame = pd.DataFrame()
        for date_list in logs_date_list:
            date_frame.append(pd.read_msgpack(red.get(date_list)))
        return date_frame



    def CaseLogGet(self,start_date,end_date):
        def CaseLog_DicToList(event,shop_reflect):
            message = ' / '.join(info + ':' + str(event['message'][info]) for info in event['message']) if isinstance(
                event['message'], dict) else event['message']
            event_list = [event['date'].strftime('%Y-%m-%d %H:%M:%S'), event['case_id'], event['behave'],
                          event['manipulator'], shop_reflect[str(event['shop_id'])], message]
            return event_list

        start_date = DateStrToDate(start_date)
        shop_reflect = json.loads(red.get('shop_data').decode())
        end_date = DateStrToDate(end_date,hour=23,minute=59,seconds=59)
        logs = CaseLogs.objects(Q(date__gte=start_date) & Q(date__lte=end_date)).all()
        stactic = list(CaseLog_DicToList(event,shop_reflect) for log in logs
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

    def Statistic_index(self,statistic_date,statistic_date_end,compare_date,compare_date_end,shop_get):
        statistic_date = DateStrToDate(statistic_date)
        statistic_end_date  = DateStrToDate(statistic_date_end,hour=23,minute=59,seconds=59)
        compare_date = DateStrToDate(compare_date)
        compare_end_date = DateStrToDate(compare_date_end,hour=23,minute=59,seconds=59)
        if int(shop_get) == 0 or not shop_get:
            shop_ids = [i for i in range(2,24)]
        else:shop_ids = [int(shop_get)]
        case_data = pd.read_msgpack(red.get('case_data'))
        payment_logs = pd.read_msgpack(red.get('payment_logs'))
        data_execute = Data_Execute()

        statistic_data = case_data[(case_data['apply_date']>=statistic_date)&(case_data['apply_date']<statistic_end_date)&(case_data['shop_id'].isin(shop_ids))]
        statistic_compare = case_data[(case_data['apply_date']>=compare_date)&(case_data['apply_date']<compare_end_date)&(case_data['shop_id'].isin(shop_ids))]

        payment_data = payment_logs[(payment_logs['date']>=statistic_date)&(payment_logs['date']<statistic_end_date)&(payment_logs['shop_id'].isin(shop_ids))]
        payment_compare = payment_logs[(payment_logs['date']>=compare_date)&(payment_logs['date']<compare_end_date)&(payment_logs['shop_id'].isin(shop_ids))]

        statistic = data_execute.index_stactic(statistic_data,1,statistic_date.strftime('%Y-%m-%d'),index=True,payment_logs=payment_data)
        compare = data_execute.index_stactic(statistic_compare,2,compare_date.strftime('%Y-%m-%d'),index=True,payment_logs=payment_compare)
        result_list = [statistic,compare]
        return result_list



    def Statistic_detail(self,start_date,end_date,type,shop_get):
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date)
        case_data = pd.read_msgpack(red.get('case_data'))
        if int(shop_get) == 0 or not shop_get:
            shop_ids = [i for i in range(2, 24)]
        else:
            shop_ids = [int(shop_get)]
        limit_frame = case_data[case_data['shop_id'].isin(shop_ids)]


        data_excute = Data_Execute()
        result_list = []

        if int(type) == 1:#按日统计
            i=0
            while start_date<=end_date:
                start_date_end = start_date+datetime.timedelta(days=1)
                date_data = limit_frame[(limit_frame['apply_date']>=start_date)&(limit_frame['apply_date']<start_date_end)]
                statistic_data = data_excute.index_stactic(date_frame=date_data,data_name=i,date_index=start_date.strftime("%Y-%m-%d"))
                result_list.append(statistic_data)
                i+=1
                start_date+=datetime.timedelta(days=1)

        elif int(type) == 7:#按周统计
            i = 0
            while start_date<=end_date:
                start_date_end = min(start_date + datetime.timedelta(days=7),end_date)
                date_data = limit_frame[(limit_frame['apply_date'] >= start_date) & (limit_frame['apply_date'] < start_date_end)]
                statistic_data = data_excute.index_stactic(date_frame=date_data, data_name=i,date_index="%s/%s"%(start_date.strftime("%Y-%m-%d"),start_date_end.strftime("%m-%d")))
                result_list.append(statistic_data)
                i += 1
                start_date += datetime.timedelta(days=7)


        else: #按月统计
            i = 0

            date_list = log_datelist(start_date, end_date)
            for date in date_list:
                start = datetime.datetime(date[0], date[1], 1)
                if date[1]!=12:
                    end = datetime.datetime(date[0], date[1] + 1, 1) - datetime.timedelta(days=1)
                else:
                    end = datetime.datetime(date[0],12,31)
                date_data = limit_frame[(limit_frame['apply_date'] >= start) & (limit_frame['apply_date'] < end)]
                statistic_data = data_excute.index_stactic(date_frame=date_data,data_name=i,date_index="%s/%s"%(start.strftime("%Y-%m-%d"),end.strftime("%m-%d")))
                result_list.append(statistic_data)
                i += 1

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
                              'goods':0,'merit_pay':'%.2f'%0.0}
            return new_none_data

        shop_reflect=json.loads(red.get('shop_data').decode())

        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date,23,59,59)
        case_data = pd.read_msgpack(red.get('case_data'))
        payment_logs = pd.read_msgpack(red.get('payment_logs'))
        data = case_data[(case_data['apply_date']>=start_date)&(case_data['apply_date']<end_date)]
        payment_limit = payment_logs[(payment_logs['date']>=start_date)&(payment_logs['date']<end_date)]

        shop_list = set(data['shop_id'].dropna(how='any'))
        data_excute = Data_Execute()
        result_dict = defaultdict(list)
        result_list = []
        date_index = "%s/%s"%(start_date.strftime('%Y-%m-%d'),end_date.strftime('%m-%d'))

        for shop in shop_list:

            shop_data = data_excute.detail_by_shop(date_frame=data[data['shop_id']==shop],payment_logs=payment_limit[payment_limit['shop_id']==shop],date_index=date_index,data_name=shop)
            shop_data['data_name']=shop_reflect[str(shop)]
            result_dict[int(shop)]=shop_data

        for shop_id in shop_reflect:
            if not result_dict[int(shop_id)]:
                result_list.append(shop_none_data(shop_reflect[shop_id],date_index))
            else:
                result_list.append(result_dict[int(shop_id)])

        return result_list

    #催收表处理
    def cuishou_by_shop(self,start_date,end_date,shop_get):
        def cuishou(shop_name,date):
            none_data ={'date': date, 'data_name': shop_name, 'overtime_amount': '%.2f' % 0.0, 'overtime_num': 0,
             'waicui_num': 0, 'waicui_amount': '%.2f' % 0.0, 'overtime_rate': '%.2f%%' % 0.0,
             'diancui_waicui_rate': '%.2f%%' % 0.0,
             'waicui_end_num': 0, 'waicui_end_amount': '%.2f' % 0.0,'waicui_rate':'%.2f%%'%0.0}
            return none_data

        shop_reflect = json.loads(red.get('shop_data').decode())
        if int(shop_get) == 0 or not shop_get:
            shop_ids = [int(i) for i in shop_reflect.keys()]
        else:
            shop_ids = [int(shop_get)]
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date)
        case_data = pd.read_msgpack(red.get('case_data'))

        result_list = []
        date_index = "%s/%s" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%m-%d'))

        data = case_data[(case_data['apply_date'] >= start_date) & (case_data['apply_date'] <= end_date)]
        data_excute = Data_Execute()

        for shop in shop_ids:
            shop_data = data_excute.cuishou_by_shop(table=data[data['shop_id']==shop],date_index=date_index,data_name=shop)
            shop_data['data_name']=shop_reflect[str(shop)]
            result_list.append(shop_data)
        return result_list

    #复审表处理
    def fushen_by_person(self,start_date,end_date):
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date,hour=23,minute=59,seconds=59)
        case_data = pd.read_msgpack(red.get('case_data'))

        data = case_data[(case_data['apply_date'] >= start_date) & (case_data['apply_date'] < end_date)]
        data_excute = Data_Execute()
        approvers = set(data['approve_approver'].dropna(how='any').tolist())
        date_index = "%s/%s" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%m-%d'))
        result_list = []


        for approver in approvers:
            table = data[data['approve_approver']==approver]
            statistic_data=data_excute.approve_by_person(table,date_index=date_index,data_name=approver)
            result_list.append(statistic_data)
        return result_list

    def apply_by_shop(self,start_date,end_date,shop_ids=None):
        shop_reflect = json.loads(red.get('shop_data').decode())
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date, hour=23, minute=59, seconds=59)
        if int(shop_ids) == 0 or not shop_ids:
            shop_ids = [int(i) for i in shop_reflect.keys()]
        else:shop_ids = [int(shop_ids)]

        case_data = pd.read_msgpack(red.get('case_data'))
        data = case_data[(case_data['apply_date'] >= start_date) & (case_data['apply_date'] < end_date)&(case_data['shop_id'].isin(shop_ids))]
        data_excute = Data_Execute()
        date_index = "%s/%s" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%m-%d'))
        result_list = []


        apply_approvers = set(data['apply_approver'].dropna(how='any'))

        for apply_approver in apply_approvers:
            apply_by_person = data[data['apply_approver'] == apply_approver]
            statistic_data = data_excute.apply_by_shop(apply_by_person,date_index=date_index,data_name=apply_approver)
            statistic_data['shop_name'] = shop_reflect[str(list(set(apply_by_person['shop_id']))[0])]
            result_list.append(statistic_data)
        return result_list


    #中介信息
    def recommend_by_shop(self,start_date,end_date):
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date, hour=23, minute=59, seconds=59)
        case_data = pd.read_msgpack(red.get('case_data'))
        payment_logs = pd.read_msgpack(red.get('payment_logs'))
        shop_reflect = json.loads(red.get('shop_data').decode())
        result_list = []

        data = case_data[case_data['apply_date'] <= end_date]
        payment_limit = payment_logs[(payment_logs['date'] >= start_date) & (payment_logs['date'] < end_date)]

        data_excute = Data_Execute()
        date_index = "%s/%s" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%m-%d'))

        for shop_id in shop_reflect:
            shop_data = data_excute.recommend_by_shop(table=data[data['shop_id'] == int(shop_id)],payment_logs=payment_limit[payment_limit['shop_id']==int(shop_id)],date_index=date_index,data_name=shop_reflect[str(shop_id)],start_date=start_date)
            result_list.append(shop_data)
        return result_list

    #业务员表格
    def saler_by_shop(self,start_date,end_date,shop_ids=None):
        start_date = DateStrToDate(start_date)
        end_date = DateStrToDate(end_date, hour=23, minute=59, seconds=59)
        shop_reflect = json.loads(red.get('shop_data').decode())
        if int(shop_ids) == 0 or not shop_ids:
            shop_ids = [int(i) for i in shop_reflect.keys()]
        else:shop_ids = [int(shop_ids)]

        case_data = pd.read_msgpack(red.get('case_data'))
        data = case_data[(case_data['apply_date'] >= start_date) & (case_data['apply_date'] < end_date) & (
        case_data['shop_id'].isin(shop_ids))]
        data_excute = Data_Execute()
        date_index = "%s/%s" % (start_date.strftime('%Y-%m-%d'), end_date.strftime('%m-%d'))
        result_list = []
        salers = set(data['sale_name'].dropna(how='any'))

        for saler in salers:
            saler_data = data[data['sale_name']==saler]
            statistic_data = data_excute.saler_by_shop(saler_data,date_index,saler)
            saler_shop_id = list(set(saler_data['shop_id']))
            if saler_shop_id!=[]:
                statistic_data['shop_name'] = shop_reflect[str(saler_shop_id[0])]
            else:
                statistic_data['shop_name'] = "无门店"
            result_list.append(statistic_data)
        return result_list



    def merit_by_person(self,method_dic):
        case_data = pd.read_msgpack(red.get('case_data'))
        shop_reflect = json.loads(red.get('shop_data').decode())
        result_list = []
        shop_id = method_dic['shop_id']
        if int(shop_id) == 0:
            shop_ids = [int(i) for i in shop_reflect.keys()]
        else:
            shop_ids = [int(shop_id)]
        case_data_in_shops = case_data[case_data['shop_id'].isin(shop_ids)]
        rules = method_dic['rules']
        data_execute = Data_Execute()

        sale_names = set(case_data_in_shops['sale_name'].dropna(how='any'))
        for sale_name in sale_names:
            data_by_person = case_data_in_shops[case_data_in_shops['sale_name']==sale_name]
            person_shop_id_list = list(set(data_by_person['shop_id']))
            person_shop_id = person_shop_id_list[0]
            person_list = data_execute.merit_by_sale_name(data_by_person,sale_name,rules,shop_reflect[str(person_shop_id)])
            result_list += person_list
        return result_list




#========================================================================================


#数据统计函数
class Data_Execute:

    #进件计算
    def apply_info(self,table):
        jinjian = len(table)  # 进件数
        apply_success = table[table['apply_result'] == '通过']
        apply_su_num = len(apply_success)#批件数

        return jinjian,apply_success,apply_su_num

    #放款计算
    def loan_info(self,table):
        loan_amount = table['loan_amount'].sum()  # 放款总额
        hetong = len(table)  # 放款合同数
        recommend_cases = table[~table['recommend_name'].isnull()]
        recommend_num = len(recommend_cases)  # 推荐单量
        recommend_amount = recommend_cases['loan_amount'].sum() if recommend_num!=0 else 0.0 # 推荐放款量
        return loan_amount, hetong,recommend_num,recommend_amount

    #逾期计算
    def overtime_info(self,table):
        overtime_cases = table[table['overtime'] > 0]
        overtime_num = len(overtime_cases)  # 逾期数

        waicui_num = len(overtime_cases[overtime_cases['waicui_ternors'] != ()])
        diancui_amount = overtime_cases['diancui_amount'].sum()
        waicui_amount = overtime_cases['waicui_amount'].sum() if waicui_num!=0 else 0.0
        overtime_amount = diancui_amount + waicui_amount  # 逾期款数

        return overtime_num, overtime_amount, waicui_num, waicui_amount

    #到期计算
    def payment_info(self,table):
        payment_data = table
        if not payment_data.empty:
            principal_rate = payment_data['本期已还本金'].sum() / payment_data['本期应还本金'].sum()  # 本金还款率
            interest_rate = payment_data['本期已还利息'].sum() / payment_data['本期应还利息'].sum()  # 利息还款率
            fee_rate = payment_data['本期已还费用'].sum() / payment_data['本期应还费用'].sum()  # 费用还款率
        else:
            principal_rate, interest_rate, fee_rate = 0.0, 0.0, 0.0
        return principal_rate, interest_rate, fee_rate

    #催收计算
    def cuishou_info(self,table):
        diancui_num = len(table[table['diancui_ternors'] != ()])
        diancui_waicui_rate = len(table[(table['diancui_ternors'] != ()) & (table['waicui_ternors'] != ())]) / diancui_num if diancui_num else 0.0#电催外催转化率

        f = lambda x: True if x['status'][10] >= 1 and x['status'][-1] == 1 else False
        waicui_end_cases = table[table.apply(f, axis=1)]
        waicui_end_num = len(waicui_end_cases)#外催结清单量
        waicui_end_amount = waicui_end_cases['amount'].sum()#外催结清合同额
        return diancui_waicui_rate,waicui_end_num,waicui_end_amount

    #复审信息计算
    def approve_info(self,table):
        approve_cases = table[~table['approve_date'].isnull()]
        approve_num = len(approve_cases)
        approve_success_cases = approve_cases[approve_cases['approve_result'].str.contains('通过') == True]
        approve_success_num = len(approve_success_cases)
        approve_dely = approve_num - approve_success_num
        approve_retry = len(approve_cases[approve_cases['approve_result'] == '退单通过'])
        return approve_num,approve_success_num,approve_dely,approve_retry

    #中介单信息
    def recommned_info(self,table,start_date):
        recommend_num_entire = len(set(table['recommend_name'].dropna(how='any')))
        table_new = table[table['apply_date'] >= start_date]
        recommend_num_new = len(set(table_new['recommend_name'].dropna(how='any')))
        recommend_fee = table_new['recommend_fee'].sum()
        return recommend_num_entire,recommend_num_new,recommend_fee

    def case_classify(self,table):
        renew_num = len(table[table['is_renew_case'] == 1])
        ontime_num = len(table[table['status_code'] == 'A2'])
        advance_num = len(table[table['status_code'] == 'A3'])
        return  renew_num,ontime_num,advance_num

    #有效单计算
    def goods_num(self,case_frame,limit,is_waicui_valid=False):
        if not is_waicui_valid:
            f1 = lambda x : 1 if x[3]>=limit and x[10] == 0 else 0
        else:
            f1 = lambda x: 1 if x[3]>= limit else 0
        case_frame['is_goods'] = case_frame['status'].apply(f1)
        goods_cases = case_frame[case_frame['is_goods'] == 1]
        goods = len(goods_cases)
        goods_loan_amount = goods_cases['loan_amount'].sum() if goods != 0 else 0.0
        return goods,goods_loan_amount

    #绩效计算
    def merit_pay_figure(self,personal_data,rule):
        start_date = DateStrToDate(rule['start_date'])
        end_date = DateStrToDate(rule['end_date'], 23, 59, 59)
        date_index = "%s/%s"%(start_date.strftime("%Y-%m-%d"),end_date.strftime("%m-%d"))
        if not personal_data.empty:
            time_limit_data = personal_data[(personal_data['apply_date']>=start_date)&(personal_data['apply_date']<end_date)]
            method = rule['method']
            rule_info = rule['method_info']
            if method == 'by_goods':
                merit_dict = self.figure_merit_by_goods(time_limit_data,rule_info)
            elif method == 'by_loanamount':
                merit_dict = self.figure_merit_by_loan_amount(time_limit_data,rule_info)
            elif method == "by_num":
                merit_dict = self.figure_merit_by_num(time_limit_data,rule_info)
            else:
                merit_dict = {'goods': 0, 'merit_pay': 0.0}
        else:
            merit_dict= {'goods':0,'merit_pay':0.0}
        merit_dict['date_index']=date_index
        return merit_dict

    def figure_merit_by_goods(self,time_limit_data,rule_info):
        if not time_limit_data.empty:
            limit = rule_info['limit']
            is_waicui_vaild = True if int(rule_info['is_waicui_valid']) ==1 else False
            goods,goods_loan_amount = self.goods_num(time_limit_data,limit,is_waicui_vaild)
            loan_amount = time_limit_data['loan_amount'].sum()
            submethod = rule_info['submethod']
            merit_pay = 0.0
            sublimits = rule_info['sublimit']
            subrules = rule_info['subrule']
            if submethod == 'stage':
                for i in range(len(sublimits)-1):
                    merit_pay += min(max(goods - sublimits[i],0),sublimits[i+1]-sublimits[i])*subrules[i]
            elif submethod  == "convert":
                for i in range(len(sublimits)-1):
                    if goods<=float(sublimits[i + 1]):
                        subrule = subrules[i]
                        merit_pay = self.subrule_figure(time_limit_data,subrule,goods=goods,goods_loan_amount=goods_loan_amount,loan_amount=loan_amount)
                        break
            else:merit_pay =0.0
        else:goods,merit_pay,goods_loan_amount,loan_amount = 0,0.0,0.0,0.0
        return {'goods':goods,'merit_pay':merit_pay,'goods_loan_amount':goods_loan_amount,'loan_amount':loan_amount}

    def figure_merit_by_loan_amount(self,time_limit_data,rule_info):
        if not time_limit_data.empty:
            limit = rule_info['limit']
            is_waicui_vaild = True if int(rule_info['is_waicui_valid']) == 1 else False
            goods, goods_loan_amount = self.goods_num(time_limit_data, limit, is_waicui_vaild)
            submethod = rule_info['submethod']
            loan_amount = time_limit_data['loan_amount'].sum()
            merit_pay = 0.0
            sublimits = rule_info['sublimit']
            subrules = rule_info['subrule']
            if submethod == 'stage':
                for i in range(len(sublimits) - 1):
                    merit_pay += min(max(loan_amount - sublimits[i], 0), sublimits[i + 1] - sublimits[i]) * subrules[i]
            elif submethod == "convert":
                for i in range(len(sublimits) - 1):
                    if loan_amount <= float(sublimits[i + 1]):
                        subrule = subrules[i]
                        merit_pay = self.subrule_figure(time_limit_data, subrule, goods=goods,goods_loan_amount=goods_loan_amount,loan_amount=loan_amount)
                        break
            else:merit_pay = 0.0
        else:goods, merit_pay, goods_loan_amount, loan_amount = 0, 0.0, 0.0, 0.0
        return {'goods': goods, 'merit_pay': merit_pay, 'goods_loan_amount': goods_loan_amount,
                    'loan_amount': loan_amount}

    def figure_merit_by_num(self,time_limit_data,rule_info):
        if not time_limit_data.empty:
            limit = rule_info['limit']
            is_waicui_vaild = True if int(rule_info['is_waicui_valid']) == 1 else False
            goods, goods_loan_amount = self.goods_num(time_limit_data, limit, is_waicui_vaild)
            loan_amount = time_limit_data['loan_amount'].sum()
            submethod = rule_info['submethod']
            num = len(time_limit_data)
            merit_pay = 0.0
            sublimits = rule_info['sublimit']
            subrules = rule_info['subrule']
            if submethod == 'stage':
                for i in range(len(sublimits) - 1):
                    merit_pay += min(max(num - sublimits[i], 0), sublimits[i + 1] - sublimits[i]) * subrules[i]
            elif submethod == 'convert':
                for i in range(len(sublimits) - 1):
                    if num <= float(sublimits[i + 1]):
                        subrule = subrules[i]
                        merit_pay = self.subrule_figure(time_limit_data,subrule,goods=goods,goods_loan_amount=goods_loan_amount,loan_amount=loan_amount)
                        break
            else:merit_pay = 0.0
        else:goods, merit_pay, goods_loan_amount, loan_amount = 0, 0.0, 0.0, 0.0
        return {'goods': goods, 'merit_pay': merit_pay, 'goods_loan_amount': goods_loan_amount,
                    'loan_amount': loan_amount}

    def subrule_figure(self,table,subrule,goods=0,goods_loan_amount=0,loan_amount=0):
        type_by = subrule['by']
        if not table.empty:
            if type_by == 'num':
                num = len(table)
                merit = num * float(subrule['data'])
            elif type_by == 'loan_amount':
                merit = loan_amount * float(subrule['data'])
            elif type_by == 'goods':
                merit = goods * float(subrule['data'])
            elif type_by == 'goods_loan':
                merit = goods_loan_amount *float(subrule['data'])
            else:merit = 0.0
        else:
            merit = 0.0
        return merit

    #总览统计函数
    def index_stactic(self,date_frame,data_name,date_index,index=False,payment_logs=None):
        if not date_frame.empty:
            jinjian, apply_success, apply_su_num = self.apply_info(date_frame)
            approve_num, approve_success_num, approve_dely, approve_retry = self.approve_info(date_frame)
            overtime_num, overtime_amount, waicui_num, waicui_amount = self.overtime_info(date_frame)
            loan_amount, hetong, recommend_num, recommend_amount = self.loan_info(date_frame)
            renew_num, ontime_num, advance_num = self.case_classify(date_frame)
            goods = self.goods_num(date_frame,5)

            if index:
                principal_rate, interest_rate, fee_rate = self.payment_info(payment_logs)
                diancui_waicui_rate, waicui_end_num, waicui_end_amount = self.cuishou_info(date_frame)
            else:
                principal_rate, interest_rate, fee_rate = 0.0,0.0,0.0
                diancui_waicui_rate, waicui_end_num, waicui_end_amount = 0.0,0,0.0

            statistic_data = {'date': date_index, 'data_name': data_name,
                              'jinjian': jinjian, 'hetong': hetong, 'loan': '%.2f' % loan_amount, 'overtime': overtime_num,
                              'overtime_amount': '%.2f' % overtime_amount, 'waicui_amount': '%.2f' % waicui_amount,
                              'principal_rate': '%.2f%%' % (principal_rate * 100), 'interest_rate': '%.2f%%' % (interest_rate *100),
                              'fee_rate': '%.2f%%' % (fee_rate * 100), 'new': approve_success_num-renew_num, 'renew': renew_num, 'recommend': recommend_num, 'ontime': ontime_num,
                              'advance': advance_num, 'waicui': waicui_num, 'apply_pass': apply_su_num,
                              'apply_rely': "%.2f%%"%((jinjian - apply_su_num)/jinjian*100 if jinjian!=0 else 0.0), 'approve_pass': approve_success_num,
                              'approve_rate': "%.2f%%"%(approve_success_num/approve_num*100 if approve_num!=0 else 0.0),
                              'recommend_amount': '%.2f'%(recommend_amount),
                              'goods': goods,'waicui_end_num':waicui_end_num}
        else:
            statistic_data = {'date':date_index,'data_name':data_name,
                'jinjian': 0, 'hetong': 0, 'loan': '%.2f' % 0, 'overtime': 0,
                'overtime_amount': '%.2f' % 0, 'waicui_amount': '%.2f' % 0,
                'principal_rate': '%.2f%%' % (0 * 100), 'interest_rate': '%.2f%%' % (0),
                'fee_rate': '%.2f%%' % (0 * 100),'new':0,'renew':0,'recommend':0,'ontime':0,'advance':0,'waicui':0,'apply_pass':0,
                              'apply_rely':'0.00%','approve_pass':0,'approve_rate':'0.00%','recommend_amount':'0.00',
                              'goods':0,'waicui_end_num':0}
            statistic_data['date'],statistic_data['data_name']=date_index,data_name

        return statistic_data



    #门店基本信息统计计算
    def detail_by_shop(self,date_frame,payment_logs,date_index,data_name):
        if not date_frame.empty:
            jinjian, apply_success, apply_su_num = self.apply_info(date_frame)
            overtime_num, overtime_amount, waicui_num, waicui_amount = self.overtime_info(date_frame)
            approve_num, approve_success_num, approve_dely, approve_retry = self.approve_info(date_frame)
            loan_amount, hetong, recommend_num, recommend_amount = self.loan_info(date_frame)
            principal_rate, interest_rate, fee_rate = self.payment_info(payment_logs)
            renew_num, ontime_num, advance_num = self.case_classify(date_frame)
            goods = self.goods_num(date_frame, 5)

            statistic_data = {'date': date_index, 'data_name': data_name,
                              'jinjian': jinjian, 'hetong': hetong, 'loan': '%.2f' % loan_amount, 'overtime': overtime_num,
                              'overtime_amount': '%.2f' % overtime_amount, 'waicui_amount': '%.2f' % waicui_amount,
                              'principal_rate': '%.2f%%' % (principal_rate * 100), 'interest_rate': '%.2f%%' % (interest_rate*100),
                              'fee_rate': '%.2f%%' % (fee_rate * 100), 'new': approve_success_num-renew_num, 'renew': renew_num, 'recommend': recommend_num, 'ontime': ontime_num,
                              'advance': advance_num, 'waicui': waicui_num, 'apply_pass': apply_su_num,
                              'apply_rely': "%.2f%%"%((jinjian - apply_su_num)/jinjian*100 if jinjian!=0 else 0.0),
                              'approve_pass': approve_success_num,
                              'approve_rate': "%.2f%%"%(approve_success_num/approve_num*100 if approve_num!=0 else 0.0),
                              'recommend_amount': "%.2f"%recommend_amount,
                              'goods': goods,'merit_pay':'%.2f'%0.0}
        else:
            statistic_data = {'date':date_index,'data_name':data_name,
                'jinjian': 0, 'hetong': 0, 'loan': '%.2f' % 0, 'overtime': 0,
                'overtime_amount': '%.2f' % 0, 'waicui_amount': '%.2f' % 0,
                'principal_rate': '%.2f%%' % (0 * 100), 'interest_rate': '%.2f%%' % (0),
                'fee_rate': '%.2f%%' % (0 * 100),'new':0,'renew':0,'recommend':0,'ontime':0,'advance':0,'waicui':0,'apply_pass':0,
                              'apply_rely':'0.00%','approve_pass':0,'approve_rate':'0.00%','recommend_amount':'0.00',
                              'goods':0,'merit_pay':'%.2f'%0.0}
            statistic_data['date'], statistic_data['data_name'] = date_index, data_name
        return statistic_data

    #门店催收信息统计计算
    def cuishou_by_shop(self,table,date_index,data_name):
        if not table.empty:
            approve_num, approve_success_num, approve_dely, approve_retry = self.approve_info(table)
            overtime_num, overtime_amount, waicui_num, waicui_amount = self.overtime_info(table)
            diancui_waicui_rate, waicui_end_num, waicui_end_amount = self.cuishou_info(table)

            statistic_data = {'date':date_index,'data_name':data_name,'overtime_amount':'%.2f'%float(overtime_amount),'overtime_num':overtime_num,
                              'waicui_num':waicui_num,'waicui_amount':'%.2f'%waicui_amount,
                              'overtime_rate':'%.2f%%'%(overtime_num/approve_success_num*100 if approve_success_num else 0.0),
                              'diancui_waicui_rate':'%.2f%%'%(diancui_waicui_rate*100),
                              'waicui_end_num':waicui_end_num,'waicui_end_amount':'%.2f'%waicui_end_amount,
                              'waicui_rate':'%.2f%%'%(waicui_num/approve_success_num*100 if approve_success_num else 0.0)}
        else:
            statistic_data = {'date':date_index,'data_name':data_name,'overtime_amount':'%.2f'%0.0,'overtime_num':0,
                              'waicui_num':0,'waicui_amount':'%.2f'%0.0,'overtime_rate':'%.2f%%'%0.0,'diancui_waicui_rate':'%.2f%%'%0.0,
                              'waicui_end_num':0,'waicui_end_amount':'%.2f'%0.0,'waicui_rate':'%.2f%%'%0.0}
        return statistic_data

    def approve_by_person(self,table,date_index,data_name):
        if not table.empty:
            overtime_num, overtime_amount, waicui_num, waicui_amount = self.overtime_info(table)
            approve_num, approve_success_num, approve_dely,approve_retry = self.approve_info(table)
            loan_amount, hetong, recommend_num, recommend_amount = self.loan_info(table)
            statistic_data = {
                'date':date_index,'data_name':data_name,'approve_num':approve_num,'approve_success_num':approve_success_num,'approve_dely':approve_dely,
                'exhaust_time_mean':None,'waicui_num':waicui_num,'waicui_amount':'%.2f'%waicui_amount,
                'waicui_rate':'%.2f%%'%(waicui_num/approve_success_num*100 if approve_success_num else 0.0),
                'waicui_amount_rate':'%.2f%%'%(waicui_amount/loan_amount*100 if loan_amount else 0.0),'overtime_num':overtime_num,
                'overtime_rate':'%.2f%%'%(overtime_num/approve_success_num*100 if approve_success_num else 0.0)}
        else:
            statistic_data = {
                'date': date_index, 'data_name': data_name, 'approve_num': 0,
                'approve_success_num': 0,'approve_dely':0,
                'exhaust_time_mean': None, 'waicui_num': 0,
                'waicui_amount': '%.2f%%' % 0.0, 'waicui_rate': '%.2f' % 0.0,
                'waicui_amount_rate': '%.2f'%0.0, 'overtime_num': 0, 'overtime_rate': '%.2f'%0.0}
        return statistic_data

    def recommend_by_shop(self,table,payment_logs,start_date,date_index,data_name):
        if not table.empty:
            recommend_num_entire, recommend_num_new, recommend_fee = self.recommned_info(table,start_date)
            table_new = table[table['apply_date']>=start_date]
            table_new = table_new[~table_new['recommend_name'].isnull()]#只计算推荐单
            loan_amount, hetong, recommend_num, recommend_amount = self.loan_info(table_new)
            overtime_num, overtime_amount, waicui_num, waicui_amount = self.overtime_info(table_new)
            principal_rate, interest_rate, fee_rate = self.payment_info(payment_logs)

            statistic_data ={ 'date':date_index,'data_name':data_name,'recommend_num_entire':recommend_num_entire,'recommend_num_new':recommend_num_new,
                              'recommend':recommend_num,'recommend_amount':'%.2f'%recommend_amount,'recommend_fee':'%.2f'%recommend_fee,'overtime_num':overtime_num,
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
            jinjian, apply_success, apply_su_num = self.apply_info(table)
            approve_num, approve_success_num, approve_dely, approve_retry = self.approve_info(table)
            overtime_num, overtime_amount, waicui_num, waicui_amount = self.overtime_info(table)
            statistic_data={'date':date_index,'data_name':data_name,'jinjian':jinjian,'apply_su_num':apply_su_num,'approve_success_num':approve_success_num,
                            'approve_dely_rate':'%.2f'%(approve_dely/approve_num if approve_num else 0.0),'approve_rate':'%.2f'%(approve_success_num/apply_su_num if apply_su_num else 0.0),
                            'waicui_num':waicui_num,'waicui_amount':'%.2f'%waicui_amount,'approve_retry':approve_retry,'approve_retry_rate':'%.2f'%(approve_retry/apply_su_num if apply_su_num else 0.0),

            }
        else:
            statistic_data={'date':date_index,'data_name':data_name,'jinjian':0,'apply_su_num':0,'approve_success_num':0,
                            'approve_dely_rate':'%.2f'%0.0,'approve_rate':'%.2f'%0.0,'waicui_num':0,'waicui_amount':'%.2f'%0.0,
                            'approve_retry':0,'approve_retry_rate':'%.2f'%0.0}

        return statistic_data

    def saler_by_shop(self,table,date_index,data_name):
        if not table.empty:
            jinjian, apply_success, apply_su_num = self.apply_info(table)
            approve_num, approve_success_num, approve_dely, approve_retry = self.approve_info(table)
            overtime_num, overtime_amount, waicui_num, waicui_amount = self.overtime_info(table)
            statistic_data = {'date': date_index, 'data_name': data_name, 'jinjian': jinjian,
                              'apply_su_num': apply_su_num, 'approve_success_num': approve_success_num,
                              'approve_dely_rate': '%.2f' % (approve_dely / approve_num if approve_num else 0.0),
                              'approve_rate': '%.2f' % (approve_success_num / apply_su_num if apply_su_num else 0.0),
                              'waicui_num': waicui_num, 'waicui_amount': '%.2f' % waicui_amount,
                              'approve_retry': approve_retry,
                              'approve_retry_rate': '%.2f' % (approve_retry / apply_su_num if apply_su_num else 0.0),}
        else:
            statistic_data = {'date': date_index, 'data_name': data_name, 'jinjian': 0, 'apply_su_num': 0,
                              'approve_success_num': 0,
                              'approve_dely_rate': '%.2f' % 0.0, 'approve_rate': '%.2f' % 0.0, 'waicui_num': 0,
                              'waicui_amount': '%.2f' % 0.0,
                              'approve_retry': 0, 'approve_retry_rate': '%.2f' % 0.0}
        return statistic_data


    #业务员绩效
    def merit_by_sale_name(self,table,data_name,rules,shop_name):
        if not table.empty:
            statistic_list = []
            for rule in rules:
                merit_dic = self.merit_pay_figure(table,rule)
                merit_dic['data_name']=data_name
                merit_dic['shop_name']=shop_name
                statistic_list.append(merit_dic)
        else:
            statistic_list = []
        return statistic_list





