#! /usr/bin/env python
# -*- coding: utf-8 -*-
from flask import render_template, redirect, request, url_for, current_app, abort, jsonify, session, flash
from flask_login import login_user, logout_user, current_user
from datetime import datetime
import json
from ..models import User, News, Notice, Application, Apply, TempInstance
from ..util.authorize import admin_login
from ..util.file_manage import get_file_type
from PIL import Image
import os
from ..util.utils import get_login_data, get_secure_api_client
from . import admin
from .. import db


"""
    管理员登录与主控制台部分
"""


@admin.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('admin/admin_login.html', title=u'管理员登录')
    elif request.method == 'POST':
        _form = request.form
        u = User.query.filter_by(email=_form['email']).first()
        if u is None:
            message_e = u'邮箱不存在'
            return render_template('admin/admin_login.html',
                                   title=u"管理员登录",
                                   data=_form,
                                   message_e=message_e)
        if u and u.verify_password(_form['password']) and u.permissions == 0:
            login_user(u)
            u.last_login = datetime.now()
            db.session.commit()
            return redirect(url_for('admin.index'))
        else:
            message_p = u"密码错误,或该用户未注册为管理员"
            return render_template('admin/admin_login.html',
                                   title=u"管理员登录",
                                   data=_form,
                                   message_p=message_p)


@admin.route('/')
@admin_login
def index():
    """
    管理员的控制台主页
    """
    api_client = get_secure_api_client(session, current_user)

    # 获取认证用户数量
    auth_users = User.query.filter_by(is_auth=1).all()

    # 获取总用户数量
    all_users = User.query.all()

    # 获取系统总实例数量
    ins_num = len(api_client.get_instances_exist_list())

    # 获取系统可用模板数量
    app_num = len(Application.query.all())

    # 获取系统各资源配额的总使用率
    used_cpu = 0
    used_memory = 0
    used_apps = 0
    max_cpu = current_app.config['MAX_CPU']
    max_memory = current_app.config['MAX_MEMORY']
    max_apps = current_app.config['MAX_APPS']
    for u in all_users:
        used_cpu += u.used_cpu
        used_memory += u.used_memory
        used_apps += u.used_apps
    cpu_rate = round(float(used_cpu)/max_cpu, 4)*100
    memory_rate = round(float(used_memory)/max_memory, 4)*100
    apps_rate = round(float(used_apps)/max_apps, 4)*100
    sum_rate = round((cpu_rate + memory_rate) / 2, 2)

    return render_template('admin/index.html',
                           title=u'主控制台',
                           auth_num=len(auth_users),
                           instance_num=ins_num,
                           used_cpu=round(float(used_cpu)/1000, 2),
                           used_memory=round(float(used_memory)/1000, 2),
                           used_apps=used_apps,
                           app_num=app_num,
                           max_apps=max_apps,
                           max_memory=max_memory/1000,
                           max_cpu=max_cpu/1000,
                           cpu_rate=cpu_rate,
                           memory_rate=memory_rate,
                           instance_rate=apps_rate,
                           sum_rate=sum_rate)


"""
    图表部分
"""


@admin.route('/chart/cpu_dist')
@admin_login
def load_cpu_distribute():
    """
    读取当前使用cpu资源配额的用户的数量分布返回给前端ajax
    主要区分为使用0.2核以下的用户、0.4核以下的用户、0.6核以下的用户、0.8核以下的用户、0.8核以上的用户
    """
    auth_user = User.query.filter_by(is_auth=1).all()
    no_num, lowest_num, low_num, middle_num, high_num, super_num = 0, 0, 0, 0, 0, 0
    for u in auth_user:
        if u.used_cpu == 0:
            no_num += 1
        elif u.used_cpu <= 200:
            lowest_num += 1
        elif u.used_cpu <= 400:
            low_num += 1
        elif u.used_cpu <= 600:
            middle_num += 1
        elif u.used_cpu <= 800:
            high_num += 1
        else:
            super_num += 1
    result = [no_num, lowest_num, low_num, middle_num, high_num, super_num]
    return jsonify(result=result)


