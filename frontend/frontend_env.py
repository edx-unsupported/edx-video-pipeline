#!/usr/bin/env python
"""
VEDA Environment variables

"""


import os
import sys
import django
from django.utils.timezone import utc


project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_path not in sys.path:
    sys.path.append(project_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'VEDA.settings.local')

django.setup()

from VEDA_OS01.models import Institution
from VEDA_OS01.models import Course
from VEDA_OS01.models import Video
from VEDA_OS01.models import URL
from VEDA_OS01.models import VedaUpload

"""
TERM COLORS
"""
NODE_COLORS_BLUE = '\033[94m'
NODE_COLORS_GREEN = '\033[92m'
NODE_COLORS_RED = '\033[91m'
NODE_COLORS_END = '\033[0m'

VEDA_UTCOFFSET = -4
