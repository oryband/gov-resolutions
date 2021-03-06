# -*- coding: utf-8 -*-

import arrow
import json
import re

from scrapy import signals
from scrapy.exporters import JsonLinesItemExporter


class ResolutionError(RuntimeError):
    """Raised when crawling resulted in unexpected results.

    e.g. multiple titles, empty bodies, etc.
    """
    pass


class ResolutionPipeline(object):
    """Pipeline used for ResolutionSpider."""
    def __init__(self):
        self.file = None
        self.exporter = None

        # compile regular expressions:

        # input looks like 'dec14R.aspx'
        # we need the resolution number (14R)
        self.resolution_number_pattern = re.compile(r"^\D+(?P<number>.+?)\..*$")

        # input looks like 'ממשלה/הממשלה ה - 34 בנימין נתניהו;'
        # we need the government number (34) and prime minister name (בנימין נתניהו)
        self.gov_pattern = re.compile(r'^.+\s??\-\s?(?P<gov_number>.+?)\s+?(?P<pm_name>.+?);?$')

    def open_spider(self, spider):
        """Initialize export JSON lines file."""
        self.file = open("gov.json", "wb")
        self.exporter = JsonLinesItemExporter(self.file, ensure_ascii=False)
        self.exporter.start_exporting()

    def close_spider(self, spider):
        """Close export file."""
        self.file.close()
        self.exporter.finish_exporting()

    def process_item(self, item, spider):
        """Sanitize text for each field, and export to file."""
        try:
            data = {
                'url': item["url"],
                'date': self.get_date(item).timestamp,
                'resolution_number': self.get_resolution_number(item),
                'gov_number': self.get_gov_number(item),
                'pm_name': self.get_pm_name(item),
                'title': self.get_title(item),
                'subject': self.get_subject(item),
                'body': self.get_body(item),
            }
        except ResolutionError as ex:
            # if one of the fields fails sanitation,
            # raise and exception
            # and export the url leading to the specific resolution
            # for later (human) review
            self.exporter.export_item({'error': repr(ex),
                                       'url': item["url"],
                                      })
        else:
            self.exporter.export_item(data)

        return item

    # the following are specific field handling functions
    # e.g. cleaning, stripping, etc.
    # these should be called before dumping the data

    def get_date(self, item):
        if len(item["date"]) != 1:
            raise ResolutionError("Date field length is not 1 for item %s", item)
        return arrow.get(item["date"][0], "YYYYMMDD")

    def get_resolution_number(self, item):
        if len(item["resolution_number"]) != 1:
            raise ResolutionError("Resolution number field length is not 1 for item %s", item)
        return self.resolution_number_pattern.search(item["resolution_number"][0]).group('number')

    def get_gov_number(self, item):
        if len(item["gov"]) != 1:
            raise ResolutionError("Government field length is not 1 for item %s", item)
        gov_match = self.gov_pattern.search(item["gov"][0])
        return gov_match.group("gov_number")

    def get_pm_name(self, item):
        if len(item["gov"]) != 1:
            raise ResolutionError("Government field length is not 1 for item %s", item)
        gov_match = self.gov_pattern.search(item["gov"][0])
        return gov_match.group("pm_name")

    def get_title(self, item):
        if len(item["title"]) == 0:
            raise ResolutionError("Title fields is empty for item %s", item)
        return '\n'.join(item["title"]).strip()

    def get_subject(self, item):
        if len(item["subject"]) == 0:
            raise ResolutionError("Subject field is empty for item %s", item)
        return '\n'.join(item["subject"]).strip()

    def get_body(self, item):
        if len(item["body"]) == 0:
            raise ResolutionError("Body field is empty for item %s", item)
        # return '\n'.join(item["body"]).strip()

        # body is originally a list of lines
        # it is intentionally not stripped
        # some resolutions have custom css, tables,
        # and other crap which i'd rather not process here,
        # but in a later stage, unrelated to the scraper
        return item["body"]
