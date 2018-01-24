#!/usr/bin/python
# -*- coding: UTF-8 -*-
import re,datetime

#将合同日志表字典变为列表



def CaseInfoList(case):
    info_list=[case.case_id, case.customer_id, case.customer_name, case.ic_number, '%.2f'%case.amount, case.start_date.strftime('%Y-%m-%d'),
                 case.end_date.strftime('%Y-%m-%d'), case.start_date.strftime('%Y-%m-%d'),
                 case.case_tenor, None, case.sale_name, case.risk_manager_name, case.approver, case.card_name, case.shop_id,
               '%.2f'%case.plateform_fee, '%.2f'%case.guarantor_fee,
               '%.2f'%case.service_fee1, '%.2f'%case.service_fee2, '%.2f'%case.risk_fee]
    return info_list


def DateStrToDate(DateString,hour=0,minute=0,seconds=0):
    date_set = re.findall('(.+)-(.+)-(.+)', DateString)
    date = datetime.datetime(int(date_set[0][0]), int(date_set[0][1]), int(date_set[0][2]), int(hour),
                                   int(minute),int(seconds))
    return date


def log_datelist(date_first,date_final):
    date_list = []
    for year in range(date_first.year, date_final.year + 1):
        if year == date_first.year and year != date_final.year:
            for month in range(date_first.month, 13):
                date_list.append((year, month))
        elif year == date_first.year and year == date_final.year:
            for month in range(date_first.month, date_final.month + 1):
                date_list.append((year, month))
            break
        elif year != date_final.year:
            for month in range(1, 13):
                date_list.append((year, month))
        else:
            for month in range(1, date_final.month + 1):
                date_list.append((year, month))
    return date_list





