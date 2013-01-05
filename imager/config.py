# coding: utf-8
#
# Copyright YEAR Foo Bar
# Powered by cyclone
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import os
import sys
import ConfigParser

from cyclone.util import ObjectDict


def tryget(func, section, option, default=None):
    try:
        return func(section, option)
    except ConfigParser.NoOptionError:
        return default


def my_parse_config(filename):
    cp = ConfigParser.RawConfigParser()
    cp.read([filename])

    conf = dict(raw=cp, config_file=filename)

    # server settings
    conf["debug"] = tryget(cp.getboolean, "server", "debug", False)
    conf["xheaders"] = tryget(cp.getboolean, "server", "xheaders", False)
    conf["cookie_secret"] = cp.get("server", "cookie_secret")
    conf["xsrf_cookies"] = tryget(cp.getboolean,
                                  "server", "xsrf_cookies", False)

    # make relative path absolute to this file's parent directory
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    getpath = lambda k, v: os.path.join(root, tryget(cp.get, k, v))

    # locale, template and static directories
    conf["locale_path"] = getpath("frontend", "locale_path")
    conf["static_path"] = getpath("frontend", "static_path")
    conf["template_path"] = getpath("frontend", "template_path")

    # redis support
    if tryget(cp.getboolean, "redis", "enabled", False) is True:
        conf["redis_settings"] = ObjectDict(
            unixsocket=tryget(cp.get, "redis", "unixsocket", None),
            host=tryget(cp.get, "redis", "host", "127.0.0.1"),
            port=tryget(cp.getint, "redis", "port", 6379),
            dbid=tryget(cp.getint, "redis", "dbid", 0),
            poolsize=tryget(cp.getint, "redis", "poolsize", 10))

    # email support
    if tryget(cp.getboolean, "email", "enabled", False) is True:
        conf["email_settings"] = ObjectDict(
            host=cp.get("email", "host"),
            port=tryget(cp.getint, "email", "port"),
            tls=tryget(cp.getboolean, "email", "tls"),
            username=tryget(cp.get, "email", "username"),
            password=tryget(cp.get, "email", "password"))

    # file storage support
    if tryget(cp.getboolean, "filestore", "enabled", False) is True:
        conf["filestore"] = ObjectDict(path=cp.get("filestore", "path"))
    # throttle
    conf["max_req_per_min"] = int(cp.get("throttle", "max_req_per_min"))

    return conf


def parse_config(filename):
    try:
        return my_parse_config(filename)
    except Exception, e:
        print("Error parsing %s: %s" % (filename, e))
        sys.exit(1)
