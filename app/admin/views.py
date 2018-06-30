#! /usr/bin/env python
# -*- coding: utf-8 -*-
import re
from flask import render_template, redirect, request, url_for, current_app, abort, jsonify, session, flash
from flask_login import login_user, logout_user, current_user
from datetime import datetime
import json
from ..models import User, Log, Equipment
from ..util.authorize import admin_login, super_login
from ..util.file_manage import get_file_type
from PIL import Image
import os
from ..util.utils import get_login_data, clear_session_cookie
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
        if u and u.verify_password(_form['password']):
            login_user(u)
            u.last_login = datetime.now()
            user_log = Log(user=u, content=u'登录平台')  # 记录用户的操作日志
            db.session.add(user_log)
            db.session.commit()
            current_app.logger.info("user %s login ITC" % u.email)
            return redirect(url_for('admin.index'))
        else:
            message_p = u"密码错误,或该用户未注册为管理员"
            return render_template('admin/admin_login.html',
                                   title=u"管理员登录",
                                   data=_form,
                                   message_p=message_p)


@admin.route('/logout/')
@admin_login
def logout():
    """用户登出"""
    user_log = Log(user=current_user, content=u'登出平台')  # 记录用户的操作日志
    db.session.add(user_log)
    db.session.commit()
    logout_user()
    clear_session_cookie(session)
    return redirect(url_for('admin.login'))


@admin.route('/')
@admin_login
def index():
    """
    管理员的控制台主页
    """

    # 获取认证用户数量
    # auth_users = User.query.filter_by(is_auth=1).all()

    # 获取总用户数量
    all_users = User.query.all()
    # print(all_users)

    return render_template('admin/index.html',
                           title=u'主控制台',
                           auth_num=len(all_users),
                           instance_num=3,
                           used_cpu=3,
                           used_memory=5,
                           used_apps=6,
                           app_num=7,
                           max_apps=7,
                           max_memory=6,
                           max_cpu=5,
                           cpu_rate=4,
                           memory_rate=3,
                           instance_rate=2,
                           sum_rate=1)


"""
    图表部分
"""

#
# @admin.route('/chart/cpu_dist')
# @admin_login
# def load_cpu_distribute():
#     """
#     读取当前使用cpu资源配额的用户的数量分布返回给前端ajax
#     主要区分为使用0.2核以下的用户、0.4核以下的用户、0.6核以下的用户、0.8核以下的用户、0.8核以上的用户
#     """
#     auth_user = User.query.filter_by(is_auth=1).all()
#     no_num, lowest_num, low_num, middle_num, high_num, super_num = 0, 0, 0, 0, 0, 0
#     for u in auth_user:
#         if u.used_cpu == 0:
#             no_num += 1
#         elif u.used_cpu <= 200:
#             lowest_num += 1
#         elif u.used_cpu <= 400:
#             low_num += 1
#         elif u.used_cpu <= 600:
#             middle_num += 1
#         elif u.used_cpu <= 800:
#             high_num += 1
#         else:
#             super_num += 1
#     result = [no_num, lowest_num, low_num, middle_num, high_num, super_num]
#     return jsonify(result=result)
#
#
# @admin.route('/chart/memory_dist')
# @admin_login
# def load_memory_distribute():
#     """
#     读取当前使用内存资源配额的用户的数量分布返回给前端ajax
#     主要区分为使用256M以下的用户、512M以下的用户、1024M以下的用户、2048M核以下的用户、2048M以上的用户
#     """
#     auth_user = User.query.filter_by(is_auth=1).all()
#     no_num, lowest_num, low_num, middle_num, high_num, super_num = 0, 0, 0, 0, 0, 0
#     for u in auth_user:
#         if u.used_memory == 0:
#             no_num += 1
#         elif u.used_memory <= 256:
#             lowest_num += 1
#         elif u.used_memory <= 400:
#             low_num += 1
#         elif u.used_memory <= 600:
#             middle_num += 1
#         elif u.used_memory <= 800:
#             high_num += 1
#         else:
#             super_num += 1
#     result = [no_num, lowest_num, low_num, middle_num, high_num, super_num]
#     return jsonify(result=result)
#
#
# @admin.route('/chart/app_dist')
# @admin_login
# def load_app_distribute():
#     """
#     读取系统所有正在运行的实例分布,并返回给前端ajax
#     """
#     api_client = get_secure_api_client(session, current_user)
#     instance_list = api_client.get_instances_exist_list()
#     app_dict = dict()
#     if len(instance_list) != 0:
#         for i in instance_list:
#             if i['appname'] not in app_dict:
#                 app_dict[i['appname']] = 1
#             else:
#                 app_dict[i['appname']] += 1
#     else:
#         app_dict['No Any Instances'] = 0
#         print app_dict.keys()
#     return jsonify(apps=app_dict.keys(), values=app_dict.values())
#
#
# @admin.route('/chart/instance_dist')
# @admin_login
# def load_instance_distribute():
#     """
#     读取系统中拥有不同实例数的用户数量：0个、2个以下、4个以下、6个以下、6个以上
#     """
#     auth_user = User.query.filter_by(is_auth=1).all()
#     no_num, lowest_num, low_num, middle_num, high_num = 0, 0, 0, 0, 0
#     for u in auth_user:
#         if u.used_apps == 0:
#             no_num += 1
#         elif u.used_apps <= 2:
#             lowest_num += 1
#         elif u.used_apps <= 4:
#             low_num += 1
#         elif u.used_apps <= 6:
#             middle_num += 1
#         else:
#             high_num += 1
#     result = [no_num, lowest_num, low_num, middle_num, high_num]
#     return jsonify(result=result)
#
#
"""
    用户管理部分
"""


