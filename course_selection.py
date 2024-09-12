import functools
import re

import requests
from parsel import Selector
# tool use to get hash key
from PIL import Image
from io import BytesIO
from bs4 import BeautifulSoup

def download_and_show_captcha(html_content, img_id):
    # 使用 BeautifulSoup 查找 <img> 標籤的 src 屬性
    soup = BeautifulSoup(html_content, 'lxml')
    img_tag = soup.find('img', id=img_id)
    
    if img_tag:
        img_src = img_tag['src']
        
        # 判斷圖片URL是否是相對路徑或缺少部分路徑，若是則補全為完整URL
        if not img_src.startswith("http"):
            # 修正 URL，將 BaseData 放置在 EleCos 後面
            img_src = img_src.replace("BaseData", "/EleCos/BaseData")
            img_src = f"https://www.ais.tku.edu.tw{img_src}"
        
        print(f"Captcha URL: {img_src}")
        
        # 發送請求下載驗證碼圖片
        response = requests.get(img_src)
        if response.status_code == 200:
            # 打開並顯示圖片
            img = Image.open(BytesIO(response.content))
            img.show()
        else:
            print(f"Failed to download captcha image.{response.status_code}")
    else:
        print(f"No image found with id: {img_id}")

class TKUCourseSelector:
    captcha_pattern = re.compile('^\[("[0-9a-z]{64}",?){6}\]$')
    captcha_mapping = {
        '4ae81572f06e1b88fd5ced7a1a000945432e83e1551e6f721ee9c00b8cc33260': '0',
        'a9f51566bd6705f7ea6ad54bb9deb449f795582d6529a0e22207b8981233ec58': '1',
        'fcb5f40df9be6bae66c1d77a6c15968866a9e6cbd7314ca432b019d17392f6f4': '2',
        'e632b7095b0bf32c260fa4c539e9fd7b852d0de454e9be26f24d0d6f91d069d3': '3',
        '559aead08264d5795d3909718cdd05abd49572e84fe55590eef31a88a08fdffd': '4',
        'a83dd0ccbffe39d071cc317ddf6e97f5c6b1c87af91919271f9fa140b0508c6c': '5',
        '8de0b3c47f112c59745f717a626932264c422a7563954872e237b223af4ad643': '6',
        'a25513c7e0f6eaa80a3337ee18081b9e2ed09e00af8531c8f7bb2542764027e7': '7',
        '6b23c0d5f35d1b11f9b683f0b0a617355deb11277d91ae091d399c655b87940d': '8',
        '3f39d5c348e5b79d06e842c114e6cc571583bbf44e4b0ebfda1a01ec05745d43': '9'
    }

    def __init__(self):
        self.session = requests.Session()
        # Global timeout
        self.session.request = functools.partial(self.session.request, timeout=30)
        self.session.headers['User-Agent'] = (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:73.0) Gecko/20100101 Firefox/73.0')
        self.last_page = None

    @staticmethod
    def get_captcha_code(text: str):
        print(text)
        assert __class__.captcha_pattern.match(text) is not None, "captcha not match!"
        return ''.join(map(__class__.captcha_mapping.get, eval(text)))

    @staticmethod
    def get_hidden_arg(html: str):
        sel = Selector(html)
        return {
            prop: sel.css(f'#{prop}::attr("value")').get()
            for prop in ('__VIEWSTATE', '__VIEWSTATEGENERATOR', '__EVENTVALIDATION')
        }

    def login(self, student_num: str, passwd: str) -> requests.Response:
        login_page = self.session.get(
            'https://www.ais.tku.edu.tw/EleCos/login.aspx?ReturnUrl=%2felecos%2f')
        captcha_page = self.session.post(
            'https://www.ais.tku.edu.tw/EleCos/Handler1.ashx')

        post_data = self.get_hidden_arg(login_page.text)
        post_data.update({
            '__EVENTTARGET': 'btnLogin',
            'txtCONFM': self.get_captcha_code(captcha_page.text),
            'txtStuNo': student_num,
            'txtPSWD': passwd
        })

        login_resp = self.session.post(
            'https://www.ais.tku.edu.tw/EleCos/login.aspx?ReturnUrl=%2felecos%2f', data=post_data)
        assert login_resp.history and login_resp.history[0].status_code == 302, "Login failed QWQ"

        self.last_page = login_resp
        return login_resp

    def _action(self, course_id: str, action: str) -> requests.Response:
        post_data = self.get_hidden_arg(self.last_page.text)
        post_data.update({
            '__EVENTTARGET': action,
            'txtCosEleSeq': course_id
        })

        self.last_page = resp = self.session.post(
            'https://www.ais.tku.edu.tw/EleCos/action.aspx', data=post_data)
        assert resp.status_code == 200 and resp.history == [], f"action({action}) failed!"
        
        return self.last_page

    def course_info(self, course_id: str) -> requests.Response:
        return self._action(course_id, 'btnOffer')

    def add_course(self, course_id: str) -> requests.Response:
        return self._action(course_id, 'btnAdd')

    def del_course(self, course_id: str) -> requests.Response:
        return self._action(course_id, 'btnDel')


if __name__ == "__main__":
    from getpass import getpass

    course_selector = TKUCourseSelector()
    resp = course_selector.login(input('Student Number: '), getpass())
    info_resp = course_selector.course_info(input('Course ID: '))
    add_resp = course_selector.add_course(input('Course ID: '))
    del_resp = course_selector.del_course(input('Course ID: '))
