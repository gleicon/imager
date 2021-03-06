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


import cyclone.escape
import cyclone.httpclient
import cyclone.web
from twisted.internet import defer
from base62 import base62_encode, base62_decode
import os
import mimetypes
import time
import txmetrics


class MetricsMixin(object):
    metrics_factory = None
    
    @classmethod
    @defer.inlineCallbacks
    def setup(self, redis):
        yield redis._connected
        self.metrics_factory = txmetrics.TxMetricsFactory("imager", redis=redis)
        self.index_counter = yield self.metrics_factory.new_counter("index")
        self.upload_counter = yield self.metrics_factory.new_counter("uploads")
        self.transload_counter = yield self.metrics_factory.new_counter("transloads")
        self.invalid_file_counter = yield self.metrics_factory.new_counter("invalid_files")
        self.error_counter = yield self.metrics_factory.new_counter("errors")
        self.not_found_counter = yield self.metrics_factory.new_counter("not_found")
        self.unauthorized_counter = yield self.metrics_factory.new_counter("unauthorized")
        self.raw_image_view_counter = yield self.metrics_factory.new_counter("raw_images_served")
        self.image_view_handler_counter = yield self.metrics_factory.new_counter("images_viewed")
        self.image_data_handler_counter = yield self.metrics_factory.new_counter("image_data_served")
        self.image_like_handler_counter = yield self.metrics_factory.new_counter("total_likes")
        self.image_dislike_handler_counter = yield self.metrics_factory.new_counter("total_dislikes")
        self.image_status_handler_counter = yield self.metrics_factory.new_counter("images_statused")
        self.system_status_dump_counter = yield self.metrics_factory.new_counter("system_status")
    
    @defer.inlineCallbacks
    def dump(self):
        metrics={}
        yield self.incr("system_status_dump_counter")
        metrics["index_counter"]=yield self.index_counter.get_value()
        metrics["uploads_counter"]=yield self.upload_counter.get_value()
        metrics["transload_counter"]=yield self.transload_counter.get_value()
        metrics["invalid_file_counter"]=yield self.invalid_file_counter.get_value()
        metrics["error_counter"]=yield self.error_counter.get_value()
        metrics["not_found_counter"]=yield self.not_found_counter.get_value()
        metrics["unauthorized_counter"]=yield self.unauthorized_counter.get_value()
        metrics["raw_image_view_counter"]=yield self.raw_image_view_counter.get_value()
        metrics["image_view_handler_counter"]=yield self.image_view_handler_counter.get_value()
        metrics["image_data_handler_counter"]=yield self.image_data_handler_counter.get_value()
        metrics["image_like_handler_counter"]=yield self.image_like_handler_counter.get_value()
        metrics["image_dislike_handler_counter"]=yield self.image_dislike_handler_counter.get_value()
        metrics["image_status_handler_counter"]=yield self.image_status_handler_counter.get_value()
        metrics["system_status_dump_counter"]=yield self.system_status_dump_counter.get_value()
        defer.returnValue(cyclone.escape.json_encode(metrics))
        
    def incr(self, metric_name):
        counter = getattr(self, metric_name)
        m = getattr(counter, "incr")
        if m is not None:
            m()


class TemplateFields(dict):
    """Helper class to make sure our
        template doesn't fail due to an invalid key"""
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            return None

    def __setattr__(self, name, value):
        self[name] = value


