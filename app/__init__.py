from flask import Flask
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
from config import config
from flask_login import LoginManager
from flask_mongoengine import MongoEngine
import pandas as pd
import redis,json,datetime,time
from pandas import DataFrame
from flask_apscheduler import APScheduler


bootstrap=Bootstrap()
moment=Moment()
db=SQLAlchemy()
login_manager=LoginManager()
mdb = MongoEngine()
login_manager.session_protection = 'strong'
login_manager.login_view = 'auth.login'
pool = redis.ConnectionPool(host='127.0.0.1', port=6379, db=0)
red = redis.StrictRedis(connection_pool=pool)
scheduler = APScheduler()

def data_profile():
    from .models import Case, CaseLogs
    from .main.sqlhelper import find_shop
    print('Data Profile are excusing...')

    now = datetime.datetime.now()
    cases = Case.objects().all()
    case_logs = CaseLogs.objects.all()

    print('Mongo Data has reload')

    cases_info_list = []
    for case in cases:
        overtime = 0

        chushen_events = case.logs['chushen']
        if chushen_events:
            apply_date = chushen_events[0]['date']
            apply_approver = chushen_events[0]['manipulator']
            apply_result = chushen_events[0]['message']
        else:
            apply_date, apply_approver, apply_result = None, None, None

        fushen_events = case.logs['fushen']
        if fushen_events:
            approve_date = fushen_events[0]['date']
            approve_approver = fushen_events[0]['manipulator']
            approve_result = fushen_events[0]['message']
        else:
            approve_date, approve_approver, approve_result = None, None, None

        loan_events = case.logs['loan']
        if loan_events:
            loan_date = None
            for event in loan_events:
                if '发送成功' in event['message']['message']:
                    loan_date = event['date']
                    break
        else:
            loan_date = None

        diancui_events = case.logs['diancui']
        if diancui_events:
            overtime = 1
            diancui_ternors = []
            diancui_amount = 0.0
            for diancui_event in diancui_events:
                if diancui_event['message']['期数'] not in diancui_ternors:
                    diancui_ternors.append(diancui_event['message']['期数'])
                    diancui_amount += float(diancui_event['message']['金额'])
        else:
            diancui_ternors, diancui_amount = [], 0.0

        waicui_events = case.logs['waicui']
        if waicui_events:
            overtime = 1
            waicui_ternors = []
            waicui_amount = 0.0
            for waicui_event in waicui_events:
                if waicui_event['message']['期数'] not in waicui_ternors:
                    waicui_ternors.append(waicui_event['message']['期数'])
                    waicui_amount += float(waicui_event['message']['金额'])
        else:
            waicui_ternors, waicui_amount = [], 0.0

        case_dict = {'case_id': case.case_id, 'shop_id': case.shop_id, 'status': case.case_status,
                     'amount': float(case.amount) if case.amount else 0.0,
                     'loan_date': loan_date, 'loan_amount': float(case.loan_amount) if case.loan_amount else 0.0,
                     'status_code': case.status_code, 'recommend_name': case.recommend_name,
                     'recommend_fee': float(case.recommend_fee) if case.recommend_fee else 0.0,
                     'apply_date': apply_date, 'apply_approver': apply_approver,
                     'apply_result': apply_result, 'approve_date': approve_date, 'approve_approver': approve_approver,
                     'approve_result': approve_result,
                     'overtime': overtime, 'diancui_ternors': diancui_ternors, 'diancui_amount': diancui_amount,
                     'waicui_ternors': waicui_ternors, 'waicui_amount': waicui_amount,
                     'sale_name': case.sale_name, 'is_renew_case': case.is_renew_case}
        cases_info_list.append(case_dict)

    print('Case Data execute already！')
    new_case_frame = DataFrame(cases_info_list)
    red.set('case_data', new_case_frame.to_msgpack(compress='zlib'))

    #到期信息存入
    print('Payment Data executing...')
    payment_events = []
    for case_log in case_logs:
        for event in case_log.events['payment']:
            payment_dict = {'date': event['date'], 'case_id': event['case_id'], 'ternor': event['manipulator'],
                            '本期应还本金': event['message']['本期应还本金'],
                            '本期已还本金': event['message']['本期已还本金'], '本期应还利息': event['message']['本期应还利息'],
                            '本期已还利息': event['message']['本期已还利息'], '本期应还费用': event['message']['本期应还费用'],
                            '本期已还费用': event['message']['本期已还费用'], 'shop_id': event['shop_id']}
            payment_events.append(payment_dict)
    payment_logs = DataFrame(payment_events)
    red.set('payment_logs', payment_logs.to_msgpack(compress='zlib'))
    print("Payment Data execute already!")


    #门店信息存入js
    shop_data = find_shop()  # 查询所有门店的名称
    shop_reflect = {}
    for shop_info in shop_data:
        shop_reflect[int(shop_info['id'])] = shop_info['abbreviation']
    shop_reflect.pop(7)  # 将测试门店除去
    shop=json.dumps(shop_reflect)
    red.set('shop_data', shop)
    print('Shop Data complete')
    print('Exhaust time:', datetime.datetime.now() - now)


def create_app(config_name):
    app=Flask(__name__)

    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    bootstrap.init_app(app)
    moment.init_app(app)
    db.init_app(app)
    login_manager.init_app(app)
    mdb.init_app(app)
    scheduler.init_app(app)

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint,url_prefix='/auth')
    #
    # data_profile()#数据准备
    scheduler.start()


    return app
