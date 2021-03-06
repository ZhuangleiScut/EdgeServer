#! /usr/bin/env python
# -*- coding: utf-8 -*-

from flask import redirect, request, url_for, render_template
from flask_login import current_user
from functools import wraps

"""
    超级管理员身份登录
"""


def super_login(func):
    """过滤器：已经使用管理员身份登录"""

    @wraps(func)
    def wrap(*args, **kwargs):
        if current_user.is_authenticated and current_user.permissions == 0:
            return func(*args, **kwargs)
        else:
            return redirect(url_for('admin.login'))

    return wrap


"""
    普通管理员身份登录
"""


def admin_login(func):
    """过滤器：已经使用管理员身份登录"""

    @wraps(func)
    def wrap(*args, **kwargs):
        if current_user.is_authenticated:
            return func(*args, **kwargs)
        else:
            return redirect(url_for('admin.login'))

    return wrap
# def user_auth(func):
#     """过滤器：已经通过管理员的用户认证"""
#     @wraps(func)
#     def wrap(*args, **kwargs):
#         if current_user.is_auth == 1:
#             return func(*args, **kwargs)
#         else:
#             return render_template('user/unauthed.html', title=u'暂无权限访问')
#     return wrap
