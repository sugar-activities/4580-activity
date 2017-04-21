# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import json

from gettext import gettext as _
import gtk

from sugar import profile
from sugar import mime
from sugar.activity import activity
from sugar.graphics.icon import Icon
from sugar.activity.widgets import StopButton
from sugar.activity.widgets import ActivityToolbarButton
from sugar.activity.widgets import ToolbarButton
from sugar.graphics.toolbarbox import ToolbarBox
from articles import ArticlesManager
from tracker import ArticlesTracker
import config
from articles_browser import ArticlesBrowser
import sqlite3
import os
import shutil

class NewsActivity(activity.Activity):
  def __init__(self, handle):
    activity.Activity.__init__(self, handle, True)

    # Toolbar(s)
    toolbarbox = ToolbarBox()

    # The Activity Button:
    activity_button = ActivityToolbarButton(self)

    # Insert the Activity Toolbar Button in the toolbarbox
    toolbarbox.toolbar.insert(activity_button, 0)

    separator = gtk.SeparatorToolItem()
    separator.set_expand(False)
    separator.set_draw(True)
    toolbarbox.toolbar.insert(separator, -1)

    stopbtn = StopButton(self)
    toolbarbox.toolbar.insert(stopbtn, -1)

    self.set_toolbar_box(toolbarbox)

    # For a white background:
    canvas = gtk.EventBox()
    canvas.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))

    db_file = self.get_activity_root() + "/articles.db"
    if not os.path.exists(db_file):
      shutil.copy(activity.get_bundle_path() + "/default.db", db_file)

    self.manager = ArticlesManager(sqlite3.connect(db_file, isolation_level=None, \
        check_same_thread=False))
    self.manager.initialize_db()

    track = ArticlesTracker(config.TRACKER_URL)
    self.manager.connect('article-liked', lambda m, article_id: track.track_action_on_thread('liked', article_id))
    self.manager.connect('article-read', lambda m, article_id: track.track_action_on_thread('read', article_id))

    web = ArticlesBrowser(self.manager, base="file://" + activity.get_bundle_path() + "/")
    scroller = gtk.ScrolledWindow()
    scroller.add(web)
    scroller.show()
    web.show()
    canvas.add(scroller)
    self.set_canvas(canvas)
    self.show_all()

  def can_close(self):      
    self.manager.garbage_collect()
    return True


