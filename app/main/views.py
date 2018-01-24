#!/usr/bin/python
# -*- coding: UTF-8 -*-
from datetime import datetime
from flask import render_template,session,redirect,url_for,jsonify,request
from flask_login import login_required
from . import main
from .. import db,red
from .forms import NameForm
from ..models import User
from .table_data_server import TableExcute
import re,datetime,json

@main.route('/',methods=['GET','POST'])
@login_required
def index():
    form=NameForm()
    if form.validate_on_submit():
        user=User.query.filter_by(username=form.name.data).first()
        print(user)
        if user is None:
            user=User(username=form.name.data)
            db.session.add(user)
            db.session.commit()
            session["known"]=False
        else:
            session["known"]=True
        session['name']=form.name.data
        return redirect(url_for('.index'))
    return render_template('index.html', current_time=datetime.utcnow(),form=form,name=session.get("name"),known=session.get("known",False))

#统计信息表
@main.route('/statistic',methods=['GET','POST'])
def statistic():
    shop_get = request.args.get('shop')
    date = request.args.get('date')
    print(date)
    shop_list = json.loads(red.get('shop_data').decode())
    shop = None
    for shop_id in shop_list:
        if shop_list[shop_id] == shop_get:
            shop = {'shop_name':shop_get,'shop_id':shop_id}
            break

    detail_start_date = '2017-07-15'
    detail_end_date = '2017-09-15'
    return render_template('statistic.html',detail_start_date=detail_start_date,detail_end_date=detail_end_date,shop = shop)

#详细信息表
@main.route('/detail',methods=['GET','POST'])
def detail():
    log_start_date,log_end_date = request.args.get('start_date'),request.args.get('end_date')
    print(log_start_date,log_end_date)
    return render_template('logs_detail.html', log_start_date=log_start_date, log_end_date=log_end_date)

#门店信息表
@main.route('/shop',methods = ['GET','POST'])
def shop():
    return render_template('shop.html')

#催收信息表
@main.route('/shop/cuishou',methods = ['GET','POST'])
def shop_cuishou():
    return render_template('overtimeshop.html')

#复审信息表
@main.route('/approve',methods = ['GET','POST'])
def approve():
    return render_template('approve.html')

#中介信息表
@main.route("/recommend",methods = ['GET','POST'])
def recommend():
    return render_template('recommend.html')

#风控信息表
@main.route("/apply",methods = ['GET','POST'])
def apply():
    shop_list = json.loads(red.get('shop_data').decode())
    return render_template('apply.html',shop_list = shop_list)


@main.route("/merit",methods = ['GET','POST'])
def merit():
    return render_template('merit.html')

#合同日志信息表返回函数
@main.route("/caselog_get",methods=['GET','POST'])
def caselog_get():
    index = request.form.get('index')
    if int(index) ==1:
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        table = TableExcute()
        dataitems = table.CaseLogGet(start_date,end_date)
        return jsonify(dataitems)
    else:
        return None

#合同信息表返回数据
@main.route("/case_get",methods=['GET','POST'])
def case_get():
    table = TableExcute()
    dataitems = table.CaseGet()
    return jsonify(dataitems)

#统计表返回数据
@main.route("/statistic_get",methods = ['GET','POST'])
def statistic_get():
    index = request.form.get('index')
    if int(index) ==0:
        date,date_end = request.form.get('date'),request.form.get('date_end')
        compare_date,compare_date_end = request.form.get('compare'),request.form.get("compare_end")
        shop_get = request.form.get("shop")
        print(date,date_end,compare_date,compare_date_end,shop_get)
        table =TableExcute()
        dataitems = table.Statistic_index(statistic_date=date,statistic_date_end=date_end,compare_date = compare_date,compare_date_end=compare_date_end,shop_get=shop_get)
        return jsonify(dataitems)


#统计详细信息表返回
@main.route("/statistic_detail_get",methods = ['POST'])
def statistic_detail_get():
    date,end_date,type = request.form.get('date'),request.form.get('end_date'),request.form.get('long')
    shop_get = request.form.get('shop')
    table = TableExcute()
    dataitems = table.Statistic_detail(date,end_date,type,shop_get)
    return jsonify(dataitems)

#门店基本信息返回表
@main.route("/statistic_by_shop",methods=['POST'])
def statistic_by_shop():
    date, end_date= request.form.get('date'), request.form.get('end_date')
    table = TableExcute()
    dataitems = table.Statistic_by_shop(date,end_date)
    return jsonify(dataitems)

#门店催收信息
@main.route("/cuishou_data/shop",methods=['POST'])
def cuishou_by_shop():
    date, end_date = request.form.get('date'), request.form.get('end_date')
    table = TableExcute()
    dataitems = table.cuishou_by_shop(date,end_date)
    return jsonify(dataitems)

#复审门店信息
@main.route("/approve/data",methods=['POST'])
def approve_data():
    date,end_date = request.form.get('date'),request.form.get('end_date')
    table = TableExcute()
    dataitems = table.fushen_by_person(date,end_date)
    return jsonify(dataitems)

#中介信息
@main.route("/recommend/data",methods=['POST'])
def recommend_data():
    date, end_date = request.form.get('date'), request.form.get('end_date')
    table = TableExcute()
    dataitems = table.recommend_by_shop(date,end_date)
    return jsonify(dataitems)

#风控信息
@main.route("/apply/data",methods = ['GET','POST'])
def apply_data():
    date, end_date,shop_id = request.form.get('date'), request.form.get('end_date'),request.form.get('shop_id')
    print(shop_id)
    table=TableExcute()
    data_items = table.apply_by_shop(date,end_date,shop_id)
    return jsonify(data_items)

#绩效数据
@main.route("/merit/data",methods = ['GET','POST'])
def merit_data():
    date, end_date = request.form.get('date'), request.form.get('end_date')
    table = TableExcute()
    data_items = table.merit_by_person(date,end_date)
    return jsonify(data_items)



#返回详细页面
@main.route("/detail/row",methods=['POST'])
def find_detail_in_row():
    date,type = request.form.get('date'),request.form.get('type')
    if int(type)==1:
        date_info=re.findall('(.+)-(.+)-(.+)',date)
        start_date = datetime.datetime(int(date_info[0][0]),int(date_info[0][1]),int(date_info[0][2]))
        end_date = start_date+datetime.timedelta(days=1)
        dataitems = {'start_date': start_date.strftime("%Y-%m-%d"), 'end_date':end_date.strftime("%Y-%m-%d") }
    else:
        date_info=re.findall('(.+)-(.+)-(.+)/(.+)-(.+)',date)
        start_date = datetime.datetime(int(date_info[0][0]),int(date_info[0][1]),int(date_info[0][2]))
        end_date = datetime.datetime(int(date_info[0][0]),int(date_info[0][3]),int(date_info[0][4]))
        if start_date>end_date:
            end_date = datetime.datetime(int(date_info[0][0])+1, int(date_info[0][3]), int(date_info[0][4]))
        dataitems = {'start_date': start_date.strftime("%Y-%m-%d"), 'end_date': end_date.strftime("%Y-%m-%d")}
    return jsonify(dataitems)


