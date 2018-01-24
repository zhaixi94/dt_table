#!/usr/bin/python
# -*- coding: UTF-8 -*-

from app.main.sqlhelper import find_all_case,Find_all_verify_messege,Find_all_loan_message,Find_all_overtime_message,Find_all_daihuan_message,Find_all_inadvance_message,Find_all_refund_message,find_normal_cases,find_the_first_day
from app.models import Case,CaseLogs,ErrorLogs
from .sqlhelper import is_first_case
import datetime,time
import numpy as np
from mongoengine.queryset.visitor import Q
from collections import defaultdict
import threading
import pandas as pd


class MyMongo_executive(object):
    # 合同表生成函数
    def Case_init(self,start_date,end_date = datetime.datetime.now()):
        def struct_case(case):
            if not case['start_date']:  # 计算是否是首借单
                first_case_flag = 0
            else:
                first_case_flag = 0 if is_first_case(start_date=case['start_date'], customer_id=case['customer_id'])[
                                           'signFrequency'] <= 1 else 1

            newcase = Case()
            newcase.create_time = case['create_time']
            newcase.case_id = case['apply_sn']
            newcase.customer_id = case['customer_id']
            newcase.customer_name = case['customer_name']
            newcase.ic_number = case['ic_number']
            newcase.is_renew_case = first_case_flag
            newcase.amount = case['amount']
            newcase.start_date = case['start_date']
            newcase.end_date = case['end_date']
            newcase.case_tenor = case['tenor']
            newcase.sale_name = case['SALES_NAME']
            newcase.risk_manager_name = case['risk_manager_name']
            newcase.approver = case['approver']
            newcase.approve_time = case['approve_time']
            newcase.approve_status=None
            newcase.card_name = None
            newcase.shop_id = case['shop_id']
            newcase.plateform_fee = case['platform_fee']
            newcase.guarantor_fee = case['guarantor_fee']
            newcase.service_fee1 = case['service_fee1']
            newcase.service_fee2 = case['service_fee2']
            newcase.risk_fee = case['risk_fee']
            newcase.case_status = []
            newcase.status_code = case['status']
            newcase.recommend_name = case['real_name']
            newcase.recommend_fee = case['referral_fee']
            newcase.logs = {'chushen': [], 'fushen': [], 'loan': [], 'diancui': [], 'waicui': [], 'daihuan_apply': [],
                            'daihuan_approve': [], 'inadvance_apply': [], 'inadvance_approve': [], 'refund': [],
                            'end': [], 'payment': []}
            newcase.save()

        case_data = find_all_case(start_date=start_date, end_date=end_date)
        if case_data:
            thread_list = list(threading.Thread(target=struct_case,args=(case,)) for case in case_data)
            i = 1
            for thread in thread_list:
                thread.start()
                i+=1
                if i%50==0:time.sleep(3)

            for thread in thread_list:
                thread.join()


    #生成器返回
    def events_list_generator(self,events_generator):
        try:
            return events_generator.__next__()
        except StopIteration:
            return []

    # 合同日志表生成函数
    def CaseLog_inti_(self, start_date,end_date = datetime.datetime.now()):
        stop_date = end_date
        event_dict = defaultdict(dict)
        payment_dict = defaultdict(list)#payment需要更新所以单独处理
        verify_data = Find_all_verify_messege(start_date=start_date, end_date=end_date)#审核信息
        loan_data = Find_all_loan_message(start_date, end_date)#放款信息
        refund_data = Find_all_refund_message(start_date,end_date)#还款信息
        overtime_data = Find_all_overtime_message(start_date,end_date)#逾期信息
        daihuan_data = Find_all_daihuan_message(start_date,end_date)#代还信息
        inadvance_data = Find_all_inadvance_message(start_date,end_date)#提前还款减免


        chushen_events = self.find_case_by_('chushen',verify_data,start_date)
        fushen_events = self.find_case_by_('fushen',verify_data,start_date)
        loan_events = self.find_case_by_('loan',loan_data,start_date)
        overtime_events = self.find_case_by_('overtime',overtime_data,start_date)
        daihuan_apply_events = self.find_case_by_('daihuan_apply',daihuan_data,start_date)
        daihuan_approve_events = self.find_case_by_('daihuan_approve',sorted(list(daihuan_data),key=lambda x:x['approval_date']),start_date)
        inadvance_apply_events = self.find_case_by_('inadvance_apply',inadvance_data,start_date)
        inadvance_approve_events = self.find_case_by_('inadvance_approve',sorted(list(inadvance_data),key=lambda x:x['approval_date']),start_date)
        refund_events = self.find_case_by_('refund',refund_data,start_date)#还款
        payment_events = self.find_case_by_payment(refund_data,start_date,end_date)#到期


        while start_date < end_date:
            # 生成初审日志
            chushen_event = self.events_list_generator(chushen_events)
            # 生成复审信息
            fushen_event = self.events_list_generator(fushen_events)
            # 生成放款信息
            loan_event = self.events_list_generator(loan_events)
            #生成违约信息
            overtime_event = self.events_list_generator(overtime_events)
            #生成代还款减免申请信息
            daihuan_apply_event = self.events_list_generator(daihuan_apply_events)
            # 生成代还款减免审批信息
            daihuan_approve_event = self.events_list_generator(daihuan_approve_events)
            #生成提前结清减免申请
            inadvance_apply_event = self.events_list_generator(inadvance_apply_events)
            #生成提前结清减免审批
            inadvance_approve_event = self.events_list_generator(inadvance_approve_events)
            #生成还款信息
            refund_event  = self.events_list_generator(refund_events)


            event_list_chushen,chushen_rely = self.built_verify_events_message(chushen_event, True)
            event_list_fushen,fushen_rely = self.built_verify_events_message(fushen_event, False)
            event_list_loan,loan_amount =self.built_loan_events_message(loan_event)
            event_list_diancui,event_list_waicui,diancui_amount,waicui_amount = self.built_overtime_events_message(overtime_event)
            event_list_daihuanapply,daihuan_apply_rely=self.built_daihuan_events_message(daihuan_apply_event,True)
            event_list_daihuanapprove ,daihuan_approve_rely= self.built_daihuan_events_message(daihuan_approve_event,False)
            event_list_inadvanceapply,inadvance_apply_rely = self.built_inadvance_events_message(inadvance_apply_event,True)
            event_list_inadvanceapprove,inadvance_approve_rely = self.built_inadvance_events_message(inadvance_approve_event,False)
            event_list_refund,refund_amount = self.built_refund_events_message(refund_event)
            event_list_payment = self.built_payment_events_message(payment_events,start_date)

            #生成日志矩阵
            matrix = [[len(event_list_chushen),len(event_list_fushen),len(event_list_daihuanapply),len(event_list_daihuanapprove),len(event_list_inadvanceapply),
                        len(event_list_inadvanceapprove),len(event_list_loan),len(event_list_refund),len(event_list_diancui),len(event_list_waicui)],
                       [int(chushen_rely),int(fushen_rely),int(daihuan_apply_rely),int(daihuan_approve_rely),int(inadvance_apply_rely),
                        int(inadvance_approve_rely),float(loan_amount),float(refund_amount),float(diancui_amount),float(waicui_amount)]]



            log_dict = {'chushen':event_list_chushen,'fushen':event_list_fushen,'loan':event_list_loan,'diancui':event_list_diancui,'waicui':event_list_waicui,'daihuan_apply':event_list_daihuanapply,
                        'daihuan_approve':event_list_daihuanapprove,'inadvance_apply':event_list_inadvanceapply,'inadvance_approve':event_list_inadvanceapprove,'refund':event_list_refund,'payment':event_list_payment}

            #将日志信息按合同号保存至内存中
            event_dict=self.append_event(event_dict,log_dict)

            #将到期信息整合


            #将日志信息插入日志信息表中
            date_string = "%s" % (start_date.strftime("%Y-%m-%d"))
            date_obj = CaseLogs()
            date_obj.date = start_date
            date_obj.date_string = date_string
            date_obj.events = log_dict
            date_obj.events_matrix = matrix
            date_obj.save()
            start_date += datetime.timedelta(days=1)
        # 将日志信息首先加入至已创建的合同表中
        self.update_infomation_to_case(event_dict)
        return stop_date

    #信息生成器
    def find_case_by_(self,type,data,date):
        type_index={'chushen':'create_time','fushen':'approve_time','loan':'last_update_time','overtime':'CREATE_TIME',
                    'daihuan_apply':'apply_date','daihuan_approve':'approval_date','inadvance_apply':'apply_date','inadvance_approve':'approval_date',
                    'refund':'create_time'}
        compare_date = date.replace(hour=23, minute=59, second=59)
        events = []
        data = list(data)
        index = type_index[type]
        i=0
        while i < len(data):
            if data[i][index] and self.Date_To_Datetime(data[i][index])<= compare_date:
                events.append(data[i])
                i+=1
            elif not data[i][index]:
                i+=1
            else:
                yield events
                compare_date += datetime.timedelta(days=1)
                events = []

    # 构建审批-合同日志表信息
    def built_verify_events_message(self,case_list, is_chushen=True):
        def chushen_case(case):
            dic = {}
            if case['approve_time']:
                rely=0
                dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic[
                    'shop_id'] = case['create_time'], \
                                   case['apply_sn'], "风控审批", case['risk_manager_name'], "通过",case['shop_id']
            else:
                rely = 1
                dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic[
                    'shop_id'] = case['create_time'], \
                                   case['apply_sn'], "风控审批", case['risk_manager_name'], "拒绝", case['shop_id']
            return dic,rely

        def fushen_case(case):
            dic = {}
            if case['approve_rst'] == 'AR':
                if case['back_count']==0:
                    rely = 0
                    dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic[
                        'shop_id'] = case['approve_time'], \
                                       case['apply_sn'], "复审审批", case['approver'], "通过", case['shop_id']
                else:
                    rely = 0
                    dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic[
                        'shop_id'] = case['approve_time'], \
                                     case['apply_sn'], "复审审批", case['approver'], "退单通过", case['shop_id']

            elif case['apply_state']=='A5' and case['back_count']>0:
                rely = 0
                dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic[
                    'shop_id'] = case['approve_time'], \
                                 case['apply_sn'], "复审审批", case['approver'], "退单", case['shop_id']
            else:
                rely = 1
                dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic[
                    'shop_id'] = case['approve_time'], \
                                   case['apply_sn'], "复审审批", case['approver'], "拒绝", case['shop_id']
            return dic,rely

        if case_list:
            if is_chushen:
                event_list,rely= list(chushen_case(case)[0] for case in case_list),list(chushen_case(case)[1] for case in case_list)
                rely = np.array(rely).sum()
            else:
                event_list,rely = list(fushen_case(case)[0] for case in case_list),list(fushen_case(case)[1] for case in case_list)
                rely = np.array(rely).sum()
        else:
            event_list = []
            rely =0
        return event_list,rely

    #构建放款-合同日志表信息
    def built_loan_events_message(self,loan_data_list):
        def loan_event(case):
            dic = {}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic['shop_id'] = \
                case['last_update_time'], case['apply_sn'], '放款', case['last_update_uid'], {'合同金额': float(case['amount']),'实际放款金额': float(case['loan_amount']),'message':case['content']}, case['shop_id']
            amount = float(case['loan_amount'])
            return dic,amount

        event_list,amount = list(loan_event(case)[0] for case in loan_data_list),list(loan_event(case)[1] for case in loan_data_list)
        amount = np.array(amount).sum()

        return event_list,amount

    #构建违约-合同日志表信息
    def built_overtime_events_message(self,overtime_data_list):
        def diancui(case):
            dic = {}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic['shop_id'] = \
            case['CREATE_TIME'],case['src_case_id'],'电催',case['TASK_USER'],{'期数':case['input_term_no'],'金额':float(case['outstanding_amount'])},case['shop_id']
            amount = float(case['outstanding_amount'])
            return dic,amount

        def waicui(case):
            dic = {}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic['shop_id'] = \
                case['CREATE_TIME'], case['src_case_id'], '外催', case['TASK_USER'], {'期数': case['input_term_no'],'金额':float(case['outstanding_amount'])}, case['shop_id']
            amount = float(case['outstanding_amount'])
            return dic,amount

        info_list=list(map(lambda case: diancui(case) if case['TASK_CATEGORY_ID']=='TC00000001' or case['TASK_CATEGORY_ID']=='TC00000002' else waicui(case),overtime_data_list))
        diancui_list  = list(info[0] for info in info_list if info[0]['behave'] == '电催')
        waicui_list = list(info[0] for info in info_list if info[0]['behave'] == '外催')
        diancui_amount = np.array(list(info[1] for info in info_list if info[0]['behave']=='电催')).sum()
        waicui_amount = np.array(list(info[1] for info in info_list if info[0]['behave']=='外催')).sum()
        return diancui_list,waicui_list,diancui_amount,waicui_amount

    #代还款减免-合同日志信息表
    def built_daihuan_events_message(self,daihuan_data_list,is_apply=True):
        def apply(case):
            dic={}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic['shop_id'] = \
            case['apply_date'],case['src_case_id'],'代还款减免申请',case['apply_uid'],'通过'if case['reduction_status']=='Y' else '拒绝',case['shop_id']
            rely = 1 if case['reduction_status'] =='N' else 0
            return dic,rely

        def approve(case):
            dic={}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic['shop_id'] = \
            case['approval_date'],case['src_case_id'],'代还款减免审批',case['approval_uid'],'通过' if case['reduction_take_effect'] =='Y' else '拒绝',case['shop_id']
            rely = 1 if case['reduction_take_effect'] =='N' else 0
            return dic,rely

        if is_apply:
            event_list,rely=list(apply(case)[0] for case in daihuan_data_list),list(apply(case)[1] for case in daihuan_data_list)
            rely =np.array(rely).sum()
        else:
            event_list,rely = list(approve(case)[0] for case in daihuan_data_list),list(approve(case)[1] for case in daihuan_data_list)
            rely = np.array(rely).sum()
        return event_list,rely

    #提前还款减免—合同日志信息表
    def built_inadvance_events_message(self,inadvance_data,is_apply=True):
        def apply(case):
            dic={}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic['shop_id'] = \
            case['apply_date'],case['src_case_id'],'提前结清减免申请',case['apply_uid'],'通过'if case['reduction_status']=='Y' else '拒绝',case['shop_id']
            rely = 1 if case['reduction_status'] =='N'else 0
            return dic,rely

        def approve(case):
            dic={}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic['shop_id'] = \
            case['approval_date'],case['src_case_id'],'提前结清减免审批',case['approval_uid'],'通过'if case['reduction_take_effect']=='Y' else '拒绝',case['shop_id']
            rely = 1 if case['reduction_take_effect']=='N' else 0
            return dic,rely

        if is_apply:
            event_list,rely=list(apply(case)[0] for case in inadvance_data),list(apply(case)[1] for case in inadvance_data)
            rely=np.array(rely).sum()
        else:
            event_list,rely = list(approve(case)[0] for case in inadvance_data),list(approve(case)[1] for case in inadvance_data)
            rely = np.array(rely).sum()

        return event_list,rely

    #还款-合同信息表
    def built_refund_events_message(self,refund_data):
        def refund_event(case):
            dic = {}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'], dic['shop_id'] = \
                case['create_time'], case['src_case_id'], '还款',case['create_user_id'], {'期数':case['tenor'],'还款金额':float(case['pay_amount']),
                                                                                        '本期应还本金':float(case['principal']) if case['principal'] else 0,
                                                                                        '本期应还利息':float(case['interest']) if case['interest'] else 0,
                                                                                        '本期应还费用':float(case['fee']) if case['fee'] else 0,
                                                                                        '本期已还本金':float(case['principal_act'] if case['principal_act'] else 0),
                                                                                        '本期已还利息':float(case['interest_act'] ) if case['interest_act'] else 0,
                                                                                        '本期已还费用':float(case['fee_act']) if case['fee_act'] else 0,
                                                                                        '本期应还时间':self.Date_To_Datetime(case['payment_date'])}, case['shop_id']
            amount = float(case['pay_amount'])
            return dic,amount
        event_list,amount = list(refund_event(case)[0] for case in refund_data if case['src_case_id']),list(refund_event(case)[1] for case in refund_data if case['src_case_id'])
        amount = np.array(amount).sum()
        return  event_list,amount

    def find_case_by_payment(self,data_payment,start_date,end_date):
        data_payment = sorted(data_payment, key=lambda x: x['payment_date'])
        data_paymeny_list = list(
            [date['payment_date'], date['src_case_id'], date['tenor'], date['principal'], date['interest'], date['fee'],
             date['principal_act'], date['interest_act'], date['fee_act'],date['shop_id']] for date in data_payment)
        data_frame = pd.DataFrame(data_paymeny_list)
        start_date, end_date = datetime.date(start_date.year, start_date.month, start_date.day), datetime.date(
            end_date.year, end_date.month, end_date.day)
        data_frame = data_frame[(data_frame[0] >= start_date) & (data_frame[0] <= end_date)]
        return data_frame

    def built_payment_events_message(self,data_frame,date):
        def payment(date_data):
            dic = {}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message'],dic['shop_id']= self.Date_To_Datetime(date_data[0]), date_data[1], '到期', \
                                                                                       int(date_data[2]), {'本期应还本金': float(date_data[3]) if date_data[3] else 0,
                                                                                                      '本期应还利息': float(date_data[4]) if date_data[4] else 0,
                                                                                                      '本期应还费用': float(date_data[5]) if date_data[5] else 0,
                                                                                                      '本期已还本金': float(date_data[6]) if date_data[6] else 0,
                                                                                                      '本期已还利息': float(date_data[7]) if date_data[7] else 0,
                                                                                                      '本期已还费用': float(date_data[8]) if date_data[8] else 0},int(date_data[9])
            return dic
        date = datetime.date(date.year,date.month,date.day)
        end_date =date+datetime.timedelta(days=1)
        data_frame = data_frame[(data_frame[0] >= date) & (data_frame[0] <= end_date)]

        events_list = list(payment(data_frame.loc[index].values) for index in data_frame.index)
        return events_list


    def append_event(self,event_dic,log_dict):
        for behave in log_dict:
            for event in log_dict[behave]:
                if event['case_id'] and (behave in event_dic[event['case_id']]):
                    event_dic[event['case_id']][behave].append(event)
                else:
                    event_dic[event['case_id']][behave] = [event]
        return event_dic

    #合同更新
    def update_infomation_to_case(self,event_dict):


        def insert(case_id,behave_list):
            case_data = Case.objects(case_id=case_id).first()
            if case_data:
                for behave in behave_list:
                    case_data.logs[behave] += behave_list[behave]
                case_data = self.update_case_status(case_data)
                case_data.save()
            else:
                error_string = '合同%s无申请记录,却进行%s操作日志' % (case_id, list(behave for behave in behave_list))
                self.insert_erro_log(logstring=error_string)

        thread_list = []
        for case_id in event_dict:
            t1 = threading.Thread(target=insert,args=(case_id,event_dict[case_id],))
            thread_list.append(t1)

        for thread in thread_list:thread.start()
        for thread in thread_list:thread.join()




    #记录错误日志
    def insert_erro_log(self,logstring):
        now = datetime.datetime.now()
        error = ErrorLogs()
        error.date = now
        error.error = logstring
        error.save()

    #更新合同状态码
    def update_case_status(self,case):
        if case.logs['refund'] and int(case.logs['refund'][-1]['message']['期数']) == int(case.case_tenor):
            case.logs['end'] = [{'date':case.logs['refund'][-1]['date'],'case_id':case.case_id,'behave':'合同结束','manipulator':'','message':'','life_flag':0}]

        if  case.logs['fushen']:
            if case.approve_time :#如果原本没有复审时间，加入复审时间
                case.approve_time = case.logs['fushen'][0]['date']
            if not case.approve_status or case.approve_status !=case.logs['fushen'][0]['message']:#如果原来没有复审状态，加上复审状态
                case.approve_status = case.logs['fushen'][0]['message']


        if (not case.payment_date and case.logs['refund']) or (case.logs['refund'] and case.payment_date<case.logs['refund'][-1]['message']['本期应还时间']):#更新本期应还时间
            case.payment_date = case.logs['refund'][-1]['message']['本期应还时间']
        status = [len(case.logs['chushen']),len(case.logs['fushen']),len(case.logs['loan']),len(case.logs['refund']),len(case.logs['daihuan_apply']),len(case.logs['daihuan_approve']),
                  len(case.logs['inadvance_apply']),len(case.logs['inadvance_approve']),len(case.logs['payment']),len(case.logs['diancui']),len(case.logs['waicui']),len(case.logs['end'])]
        case.case_status = status
        return case

    def Date_To_Datetime(self,date):
        if isinstance(date,datetime.date):
            date_time = datetime.datetime(date.year,date.month,date.day,8,0,0)
            return date_time
        else:
            return date

    #每次还款时将到期信息整合以备更新
    def append_payment_data(self,event_list_refund):
        def payment(date_data):
            dic = {}
            dic['date'], dic['case_id'], dic['behave'], dic['manipulator'], dic['message']= self.Date_To_Datetime(date_data[0]), date_data[1], '到期', \
                                                                                       int(date_data[2]), {'本期应还本金': float(date_data['本期应还本金']) if date_data['本期应还本金'] else 0,
                                                                                                      '本期应还利息': float(date_data['本期应还利息']) if date_data['本期应还利息'] else 0,
                                                                                                      '本期应还费用': float(date_data['本期应还费用']) if date_data['本期应还费用'] else 0,
                                                                                                      '本期已还本金': float(date_data['本期已还本金']) if date_data['本期已还本金'] else 0,
                                                                                                      '本期已还利息': float(date_data['本期已还利息']) if date_data['本期已还利息'] else 0,
                                                                                                      '本期已还费用': float(date_data['本期已还费用']) if date_data['本期已还费用'] else 0}
            return dic


    def test(self,startdate,enddate):
        now  = datetime.datetime.now()
        loan_data = Find_all_loan_message(startdate, now)  # 放款信息
        loan_events = self.find_case_by_('loan', loan_data, startdate)
        while True:
            print(loan_events.__next__())

    #退单合同检查更新
    def approve_cases_update(self):
        retry_cases = Case.objects(approve_status='退单通过').all()
        retry_cases_id = list(case.case_id for case in retry_cases)
        retry_cases_info = find_normal_cases(retry_cases_id)
        event_list, rely = self.built_verify_events_message(retry_cases_info, is_chushen=False)
        logs_data = CaseLogs.objects(date_string=datetime.datetime.now().strftime("%Y-%m-%d")).first()

        for case in retry_cases:
            for case_info in event_list:
                if case.case_id == case_info['case_id']:
                    if case.approve_time != case_info['date']:
                        case.approve_time = case_info['date']
                    if case.approve_status != case_info['message']:
                        case.approve_status = case_info['message']
                        case.logs['fushen'].append(case_info)
                        logs_data.events['fushen'].append(case_info)
            case.save()



