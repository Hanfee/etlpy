# coding=utf-8
import gzip
import re
import socket
import urllib.request
try:
    from lxml import etree
except ImportError:
    from xml import etree
from urllib.parse import urlparse,urlunparse
import extends;
import http.cookiejar
from urllib.request import quote

boxRegex = re.compile(r"\[\d{1,3}\]");


class CrawItem(extends.EObject):
    def __init__(self, name=None, sample=None, ismust=False, isHTMLorText=True, xpath=None):
        self.XPath = xpath;
        self.Sample = sample;
        self.Name = name;
        self.IsMust = ismust;
        self.IsHTMLorText = isHTMLorText;
        self.Children = [];

    def __str__(self):
        return "%s %s %s" % (self.Name, self.XPath, self.Sample);


def RemoveFinalNum(paths):
    v = paths[-1];
    m = boxRegex.search(v);
    if m is None:
        return paths;
    s = m.group(0);
    paths[-1] = v.replace(s, "");
    return paths;


def GetMaxCompareXPath(items):
    xpaths = [r.XPath.split('/') for r in items];
    minlen = min(len(r) for r in xpaths);
    c = None;
    for i in range(minlen):
        for index in range(len(xpaths)):
            path = xpaths[index];
            if index == 0:
                c = path[i];
            elif c != path[i]:
                first = path[0:i + 1];
                return '/'.join(RemoveFinalNum(first));


attrsplit=re.compile('@|\[');

def GetDataFromXPath(node, path):
    p = node.xpath(path);
    if p is None:
        return None;
    if len(p) == 0:
        return None;
    paths = path.split('/');
    last = paths[-1];
    if last.find('@')>=0 and last.find('[1]')>=0:
        return p[0];
    return  getnodetext(p[0]);








def GetImage(addr, fname):
    u = urllib.urlopen(addr)
    data = u.read()
    f = open(fname, 'wb')
    f.write(data)
    f.close()


def urlEncodeNonAscii(b):
    return re.sub('[\x80-\xFF]', lambda c: '%%%02x' % ord(c.group(0)), b)

def iriToUri(iri):
    parts= urlparse(iri)

    pp= [(parti,part) for parti, part in enumerate(parts)]
    res=[];
    for p in pp:
        res.append(p[1] if p[0] != 4 else quote(p[1] ))

    return urlunparse(res);




extract = re.compile('\[(\w+)\]');

charset = re.compile(r'content="text/html;.?charset=(.*?)"');
class HTTPItem(extends.EObject):
    def __init__(self):
        self.Url = ''
        self.Cookie = '';
        self.Headers = None;
        self.Timeout = 30;
        self.opener = "";
        self.postdata=''

    def PraseURL(self, url):
        u = Para2Dict(urlparse(self.Url).query, '&', '=');
        for r in extract.findall(url):
            url = url.replace('[' + r + ']', u[r])
        return url;

    def GetHTML(self, destUrl=None):
        if destUrl is None:
            destUrl = self.Url;
        destUrl = self.PraseURL(destUrl);
        socket.setdefaulttimeout(self.Timeout);
        cj = http.cookiejar.CookieJar()
        pro = urllib.request.HTTPCookieProcessor(cj)
        opener = urllib.request.build_opener(pro)
        t = [(r, self.Headers[r]) for r in self.Headers];
        opener.addheaders = t;
        binary_data = self.postdata.encode('utf-8')
        try:
            destUrl.encode('ascii')
        except UnicodeEncodeError:
            destUrl =  iriToUri(destUrl)

        try:
            if self.postdata=='':
                page=opener.open(destUrl);
            else:
                page = opener.open(destUrl, binary_data)
            html = page.read()
        except Exception as e:
            print(e);
            return ""


        if page.info().get('Content-Encoding') == 'gzip':
            html = gzip.decompress(html)
        encoding = charset.search(str(html))
        if encoding is not None:
            encoding = encoding.group(1);
        if encoding is None:
            encoding = 'utf-8'
        try:
            html=html.decode(encoding)
        except UnicodeDecodeError as e:
            print(e);
            import chardet
            encoding= chardet.detect(html)
            html=html.decode(encoding);

        return html;


# 解压函数
def ungzip(data):
    data = gzip.decompress(data)
    return data;

def IsNone(data):
    return  data is  None or data=='';

def __getnodetext__(node, arrs):
    t=node.text;
    if t is not None:
        s = t.strip();
        if s != '':
            arrs.append(s)
    for sub in node.iterchildren():
        __getnodetext__(sub,arrs)

