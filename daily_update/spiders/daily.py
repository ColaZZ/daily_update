# -*- coding: utf-8 -*-
import copy
import re
import time

import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.http import Request
from scrapy_redis.spiders import RedisSpider

from ..utils import changeChineseNumToArab
from ..items import DailyUpdateItem


CATEGORY_MAPS = {
    '玄幻小说': 1,
    '仙侠小说': 2,
    '都市小说': 3,
    '军史小说': 4,
    '网游小说': 5,
    '科幻小说': 6,
    '恐怖小说': 7,
    '其他小说': 8
}


class DailySpider(scrapy.Spider):
    name = 'daily'

    allowed_domains = ['xkushu.com']
    redis_key = "novel:start_urls"
    start_urls = ['https://www.xkushu.com']

    # rules = (
    #     Rule(LinkExtractor(allow=r'Items/'), callback='parse_item', follow=True),
    # )

    # def parse_item(self, response):
    #     item = {}
    #     #item['domain_id'] = response.xpath('//input[@id="sid"]/@value').get()
    #     #item['name'] = response.xpath('//div[@id="name"]').get()
    #     #item['description'] = response.xpath('//div[@id="description"]').get()
    #     return item

    def parse(self, response):
        # tags链接
        tag_url = response.xpath(
            '//div[@class="menu_list_id lan1"]/li/a/@href | //div[@class="menu_list_id lan1"]/li/a/text()').extract()


        tag_urls = [tag_url[i:i + 2] for i in range(2, len(tag_url), 2)]

        # print(tag_urls, len(tag_urls))
        for tu in tag_urls[:8]:
            tag_url = self.start_urls[0] + tu[0]
            category = tu[1]

            category_id = CATEGORY_MAPS.get(category)
            meta = {
                "category_id": copy.deepcopy(category_id),
                "category": copy.deepcopy(category)
            }
            # 下一步
            yield Request(tag_url, meta=copy.deepcopy(meta), callback=self.parse_tag_detail)

    #
    def parse_tag_detail(self, response):
        # 传入上层meta
        meta_start = response.meta
        novel_info_1 = response.xpath('//div[@id="centerl"]/div[@id="content"]/table/tr[not(@align)]')

        for ni1 in novel_info_1:
            tdd = ni1.xpath('td')
            article_url = self.start_urls[0] + tdd[0].xpath('a/@href').extract_first(default=' ')
            article_title = tdd[0].xpath('a/text()').extract_first(default=' ')
            author = tdd[2].xpath('text()').extract_first(default=" ")
            # thumb = ni1.xpath('span[@class="pic"]/a/img/@src').extract_first(default=' ')

            meta = response.meta
            meta["article_url"] = article_url
            meta["article_title"] = article_title
            meta["author"] = author
            # meta["thumb"] = thumb
            meta["article_url_base"] = article_url[20:]

            yield Request(article_url, meta=meta, callback=self.parse_menu)

        next_page = response.xpath('//div[@class="pagelink"]/a[@class="next"]/@href').extract_first(default=' ')
        if next_page:
            yield Request(next_page, meta=meta_start, callback=self.parse_tag_detail)

    def parse_menu(self, response):
        today = time.strftime("%Y-%m-%d", time.localtime())
        update_time = response.xpath('//head/meta[@property="og:novel:update_time"]/@content').extract_()
        if update_time >= today:
            menu_list = response.xpath('//div[@id="indexmain"]//div[@id="list"]/dl/dd/a/@title '
                                       '| //div[@id="indexmain"]//div[@id="list"]/dl/dd/a/@href ').extract()
            head_list = response.xpath(
                '//head/meta[@property="og:description"]/@content | //head/meta[@property="og:image"]/@content').extract()
            status = response.xpath('//head/meta[@property="og:novel:status"]/@content').extract_first(default=' ')
            last_chapter_list = response.xpath(
                '//div[@class="ml_content"]//div[@class="zb"]//div[@class="newest"]//div[@class="last9"]/ul/li/a/@href | '
                '//div[@class="ml_content"]//div[@class="zb"]//div[@class="newest"]//div[@class="last9"]/ul/li/a/text()').extract()
            last_chapter = last_chapter_list[1]
            lastest_chapter_id = last_chapter_list[0][:-5]

            if status == "连载中":
                is_full = 0
            elif status == "已完结":
                is_full = 1
            else:
                is_full = 2


            menu_list_group = [menu_list[i:i + 2] for i in range(0, len(menu_list), 2)]
            meta = response.meta
            meta["last_chapter"] = last_chapter
            meta["lastest_chapter_id"] = lastest_chapter_id

            for index, ml in enumerate(menu_list_group):
                chapter_url_base = ml[0]
                chapter_name = ml[1]
                # chapter_sort 即为我们自定义的章节顺序
                count = chapter_name.count("第")
                re_str = (count - 1) * "." + "第(.*?)章"
                result = re.findall(re_str, chapter_name)
                if not result:
                    if ("序" in result) or ("楔子" in result):
                        chapter_sort = 0
                    else:
                        chapter_sort = -1
                else:
                    try:
                        chapter_sort = int(changeChineseNumToArab(result[0]))
                    except:
                        break

                article_title = meta.get("article_title", "")
                chapter_url = response.meta["article_url"] + chapter_url_base
                meta["chapter_url_base"] = chapter_url_base
                meta["chapter_name"] = chapter_name
                meta["article_title"] = article_title
                meta['info'] = head_list[0][:511]
                meta['chapter_sort'] = chapter_sort
                meta['status'] = status
                meta['is_full'] = is_full
                meta['thumb'] = head_list[1]

                yield Request(chapter_url, meta=meta, callback=self.parse_content)

    def parse_content(self, response):
        content = response.xpath('//div[@id="main"]/div[@id="content"]/text()').extract()
        content = "<br><br>".join(content[1:])
        words = len(content)

        item = DailyUpdateItem()
        item['article_title'] = response.meta["article_title"]
        item['chapter_name'] = response.meta["chapter_name"]
        item['chapter_content'] = content
        item['chapter_url_base'] = response.meta["chapter_url_base"]
        item['article_url'] = response.meta["article_url"]
        item['author'] = response.meta.get("author", "")
        item['category_id'] = response.meta.get("category_id", 0)
        item['category'] = response.meta.get("category", "")
        item['is_full'] = response.meta.get("is_full", 0)
        item['status'] = response.meta.get("status", 1)
        item['last_chapter'] = response.meta.get("last_chapter", " ")
        item['allowed_domain'] = self.allowed_domains[0]
        item['article_title'] = response.meta.get("article_title", "")
        item['article_url_base'] = response.meta.get("article_url_base", "")
        item['info'] = response.meta.get("info", "")
        item['thumb'] = response.meta.get("thumb")
        item['lastest_chapter_id'] = response.meta.get("lastest_chapter_id", "")
        item['chapter_sort'] = response.meta.get("chapter_sort", -1)
        item['words'] = words

        yield item

