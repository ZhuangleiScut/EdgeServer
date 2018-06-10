#! /usr/bin/env python
# -*- coding: utf-8 -*-
import re
from flask import render_template, redirect, request, url_for, current_app, abort, jsonify, session, flash
from flask_login import login_user, logout_user, current_user
from datetime import datetime
import json
from ..models import User, Log
from ..util.authorize import admin_login
from ..util.file_manage import get_file_type
from PIL import Image
import os
from ..util.utils import get_login_data, clear_session_cookie
from . import image
from .. import db
import time

basedir = os.path.abspath(os.path.dirname(__file__))

@image.route('/', methods=['GET', 'POST'])
def get_frame():
    if request.method == 'POST':
        upload_file = request.files['file']
        old_file_name = upload_file.filename
        print(basedir)
        if upload_file:
            file_path = os.path.join(current_app.config['IMAGE_FOLDER'] , old_file_name)
            upload_file.save(file_path)
            print(file_path)
            print("success")
            # print('file saved to %s' % file_path)
            return 'success'
        else:
            return 'failed'

    else:
        return 'Please upload image!'
