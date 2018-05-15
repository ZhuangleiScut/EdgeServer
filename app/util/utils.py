#! /usr/bin/env python
# -*- coding: utf-8 -*-

from .API_manage import ApiClient, TOKEN_EXPIRE_HOUR
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
import random
import string
import datetime
from . import filter_blueprint

"""
    本文件包含一些常用的工具函数
"""


def generate_ehpc_login_token(secret, email, expiration=600):
    """生成一个EHPC login token, 过期时间为600秒"""
    s = Serializer(secret, expiration)
    return s.dumps({'email': email})


def verify_ehpc_login_token(secret, token):
    """校验token，并返回所要登录的用户的email，如果token过期则返回None"""
    s = Serializer(secret)
    try:
        data = s.loads(token)
    except:
        return None
    email = data.get('email')
    return email


def reset_proxy_url(url):
    """把API后端返回的url设置为当前域名的url"""
    pass


def generate_password():
    """随机生成8位的数字字母的密码"""
    return ''.join(random.sample(string.ascii_letters + string.digits, 8))


def get_login_data(user):
    """得到该用户的API登录数据"""
    return '{"username":"%s","password":"%s"}' % (user.username, user.api_password)


def get_secure_api_client(session, cur_user):
    """
    返回用户cookie是合法可用的一个api_client
    确保当前session中的cookie是未过期的，若过期或者没有cookie，则登录该用户并保存cookie
    """
    if not session.get('login_cookie') or not session.get('expire_time') \
            or session.get('expire_time') < datetime.datetime.now():
        api_client = ApiClient(login_data=get_login_data(cur_user))
        if api_client.login():
            session['login_cookie'] = api_client.get_login_cookie()
            session['expire_time'] = datetime.datetime.now() + datetime.timedelta(hours=TOKEN_EXPIRE_HOUR)
        else:
            print u"获取secure_api_client时登录失败！"
    else:
        api_client = ApiClient(login_cookie=session['login_cookie'])
    return api_client


def clear_session_cookie(session):
    """清空session中cookie"""
    session['login_cookie'] = None
    session['expire_time'] = None


