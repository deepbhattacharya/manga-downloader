## DESIGN
## This script takes in an url pointing to the main page of a comic/manga/manhwa in Batoto.net
## It then parses the chapter links, goes to each, downloads the images for each chapter and compresses
## them into zip files.
## Alternatively, we may be able to specify a name, and have the script search for it and ask for results.
## All choices should be one click; the software is deferential to the user.
## Let's build the script block by block, so we may have the choice to put in a GUI later.

## FUNCTIONS
## 1. Parsing an url to get the chapter links
## 1A.Confirm that an url points to the main page of a comic
## 2. Given a chapter link, identifying all the pages
## 2A.Retrieve the volume number, chapter number and name of the chapter; including support for fractional and negative chapter numbers
## 3. Downloading the pages and compressing them

import re
import urllib2
from lxml import html
from lxml.etree import tostring
from StringIO import StringIO
import gzip
import shutil
import os
import os.path
import glob
import sys
import zipfile
import urlparse
import argparse
import unicodedata
from string import maketrans

## Constants
__DOWNLOAD__ = True
__DEBUG__ = False
__RETRY_URL__ = 5

## Function to compress a directory
def zipdir(path, zipf):
    for root, dirs, files in os.walk(path):
        for f in files:
            zipf.write(os.path.join(root, f), arcname = os.path.basename(f))

## Function to ask for URL
def checkURLType(url_input):
    print "Checking: " + url_input
    url_ok = False
    for url_type in URL_TYPES:
        if re.compile(URL_TYPES[url_type]['url']).match(url_input):
            print "Site supported: " + url_type
            url_ok = True
            break
    if not url_ok:
        print "URL not supported or unknown"
        exit(1)
    return url_type

## Function to get a webpage
def readURL(url):
    if url[0] == '/':
        url = url_type + url
    if __DEBUG__:
        print "Reading url: " + url
    request = urllib2.Request(url)
    request.add_header('Accept-encoding', 'gzip')
    for i in range(1, __RETRY_URL__):
        try:
            response = urllib2.urlopen(request)
            if response.info().get('Content-Encoding') == 'gzip': # Large pages are often gzipped
                buf = StringIO(response.read())
                data = gzip.GzipFile(fileobj = buf)
            else:
                data = response
            return data
        except:
            pass

## Function to retrieve and parse an HTML page
def readHTML(url):
    data = readURL(url)
    page =  html.parse(data)
    return page

## Function to download an image from a direct URL
def downloadImage(img_url, file_path):
    data = readURL(img_url)
    with open(file_path, 'wb') as f:
        f.write(data.read())

## Fuction to clean the path from problematic characters.
def cleanPath(pathString):
    if isinstance(pathString, unicode):
        pathString = unicodedata.normalize('NFKD', pathString).encode('ascii', 'ignore')
    pathString = pathString.translate(None, '\/:*?<>|')
    transTable = maketrans("\"", "\'")
    pathString = pathString.translate(transTable)
    return pathString

## Generic class representing a manga chapter
class MangaChapter(object):
    def __init__(self, manga_name, chapter_number, chapter_url, chapter_root_path, chapter_title=None, volume_number=None, group_name=None):
        self.chapter_number = chapter_number
        self.volume_number = volume_number
        self.chapter_title = chapter_title
        self.chapter_url = chapter_url
        self.group_name = group_name
        self.chapter_root_path = chapter_root_path
        self.page_list = []
        self.page_num = 0
        prefix = [manga_name]
        if volume_number is not None:
            prefix.append("Volume " + volume_number)
        prefix.append("Chapter " + chapter_number)
        if chapter_title is not None:
            prefix.append("- " + chapter_title)
        if group_name is not None:
            prefix.append("[" + group_name + "]")
        self.prefix = " ".join(prefix)

    def show(self):
        print "Vol: ", self.volume_number, " Ch: ", self.chapter_number, " - ", self.chapter_title, ", by: ", self.group_name

    def addPage(self, page_url):
        self.page_list.append(page_url)

    def retrieveAllPages(self):
        raise NotImplementedError # To be overridden in subclasses

    def downloadPage(self, page_url, page_file_path):
        raise NotImplementedError # To be overridden in subclasses
    
    def downloadChapter(self):
        pathA = cleanPath(self.chapter_root_path)
        pathB = cleanPath(self.prefix)
        dir_path = os.path.join(pathA, pathB)
        if verbose:
            print ""
            print dir_path
        zip_path = dir_path + ".zip"
        if os.path.exists(zip_path):
            zipf = zipfile.ZipFile(zip_path)
            if zipf.testzip() is None:
                if __DEBUG__:
                    print "Skipping chapter " + self.chapter_number
                return
            else:
                os.remove(zip_path)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
        os.makedirs(dir_path)
        self.retrieveAllPages()
        for page_url in self.page_list:
            self.page_num = self.page_num + 1
            page_path = os.path.join(dir_path, "p" + str(self.page_num).zfill(3))
            self.downloadPage(page_url, page_path)
        zipf = zipfile.ZipFile(zip_path, "w")
        zipdir(dir_path, zipf)
        zipf.close()
        shutil.rmtree(dir_path)

