#!/usr/bin/python
# -*- coding: UTF-8 -*-

import MySQLdb
import MySQLdb.cursors

def get_conn():
    host='192.168.98.133'
    username='root'
    passwd='1qaz2WSX!@'
    db='consumerfin7'
    port=3306
    conn=MySQLdb.connect(host=host,port=port,user=username,passwd=passwd,db=db,charset='utf8',cursorclass=MySQLdb.cursors.DictCursor)
    return conn

#信息查询装饰函数(单个)
def Search(func):
    def out(*args,**kwargs):
        conn = get_conn()
        cursor = conn.cursor()
        sql,parama = func(*args,**kwargs)
        cursor.execute(sql, parama)
        data = cursor.fetchone()
        cursor.close()
        conn.close()
        return data
    return out

#信息查询装饰函数（全部）
def SearchAll(func):
    def out(*args,**kwargs):
        conn = get_conn()
        cursor = conn.cursor()
        sql,parama = func(*args,**kwargs)
        cursor.execute(sql, parama)
        data = cursor.fetchall()
        cursor.close()
        conn.close()
        return data
    return out

#信息插入装饰器
def Insert(func):
    def out(*args,**kwargs):
        conn = get_conn()
        cursor = conn.cursor()
        sql,parama = func(*args,**kwargs)
        cursor.execute(sql, parama)
        conn.commit()
        cursor.close()
        conn.close()
    return out


#查找所有合同表字段
@SearchAll
def find_all_case(start_date,end_date):
    sql='''SELECT case_basic.create_time,apply_sn,amount,case_basic.customer_id,start_date,end_date,tenor,case_basic.shop_id,guarantor_fee,platform_fee,service_fee1,service_fee2,risk_fee,case_basic.`status`,mp_customer_basic_info.customer_name,ic_number,cm_app_consumptioninst.SALES_NAME,risk_manager_name,cm_app_case.approve_time,approver,sys_get_customer_act.real_name
            from
            (select ac_order.create_time,apply_sn,ac_order.shop_id,mp_contract_account_2_info.customer_id,amount,start_date,end_date,tenor,guarantor_fee,platform_fee,service_fee1,service_fee2,risk_fee,`status`,cm_app_consumptioninst.promoter_mobile
            from ac_order
            LEFT JOIN mp_contract_account_2_info on ac_order.apply_sn = mp_contract_account_2_info.src_case_id
						LEFT JOIN cm_app_consumptioninst on ac_order.apply_sn = cm_app_consumptioninst.src_case_id
            where ac_order.create_time is not NULL)as case_basic
            LEFT JOIN mp_customer_basic_info on case_basic.customer_id = mp_customer_basic_info.id
            LEFT JOIN cm_app_consumptioninst on case_basic.apply_sn = cm_app_consumptioninst.src_case_id
            left JOIN cm_app_case on case_basic.apply_sn = cm_app_case.src_case_id
			LEFT JOIN sys_get_customer_act on case_basic.promoter_mobile = sys_get_customer_act.mobile_phone_number
            where case_basic.create_time BETWEEN %s and %s
            ORDER BY case_basic.create_time'''
    param=(start_date.strftime("%Y-%m-%d 00:00:00"),end_date.strftime("%Y-%m-%d 23:59:59"))
    return sql,param


#找到开始日期
@Search
def find_the_first_day():
    sql="SELECT create_time,apply_sn "\
        "FROM ac_order "\
        "WHERE create_time is not NULL "\
        "ORDER BY create_time;"
    param = ()
    return sql,param

#寻找所有审核信息
@SearchAll
def Find_all_verify_messege(start_date,end_date):
    sql='''SELECT ac_order.create_time,ac_order.shop_id,apply_sn,salesman_Manage_name,apply_state,cm_app_case.approve_time,approver,approve_rst,cm_app_consumptioninst.risk_manager_name
            from ac_order
            LEFT JOIN cm_app_case on ac_order.apply_sn = cm_app_case.src_case_id
            LEFT JOIN cm_app_consumptioninst on ac_order.apply_sn = cm_app_consumptioninst.src_case_id
            WHERE ac_order.create_time BETWEEN %s and %s or cm_app_case.approve_time BETWEEN %s and %s and ac_order.create_time is not NULL
            order by ac_order.create_time;'''
    param = (start_date.strftime("%Y-%m-%d 00:00:00"),end_date.strftime("%Y-%m-%d 23:59:59"),
             start_date.strftime("%Y-%m-%d 00:00:00"), end_date.strftime("%Y-%m-%d 23:59:59"))
    return sql,param

#查询所有放款信息
@SearchAll
def Find_all_loan_message(start_date,end_date):
    sql='''select mp_contract_loan_info.transation_date,mp_contract_loan_info.apply_sn,mp_contract_loan_info.amount,mp_contract_loan_info.loan_amount,mp_contract_loan_info.last_update_uid,content,mp_contract_loan_info.last_update_time,ac_order.shop_id
            from mp_contract_loan_info
			LEFT JOIN ac_order on mp_contract_loan_info.apply_sn = ac_order.apply_sn
            where transation_date BETWEEN %s and %s
            ORDER BY transation_date'''
    param = (start_date.strftime("%Y-%m-%d 00:00:00"),end_date.strftime("%Y-%m-%d 23:59:59"))
    return sql,param