@admin.route('/user')
@admin_login
def user():
    """管理员查看系统用户列表"""
    users = User.query.all()
    return render_template('admin/user/index.html',
                           users=users,
                           title=u'用户管理')


@admin.route('/user/log/<int:uid>')
@admin_login
def user_log(uid):
    """进入用户的操作日志页面"""
    _user = User.query.filter_by(id=uid).first_or_404()
    logs = Log.query.filter_by(user=_user).order_by(db.desc(Log.created_time)).limit(20).all()
    return render_template('admin/user/operation_log.html',
                           logs=logs,
                           title=u'%s-操作日志' % _user.real_name)


"""
   用户操作日志相关
"""


@admin.route('/log/')
@admin_login
def log():
    """查看所有用户的操作日志页面"""
    logs = Log.query.order_by(db.desc(Log.created_time)).limit(20).all()
    return render_template('admin/user/operation_log.html',
                           logs=logs,
                           title=u'操作日志')


# @admin.route('/user/unauth_user')
# @admin_login
# def unauth_user():
#     """管理员查看未通过认证的用户列表"""
#     users = User.query.filter_by(is_auth=0).all()
#     return render_template('admin/user/unauthed_user.html',
#                            users=users,
#                            title=u'审核待认证用户')
#
#
# @admin.route('/user/auth/<int:uid>', methods=['GET', 'POST'])
# @admin_login
# def user_auth(uid):
#     """管理员审核通过普通用户的认证"""
#     u = User.query.filter_by(id=uid).first_or_404()
#     api_client = get_secure_api_client(session, current_user)
#     if api_client.create_user(u.username, u.api_password) == 200:  # 200 为状态返回码
#         u.is_auth = 1
#         db.session.commit()
#     return redirect(url_for('admin.unauth_user'))


@admin.route('/user/del/', methods=['GET', 'POST'])
@super_login
def user_del():
    """管理员删除未验证用户"""
    uid = request.form['id']
    u = User.query.filter_by(id=uid).first_or_404()

    # 超级管理员不能被删除
    if u.email != 'admin@qq.com':
        db.session.delete(u)
    db.session.commit()
    return redirect(url_for('admin.user'))
    print(uid)


@admin.route('/user/add/', methods=['GET', 'POST'])
@super_login
def user_add():
    if request.method == 'GET':
        return render_template("admin/user/add.html", title=u"添加管理员")
    elif request.method == 'POST':
        _form = request.form
        username = _form['username']
        email = _form['email']
        password = _form['password']
        password2 = _form['password2']

        """此处可继续完善后端验证，如过滤特殊字符等"""
        message_e, message_u, message_p = "", "", ""
        if User.query.filter_by(username=username).first():
            message_u = u'用户名已存在'
        if User.query.filter_by(email=email).first():
            message_e = u'邮箱已存在'
        if password != password2:
            message_p = u'两次输入密码不一致'

        if not re.search('^[a-zA-Z][a-zA-Z0-9]{2,12}$', username):
            message_u = u'用户名必须以字母开头,只能包含字母或数字, 且不能小于3位大于11位'
        # if not re.search('^[a-zA-Z][a-zA-Z0-9]{5,}$', password):
        #     message_p = u'密码只能包含字母与数字, 且不能小于6位'

        data = None
        if message_u or message_e or message_e:
            data = _form
        if message_u or message_p or message_e:
            return render_template("admin/user/add.html", form=_form,
                                   title=u'添加管理员',
                                   message_u=message_u,
                                   message_p=message_p,
                                   message_e=message_e,
                                   data=data)
        else:
            reg_user = User()
            reg_user.email = email
            reg_user.password = password
            reg_user.username = username
            reg_user.avatar_url = current_app.config['DEFAULT_AVATAR']
            # reg_user.api_password = generate_password()
            db.session.add(reg_user)
            db.session.commit()
            # login_user(reg_user)
            # reg_user.last_login = datetime.now()
            db.session.commit()
            return redirect(url_for('admin.user'))