def getnodetext(node):
    if node is None:
        return ""
    arrs=[];
    __getnodetext__(node,arrs);
    return ' '.join(arrs);


class SmartCrawler(extends.EObject):
    def __init__(self):
        self.IsMultiData = "List";
        self.HttpItem = None;
        self.Name = None;
        self.CrawItems = None;
        self.Login = "";
        self.haslogin = False;
        self.RootXPath=''

    def autologin(self, loginItem):
        if loginItem.postdata is None:
            return;
        import http.cookiejar
        cj = http.cookiejar.CookieJar()
        pro = urllib.request.HTTPCookieProcessor(cj)
        opener = urllib.request.build_opener(pro)
        t = [(r, loginItem.Headers[r]) for r in loginItem.Headers];
        opener.addheaders = t;
        binary_data = loginItem.postdata.encode('utf-8')
        op = opener.open(loginItem.Url, binary_data)
        data = op.read().decode('utf-8')
        print(data)
        self.HttpItem.Url = op.url;
        return opener;

    def CrawData(self, url):

        if   self.Login !="" and  self.haslogin == False:
            self.HttpItem.opener = self.autologin(self.Login);
            self.haslogin = True;
        html = self.HttpItem.GetHTML(url);

        root =None if html=='' else etree.HTML(html);
        if root is None:
            return {} if self.IsMultiData == 'One' else [];

        tree = etree.ElementTree(root);
        if isinstance(self.CrawItems, list) and len(self.CrawItems) == 0:
            return {'Content': html};

        return self.GetDataFromCrawItems(tree );

    def GetDataFromCrawItems(self,tree):
        documents = [];
        if self.IsMultiData =='One':
            document = {};
            for r in self.CrawItems:
                data = GetDataFromXPath(tree, r.XPath);
                if data is not None:
                    document[r.Name] = data;
                else:
                    document[r.Name] = "";
            return document;
        else:
            if not IsNone(self.RootXPath):
                rootXPath = self.RootXPath;
            else:
                rootXPath = GetMaxCompareXPath(self.CrawItems);
            nodes = tree.xpath(rootXPath)
            if nodes is not None:
                for node in nodes:
                    document = {};
                    for r in self.CrawItems:
                        path=r.XPath;
                        if IsNone(self.RootXPath):
                            paths=r.XPath.split('/');
                            path='/'.join(paths[len(rootXPath.split('/')):len(paths)]);
                        else:
                            path=  tree.getpath(node)+ path;
                        data = GetDataFromXPath(node,path);
                        if data is not None:
                            document[r.Name] = data;
                    if len(document) == 0:
                        continue;
                    documents.append(document);
                return documents;

def Para2Dict(para, split1, split2):
    r = {};
    for s in para.split(split1):
        rs = s.split(split2);
        if len(rs) < 2:
            continue;
        key = rs[0];
        value = s[len(key) + 1:];
        r[rs[0]] = value;

    return r;


def GetHTML(url, code=None):
    url = url.strip();
    if not url.startswith('http'):
        url = 'http://' + url;
        print("auto transform %s" % (url));
    socket.setdefaulttimeout(30)
    i_headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1) Gecko/20090624 Firefox/3.5",
                 "Accept": "text/plain"}
    req = urllib.request.Request(url=url, headers=i_headers)
    page = urllib.request.urlopen(req)
    html = page.read()
    return html;


def GetHTMLFromFile(fname):
    f = open(fname, 'r', 'utf-8');
    r = f.read();
    return r;


def GetCrawNode(craws, name, tree):
    for r in craws:
        if r.Name == name:
            return tree.xpath(r.XPath);
    return None;


def GetImageFormat(name):
    if name is None:
        return None, None;
    p = name.split('.');
    if len(p) != 2:
        return name, 'jpg';

    back = p[-1];
    if back == "jpg" or back == "png" or back == "gif":  # back=="png"  ignore because png is so big!
        return p[-2], back;
    return None, None;


def GetCrawData(crawitems, tree):
    doc = {};
    for crawItem in crawitems:
        node = tree.xpath(crawItem.XPath);
        if len(node) == 0:
            if crawItem.IsMust:
                return;
        if crawItem.IsHTMLorText is False:
            text = node[0].text;
        else:
            text = etree.tostring(node[0]);
        doc[crawItem.Name] = text;
    return doc;


def GetHtmlTree(html):
    root = etree.HTML(html);
    tree = etree.ElementTree(root);
    return tree;