@admin.route('/chart/memory_dist')
@admin_login
def load_memory_distribute():
    """
    读取当前使用内存资源配额的用户的数量分布返回给前端ajax
    主要区分为使用256M以下的用户、512M以下的用户、1024M以下的用户、2048M核以下的用户、2048M以上的用户
    """
    auth_user = User.query.filter_by(is_auth=1).all()
    no_num, lowest_num, low_num, middle_num, high_num, super_num = 0, 0, 0, 0, 0, 0
    for u in auth_user:
        if u.used_memory == 0:
            no_num += 1
        elif u.used_memory <= 256:
            lowest_num += 1
        elif u.used_memory <= 400:
            low_num += 1
        elif u.used_memory <= 600:
            middle_num += 1
        elif u.used_memory <= 800:
            high_num += 1
        else:
            super_num += 1
    result = [no_num, lowest_num, low_num, middle_num, high_num, super_num]
    return jsonify(result=result)


@admin.route('/chart/app_dist')
@admin_login
def load_app_distribute():
    """
    读取系统所有正在运行的实例分布,并返回给前端ajax
    """
    api_client = get_secure_api_client(session, current_user)
    instance_list = api_client.get_instances_exist_list()
    app_dict = dict()
    if len(instance_list) != 0:
        for i in instance_list:
            if i['appname'] not in app_dict:
                app_dict[i['appname']] = 1
            else:
                app_dict[i['appname']] += 1
    else:
        app_dict['No Any Instances'] = 0
        print app_dict.keys()
    return jsonify(apps=app_dict.keys(), values=app_dict.values())


@admin.route('/chart/instance_dist')
@admin_login
def load_instance_distribute():
    """
    读取系统中拥有不同实例数的用户数量：0个、2个以下、4个以下、6个以下、6个以上
    """
    auth_user = User.query.filter_by(is_auth=1).all()
    no_num, lowest_num, low_num, middle_num, high_num = 0, 0, 0, 0, 0
    for u in auth_user:
        if u.used_apps == 0:
            no_num += 1
        elif u.used_apps <= 2:
            lowest_num += 1
        elif u.used_apps <= 4:
            low_num += 1
        elif u.used_apps <= 6:
            middle_num += 1
        else:
            high_num += 1
    result = [no_num, lowest_num, low_num, middle_num, high_num]
    return jsonify(result=result)


"""
    用户管理部分
"""


@admin.route('/user')
@admin_login
def user():
    """管理员查看认证系统用户列表"""
    users = User.query.filter_by(is_auth=1).all()
    return render_template('admin/user/index.html',
                           users=users,
                           title=u'用户管理')


@admin.route('/user/unauth_user')
@admin_login
def unauth_user():
    """管理员查看未通过认证的用户列表"""
    users = User.query.filter_by(is_auth=0).all()
    return render_template('admin/user/unauthed_user.html',
                           users=users,
                           title=u'审核待认证用户')


@admin.route('/user/auth/<int:uid>', methods=['GET', 'POST'])
@admin_login
def user_auth(uid):
    """管理员审核通过普通用户的认证"""
    u = User.query.filter_by(id=uid).first_or_404()
    api_client = get_secure_api_client(session, current_user)
    if api_client.create_user(u.username, u.api_password) == 200:  # 200 为状态返回码
        u.is_auth = 1
        db.session.commit()
    return redirect(url_for('admin.unauth_user'))


@admin.route('/user/del/', methods=['GET', 'POST'])
@admin_login
def user_del():
    """管理员删除未验证用户"""
    uid = request.form['id']
    u = User.query.filter_by(id=uid).first_or_404()

    db.session.delete(u)
    db.session.commit()
    return redirect(url_for('admin.unauth_user'))
    print(uid)
    # u = User.query.filter_by(id=uid).first_or_404()
    # api_client = get_secure_api_client(session, current_user)
    # if api_client.create_user(u.username, u.api_password) == 200:  # 200 为状态返回码
    #     u.is_auth = 1
    #     db.session.commit()
    # return redirect(url_for('admin.unauth_user'))

"""
    实例管理部分
"""


@admin.route('/instance', methods=['GET', 'POST'])
@admin_login
def instance():
    """管理员查看系统所有正在运行的实例"""
    api_client = get_secure_api_client(session, current_user)
    data = api_client.get_instances_exist_list()
    return render_template("admin/instance/index.html",
                           instances=data,
                           title=u"所有实例")


