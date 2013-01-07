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


from twisted.internet import defer

from imager.storage import DatabaseMixin
from imager.utils import BaseHandler
import cyclone.web


class IndexHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self):
        yield self.incr("index_counter")
        self._render("index.html")


class AboutHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self):
        yield self.incr("about_counter")
        self._render("about.html")


class InvalidFileHandler(BaseHandler):
    @defer.inlineCallbacks
    def get(self):
        yield self.incr("invalid_file_counter")
        self._render("invalid_file.html")


class UploadHandler(BaseHandler, DatabaseMixin):

    @defer.inlineCallbacks
    def post(self):
        """
            accepts upload, parameter -> file
        """
        files = self.request.files.get('file', None)

        if files is not None:
            fileinfo = files[0]
            fname = fileinfo['filename']
            fbody = fileinfo['body']
            mime = fileinfo['content_type']
            if mime not in self.IMAGE_MIME_LIST:
                self.redirect('/invalid_file.html')
            else:
                bid = yield self._save_and_create_uuid(fname, fbody,
                                                       mime, None)
                yield self.incr("invalid_file_counter")
                self.redirect("/i/%s" % bid)
        else:
            yield self.incr("error_counter")
            self.redirect("/error.html")


class TransloadHandler(BaseHandler, DatabaseMixin):

    @defer.inlineCallbacks
    def get(self):
        yield self._transload()

    @defer.inlineCallbacks
    def post(self):
        yield self._transload()

    @defer.inlineCallbacks
    def _transload(self):
        """
            accepts url, parameter -> url
        """
        url = self.get_argument('url', None)

        if url is not None:
            (fname, fbody, mime) = yield self._get_image_from_url(url)
            if mime not in self.IMAGE_MIME_LIST:
                print "error"
                self.redirect('/invalid_file.html')
            else:
                bid = yield self._save_and_create_uuid(fname, fbody,
                                                       mime, url)
                yield self.incr("transload_counter")
                self.redirect("/i/%s" % bid)
        else:
            yield self.incr("error_counter")
            self.redirect("/error.html")


class ImageHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def get(self, b62):
        yield self._image_exists(b62)
        (mime, img_path) = yield self._get_image_by_b62(b62)
        if img_path is None:
            raise cyclone.web.HTTPError(404)

        self.set_header("Content-Type", mime)

        object_file = open(img_path, "r")
        try:
            yield self.incr("raw_image_view_counter")
            self.finish(object_file.read())
        finally:
            object_file.close()


class ImageViewerHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def get(self, b62):
        yield self._image_exists(b62)
        yield self.incr("image_view_handler_counter")
        self._render('image.html', image=b62)


class ImageDataHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def get(self, b62):
        yield self._image_exists(b62)
        data = yield self._get_image_data(b62)
        yield self.incr("image_data_handler_counter")
        self.set_header("Content-Type", "application/json")
        self.finish(data)


class ImageLikeHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def post(self, b62):
        yield self._image_exists(b62)

        t = yield self._throttle(b62, self.request.remote_ip)

        if t > self.settings.max_req_per_min:
            raise cyclone.web.HTTPError(401)

        v = yield self._like(b62)
        yield self.incr("image_like_handler_counter")
        self.finish("%d" % v)


class ImageDislikeHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def post(self, b62):
        v = yield self._image_exists(b62)

        t = yield self._throttle(b62, self.request.remote_ip)

        if t > self.settings.max_req_per_min:
            raise cyclone.web.HTTPError(401)

        v = yield self._dislike(b62)
        yield self.incr("image_dislike_handler_counter")
        self.finish("%d" % v)