def test():
    print('test')


def timeily_quest():
    now = datetime.datetime.now()
    now = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = now - datetime.timedelta(days=1)
    mymon = MyMongo_executive()
    mymon.Case_init(start_date=yesterday, end_date=now)
    mymon.CaseLog_inti_(start_date=yesterday, end_date=now)
    mymon.approve_cases_update()

def db_init():
    start_date = find_the_first_day()['create_time'].replace(hour=0, minute=0, second=0, microsecond=0)
    now = datetime.datetime.now()
    mymon = MyMongo_executive()
    mymon.Case_init(start_date)
    mymon.CaseLog_inti_(start_date)
    print(datetime.datetime.now() - now)


# startdate=datetime.datetime(2017,7,10,0,0,0)
# enddate = datetime.datetime(2017,7,15,0,0,0)
# # print(CaseLog_inti_(startdate))
# # print(Case_init(startdate))
# # print(CaseLog_inti_(startdate))
# mymon = MyMongo_executive()
# mymon.Case_init(startdate)
# mymon.CaseLog_inti_(startdate)
# mymon.test(startdate,enddate)

#
# logs =CaseLogs.objects(Q(date__gte = startdate)& Q(date__lte=enddate)).all()
# matrix_index = np.zeros([2,9],dtype='float')
# for log in logs:
#     matrix=np.array(list(log.events_matrix))
#     print('进件量',int(matrix[0][0]))
#     print('风控批件',int(matrix[0][0]-matrix[1][0]))