@admin.route('/instance/deleted', methods=['GET', 'POST'])
@admin_login
def instance_deleted():
    """管理员查看系统所有被删除的实例"""
    api_client = get_secure_api_client(session, current_user)
    data = api_client.get_instances_list()
    return render_template("admin/instance/deleted_instance.html",
                           instances=data['instances'],
                           title=u"被删除的实例列表")


@admin.route('/instance/<int:iid>', methods=['GET', 'POST'])
@admin_login
def instance_detail(iid):
    """管理员查看系统某个实例详情"""
    api_client = get_secure_api_client(session, current_user)
    i_data = api_client.get_instance_detail(iid=iid)
    instance = i_data['instance']
    config = i_data['config'][0]
    param = json.loads(config['param'])
    proxy = api_client.get_instance_proxy(iid=iid)
    return render_template("admin/instance/detail.html",
                           instance=instance,
                           config=config,
                           param=param,
                           proxys=proxy['Services'],
                           title=u"实例详情")


@admin.route('/instance/del', methods=['GET', 'POST'])
@admin_login
def instance_del():
    """管理员删除某个实例"""
    iid = request.form['iid']
    username = request.form['username']
    user = User.query.filter_by(username=username).all()[0]

    api_client = get_secure_api_client(session, current_user)
    cpu, memory, nodes = api_client.get_instance_resource(iid)
    print u'管理员删除用户%s的实例的cpu、内存配额、容器数量：%d, %d, %d' % (user.username, cpu, memory, nodes)

    resp = api_client.delete_instance(iid)
    print resp
    if resp == 200:
        user.used_apps -= nodes
        user.used_cpu -= cpu * nodes
        user.used_memory -= memory * nodes
        db.session.commit()
        flash('Deleted success')
        return jsonify(status='ok')


@admin.route('/instance/pause/', methods=['GET', 'POST'])
@admin_login
def instance_pause():
    """管理员暂停一个实例：删除它并把创建其的参数保留到数据库中，但请注意暂停实例不会归还用户资源"""
    iid = request.form['iid']
    username = request.form['username']
    api_client = get_secure_api_client(session, current_user)

    user = User.query.filter_by(username=username).all()[0]
    print u'管理员即将暂停用户%s的实例(iid为%s)' % (user.username, iid)

    cpu, memory, nodes = api_client.get_instance_resource(iid)
    print u'管理员删除用户%s的实例的平均cpu、平均内存配额、容器数量：%d, %d, %d' % (user.username, cpu, memory, nodes)

    ins_data = api_client.get_instance_detail(iid)

    param = ins_data['config'][0]['param']
    print u'保留参数为%s' % param

    back_aid = ins_data['instance']['aid']
    application = Application.query.filter_by(aid=back_aid).all()[0]
    instance_name = ins_data['instance']['instancename']

    resp = api_client.delete_instance(iid)
    print resp
    if resp == 200:
        temp_instance = TempInstance()
        temp_instance.name = instance_name
        temp_instance.user = user
        temp_instance.application = application
        temp_instance.param = param
        temp_instance.cpu_num = cpu
        temp_instance.memory_num = memory
        temp_instance.apps_num = nodes
        db.session.commit()
        flash('Paused success')
        return jsonify(status='ok')


"""
    资源配额部分
"""


@admin.route('/resource')
@admin_login
def resource():
    """资源配额首页"""
    # 返回所有待审核的申请
    applies = Apply.query.filter_by(status=0)

    # 获取系统各资源配额的总分配率
    auth_users = User.query.filter_by(is_auth=1).all()
    dist_cpu = 0
    dist_memory = 0
    dist_apps = 0
    max_cpu = current_app.config['MAX_CPU']
    max_memory = current_app.config['MAX_MEMORY']
    max_apps = current_app.config['MAX_APPS']

    for u in auth_users:
        dist_cpu += u.max_cpu
        dist_memory += u.max_memory
        dist_apps += u.max_apps
    cpu_rate = round(float(dist_cpu) / max_cpu, 4) * 100
    memory_rate = round(float(dist_memory) / max_memory, 4) * 100
    apps_rate = round(float(dist_apps) / max_apps, 4) * 100

    return render_template("admin/machine/index.html",
                           title=u"资源配额管理",
                           applies=applies,
                           dist_cpu=float(dist_cpu)/1000,
                           dist_memory=float(dist_memory)/1000,
                           dist_apps=dist_apps,
                           max_cpu=float(max_cpu)/1000,
                           max_memory=float(max_memory)/1000,
                           max_apps=max_apps,
                           cpu_rate=cpu_rate,
                           memory_rate=memory_rate,
                           apps_rate=apps_rate)