class BaseHandler(cyclone.web.RequestHandler, MetricsMixin):
    IMAGER_UUID = 'IMAGER:UUID:'
    IMAGER_CLICK_RANKING = 'IMAGER:CLICK:RANKING'
    IMAGER_LIKE_RANKING = 'IMAGER:LIKE:RANKING'
    IMAGER_DISLIKE_RANKING = 'IMAGER:DISLIKE:RANKING'
    IMAGER_PREFIX = 'IMAGER:IMGPATH:%s'
    IMAGE_MIME_LIST = ['image/jpeg', 'image/png', 'image/gif']
    IMAGE_URL_THROTTLE = 'IMAGER:THROTTLE:%s:%s:%s'

    #def get_current_user(self):
    #    user_json = self.get_secure_cookie("user")
    #    if user_json:
    #        return cyclone.escape.json_decode(user_json)

    def get_user_locale(self):
        lang = self.get_secure_cookie("lang")
        if lang:
            return cyclone.locale.get(lang)

    @defer.inlineCallbacks
    def _save_and_create_uuid(self, fname, fbody, mime, transload_addr):
        uuid = yield self.redis.incr(self.IMAGER_UUID)
        b62 = base62_encode(uuid)

        fn = self._hash_by_name(fname, uuid)
        bdir = os.path.dirname(fn)

        try:
            if not os.path.exists(bdir):
                os.makedirs(bdir)
        except Exception, e:
            print e

        fh = open(fn, 'wb')
        fh.write(fbody)
        fh.close()

        yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'path', fn)
        yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'uploader_addr',
                              self.request.remote_ip)
        yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'transload_addr',
                              transload_addr)
        yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'base62', b62)
        yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'mime', mime)
        yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'clicks', 0)
        yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'likes', 0)
        yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'dislikes', 0)
        yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'name', fname)

        defer.returnValue(b62)

    def _hash_by_name(self, name, uuid):
        p = self.settings.filestore.path
        return "%s/%c/%c/%d_%s" % (p, name[0], name[1], uuid, name)

    @defer.inlineCallbacks
    def _get_image_by_b62(self, b62):
        uuid = base62_decode(b62)
        img_path = yield self.redis.hget(self.IMAGER_PREFIX % uuid, 'path')
        mime = yield self.redis.hget(self.IMAGER_PREFIX % uuid, 'mime')
        yield self.redis.hincr(self.IMAGER_PREFIX % uuid, 'clicks')
        yield self.redis.zincrby(self.IMAGER_CLICK_RANKING, 1, b62)

        if img_path is None:
            defer.returnValue((None, None))
    
        if mime is None or mime not in self.IMAGE_MIME_LIST:
            mime = mimetypes.guess_type(img_path)[0]
            yield self.redis.hset(self.IMAGER_PREFIX % uuid, 'mime', mime)

        defer.returnValue((mime, img_path))

    @defer.inlineCallbacks
    def _get_image_from_url(self, url):
        fname = url.split('/')[-1]
        response = yield cyclone.httpclient.fetch(url)
        mime = response.headers.get('Content-Type', None)
        if mime is not None:
            mime = mime[0]
        fbody = response.body
        defer.returnValue([fname, fbody, mime])

    @defer.inlineCallbacks
    def _like(self, b62):
        uuid = base62_decode(b62)
        v = yield self.redis.hincrby(self.IMAGER_PREFIX % uuid, 'likes', 1)
        yield self.redis.zincrby(self.IMAGER_LIKE_RANKING, 1, b62)
        defer.returnValue(v)

    @defer.inlineCallbacks
    def _dislike(self, b62):
        uuid = base62_decode(b62)
        v = yield self.redis.hincrby(self.IMAGER_PREFIX % uuid, 'dislikes', 1)
        yield self.redis.zincrby(self.IMAGER_DISLIKE_RANKING, 1, b62)
        defer.returnValue(v)

    @defer.inlineCallbacks
    def _get_image_data(self, b62):
        uuid = base62_decode(b62)
        data = yield self.redis.hgetall(self.IMAGER_PREFIX % uuid)
        del(data["path"])
        del(data["uploader_addr"])
        defer.returnValue(cyclone.escape.json_encode(data))

    @defer.inlineCallbacks
    def _image_exists(self, b62):
        if b62 is None:
            yield self.incr("not_found_counter")
            raise cyclone.web.HTTPError(404)

        uuid = base62_decode(b62)
        data = yield self.redis.exists(self.IMAGER_PREFIX % uuid)
        if data == 0:
            yield self.incr("not_found_counter")
            raise cyclone.web.HTTPError(404)
        defer.returnValue(data)

    @defer.inlineCallbacks
    def _throttle(self, b62, ip):
        """
            throttle by b62 hash + IP address + timestamp as: x reqs per minute
        """
        lt = time.localtime()
        ts = time.strftime("%Y:%m:%d:%H", lt)
        t = yield self.redis.incr(self.IMAGE_URL_THROTTLE % (ts, b62, ip))
        defer.returnValue(t)

    def _render(self, page, **kwargs):
        kwargs['base_domain'] = self.settings.base_domain
        self.render(page, **kwargs)
