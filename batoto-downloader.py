## DESIGN
## This script takes in an URI pointing to the main page of a comic/manga/manhwa in Batoto.net
## It then parses the chapter links, goes to each, downloads the images for each chapter and compresses
## them into zip files.
## Alternatively, we may be able to specify a name, and have the script search for it and ask for results.
## All choices should be one click; the software is deferential to the user.
## Let's build the script block by block, so we may have the choice to put in a GUI later.

## FUNCTIONS
## 1. Parsing an URI to get the chapter links
## 1A.Confirm that an URI points to the main page of a comic
## 2. Given a chapter link, identifying all the pages
## 2A.Retrieve the volume number, chapter number and name of the chapter; including support for fractional and negative chapter numbers
## 3. Downloading the pages and compressing them
## 4. Given a name, searching for it in Batoto.net and retrieving the responses.

import re
import urllib2
from lxml import html
from lxml.etree import tostring
from StringIO import StringIO
import gzip

## MANGA_URI = 'http://www.batoto.net/comic/_/comics/save-the-world-in-80-days-r12245'
## MANGA_URI = 'http://www.batoto.net/comic/_/comics/tokyo-ghoul-r3056'
## MANGA_URI = 'http://www.batoto.net/comic/_/comics/nonscale-r12295'

## Regular expressions for parsing the chapter headings and retrieve volume number, chapter number, title etc
CHAPTER_TITLE_PATTERN_CHECK_VOLUME = '^Vol\.\s*([0-9]+)\s.+'
CHAPTER_TITLE_PATTERN_WITH_VOLUME = "Vol.\s*([0-9]+)\s*Ch.\s*([0-9\.v]+):?\s+(.+)"
CHAPTER_TITLE_PATTERN_NO_VOLUME = "Ch.\s*([0-9\.v]+):?\s+(.+)"

## Generic class representing a manga chapter
class MangaChapter(object):
    def __init__(self, chapter_number, chapter_link, chapter_title=None, volume_number=None, group_name=None):
        self.chapter_number = chapter_number
        self.volume_number = volume_number
        self.chapter_title = chapter_title
        self.chapter_link = chapter_link
        self.group_name = group_name

    def downloadChapter(self):
        raise NotImplementedError # To be overridden in subclasses

    def show(self):
        print "Vol: ", self.volume_number, " Ch: ", self.chapter_number, " - ", self.chapter_title, ", by: ", self.group_name

## Subclass representing a manga chapter from Batoto
class MangaChapterBatoto(MangaChapter):
    def __init__(self, chapter_number, chapter_link, chapter_title=None, volume_number=None, group_name=None):
        super(MangaChapterBatoto, self).__init__(chapter_number, chapter_link, chapter_title, volume_number, group_name)

    def downloadChapter(self):
        pass # TODO

## Generic class representing a manga
class Manga(object):
    def __init__(self, manga_url, manga_name=None):
        self.name = manga_name
        self.url = manga_url
        self.chapter_list = []

    def addMangaChapter(self, manga_chapter):
        self.chapter_list.append(manga_chapter)
        print "Added chapter"

    def retrieveAllChapters(self):
        raise NotImplementedError # To be overridden in subclasses

## Subclass representing a manga hosted in Batoto
class MangaBatoto(Manga):
    def __init__(self, manga_url, manga_name=None):
        super(MangaBatoto, self).__init__(manga_url, manga_name)

    def retrieveAllChapters(self):
        request = urllib2.Request(self.url)
        request.add_header('Accept-encoding', 'gzip')
        response = urllib2.urlopen(request)
        if response.info().get('Content-Encoding') == 'gzip': # Large pages are often gzipped
            buf = StringIO(response.read())
            data = gzip.GzipFile(fileobj=buf)
        else:
            data = response
        page =  html.parse(data)
        ## print tostring(page) # For testing only
        if self.name is None:
            self.name = page.xpath('//h1[@class="ipsType_pagetitle"]')[0].text.strip()
            print "Set name to: " + self.name
        for ch_row in page.xpath('//table[@class="ipb_table chapters_list"]/tbody/tr')[1:]:
            if ch_row.get('class') == 'row lang_English chapter_row':
                ch_a = ch_row.xpath('.//td')[0].xpath('.//a')[0]
                ch_url = ch_a.get('href')
                ch_name = ch_a.text_content().strip(' \t\n\r')
                vol_no = ""
                ch_no = ""
                ch_title = ""
                if re.match(CHAPTER_TITLE_PATTERN_CHECK_VOLUME, ch_name):
                    m = re.match(CHAPTER_TITLE_PATTERN_WITH_VOLUME, ch_name)
                    vol_no = m.group(1)
                    ch_no = m.group(2)
                    ch_title = m.group(3)
                else:
                    m = re.match(CHAPTER_TITLE_PATTERN_NO_VOLUME, ch_name)
                    ch_no = m.group(1)
                    ch_title = m.group(2)
                assert(ch_no != "") # Chapter number is mandatory
                gr_a = ch_row.xpath('.//td')[2].xpath('.//a')[0]
                gr_name = gr_a.text.strip(' \t\n\r')
                self.addMangaChapter(MangaChapterBatoto(ch_no, ch_url, ch_title, vol_no, gr_name))


# Data structures that help instantiating the right subclasses based on URL
URI_TYPES = ['BATOTO', 'OTHER']
MANGA_CHAPTER_TYPES = {'BATOTO' : MangaChapterBatoto,
                        'OTHER' : MangaChapter}
MANGA_TYPES = {'BATOTO' : MangaBatoto,
                'OTHER' : Manga}

uri = raw_input("Enter Batoto URL: ")
if re.compile('(http://)?www\.batoto\.net.+-r[0-9]+').match(uri):
    URI_TYPE = 'BATOTO'
else:
    URI_TYPE = 'OTHER'
manga = MANGA_TYPES[URI_TYPE](uri) # Instantiate manga object
manga.retrieveAllChapters() # Add all chapters to it
for chapter in manga.chapter_list:
    chapter.show() # For testing only
    ## TODO Need to implement downloadChapter()
