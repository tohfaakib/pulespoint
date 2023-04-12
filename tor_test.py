from selenium import webdriver
from selenium.webdriver import DesiredCapabilities
import time
from stem import Signal
from stem.control import Controller

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager



def config_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless")
    # options.add_argument(f"--user-data-dir={data_dir}")
    # options.add_argument('--proxy-server=http://127.0.0.1:8181')
    options.add_argument('--proxy-server=socks5://127.0.0.1:9050')
    # options.add_argument('--proxy-server=http://54.146.102.118:8181')
    options.add_argument("--start-maximized")
    options.add_argument('—no-sandbox')
    options.add_argument('—disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    d = DesiredCapabilities.CHROME
    d['loggingPrefs'] = {'performance': 'ALL'}
    d['phantomjs.page.customHeaders.User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
    # driver = webdriver.Chrome(executable_path="chromedriver_90.exe", options=options,
    #                           desired_capabilities=d)

    s = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=s, options=options)


    return driver

def renew_connection():
    with Controller.from_port(address='127.0.0.1', port=9051) as controller:
        controller.authenticate(password="TorPass12@#")
        controller.signal(Signal.NEWNYM)

def open_url():
    renew_connection()
    driver = config_driver()
    url = 'http://mylocation.org/'
    driver.get(url)
    time.sleep(20)

open_url()