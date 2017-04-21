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
import gobject
from gtk import gdk
import os
import tempfile
import re

class Article:
  def __init__(self, article_id, category, title, timestamp, body, image, read):
    self.id = article_id
    self.title = title
    self.body = body
    self.image = image
    self.timestamp = timestamp
    self.category = category
    self.read = read

  def get_image_pixbuf(self):
    fp, file_name = tempfile.mkstemp('.jpg')
    os.write(fp, self.image)
    os.close(fp)
    pbuf = gdk.pixbuf_new_from_file(file_name)
    os.remove(file_name)
    return pbuf

  def __str__(self):
    return "Id:" + str(self.id) + " Category:" + str(self.category) + \
    " Title:" + str(self.title) + " Body:" + str(self.body) + \
    " Ts:" + str(self.timestamp)

  def __unicode__(self):
    return self.__str__()


class ArticlesManager(gobject.GObject):
  """
  Manages the articles DB
  """
  __gsignals__ = {
    'article-read': (gobject.SIGNAL_RUN_LAST,
                        gobject.TYPE_NONE, [gobject.TYPE_STRING]),
    'article-liked': (gobject.SIGNAL_RUN_LAST,
                        gobject.TYPE_NONE, [gobject.TYPE_STRING])
  }

  def __init__(self, db):
    gobject.GObject.__init__(self)
    self.db = db

  def get_top_list_by_category(self, category, limit=20):
    return self.db.execute("SELECT id, title FROM article WHERE category = ? \
        ORDER BY timestamp DESC LIMIT ?", (category, limit)).fetchall()

  def get_top_list_by_search(self, search, limit=20):
    search_words = self.__get_words_for_search(search)
    sql = """SELECT a.id, a.title
      FROM article a 
      INNER JOIN article_word aw ON aw.article_id = a.id
      WHERE 0 """
    for w in search_words:
      sql += " OR aw.word LIKE '%%" + w + "%%'"
    sql += """
      GROUP BY a.id, a.title
      ORDER BY COUNT(*) DESC, timestamp DESC LIMIT ?"""
    return self.db.execute(sql, (limit,)).fetchall()


  def find(self, article_id):
    curr = self.db.execute("SELECT id, category, title, timestamp, body, image, read \
    FROM article WHERE id = ?", (article_id,))
    row = curr.fetchone()
    if row is None:
      return None
    if row[5] is None:
      img_data = None
    else:
      img_data = buffer(row[5])
    return Article(
      row[0],
      row[1],
      row[2],
      row[3],
      row[4],
      img_data,
      row[6]
    )

  def get_liked(self):
    return self.db.execute("""SELECT id, title FROM article
    INNER JOIN likes ON id = article_id ORDER BY timestamp DESC""").fetchall()

  def is_liked(self, article_id):
    row = self.db.execute("SELECT article_id FROM likes WHERE article_id = ?", (article_id,)).fetchone()
    return row is not None

  def was_read(self, article_id):
    row = self.db.execute("SELECT read FROM article WHERE id = ?", (article_id,)).fetchone()
    if row is not None and row[0] == 1:
      return True
    return False

  def mark_liked(self, article_id):
    try:
      self.db.execute("INSERT INTO likes VALUES (?)", (article_id,))
      self.emit('article-liked', article_id)
    except:
      pass

  def remove_from_liked(self, article_id):
    self.db.execute("DELETE FROM likes WHERE article_id = ?", (article_id,))

  def mark_read(self, article_id):
    self.db.execute("UPDATE article SET read=1 WHERE id = ?", (article_id,))
    self.emit('article-read', article_id)

  def garbage_collect(self):
    for row in self.db.execute("SELECT name FROM category").fetchall():
      category = row[0]
      self.db.execute("""
      DELETE FROM article
      WHERE
        category = ?
        AND id NOT IN (SELECT article_id FROM likes)
        AND id NOT IN (SELECT a2.id FROM article a2 WHERE  
        a2.category = ? ORDER BY timestamp DESC LIMIT 20);
      """, (category, category,))

  def save(self, article):
    curr = self.db.execute("SELECT 1 FROM article WHERE id = ?", (article.id,))
    if curr.fetchone() is not None:
      return
    self.db.execute("""INSERT INTO article \
    (id, title, body, image, timestamp, category)
    VALUES (?, ?, ?, ?, ?, ?)""", (article.id, article.title, article.body,
    article.image, article.timestamp, article.category))
    self.build_index(article)

  def __get_words_for_search(self, text):
    clean = re.sub('<[^<]+?>', '', text).replace("&nbsp;", " ").replace("\n", " ")
    clean = re.sub('[\n\t\\-\r\\.,]', ' ', clean)
    clean = re.sub('&.{0,5};', '', clean)
    clean = clean.lower()
    return filter(lambda s: s != '', clean.split(" "))

  def build_index(self, article):
    for word in self.__get_words_for_search(article.title + " " + article.body):
      if word != '':
        try:
          self.db.execute("INSERT INTO article_word (article_id, word) VALUES (?, ?)", (article.id, word))
        except: pass


  def initialize_db(self):
    """
    Initialize DB schema
    """
    self.db.execute("""
CREATE TABLE IF NOT EXISTS article (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title VARCHAR(255),
  category VARCHAR(255),
  body TEXT,
  image BLOB,
  timestamp INTEGER,
  read BOOLEAN DEFAULT 0
)""")
    self.db.execute("""
CREATE INDEX IF NOT EXISTS article_category ON article(category);
  """)
    self.db.execute("""
CREATE TABLE IF NOT EXISTS likes (
  article_id INTEGER PRIMARY KEY REFERENCES article(id)
);""")
    self.db.execute("""
CREATE TABLE IF NOT EXISTS article_word (
  article_id INTEGER FOREIGNKEY REFERENCES article(id) ON DELETE CASCADE,
  word VARCHAR(255),
  CONSTRAINT article_word_uniq UNIQUE (article_id, word)
);""")
    self.db.execute("""
CREATE INDEX IF NOT EXISTS article_word_idx ON article_word(word);
  """)
    self.db.execute("""
CREATE TABLE IF NOT EXISTS category (
  name VARCHAR(255) PRIMARY KEY
)""")
    for category in ['news', 'planet', 'cool', 'fun']:
      try:
        self.db.execute("INSERT INTO category VALUES (?)", (category,))
      except:
        pass

  def get_categories(self):
    sql = "SELECT name FROM category"
    return map(lambda x: x[0], self.db.execute(sql).fetchall())

gobject.type_register(ArticlesManager)

if __name__ == '__main__':
  import sqlite3

  db = sqlite3.connect(DB_NAME, isolation_level=None)
  manager = ArticlesManager(db)
  manager.initialize_db()
  manager.is_liked(234334)
  img = open("test.jpg", "r")
  img_data = img.read()
  img.close()

  art = Article(123, 'News test', 'title', 34325423, 'hello', buffer(img_data))
  manager.save(art)
  print "Article saved in DB", art

  saved_art = manager.find(123)
  print "Retrieving article:", saved_art

  img_out = open("test_out.jpg", "w")
  img_out.write(saved_art.image)
  img_out.close()
  print "Img as pixbuf:", saved_art.get_image_pixbuf()

  print "Testing liking the article (123)"
  manager.mark_liked(123)
  print manager.get_liked()
  manager.remove_from_liked(123)
  for result in manager.get_top_list_by_search("happy birthday"):
    print result
  manager.garbage_collect()
  db.close()
