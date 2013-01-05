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
    def get(self):
        self.render("index.html")


class AboutHandler(BaseHandler):
    def get(self):
        self.render("about.html")


class InvalidFileHandler(BaseHandler):
    def get(self):
        self.render("invalid_file.html")


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
                self.redirect("/i/%s" % bid)
        else:
            self.redirect("/error.html")


class TransloadHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def post(self):
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
                self.redirect("/i/%s" % bid)
        else:
            self.redirect("/error.html")


class ImageHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def get(self, b62):
        if b62 is None:
            raise cyclone.web.HTTPError(404)

        (mime, img_path) = yield self._get_image_by_b62(b62)
        self.set_header("Content-Type", mime)

        object_file = open(img_path, "r")
        try:
            self.finish(object_file.read())
        finally:
            object_file.close()


class ImageViewerHandler(BaseHandler, DatabaseMixin):
    def get(self, b62):
        self.render('image.html', image=b62)


class ImageDataHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def get(self, b62):
        data = yield self._get_image_data(b62)
        self.set_header("Content-Type", "application/json")
        self.finish(data)


class ImageLikeHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def get(self, b62):
        t = yield self._throttle(b62, self.request.remote_ip)

        if t > self.settings.max_req_per_min:
            raise cyclone.web.HTTPError(401)

        v = yield self._like(b62)
        self.finish("%d" % v)


class ImageDislikeHandler(BaseHandler, DatabaseMixin):
    @defer.inlineCallbacks
    def get(self, b62):
        t = yield self._throttle(b62, self.request.remote_ip)

        if t > self.settings.max_req_per_min:
            raise cyclone.web.HTTPError(401)

        v = yield self._dislike(b62)
        self.finish("%d" % v)
