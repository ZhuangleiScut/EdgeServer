#! /usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Blueprint
image = Blueprint('image', __name__)
from . import views
