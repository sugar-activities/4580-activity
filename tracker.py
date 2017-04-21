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

import urllib2
import threading

class ArticlesTracker:
  def __init__(self, url, timeout=20):
    self.url = url
    self.timeout = timeout
    

  def track_action(self, action, article_id):
    try:
      urllib2.urlopen(self.url + '?action=' + action + '&article=' + str(article_id), timeout=20)
    except:
      pass

  def track_action_on_thread(self, action, article_id):
    t = threading.Thread(target=self.track_action, args=[action, article_id])
    t.start()
    return t


if __name__ == '__main__':
  tracker = ArticlesTracker('http://www.gogonews.com/updatestat.php')
  t=tracker.track_action_on_thread('read', 213)
  t.join()