## Subclass representing a manga chapter from Batoto
class MangaChapterBatoto(MangaChapter):
    def __init__(self, manga_name, chapter_number, chapter_url, chapter_root_path, chapter_title=None, volume_number=None, group_name=None):
        super(MangaChapterBatoto, self).__init__(manga_name, chapter_number, chapter_url, chapter_root_path, chapter_title, volume_number, group_name)

    def retrieveAllPages(self):
        ## Look at the options of select element at //*[@id="page_select"]
        ## Take the value for each (page url) and save them
        webpage = readHTML(self.chapter_url)
        if webpage.xpath("//a[@href='?supress_webtoon=t']"): ## Long strip format for webtoons
            if __DEBUG__:
                print "Webtoon: reading in long strip format"
            s = webpage.xpath("//div[@id='read_settings']/following-sibling::div/img")
            for l in s:
                self.addPage(l.get('src'))
        else:
            s = webpage.xpath("//*[@id='page_select']")[0]
            for option in s.xpath('.//option[@value]'):
                self.addPage(option.get('value'))

    def downloadPage(self, page_url, page_file_path):
        ## Get @src attribute of element at //*[@id="comic_page"]
        if urlparse.urlparse(page_url).path.split('.')[-1] in ['jpg', 'png']:
            img_url = page_url
        else:
            webpage = readHTML(page_url)
            img_url = webpage.xpath('//*[@id="comic_page"]')[0].get('src')
        downloadImage(img_url, page_file_path + "." + urlparse.urlparse(img_url).path.split('.')[-1])

## Subclass representing a manga chapter from Starkana
class MangaChapterStarkana(MangaChapter):
    def __init__(self, manga_name, chapter_number, chapter_url, chapter_root_path):
        super(MangaChapterStarkana, self).__init__(manga_name, chapter_number, chapter_url, chapter_root_path)

    def retrieveAllPages(self):
        ## Look at the options of select element at //*[@id="page_switch"]
        ## Take the value for each (page url) and save them
        webpage = readHTML(self.chapter_url)
        s = webpage.xpath("//*[@id='page_switch']")[0]
        for option in s.xpath('.//option[@value]'):
            self.addPage(option.get('value'))

    def downloadPage(self, page_url, page_file_path):
        ## Get @src attribute of element at //*[@id="pic"/div/img]
        webpage = readHTML(page_url)
        img_url = webpage.xpath('//*[@id="pic"]/div/img')[0].get('src')
        downloadImage(img_url, page_file_path + "." + urlparse.urlparse(img_url).path.split('.')[-1])

## Generic class representing a manga
class Manga(object):
    def __init__(self, manga_url, manga_name=None):
        self.name = manga_name
        self.url = manga_url
        self.chapter_list = []

    def createFolder(self, path):
        path = cleanPath(path)
        if not os.path.exists(path):
            os.makedirs(path)
        with open(path + '/mangadl.link', 'w') as f:
            f.write(self.url)

    def addMangaChapter(self, manga_chapter):
        self.chapter_list.insert(0, manga_chapter)
        if __DEBUG__:
            print "Added chapter " + manga_chapter.chapter_number

    def retrieveAllChapters(self):
        raise NotImplementedError # To be overridden in subclasses

## Subclass representing a manga hosted in Batoto
class MangaBatoto(Manga):
    def __init__(self, manga_url, manga_name=None):
        super(MangaBatoto, self).__init__(manga_url, manga_name)
        ## Regular expressions for parsing the chapter headings and retrieve volume number, chapter number, title etc
        self.CHAPTER_TITLE_PATTERN_CHECK_VOLUME = '^Vol\..+'
        self.CHAPTER_TITLE_PATTERN_WITH_VOLUME = '^Vol\.\s*([0-9]+|Extra)\s*Ch.\s*([0-9\.vA-Za-z-\(\)]+):?\s+(.+)'
        self.CHAPTER_TITLE_PATTERN_NO_VOLUME = '^Ch.\s*([0-9\.vA-Za-z-\(\)]+):?\s+(.+)'

    def retrieveAllChapters(self):
        webpage = readHTML(self.url)
        ## print tostring(page) # For testing only
        if self.name is None:
            self.name = webpage.xpath('//h1[@class="ipsType_pagetitle"]')[0].text.strip()
            print "Set name to: " + self.name
        assert(self.name is not None)
        ch_path = "Batoto - " + self.name
        self.createFolder(ch_path)
        for ch_row in webpage.xpath('//table[@class="ipb_table chapters_list"]/tbody/tr')[1:]:
            if ch_row.get('class') == 'row lang_English chapter_row':
                ch_a = ch_row.xpath('.//td')[0].xpath('.//a')[0]
                ch_url = ch_a.get('href')
                ch_name = unicode(ch_a.text_content().strip(' \t\n\r')).translate(dict.fromkeys(map(ord, '\\/'), None))
                if __DEBUG__:
                    print ch_name
                vol_no = None
                ch_no = None
                ch_title = None
                if re.match(self.CHAPTER_TITLE_PATTERN_CHECK_VOLUME, ch_name):
                    m = re.match(self.CHAPTER_TITLE_PATTERN_WITH_VOLUME, ch_name)
                    vol_no = m.group(1)
                    ch_no = m.group(2)
                    ch_title = m.group(3)
                else:
                    m = re.match(self.CHAPTER_TITLE_PATTERN_NO_VOLUME, ch_name)
                    ch_no = m.group(1)
                    ch_title = m.group(2)
                assert(ch_no is not None) # Chapter number is mandatory
                gr_a = ch_row.xpath('.//td')[2].xpath('.//a')[0]
                gr_name = unicode(gr_a.text.strip(' \t\n\r')).translate(dict.fromkeys(map(ord, '\\/'), None))
                self.addMangaChapter(MangaChapterBatoto(self.name, ch_no, ch_url, ch_path, ch_title, vol_no, gr_name))

