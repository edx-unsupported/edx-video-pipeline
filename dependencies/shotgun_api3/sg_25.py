
import sys
import os
import logging

import six

from .lib.httplib2 import Http, ProxyInfo, socks
from .lib.sgtimezone import SgTimezone

if six.PY3:
    from xmlrpc.client import Error, ProtocolError, ResponseError
else:
    from .lib.xmlrpclib import Error, ProtocolError, ResponseError

LOG = logging.getLogger("shotgun_api3")
LOG.setLevel(logging.WARN)

try:
    import simplejson as json
except ImportError:
    LOG.debug("simplejson not found, dropping back to json")
    try:
        import json as json
    except ImportError:
        LOG.debug("json not found, dropping back to embedded simplejson")
        # We need to munge the path so that the absolute imports in simplejson will work.
        dir_path = os.path.dirname(__file__)
        lib_path = os.path.join(dir_path, 'lib')
        sys.path.append(lib_path)
        from .lib import simplejson as json
        sys.path.pop()
