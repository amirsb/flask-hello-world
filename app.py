import json
from flask import Flask, jsonify
import sqlite3
import datetime
import requests
import pandas as pd
import urllib.parse
from bs4 import BeautifulSoup
from flask_cors import CORS
import warnings
warnings.filterwarnings("ignore")


app = Flask(__name__)
CORS(app)

def check_keywords(keywords, text):
    for keyword in keywords:
        if keyword in text:
            return True
    return False

def find_matching_subjects(text, df):
    matching_subjects = []
    keywords = df['keyword'].tolist()
    subjects = df['subject'].tolist()
    
    for keyword, subject in zip(keywords, subjects):
        if keyword in text:
            matching_subjects.append(subject)
    
    return matching_subjects

class Agency:
    def __init__(self, name, link, group, path) -> None:
        self.name = name
        self.group = group
        self.link = link
        self.path = path
        self.latestNews = []
        self.processedNews = []
    
    def getLatestNews(self, cls, cname):
        site = requests.get(self.link + self.path, verify=False)
        holder = BeautifulSoup(site.text, 'html.parser')
        self.latestNews = holder.find_all(cls, {'class':cname})
    
    def processNews(self, DCT: dict, genral = False, descriptive = True, debug = False):
        if genral:
            Allow = pd.read_excel(r"allow.xlsx")
            allow = list(Allow.keywords)
        for n in self.latestNews:
            try:
                if descriptive:
                    header = eval('n.' + str(DCT['header']) +'.text').strip().replace("\n", "")
                    abstract = eval('n.' + str(DCT['abstract']) +'.text').strip().replace("\n", "")
                    try:
                        Jdate = eval('n.' + str(DCT['Jdate']) +'.text')
                    except AttributeError  as e:
                        Jdate = datetime.date.today().strftime("%Y-%m-%d")
                    link = n.find_all(DCT['link']['tag'],{'class':DCT['link']['class']})[0].get_attribute_list(DCT['link']['prop'])[0]
                else:
                    header = n.find_all(DCT['header']['tag'])[DCT['header']['num']].text
                    abstract = n.find_all(DCT['abstract']['tag'])[DCT['abstract']['num']].text
                    try:
                        Jdate = n.find_all(DCT['Jdate']['tag'])[DCT['Jdate']['num']].text
                    except AttributeError  as e:
                        Jdate = datetime.date.today().strftime("%Y-%m-%d")
                    link = n.find_all(DCT['link']['tag'],{'class':DCT['link']['class']})[0].get_attribute_list(DCT['link']['prop'])[0]

                if not DCT['link']['full']:
                    link = self.link + link    

                news = News(self.name, self.group, header, abstract, link, Jdate)

                if genral:
                    if check_keywords(allow,news.abstract) or check_keywords(allow,news.header):
                        if news.header != "":
                            self.processedNews.append(news)
                else:
                    if news.header != "":
                        self.processedNews.append(news)

            except Exception as e:
                if debug:
                    print("An error occurred : ", str(e))

class News:
    def __init__(self, agency, group, header, abstract, link, Jdate) -> None:
        self.header = header
        self.abstract = abstract
        self.Jdate = Jdate
        self.group = group
        self.link = link
        self.agency = agency
        self.tags = []
        
    def show(self):
        print(self.header)
        print(self.abstract)
        print(self.link)
        print(self.Jdate)

def writeNews(AN : Agency, keyw = r'keywords.xlsx' , Ban = r"ban.xlsx"):
    conn = sqlite3.connect(r"NEWS.db")
    df = pd.DataFrame(columns=['date', 'header', 'abstract', 'link', 'Jdate', 'agency', 'group'])
    ban = pd.read_excel(Ban)
    ban = list(ban.keywords)
    tagKeys = pd.read_excel(keyw)

    b = 0
    for N in AN.processedNews:
        cursor = conn.cursor()
        link = N.link
        cursor.execute("SELECT * FROM news WHERE link = ?", (link,))
        existing_entry = cursor.fetchone()
        if existing_entry:
            pass
        else:
            if check_keywords(ban, N.header) or check_keywords(ban, N.abstract):
                b = b + 1
                pass
            else:
                tags = find_matching_subjects( N.header + '\n' + N.abstract.lstrip() ,tagKeys)
                tags = list(set(tags))
                lines = N.abstract.splitlines()
                stripped_lines = list(filter(None, lines))
                stripped_text = "\n".join(stripped_lines)
                df.loc[len(df.index)] = [datetime.datetime.now(), N.header, N.abstract, N.link, N.Jdate, N.agency, N.group]
                MSG = "[" + N.header +"]("+ N.link +")" + '\n' + stripped_text.lstrip() + '\n *' + N.agency + '*'
                for t in tags:
                    MSG = MSG + '\n' + urllib.parse.quote('#' + str(t).replace(" ", "_"))
                    
                #url = "https://tapi.bale.ai/bot627950531:TboLj8qu6VUgfj2AUDidwP1XcUd6Ki3iG8ZZCE3A/sendMessage?chat_id=5535395281" + "&text={}".format(MSG)
                url = "https://tapi.bale.ai/bot627950531:TboLj8qu6VUgfj2AUDidwP1XcUd6Ki3iG8ZZCE3A/sendMessage?chat_id=6268195694" + "&text={}".format(MSG)
                requests.get(url)
                
    df.to_sql('news', conn, index=False, if_exists='append')
    conn.close()
    pass

