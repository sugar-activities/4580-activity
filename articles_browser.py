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
from articles import ArticlesManager
from articles_updater import InternetArticlesUpdater
import gtk
import webkit
import sqlite3
import tempfile
import os
#TODO: statistics

class ArticlesBrowser(webkit.WebView):
  def __init__(self, manager, base="file:///tmp"):
    webkit.WebView.__init__(self)
    self.get_property("settings").set_property("enable-default-context-menu", False)
    self.manager = manager
    self.base = base
    self.action_handlers = {
      'category': self._action_category,
      'view': self._action_article,
      'like': self._action_like,
      'remove_like_article': self._action_remove_like_article,
      'liked': self._action_liked,
      'remove_liked_list': self._action_remove_from_liked_list,
      'update': self._action_update,
      'search': self._action_search
    }
    self.update_status = ''
    self.updater = InternetArticlesUpdater(HOST_ARTICLE_UPDATER, manager)
    self.updater.connect('update-completed', self._on_update_complete)
    self.updater.connect('update-failed', self._on_update_fail)
    self.load_html_string("Loading...", base_uri=self.base)
    self.last_articles_list = [] # Last drawed articles list
    self.last_search = ''
    #autoupdate
    self._action_update()
    self._action_category('news')
    self.connect('navigation-policy-decision-requested', self._on_navigate_decision)
    fp, self.tmp_image = tempfile.mkstemp('.jpg') # current article image in /tmp
    os.close(fp)


  def _on_update_complete(self, updater):
    self.update_status = 'Updated'
    self._show_update_status()

  def _on_update_fail(self, updater):
    self.update_status = "Couldn't update"
    self._show_update_status()

  # @view self.action_handlers
  def _on_navigate_decision(self, view, frame, req, action, decision):
    reason = action.get_reason()
    parts =  req.get_uri().split("://")
    if len(parts) == 2 and parts[0] == 'articles':
      self.last_action = req.get_uri()
      if parts[1].find('?') >= 0:
        action, params = parts[1].split("?")
      else:
        action = parts[1]
        params = None
      if self.action_handlers.has_key(action):
         return self.action_handlers[action](params)
      return False
    return True

  def _action_update(self, params=""):
    if not self.updater.running:
      self.update_status = 'Updating...'
      self.updater.update_on_thread()
    self._show_update_status()
    return True

  def _action_category(self, category):
    self.last_search = ''
    articles_list = self.manager.get_top_list_by_category(category)
    self._show_home(category, articles_list)
    return False

  def _action_search(self, search):
    search = search.replace("%20", " ")
    self.last_search = search
    articles_list = self.manager.get_top_list_by_search(search)
    self._show_home('', articles_list)
    return False

  def _action_article(self, article_id):
    article = self.manager.find(article_id)
    if article is None:
      return True
    self.manager.mark_read(article_id)
    self._show_home(article.category, self.last_articles_list, article)

  def _action_like(self, article_id):
    self.manager.mark_liked(article_id)
    return self._action_article(article_id)

  def _action_remove_like_article(self, article_id):
    self.manager.remove_from_liked(article_id)
    return self._action_article(article_id)

  def _action_liked(self, params=''):
    html = "<html><body>"
    html += self._draw_header('likes')
    html += """<div style="width:100%; top: 80px; position: absolute;">"""
    for (article_id, title) in self.manager.get_liked():
      html += """<a href="articles://view?""" + str(article_id) + """"><h3 style='color: #44b;'>""" + title + "</h3></a>"
      html += """<a href="articles://remove_liked_list?""" + str(article_id) + """"><img src="images/unlike_btn.svg" /></a>
      <br /><hr />"""    
    html += "</div></body></html>"
    self.load_html_string(html, base_uri=self.base)

  def _action_remove_from_liked_list(self, article_id):
    self.manager.remove_from_liked(article_id)
    return self._action_liked()

    
  def _show_home(self, section, articles_list=[], article=None):
    html = "<html><body>"
    html += self._draw_header(section)
    html += "</body></html>"
    html += """<div style="width:770px; margin-top: 50px; height: 400px;">"""
    if article is None:
      html += "<h3>Choose an article.</h3>"
    else:
      html += self._draw_article(article)
    html += "</div>"
    html += """<div style="left: 840px; top: 100px; position: absolute;">"""
    html += self._draw_articles_list(articles_list)
    html += "</div>"
    self.load_html_string(html, base_uri=self.base)

  def _draw_header(self, section):
    html = "<img src='images/logo.svg'/>"
    html += """<div style="top: 10px; left: 350px; position: absolute;">"""
    for category in ['news', 'planet', 'cool', 'fun']:
      html += self._draw_category_button(category, section==category)
    html += self._draw_likes_section_button(section=='likes')
    html += "</div>"
    html += """<div style="top: 10px; left: 980px; position: absolute;">"""
    html += self._draw_update_button()
    html += "</div>"
    html += """
    <div style="top: 80px; width: 100%; left: 5px; right 5px; position: absolute;">
      <hr width="100%" />
    </div>"""
    return html

  def _draw_update_button(self):
    html = """<a style ="margin-left: 20px" href="articles://update"><img src="images/update.svg" /></a>"""
    html += """<div style ="margin-left: 90px; margin-top: -45px; font-size: 10px" id="update_status">""" + self.update_status + """</div>"""
    return html

  def _show_update_status(self):
    gtk.idle_add(self.execute_script, 'try { document.getElementById("update_status").innerHTML = "'+self.update_status+'"; } catch(e) {}')
  
  def _draw_category_button(self, category, selected):
    if selected:
      img_suffix = '_s'
    else:
      img_suffix = ''
    html = """<a style ="margin-left: 20px" href="articles://category?""" + category + """"><img src="images/"""+category+img_suffix+""".svg" /></a>"""
    return html

  def _draw_likes_section_button(self, selected):
    if selected:
      img_suffix = '_s'
    else:
      img_suffix = ''
    html = """<a style ="margin-left: 120px" href="articles://liked"><img src="images/favourites"""+img_suffix+""".svg" /></a>"""
    return html

  def _draw_articles_list(self, articles_list):
    self.last_articles_list = articles_list
    if self.last_search != '':
      search_text = self.last_search
      color = "#000"
    else:
      search_text = 'GoGoSearch...'
      color = "#777"
    html = """<input
      type="text"
      style="color: """ + color + """; width: 300px" id="search"
      name="search" value='""" + search_text + """'
      onkeypress="if(event.keyCode != 13) { return true } window.location='articles://search?'+document.getElementById('search').value;" 
      onclick = "if(this.value == 'GoGoSearch...') { this.value = ''; this.style.color = '#000'; }"
    />
    <a href="#" onclick="window.location='articles://search?'+document.getElementById('search').value; return false;"><img valign="middle" src="images/search.svg" /></a>
    <br />"""
    html += """<div style="border: 1px #777 solid; background: #fff; width: 340px; height: 650px; overflow: auto;">"""
    for (article_id, title) in articles_list:
      html += '<div style="margin-top: 4px"><a style="color: rgb(0,0,0); text-decoration: none; font-size: 22px;" href="articles://view?'+str(article_id)+'">'
      if not self.manager.was_read(article_id):
        html += '<img src="images/star.svg" />'
      html += title
      html += "</a></div>"
    html += "</div>"
    return html

  def _draw_article(self, article):
    html = ""
    if article.image is not None:
      # save to tmp and show
      fp = open(self.tmp_image, "wb")
      fp.write(article.image)
      fp.close()
      html += "<img style='margin-right: 20px' src='file://" + self.tmp_image + "?id=" + str(article.id) + "' align='left'/>"
    html += "<h3 style='color: #55d;'>" + article.title + "</h3>"
    if self.manager.is_liked(article.id):
      html += self._draw_unlike_button(article)
    else:
      html += self._draw_like_button(article)
    html +=  "<br /><smaller><smaller>"
    html += article.body.replace("<a ", "<i ").replace("</a>", "</i>")
    html +=  "</smaller></smaller>"
    return html

  def _draw_like_button(self, article):
    html = """<a href="articles://like?""" + str(article.id) + """"><img src="images/like_btn.svg" /></a>"""
    return html

  def _draw_unlike_button(self, article):
    html = """<a href="articles://remove_like_article?""" + str(article.id) + """"><img src="images/unlike_btn.svg" /></a>"""
    return html

if __name__ == '__main__':
  def _on_quit(w):
    manager.garbage_collect()
    gtk.main_quit()

  manager = ArticlesManager(sqlite3.connect(DB_NAME, isolation_level=None, \
      check_same_thread=False))
  manager.initialize_db()
  web = ArticlesBrowser(manager, "file:///home/mike/projects/news-activity/")
    
  win = gtk.Window()

  win.connect("destroy", _on_quit)
  scroller = gtk.ScrolledWindow()


  win.add(scroller)
  scroller.add(web)

  web.show()
  scroller.show()
  win.show()
  gtk.main()