@admin.route('/resource/history')
@admin_login
def resource_history():
    """且返回所有审核过的申请"""
    applies = Apply.query.filter_by(status=1)
    return render_template("admin/machine/history.html",
                           title=u"已审核列表",
                           applies=applies)


@admin.route('/resource/auth/<int:aid>')
@admin_login
def resource_auth(aid):
    """通过审核"""
    _apply = Apply.query.get(aid)
    _apply.status = 1
    user = _apply.user
    user.max_cpu += _apply.cpu_num
    user.max_apps += _apply.instance_num
    user.max_memory += _apply.memory_num
    db.session.commit()
    return redirect(url_for('admin.resource'))


@admin.route('/resource/unauth/<int:aid>')
@admin_login
def resource_unauth(aid):
    """拒绝通过审核"""
    _apply = Apply.query.get(aid)
    _apply.status = 2
    db.session.commit()
    return redirect(url_for('admin.resource'))


"""
    应用模板部分
"""


@admin.route('/application')
@admin_login
def application():
    """管理员查看系统所有应用模板"""
    apps = Application.query.all()
    return render_template("admin/application/index.html",
                           apps=apps,
                           title=u"模板管理")


@admin.route('/application/create', methods=['GET', 'POST'])
@admin_login
def application_create():
    """管理员创建新模板"""
    if request.method == 'GET':
        return render_template("admin/application/create.html",
                               title=u"模板创建")

    elif request.method == 'POST':
        # 把自定义预设参数的信息整理成json格式的字符串,在k8s端创建成功后写入服务器端数据库

        """保存在服务器端的参数字符串，相比于发送给k8s端的参数字符串，更多了一些用于向用户展示的说明信息"""
        param_num = int(request.values.get("param-select"))
        param = list()           # 保存在服务器端的参数字符串
        param_kub = dict()       # 发送给k8s端的参数字符串
        param_kub['cpu'] = 'int'
        param_kub['memory'] = 'int'
        for i in range(1, param_num+1):
            _name = "param_name_%d" % i
            _note = "param_note_%d" % i
            _type = "param_type_%d" % i
            param_name = request.form[_name]
            param_note = request.form[_note]
            param_type = request.form[_type]
            param.append(dict(name=param_name, note=param_note, type=param_type))
            param_kub[str(param_name)] = str(param_type)

        param_str = json.dumps(param_kub).replace('"', '\\"')
        api_client = get_secure_api_client(session, current_user)
        data = api_client.create_app(appname=request.form['name_en'],
                                     path=request.form['path'],
                                     info=request.form['info_en'],
                                     param=param_str)

        if 'aid' in data:  # 若成功返回结果
            new_app = Application(name=request.form['name_zh'],
                                  aid=data["aid"],
                                  info=request.form['info_zh'],
                                  path=request.form['path'],
                                  param=json.dumps(param),
                                  param_guide=request.form['param_guide'])
            db.session.add(new_app)
            db.session.commit()
        else:
            print u"创建模板失败:"
            print data
        return redirect(url_for('admin.application'))


@admin.route('/application/delete', methods=['POST'])
@admin_login
def application_delete():
    """管理员删除模板，前端传过来的模板id为数据库所存的模板主键而非k8s端的id"""
    cur_app = Application.query.filter_by(id=request.form['aid']).first_or_404()
    api_client = get_secure_api_client(session, current_user)
    if api_client.delete_app(cur_app.aid) == 200:
        db.session.delete(cur_app)
        db.session.commit()
        print u"删除模板成功"
        return jsonify(status="success")
    else:
        print u"删除模板失败"
        return jsonify(status="failed")


