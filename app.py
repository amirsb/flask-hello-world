from flask import Flask
import sqlite3
import datetime
import requests
import pandas as pd
from bs4 import BeautifulSoup


app = Flask(__name__)

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
        site = requests.get(self.link + self.path)
        holder = BeautifulSoup(site.text, 'html.parser')
        self.latestNews = holder.find_all(cls, {'class':cname})
    
    def processNews(self, DCT: dict):
        
        for n in self.latestNews:
            try:
                header = eval('n.' + str(DCT['header']) +'.text')
                abstract = eval('n.' + str(DCT['abstract']) +'.text')
                Jdate = eval('n.' + str(DCT['Jdate']) +'.text')
                link = n.find_all(DCT['link']['tag'],{'class':DCT['link']['class']})[0].get_attribute_list(DCT['link']['prop'])[0]
                news = News(self.name, self.group, header, abstract, self.link + link, Jdate)
                self.processedNews.append(news)
            except:
                pass



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

def writeNews(AN : Agency,keyw  = r'keywords.xlsx' , Ban = r"G:\Andishkade\Rasad Project\ban.xlsx"):
    conn = sqlite3.connect(r"G:\Andishkade\Rasad Project\NEWS.db")
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
                    
                url = "https://tapi.bale.ai/bot627950531:TboLj8qu6VUgfj2AUDidwP1XcUd6Ki3iG8ZZCE3A/sendMessage?chat_id=5535395281" + "&text={}".format(MSG)
                requests.get(url)
    df.to_sql('news', conn, index=False, if_exists='append')
    conn.close()
    pass

@app.route('/')
def hello_world():
    # -------------------------------------------------------
    fars = Agency('فارس', 'https://www.farsnews.ir', 'Housing', r'/economy/civil')
    fars.getLatestNews('li','media py-3 border-bottom align-items-start')
    DCT = {'Jdate': 'time', 'header': 'h3', 'abstract': 'p', 'link': {'tag':'a', 'class': 'd-flex flex-column h-100 justify-content-between', 'prop':'href'}}
    fars.processNews(DCT)
    writeNews(fars)
    # ------------------------------------------------------
    mehr = Agency('مهر', 'https://www.mehrnews.com', 'Housing', r'/service/Economy/Construction-Housing')
    mehr.getLatestNews('li', 'news')
    DCT = {'Jdate': 'time', 'header': 'h3', 'abstract': 'p', 'link': {'tag':'a', 'class': '', 'prop':'href'}}
    mehr.processNews(DCT)
    writeNews(mehr)
    # ------------------------------------------------------
    tasnim = Agency('تسنیم', 'https://www.tasnimnews.com', 'Housing', r'/fa/service/81/%D8%B1%D8%A7%D9%87-%D9%88-%D9%85%D8%B3%DA%A9%D9%86')
    tasnim.getLatestNews('article', 'list-item')
    DCT = {'Jdate': 'time', 'header': 'h2', 'abstract': 'h4', 'link': {'tag':'a', 'class': '', 'prop':'href'}}
    tasnim.processNews(DCT)
    writeNews(tasnim)
    # -------------------------------------------------------
    return ':)'



