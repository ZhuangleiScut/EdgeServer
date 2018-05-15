#! /usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
from . import filter_blueprint

"""
    以下是常用的模板函数    
"""


@filter_blueprint.app_template_filter('compute_hours')
def compute_hours(time):
    """根据一个datetime来计算到当今的机时"""
    time = datetime.datetime.strptime(time, '%Y-%m-%d %H:%M:%S')
    now = datetime.datetime.now()
    result = u''
    if (now - time).days != 0:
        result = str((now - time).days) + u' 天 '
    result += str((now - time).seconds / 3600)
    return result
