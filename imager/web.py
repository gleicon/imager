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


import cyclone.locale
import cyclone.web

from imager import views
from imager import config
from imager.storage import DatabaseMixin


class Application(cyclone.web.Application):
    def __init__(self, config_file):
        conf = config.parse_config(config_file)
        static_path = conf["static_path"]
        handlers = [
            (r"/",      views.IndexHandler),
            (r"/about.html", views.AboutHandler),
            (r"/invalid_file.html", views.InvalidFileHandler),
            (r"/upload",    views.UploadHandler),
            (r"/transload",    views.TransloadHandler),
            (r"/img/(.+)",    views.ImageHandler),
            (r"/imgdata/(.+)",  views.ImageDataHandler),
            (r"/like/(.+)",  views.ImageLikeHandler),
            (r"/dislike/(.+)",  views.ImageDislikeHandler),
            (r"/i/(.+)",    views.ImageViewerHandler),
            (r"/css/(.+)",    cyclone.web.StaticFileHandler,
                {"path": "%s/css" % static_path}),
            (r"/js/(.+)",    cyclone.web.StaticFileHandler,
                {"path": "%s/js" % static_path}),
            (r"/font/(.+)",    cyclone.web.StaticFileHandler,
                {"path": "%s/font" % static_path}),
        ]

        # Initialize locales
        if "locales" in conf:
            cyclone.locale.load_gettext_translations(conf["locales"],
                                                     "imager")

        # Set up database connections
        DatabaseMixin.setup(conf)

        #conf["login_url"] = "/auth/login"
        #conf["autoescape"] = None
        cyclone.web.Application.__init__(self, handlers, **conf)
