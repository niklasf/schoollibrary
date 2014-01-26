# -*- coding: utf-8 -*-

# Client for a schoollibrary-server.
# Copyright (c) 2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have receicved a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from PySide.QtCore import *
from PySide.QtNetwork import *

import uuid

Ticket = QNetworkRequest.Attribute(QNetworkRequest.User)
HttpMethod = QNetworkRequest.Attribute(QNetworkRequest.User + 1)

class NetworkService(QNetworkAccessManager):
    def __init__(self, app, parent=None):
        super(NetworkService, self).__init__(parent)
        self.app = app

    def http(self, method, request, arg=None):
        ticket = str(uuid.uuid4())
        request.setAttribute(Ticket, ticket)

        method = method.upper()
        request.setAttribute(HttpMethod, method)

        if method == "DELETE":
            self.deleteResource(request)
        elif method == "GET":
            self.get(request)
        elif method == "HEAD":
            self.head(request)
        elif method == "POST":
            self.post(request, arg)
        elif method == "PUT":
            self.put(request, arg)
        else:
            self.sendCustomRequest(request, method, arg)

        return ticket