"""
个人设置相关
"""


@admin.route('/setting/information', methods=['GET', 'POST'])
@admin_login
def setting_information():
    """用户设置个人信息"""
    if request.method == 'GET':
        return render_template('admin/user/setting_information.html', title=u'个人设置')
    elif request.method == 'POST':
        _form = request.form
        cur_user = User.query.filter_by(email=current_user.email).first()
        cur_user.phone = _form['phone']
        cur_user.real_name = _form['real_name']
        cur_user.address = _form['address']
        db.session.commit()
        return render_template('admin/user/setting_information.html',
                               title=u'个人设置',
                               status='success')


@admin.route('/setting/password', methods=['GET', 'POST'])
@admin_login
def setting_password():
    """用户设置密码"""
    if request.method == 'GET':
        return render_template('admin/user/setting_password.html', title=u'个人设置')
    elif request.method == 'POST':
        _form = request.form
        cur_user = User.query.filter_by(email=current_user.email).first()
        if cur_user.verify_password(_form['origin_password']):
            if _form['new_password'] == _form['new_password2']:
                cur_user.password = _form['new_password']
                db.session.commit()
                return render_template('admin/user/setting_password.html', title=u'个人设置', status='success')
            else:
                fail_message = u'两次输入新密码不一致，请重新输入'
        else:
            fail_message = u'初始密码错误，请重新输入'

        return render_template('admin/user/setting_password.html',
                               title=u'个人设置',
                               fail_message=fail_message)


@admin.route('/setting/avatar', methods=['GET', 'POST'])
@admin_login
def setting_avatar():
    """用户上传头像"""
    if request.method == 'GET':
        return render_template('admin/user/setting_avatar.html', title=u'个人设置')
    elif request.method == 'POST':
        _file = request.files['file']
        avatar_folder = current_app.config['AVATAR_FOLDER']
        file_type = get_file_type(_file.mimetype)
        if _file and '.' in _file.filename and file_type == "img":
            im = Image.open(_file)
            im.thumbnail((128, 128), Image.ANTIALIAS)
            image_path = os.path.join(avatar_folder, "%d.png" % current_user.id)
            im.save(image_path, 'PNG')
            unique_mark = os.stat(image_path).st_mtime
            current_user.avatar_url = '/static/upload/avatar/' + '%d.png?t=%s' % (current_user.id, unique_mark)

            db.session.commit()
            message_success = u'更新图片成功'
            return render_template('admin/user/setting_avatar.html', message_success=message_success)
        else:
            message_fail = u"无效的文件类型"
            return render_template('admin/user/setting_avatar.html', message_fail=message_fail)


@admin.route('/raspi')
@admin_login
def raspi():
    """管理员查看系统用户列表"""
    raspis = Equipment.query.all()
    return render_template('admin/raspi/index.html',
                           users=raspis,
                           title=u'树莓派管理')


@admin.route('/raspi/add/', methods=['GET', 'POST'])
@admin_login
def raspi_add():
    if request.method == 'GET':
        return render_template("admin/raspi/add.html", title=u"添加树莓派")
    elif request.method == 'POST':
        _form = request.form
        username = _form['username']
        email = _form['email']
        password = _form['password']
        password2 = _form['password2']

        """此处可继续完善后端验证，如过滤特殊字符等"""
        message_e, message_u, message_p = "", "", ""
        if User.query.filter_by(username=username).first():
            message_u = u'用户名已存在'
        if User.query.filter_by(email=email).first():
            message_e = u'邮箱已存在'
        if password != password2:
            message_p = u'两次输入密码不一致'

        if not re.search('^[a-zA-Z][a-zA-Z0-9]{2,12}$', username):
            message_u = u'用户名必须以字母开头,只能包含字母或数字, 且不能小于3位大于11位'
        # if not re.search('^[a-zA-Z][a-zA-Z0-9]{5,}$', password):
        #     message_p = u'密码只能包含字母与数字, 且不能小于6位'

        data = None
        if message_u or message_e or message_e:
            data = _form
        if message_u or message_p or message_e:
            return render_template("admin/user/add.html", form=_form,
                                   title=u'添加管理员',
                                   message_u=message_u,
                                   message_p=message_p,
                                   message_e=message_e,
                                   data=data)
        else:
            reg_user = User()
            reg_user.email = email
            reg_user.password = password
            reg_user.username = username
            reg_user.avatar_url = current_app.config['DEFAULT_AVATAR']
            # reg_user.api_password = generate_password()
            db.session.add(reg_user)
            db.session.commit()
            # login_user(reg_user)
            # reg_user.last_login = datetime.now()
            db.session.commit()
            return redirect(url_for('admin.user'))