#查询所有催款信息
@SearchAll
def Find_all_overtime_message(start_date,end_date):
    sql='''SELECT overtime.CREATE_TIME,TASK_USER,TASK_CATEGORY_ID,input_term_no,overtime.contract_id,mp_contract_account_2_info.src_case_id,shop_id,mp_payment_plan_info.outstanding_amount
            from
            (SELECT cm_task.CREATE_TIME,TASK_USER,TASK_CATEGORY_ID,cm_task.input_term_no,cm_case_sum.contract_id
            from cm_task,cm_case_sum
            where cm_task.CASE_ID = cm_case_sum.case_id )as overtime,mp_contract_account_2_info,mp_payment_plan_info
            where overtime.contract_id = mp_contract_account_2_info.id and overtime.input_term_no = mp_payment_plan_info.tenor and overtime.contract_id = mp_payment_plan_info.contract_id and overtime.CREATE_TIME BETWEEN %s and %s
            ORDER by CREATE_TIME'''
    param=(start_date.strftime("%Y-%m-%d 00:00:00"),end_date.strftime("%Y-%m-%d 23:59:59"))
    return sql,param

#查询所有代还款信息
@SearchAll
def Find_all_daihuan_message(start_date,end_date):
    sql='''SELECT mp_reduction_approval.apply_date,apply_uid,mp_reduction_approval.reduction_status,approval_date,approval_uid,reduction_take_effect,mp_contract_account_2_info.src_case_id,shop_id
            from mp_reduction_approval INNER JOIN mp_contract_account_2_info
            on mp_reduction_approval.contract_id = mp_contract_account_2_info.id
            where apply_date BETWEEN %s and %s or approval_date BETWEEN %s and %s
            ORDER BY apply_date'''
    param=(start_date.strftime("%Y-%m-%d 00:00:00"),end_date.strftime("%Y-%m-%d 23:59:59"),start_date.strftime("%Y-%m-%d 00:00:00"),end_date.strftime("%Y-%m-%d 23:59:59"))
    return sql,param


#查询所有提前还清减免信息
@SearchAll
def Find_all_inadvance_message(start_date,end_date):
    sql='''SELECT mp_pretermination_approval.apply_date,apply_uid,mp_pretermination_approval.reduction_status,approval_date,approval_uid,reduction_take_effect,mp_contract_account_2_info.src_case_id,shop_id
            from mp_pretermination_approval LEFT JOIN mp_contract_account_2_info
            on mp_pretermination_approval.contract_id = mp_contract_account_2_info.id
            WHERE apply_date BETWEEN %s and %s or approval_date BETWEEN %s and %s
            ORDER BY apply_date'''
    param = (start_date.strftime("%Y-%m-%d 00:00:00"), end_date.strftime("%Y-%m-%d 23:59:59"),
             start_date.strftime("%Y-%m-%d 00:00:00"), end_date.strftime("%Y-%m-%d 23:59:59"))
    return sql,param


#查询所有还款信息
@SearchAll
def Find_all_refund_message(start_date,end_date):
    sql='''SELECT create_time,create_user_id,pay_amount,basic.tenor,basic.src_case_id,basic.principal,basic.interest,payment_date,basic.fee,principal_act,interest_act,fee_act,mp_contract_account_2_info.shop_id
            from
            (select mp_payment_plan_detail.create_time,create_user_id,pay_amount,mp_payment_plan_info.tenor,src_case_id,mp_payment_plan_info.principal,mp_payment_plan_info.interest,mp_payment_plan_info.payment_date,
            mp_payment_plan_info.fee,principal_act, interest_act,fee_act
            from mp_payment_plan_detail LEFT JOIN mp_payment_plan_info
            on mp_payment_plan_detail.plan_id = mp_payment_plan_info.id
            where create_time BETWEEN %s and %s or mp_payment_plan_info.payment_date BETWEEN %s and %s
            having payment_date is not NULL
            ORDER BY create_time)as basic
            LEFT JOIN mp_contract_account_2_info on basic.src_case_id = mp_contract_account_2_info.src_case_id'''
    param=(start_date.strftime("%Y-%m-%d 00:00:00"),end_date.strftime("%Y-%m-%d 23:59:59"),start_date.strftime("%Y-%m-%d"),end_date.strftime("%Y-%m-%d"))
    return sql,param


#判斷是否是首次借款
@Search
def is_first_case(start_date,customer_id):
    sql='''select count(0) as signFrequency FROM mp_contract_account_2_info t1 where first_payment_date <= %s and customer_id = %s
    '''
    param=(start_date.strftime('%Y-%m-%d'),customer_id)
    return sql,param

#门店名称查询
@SearchAll
def find_shop():
    sql='''select id,abbreviation from ac_business where business_type='A001'
            ORDER BY id
    '''
    param = ()
    return sql,param