@admin.route('/application/<int:aid>/pic', methods=['GET', 'POST'])
@admin_login
def application_pic(aid):
    """上传模板图片"""
    cur_app = Application.query.filter_by(id=aid).first_or_404()
    if request.method == 'GET':
        return render_template('admin/application/picture.html',
                               title=u"模板封面管理",
                               app=cur_app)
    elif request.method == 'POST':
        _file = request.files['file']
        app_folder = current_app.config['APPLICATION_FOLDER']
        file_type = get_file_type(_file.mimetype)
        if _file and '.' in _file.filename and file_type == "img":
            im = Image.open(_file)
            # im.thumbnail((383, 262), Image.ANTIALIAS)
            im.resize((383, 262), Image.ANTIALIAS)
            image_path = os.path.join(app_folder, "%d.png" % cur_app.id)
            im.save(image_path, 'PNG')
            unique_mark = os.stat(image_path).st_mtime
            cur_app.cover_img = '/static/upload/application/' + '%d.png?t=%s' % (cur_app.id, unique_mark)
            db.session.commit()
            return redirect(url_for('admin.application'))
        else:
            message_fail = u"无效的文件类型"
            return render_template('admin/application/picture.html',
                                   title=u"模板封面管理",
                                   app=cur_app,
                                   message_fail=message_fail)


"""
    资讯与公告部分
"""


@admin.route('/news')
@admin_login
def news():
    """管理员查看资讯列表"""
    news_list = News.query.all()
    return render_template('admin/article/news.html',
                           title=u'新闻资讯管理',
                           news_list=news_list)


@admin.route('/news/create', methods=['GET', 'POST'])
@admin_login
def news_create():
    """管理员创建资讯"""
    if request.method == 'GET':
        return render_template('admin/article/news_create.html', title=u'创建新闻资讯')
    elif request.method == 'POST':
        _form = request.form
        title = _form['title']
        poster = _form['poster']
        content = _form['content'].replace("\n", "")
        new_news = News(title=title, poster=poster, content=content)
        db.session.add(new_news)
        db.session.commit()
        return redirect(url_for('admin.news'))


@admin.route('/news/edit/<int:nid>', methods=['GET', 'POST'])
@admin_login
def news_edit(nid):
    """管理员编辑资讯"""
    if request.method == 'GET':
        cur_news = News.query.filter_by(id=nid).first_or_404()
        return render_template('admin/article/news_edit.html', title=u'编辑新闻资讯', news=cur_news)
    elif request.method == 'POST':
        _form = request.form
        cur_news = News.query.filter_by(id=nid).first_or_404()
        cur_news.title = _form['title']
        cur_news.poster = _form['poster']
        cur_news.content = _form['content']
        db.session.commit()
        return redirect(url_for('admin.news'))


@admin.route('/news/delete', methods=['POST'])
@admin_login
def news_delete():
    """管理员删除资讯"""
    nid = request.form['nid']
    cur_news = News.query.filter_by(id=nid).first_or_404()
    db.session.delete(cur_news)
    db.session.commit()
    return jsonify(status="success")


@admin.route('/notice')
@admin_login
def notice():
    """管理员查看公告列表"""
    notice_list = Notice.query.all()
    return render_template('admin/article/notice.html',
                           title=u'系统公告管理',
                           notice_list=notice_list)


@admin.route('/notice/create', methods=['GET', 'POST'])
@admin_login
def notice_create():
    """管理员创建公告"""
    if request.method == 'GET':
        return render_template('admin/article/notice_create.html', title=u'创建系统公告')
    elif request.method == 'POST':
        _form = request.form
        title = _form['title']
        poster = _form['poster']
        content = _form['content'].replace("\n", "")
        new_notice = Notice(title=title, poster=poster, content=content)
        db.session.add(new_notice)
        db.session.commit()
        return redirect(url_for('admin.notice'))


@admin.route('/notice/edit/<int:nid>', methods=['GET', 'POST'])
@admin_login
def notice_edit(nid):
    """管理员编辑公告"""
    if request.method == 'GET':
        cur_notice = Notice.query.filter_by(id=nid).first_or_404()
        return render_template('admin/article/notice_edit.html', title=u'编辑系统公告', notice=cur_notice)
    elif request.method == 'POST':
        _form = request.form
        cur_notice = Notice.query.filter_by(id=nid).first_or_404()
        cur_notice.title = _form['title']
        cur_notice.poster = _form['poster']
        cur_notice.content = _form['content']
        db.session.commit()
        return redirect(url_for('admin.notice'))


@admin.route('/notice/delete', methods=['POST'])
@admin_login
def notice_delete():
    """管理员删除公告"""
    nid = request.form['nid']
    cur_notice = Notice.query.filter_by(id=nid).first_or_404()
    db.session.delete(cur_notice)
    db.session.commit()
    return jsonify(status="success")