@app.route('/table_to_json')
def table_to_json():
    
    conn = sqlite3.connect(r"NEWS.db")
    query = "SELECT * FROM news"
    # Read the specific columns into a DataFrame
    df = pd.read_sql_query(query, conn)
    # Close the database connection
    conn.close()
    csv_data = df.to_csv(index=False)
    
    # Create a response with CSV data and appropriate headers
    response = Response(csv_data, content_type='text/csv')
    response.headers.add('Content-Disposition', 'attachment; filename=data.csv')
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response



@app.route('/')
def hello_world():
    # 1 -------------------------------------------------------
    try:
        fars = Agency('فارس', 'https://www.farsnews.ir', 'Housing', r'/economy/civil')
        fars.getLatestNews('li','media py-3 border-bottom align-items-start')
        DCT = {'Jdate': 'time', 'header': 'h3', 'abstract': 'p', 'link': {'tag':'a', 'class': 'd-flex flex-column h-100 justify-content-between', 'prop':'href', 'full': False}}
        fars.processNews(DCT)
        writeNews(fars)
    except Exception as e:
        pass
    # 2 -------------------------------------------------------
    try:
        mehr = Agency('مهر', 'https://www.mehrnews.com', 'Housing', r'/service/Economy/Construction-Housing')
        mehr.getLatestNews('li', 'news')
        DCT = {'Jdate': 'time', 'header': 'h3', 'abstract': 'p', 'link': {'tag':'a', 'class': '', 'prop':'href', 'full': False}}
        mehr.processNews(DCT)
        writeNews(mehr)
    except Exception as e:
        pass
    # 3 -------------------------------------------------------
    try:
        tasnim = Agency('تسنیم', 'https://www.tasnimnews.com', 'Housing', r'/fa/service/81/%D8%B1%D8%A7%D9%87-%D9%88-%D9%85%D8%B3%DA%A9%D9%86')
        tasnim.getLatestNews('article', 'list-item')
        DCT = {'Jdate': 'time', 'header': 'h2', 'abstract': 'h4', 'link': {'tag':'a', 'class': '', 'prop':'href', 'full': False}}
        tasnim.processNews(DCT)
        writeNews(tasnim)
    except Exception as e:
        pass
    # 4 -------------------------------------------------------
    try:
        masireqtesad = Agency('مسیر اقتصاد', 'https://masireqtesad.ir', 'Housing', r'/category/groups/housing/')
        masireqtesad.getLatestNews("div", "col-lg-12 col-md-12 col-sm-12 col-xs-12 end_posts dot")
        DCT = {'Jdate': 'time', 'header': 'h2', 'abstract': 'p', 'link': {'tag':'a', 'class': '', 'prop':'href', 'full': True}}
        masireqtesad.processNews(DCT)
        writeNews(masireqtesad)
    except Exception as e:
        pass
    # 5 -------------------------------------------------------
    #try:
    #    majles = Agency('خبرگزاری مجلس شورای اسلامی', 'https://www.icana.ir', 'Housing', r'/Fa/Service/%D8%A7%D9%82%D8%AA%D8%B5%D8%A7%D8%AF%DB%8C')
    #    majles.getLatestNews("div", "row NewsListMarginBottom NewsListPaddingRight")
    #    DCT = {'Jdate': {'tag':'div', 'num': 5}, 'header': {'tag':'div', 'num': 6}, 'abstract': {'tag':'div', 'num': 7}, 'link': {'tag':'a', 'class': '', 'prop':'href', 'full': True}}
    #    majles.processNews(DCT, genral = True, descriptive = False, debug= True)
    #    writeNews(majles)
    #except Exception as e:
    #    pass
    # 6 -------------------------------------------------------
    #try:
    #    mrud = Agency('وزارت راه و شهرسازی', 'http://news.mrud.ir', 'Housing', r'/service/مسکن%20و%20شهرسازی')
    #    mrud.getLatestNews("li", "text")
    #    DCT = {'Jdate': 'time', 'header': 'h3', 'abstract': 'p', 'link': {'tag':'a', 'class': '', 'prop':'href', 'full': False}}
    #    mrud.processNews(DCT)
    #    writeNews(mrud)
    #except Exception as e:
    #    pass
    # 7 -------------------------------------------------------
    try:
        donyayeqtesad = Agency('دنیای اقتصاد', 'https://donya-e-eqtesad.com', 'Housing', r'/بخش-مسکن-عمران-18')
        donyayeqtesad.getLatestNews("li", "service-special")
        DCT = {'Jdate': 'time', 'header': 'h2', 'abstract': 'div.div', 'link': {'tag':'a', 'class': '', 'prop':'href', 'full': False}}
        donyayeqtesad.processNews(DCT)
        writeNews(donyayeqtesad)
    except Exception as e:
        pass
    # -------------------------------------------------------

    #db = table_to_json()
    
    return 'Please visit the channel.'



