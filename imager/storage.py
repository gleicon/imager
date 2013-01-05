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


try:
    sqlite_ok = True
    import cyclone.sqlite
except ImportError, sqlite_err:
    sqlite_ok = False

import cyclone.redis

from twisted.enterprise import adbapi
from twisted.python import log


class DatabaseMixin(object):
    mysql = None
    redis = None
    sqlite = None

    @classmethod
    def setup(cls, conf):
        if "sqlite_settings" in conf:
            if sqlite_ok:
                DatabaseMixin.sqlite = \
                cyclone.sqlite.InlineSQLite(conf["sqlite_settings"].database)
            else:
                log.err("SQLite is currently disabled: %s" % sqlite_err)

        if "redis_settings" in conf:
            if conf["redis_settings"].get("unixsocket"):
                DatabaseMixin.redis = \
                cyclone.redis.lazyUnixConnectionPool(
                              conf["redis_settings"].unixsocket,
                              conf["redis_settings"].dbid,
                              conf["redis_settings"].poolsize)
            else:
                DatabaseMixin.redis = \
                cyclone.redis.lazyConnectionPool(
                              conf["redis_settings"].host,
                              conf["redis_settings"].port,
                              conf["redis_settings"].dbid,
                              conf["redis_settings"].poolsize)

        if "mysql_settings" in conf:
            DatabaseMixin.mysql = \
            adbapi.ConnectionPool("MySQLdb",
                                  host=conf["mysql_settings"].host,
                                  port=conf["mysql_settings"].port,
                                  db=conf["mysql_settings"].database,
                                  user=conf["mysql_settings"].username,
                                  passwd=conf["mysql_settings"].password,
                                  cp_min=1,
                                  cp_max=conf["mysql_settings"].poolsize,
                                  cp_reconnect=True,
                                  cp_noisy=conf["mysql_settings"].debug)
