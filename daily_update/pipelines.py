# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

import os
import time
import pymysql
import redis
import requests

from .settings import REDIS_HOST, REDIS_PORT, REDIS_DB


class DailyUpdatePipeline(object):
    def __init__(self):
        self.conn = pymysql.connect(host='127.0.0.1', user='root',
                                    passwd='1372561QWE', db='fiction', charset='utf8')
        self.cur = self.conn.cursor()
        redis_pool = redis.ConnectionPool(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                                          decode_responses=True)  # redis缓存连接池
        self.redis = redis.StrictRedis(connection_pool=redis_pool, decode_responses=True)

    # 主要处理方法
    def process_item(self, item, spider):
        # print("item", item)
        title = item.get('article_title', '')
        chapter_url_base = item.get('chapter_url_base', '')
        article_title = item.get('article_title', '')

        # 保存小说信息入库
        author = item.get('author', '')
        url = item.get('article_url', '')
        info = item.get('info', '')
        thumb = item.get('thumb', '')
        category_id = item.get('category_id', 0)
        category = item.get('category', 'default')
        last_chapter = item.get('last_chapter', ' ')
        chapter_name = item.get('chapter_name', ' ')
        chapter_sort = item.get('chapter_sort', -1)
        is_full = item.get('is_full', 2)        # status 判断
        status = item.get('status', '')
        allowed_domain = item.get('allowed_domain', '')
        article_url_base = item.get('article_url_base', '')
        lastest_chapter_id = item.get('lastest_chapter_id', '')
        words = item.get('words', '')

        temp_path_base = str(article_url_base)
        tp_list = temp_path_base.split("/")
        temp_path = tp_list[2]
        chapter_id = int(chapter_url_base[:-5])

        # 爬虫更新时间
        updated_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        # 写入小说缩略图
        r = requests.get(thumb, stream=True)
        if r.status_code != 404:
            thumb_path = "/volume/novel_context" + os.path.sep + "35kushu.com" + os.path.sep + "thumb"
            img_path = thumb_path + os.path.sep + str(chapter_url_base[:-5]) + ".jpg"
            with open(img_path, 'wb') as f:
                for chunk in r.iter_content():
                    f.write(chunk)
        else:
            img_path = ""

        # update/insert articles表
        if not self.redis.hexists("articels_h", title):
            sql = "insert into articles(title, pinyin, author, url, category_id, category, is_full, `status`, info, " \
                  "thumb, updated_at, last_chapter, last_chapter_id, words) values " \
                  "(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON DUPLICATE KEY UPDATE " \
                  "updated_at=%s, last_chapter=%s, last_chapter_id =%s, words=%s "
            try:
                self.cur.execute(sql, (title, int(temp_path), author, url, category_id, category, is_full, status,
                                       info, img_path, updated_at, last_chapter, lastest_chapter_id, words, updated_at,
                                       last_chapter, lastest_chapter_id, words))
                self.conn.commit()
                self.redis.hset("articles_h", title, 1)
            except Exception as e:
                if e.args[0] == 1062:
                    self.redis.hset("articles_h", title, 1)
                else:
                    print("1", e)

        r_title_id = int(self.redis.hget("articles_h", title))
        if r_title_id not in (-1, 0, 1):
            article_id = r_title_id
        else:
            sql_id = "select id from articles where url =%s"
            self.cur.execute(sql_id, [url])
            result = self.cur.fetchone()
            article_id = result[0] if result else -1
            self.redis.hset("articles_h", title, article_id)

        sql_chapter = "insert into articles_chapter(article_id, chapter_id, chapter_name, updated_at, chapter_sort) " \
                      "values(%s, %s, %s, %s, %s)"

        try:
            if article_id != 1:
                self.cur.execute(sql_chapter, (article_id, chapter_id, chapter_name, updated_at, chapter_sort))
                self.conn.commit()
        except Exception as e:
            print("2", e)

        # linux路径 TODO
        cur_path = "/home/novel" + os.path.sep + allowed_domain
        target_path = cur_path + os.path.sep + str(category_id) + os.path.sep + temp_path
        filename_path = cur_path + os.path.sep + str(category_id) + os.path.sep + temp_path + os.path.sep + \
                        str(chapter_url_base[:-5]) + '.txt'

        if not os.path.exists(target_path):
            os.makedirs(target_path)
        with open(filename_path, 'w', encoding='utf-8') as f:
            f.write(item['chapter_content'])
        return item
