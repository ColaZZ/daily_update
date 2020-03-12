# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy


class DailyUpdateItem(scrapy.Item):
    title = scrapy.Field()              # 小说标题

    chapter_name = scrapy.Field()
    chapter_content = scrapy.Field()
    chapter_url_base = scrapy.Field()

    article_url = scrapy.Field()
    lastest_url = scrapy.Field()
    last_chapter = scrapy.Field()
    author = scrapy.Field()
    updated_at = scrapy.Field()
    status = scrapy.Field()
    is_full = scrapy.Field()
    category_id = scrapy.Field()
    category = scrapy.Field()

    allowed_domain = scrapy.Field()
    article_title = scrapy.Field()
    article_url_base = scrapy.Field()

    info = scrapy.Field()
    thumb = scrapy.Field()
    lastest_chapter_id = scrapy.Field()

    chapter_sort = scrapy.Field()
    words = scrapy.Field()

