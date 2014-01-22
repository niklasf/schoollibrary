# -*- coding: utf-8 -*-

# Client for a schoollibrary-server.
# Copyright (c) 2014 Niklas Fiekas <niklas.fiekas@tu-clausthal.de>
#
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
from PySide.QtGui import *

import sys

class ProgressSpinner(QWidget):
    def __init__(self, parent=None):
        super(ProgressSpinner, self).__init__(parent)

        policy = QSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setSizePolicy(policy)

        self.timer = QTimer()
        self.timer.timeout.connect(self.onTimeout)

        self.angle = 0

        self.baseColor = self.palette().color(QPalette.Midlight)
        self.color = self.palette().color(QPalette.Highlight)

    def onTimeout(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        p.translate(self.size().width() / 2.0, self.size().height() / 2.0)

        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), 30, 30)
        path.addEllipse(QPointF(0, 0), 20, 20)

        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(self.baseColor))
        p.drawPath(path)

        gradient = QConicalGradient(QPointF(0, 0), -self.angle)
        gradient.setColorAt(0.0, Qt.transparent)
        gradient.setColorAt(0.05, self.color)
        gradient.setColorAt(0.8, Qt.transparent)
        p.setBrush(gradient)
        p.drawPath(path)

        p.end()

    def sizeHint(self):
        return QSize(60, 60)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    spinner = ProgressSpinner()
    spinner.show()
    spinner.timer.start(50)
    sys.exit(app.exec_())