## Subclass representing a manga hosted in Starkana
class MangaStarkana(Manga):
    def __init__(self, manga_url, manga_name=None):
        super(MangaStarkana, self).__init__(manga_url, manga_name)

    def retrieveAllChapters(self):
        webpage = readHTML(self.url)
        ## print tostring(page) # For testing only
        if self.name is None:
            if webpage.xpath('//meta[@property="og:title"]'):
                self.name = webpage.xpath('//meta[@property="og:title"]/@content')[0].strip()
            else:
                self.name = self.url.split('/')[-1].replace('_', ' ')
            print "Set name to: " + self.name
        assert(self.name is not None)
        ch_path = "Starkana - " + self.name
        self.createFolder(ch_path)
        for ch_row in webpage.xpath('//a[@class="download-link"]'):
            ch_no = None
            ch_url = ch_row.get('href')
            ch_no = ch_url.split('/')[-1]
            assert(ch_no is not None)
            self.addMangaChapter(MangaChapterStarkana(self.name, ch_no, ch_url, ch_path))

# Data structures that help instantiating the right subclasses based on URL
URL_TYPES = {'http://www.batoto.net' : {'url' : '(http://)?(www\.)?(batoto\.net).+-r[0-9]+', 'manga' : MangaBatoto, 'mangachapter' : MangaChapterBatoto},
            'http://www.bato.to' : {'url' : '(http://)?(www\.)?(bato\.to).+-r[0-9]+', 'manga' : MangaBatoto, 'mangachapter' : MangaChapterBatoto},
            'http://www.starkana.com' : {'url' : '(http://)?(www\.)?starkana\.com/manga/[0A-Z]/.+', 'manga' : MangaStarkana, 'mangachapter' : MangaChapterStarkana}
                }

# Parse command line arguments
parser = argparse.ArgumentParser(description = 'Download manga chapters from collection sites.')
parser.add_argument('--Debug', '-D', help = 'Run in debug mode', action = 'store_true')
parser.add_argument('--Test', '-T', help = 'Run in test mode (downloads suppressed)', action = 'store_true')
parser.add_argument('--verbose', '-v', help = 'Enable verbose mode', action = 'store_true')
group = parser.add_mutually_exclusive_group(required = False)
group.add_argument('--reload', '-r', help = 'Update all manga folders in current directory', action = 'store_true')
group.add_argument('--update', '-u', help = 'Update the manga at the url(s) provided', action = 'append')
args = vars(parser.parse_args())
url_list = []

__DEBUG__ = args['Debug']
__DOWNLOAD__ = not args['Test']
if args['verbose']:
    verbose = True
else:
    verbose = False
if args['reload']:
    for subdir in filter(lambda f: os.path.isdir(f), glob.glob('*')):
        if glob.glob(subdir + '/mangadl.link'):
            with open(subdir + '/mangadl.link', 'r') as f:
                url_list.append(f.read())
        elif glob.glob(subdir + '/* Chapter *'):
            url_input = raw_input("Enter URL for folder " + subdir + " (Press ENTER to skip) : ")
            url_list.append(url_input)
elif args['update']:
    url_list = args['update']
else:
    url_input = raw_input("Enter URL: ")
    url_list.append(url_input)

url_list = filter(None, url_list)
assert(url_list)

for url in url_list:
    url_type = checkURLType(url)
    manga = URL_TYPES[url_type]['manga'](url) # Instantiate manga object
    manga.retrieveAllChapters() # Add all chapters to it
    chapter_count = len(manga.chapter_list)
    curr_download_count = 0
    for chapter in manga.chapter_list:
        if __DEBUG__:
            chapter.show()
        sys.stdout.write("\rDownloaded " + str(curr_download_count) + "/" + str(chapter_count) + " chapters.")
        sys.stdout.flush()
        if __DOWNLOAD__:
            if __DEBUG__:
                print "\nDownloading chapter..."
            chapter.downloadChapter()
            curr_download_count = curr_download_count + 1
    sys.stdout.write("\rDownloaded " + str(curr_download_count) + "/" + str(chapter_count) + " chapters.")
    sys.stdout.flush()
    print "\n"
print "Finished."
exit(0)
