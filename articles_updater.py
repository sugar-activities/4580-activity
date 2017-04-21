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

from config import *
from articles import Article
import gobject
import urllib2
import json
import threading



class ArticlesUpdater(gobject.GObject):
  __gsignals__ = {
    'update-completed': (gobject.SIGNAL_RUN_LAST,
                        gobject.TYPE_NONE, []),
    'update-failed': (gobject.SIGNAL_RUN_LAST,
                        gobject.TYPE_NONE, [])
  }

  def update(self, manager):
    pass

gobject.type_register(ArticlesUpdater)

class InternetArticlesUpdater(ArticlesUpdater):
  def __init__(self, url, manager, timeout=20):
    ArticlesUpdater.__init__(self)
    self.url = url
    self.timeout = timeout
    self.json_decoder = json.decoder.JSONDecoder()
    self.running = False
    self.manager = manager

  def __update_category_articles(self, category):
    response = urllib2.urlopen(self.url + category, timeout=20)
    js_data = response.read().decode("ISO-8859-1").replace("\\'", "'").replace(",\n]", "]")
    for article_data in self.json_decoder.decode(js_data):
      #get the image
      img_data = None
      if article_data['image_url'] != '' and self.manager.find(article_data['id']) is None:
        try:
          img_response = urllib2.urlopen(article_data['image_url'], timeout=20)
          img_data = buffer(img_response.read())
        except: pass
      article = Article(article_id=article_data['id'],
        category=category,
        title=article_data['title'],
        timestamp=article_data['timestamp'],
        body=article_data['body'],
        image=img_data,
        read=0)
      self.manager.save(article)

  def update(self):
    self.running = True
    try:
      for category in self.manager.get_categories():
        self.__update_category_articles(category)
      self.emit('update-completed')
    except:
      self.emit('update-failed')
    finally:
      self.running = False
    
  def update_on_thread(self):
    t = threading.Thread(target=self.update)
    t.start()
    return t


if __name__ == '__main__':
  import sqlite3
  from threading import Thread
  import time
  from articles import ArticlesManager

  manager = ArticlesManager(sqlite3.connect(DB_NAME, isolation_level=None, \
      check_same_thread=False))
  manager.initialize_db()
  updater = InternetArticlesUpdater(HOST_ARTICLE_UPDATER, manager)

  ut = Thread(target=updater.update)
  ut.start()
  while ut.is_alive():
    print "Updater running..."
    time.sleep(1)
