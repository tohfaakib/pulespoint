import concurrent.futures
import datetime
import os
# import os
import re
import time
import timeit
import urllib
from configparser import ConfigParser
# from os.path import join, dirname
# from pprint import pprint
from urllib.parse import urljoin
import socket
import psycopg2
# import pyautogui
import requests
import zipcodes
from bs4 import BeautifulSoup
# from dotenv import load_dotenv
from psycopg2.extras import execute_values
from selenium import webdriver
# from seleniumwire import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException, ElementClickInterceptedException, \
    ElementNotInteractableException
# from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
# from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

from stem import Signal
from stem.control import Controller


# dotenv_path = join(dirname(__file__), '.env')
# load_dotenv(dotenv_path)

# sw_options = {'proxy': {
#             'http': 'http://lum-customer-c_f9668b90-zone-data_center:wfyp073jtmy1@zproxy.lum-superproxy.io:22225',
#             'https': 'http://lum-customer-c_f9668b90-zone-data_center:wfyp073jtmy1@zproxy.lum-superproxy.io:22225',
#             'no_proxy': 'localhost,127.0.0.1'
#             }
#         }
#

proxy = 'localhost:8119'
""" set driver args """

options = Options()
# set chrome driver args
# options.add_argument("--no-sandbox")
# options.add_argument("--headless=new")
# options.add_argument('--disable-dev-shm-usage')
# options.add_argument('--disable-gpu')
# options.binary_location = '/usr/bin/firefox-esr'
# options.add_argument('--proxy-server=socks5://0.0.0.0:9050')
# # options.add_argument(f'--proxy-server=http://{proxy}')
# options.add_argument("--disable-extensions")
# # options.add_argument("--disable-notifications")
# # options.add_argument("--disable-infobars")
# # options.add_argument("--mute-audio")
# # options.add_argument('--ignore-certificate-errors')
# # options.add_argument('--ignore-ssl-errors')
# options.add_experimental_option('excludeSwitches', ['enable-logging'])
# options.add_argument('--disable-blink-features=AutomationControlled') ## to avoid getting detected

headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    }
# options.add_argument("--headless")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu-sandbox')
options.add_argument("--single-process")
options.add_argument('--disk-cache-size-0')
options.add_argument(f'--user-agent={headers["User-Agent"]}')
# options.add_argument('--proxy-server=socks5://0.0.0.0:9050')
# options.binary_location = '/usr/bin/firefox'
# display_num = 99
# options.add_argument(f'--display={display_num}')
# os.environ['DISPLAY'] = f':{display_num}'


""" vars , consts """

# urls

URL_PULSEPOINT = "https://web.pulsepoint.org/"

# download chrome driver and set the path
# example below
# CHROME_DRIVER_PATH = "E:\\chromedriver.exe"

# CHROME_DRIVER_PATH = "C:/Users/Administrator/Desktop/Scraper/chromedriver.exe"
# s = Service(ChromeDriverManager().install())
s = Service(GeckoDriverManager().install())
# s = Service("/usr/local/bin/geckodriver")

def renew_connection():
    with Controller.from_port(address='0.0.0.0', port=9051) as controller:
        controller.authenticate(password="password")
        controller.signal(Signal.NEWNYM)


# def config(filename='C:/Users/Administrator/Desktop/Scraper/database.ini', section='postgresql'):
def config(filename='database.ini', section='postgresql'):
    # create a parser
    parser = ConfigParser()
    # read config file
    parser.read(filename)

    # get section, default to postgresql
    db = {}
    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception('Section {0} not found in the {1} file'.format(section, filename))

    return db


def internet(host="8.8.8.8", port=53, timeout=3):
    """
    Host: 8.8.8.8 (google-public-dns-a.google.com)
    OpenPort: 53/tcp
    Service: domain (DNS/TCP)
    """
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(ex)
        return False


def connect():
    """ Connect to the PostgreSQL database server """
    conn, cur_insert, cur_update = None, None, None
    try:
        # read connection parameters
        params = config()

        # connect to the PostgreSQL server
        print('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(**params)

        # create two cursors
        cur_insert = conn.cursor()
        cur_update = conn.cursor()

        # execute a statement
        print('PostgreSQL database version:')
        cur_insert.execute('SELECT version()')

        # display the PostgreSQL database server version
        db_version = cur_insert.fetchone()
        print(db_version)

        # close the communication with the PostgreSQL
        # cursor.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    # finally:
    #     if connection is not None:
    #         connection.close()
    #         print('Database connection closed.')
    return cur_insert, cur_update, conn


def calculate_duration(time_duration):
    time_duration = time_duration.replace(' ', '')
    if re.findall(r"(\d+)h", time_duration):
        duration = int(re.findall(r"(\d+)h", time_duration)[0]) * 60 + int(re.findall(r"(\d+)m", time_duration)[0])
    else:
        duration = int(re.findall(r"(\d+)m", time_duration)[0])
    return duration


def sooner_time_stamp_time(time_stamp_db, time_stamp_p):
    return time_stamp_db if datetime.datetime.strptime(time_stamp_db, '%I:%M %p') > datetime.datetime.strptime(
        time_stamp_p,
        '%I:%M %p') else time_stamp_p


def get_nominatim_geocode(address):
    url = 'https://nominatim.openstreetmap.org/search/' + urllib.parse.quote(address) + '?format=json'
    try:
        response = requests.get(url).json()
        return response[0]["lon"], response[0]["lat"]
    except Exception as e:
        # print(e)
        return None, None


def get_business_name(location):
    # https://stackoverflow.com/a/38212061/11105356
    stack = 0
    start_index = None
    results = []

    for i, c in enumerate(location):
        if c == '(':
            if stack == 0:
                start_index = i + 1  # string to extract starts one index later

            # push to stack
            stack += 1
        elif c == ')':
            # pop stack
            stack -= 1

            if stack == 0:
                results.append(location[start_index:i])

    return results[0]


def add_to_zip(city, state):
    API_KEY = 'vq5MAcpuzTyczVCHrlkHBBW1uBFxDqeVjp55zUhxDXJaSX9NqUBimjGMES8Rfg1l'
    url = f'http://www.zipcodeapi.com/rest/{API_KEY}/city-zips.json/{city}/{state}'

    res = requests.get(url)
    print("zip api response...")
    print(res.text)
    try:
        return res.json()['zip_codes'][0]
    except:
        return ''


def us_zip(city: str, state):
    try:
        filtered_zips = zipcodes.filter_by(city=city.title(), state=state)
        return filtered_zips[0]['zip_code']
    except:
        return ''


def get_data_attr(incident_contents, incident_type, cur_insert, cur_update, conn):
    print(f'length of {incident_type} incidents list ', len(incident_contents))
    data_contents_insert, data_contents_update = [], []
    for content in incident_contents:
        data_attr = dict()
        data_attr['type'] = incident_type.strip()
        data_attr['agency'] = content.select_one(
            'div.pp_incident_item_icon p.pp_wa_incident_list_agency_shortname').text.strip()
        data_attr['agency_logo'] = urljoin(URL_PULSEPOINT, content.select_one(
            'div.pp_incident_item_icon img.pp_incident_item_agency_img')['src'])
        data_attr['incident_logo'] = urljoin(URL_PULSEPOINT, content.select_one(
            'div.pp_incident_item_icon img.pp_incident_item_icon_img')['src'])

        location = content.select_one(
            'div.pp_incident_item_description h3.pp_incident_item_description_location').text.strip()
        data_attr['location'] = str(location.replace('\'', '\'\''))
        data_attr['address_2'], data_attr['business'] = None, None

        """ parse location values"""

        if '(' in location:
            data_attr['business'] = get_business_name(location)
            location = location.replace(data_attr['business'], '').replace('(', '').replace(')', '')

        if len(location.split(',')) == 3:
            data_attr['address'], data_attr['city'], data_attr['state'] = [loc.strip() for loc
                                                                           in
                                                                           location.split(',')]
        if len(location.split(',')) == 4:
            data_attr['address'], data_attr['address_2'], data_attr['city'], data_attr['state'] = [loc.strip() for loc
                                                                                                   in
                                                                                                   location.split(',')]
        data_attr['description'] = content.select_one(
            'div.pp_incident_item_description h6.pp_incident_item_description_units').text.strip()
        data_attr['title'] = content.select_one(
            'div.pp_incident_item_description h2.pp_incident_item_description_title').text.strip()
        incident_day = content.select_one(
            'div.pp_incident_item_timestamp h5.pp_incident_item_timestamp_day').text.strip()
        if incident_day.lower() == 'today':
            data_attr['date_of_incident'] = datetime.datetime.now().date()
        elif incident_day.lower() == 'yesterday':
            data_attr['date_of_incident'] = datetime.datetime.now().date() - datetime.timedelta(days=1)
        else:
            data_attr['date_of_incident'] = time.strptime(incident_day.strip(), "%m/%d/%Y")
        data_attr['duration'] = content.select_one(
            'div.pp_incident_item_timestamp h6.pp_incident_item_call_duration').text.strip()
        data_attr['timestamp_time'] = content.select_one(
            'div.pp_incident_item_timestamp h5.pp_incident_item_timestamp_time').text.strip()

        # data_attr['country'] = ''

        """Canadian Province Mapping"""
        # https://www150.statcan.gc.ca/n1/pub/92-195-x/2011001/geo/prov/tbl/tbl8-eng.htm
        canada_states_dic = {
            'Newfoundland and Labrador': 'NL',
            'Prince Edward Island': 'PE',
            'Nova Scotia': 'NS',
            'New Brunswick': 'NB',
            'Quebec': 'QC',
            'Ontario': 'ON',
            'Manitoba': 'MB',
            'Saskatchewan': 'SK',
            'Alberta': 'AB',
            'British Columbia': 'BC',
            'Yukon': 'YT',
            'Northwest Territories': 'NT',
            'Nunavut': 'NU',

        }
        for k, v in canada_states_dic.items():
            if data_attr['state'].strip().lower() == k.lower():
                data_attr['state'] = canada_states_dic[k]

        # Exception state : example - 'FL  #1005' , 'NY EAST GLENVILLE FD', ' DE / RM304'
        try:
            if len(data_attr['state'].strip()) > 2:
                s = re.search(r'[A-Z]{2}', data_attr['state'])
                data_attr['state'] = s.group().strip()
        except Exception as e:
            print(e)

        zip_cd = add_to_zip(data_attr['city'], data_attr['state'])
        if zip_cd == '':
            zip_cd = us_zip(data_attr['city'], data_attr['state'])
            print('us zip:', zip_cd)

        data_attr['zip_code'] = zip_cd

        # print(data_attr)
        # print('zip_code')
        # print(data_attr['zip_code'])

        us_state_dict = {
            "Alabama": "AL",
            "Alaska": "AK",
            "Arizona": "AZ",
            "Arkansas": "AR",
            "California": "CA",
            "Colorado": "CO",
            "Connecticut": "CT",
            "Delaware": "DE",
            "District of Columbia": "DC",
            "Florida": "FL",
            "Georgia": "GA",
            "Hawaii": "HI",
            "Idaho": "ID",
            "Illinois": "IL",
            "Indiana": "IN",
            "Iowa": "IA",
            "Kansas": "KS",
            "Kentucky": "KY",
            "Louisiana": "LA",
            "Maine": "ME",
            "Montana": "MT",
            "Nebraska": "NE",
            "Nevada": "NV",
            "New Hampshire": "NH",
            "New Jersey": "NJ",
            "New Mexico": "NM",
            "New York": "NY",
            "North Carolina": "NC",
            "North Dakota": "ND",
            "Ohio": "OH",
            "Oklahoma": "OK",
            "Oregon": "OR",
            "Maryland": "MD",
            "Massachusetts": "MA",
            "Michigan": "MI",
            "Minnesota": "MN",
            "Mississippi": "MS",
            "Missouri": "MO",
            "Pennsylvania": "PA",
            "Rhode Island": "RI",
            "South Carolina": "SC",
            "South Dakota": "SD",
            "Tennessee": "TN",
            "Texas": "TX",
            "Utah": "UT",
            "Vermont": "VT",
            "Virginia": "VA",
            "Washington": "WA",
            "West Virginia": "WV",
            "Wisconsin": "WI",
            "Wyoming": "WY",

        }

        us_states_list = list(us_state_dict.values())
        ca_state_list = list(canada_states_dic.values())

        if data_attr['state'] in ca_state_list:
            data_attr['country'] = 'CA'
        if data_attr['state'] in us_states_list:
            data_attr['country'] = 'US'

        location_to_check = data_attr.get('location').replace("\'\'", "\'\'\'\'")
        query_on_active = f"SELECT id from incidents where type = 'active' and " \
                          f"location = '{location_to_check}' and agency = '{data_attr.get('agency')}' and " \
                          f"title = '{data_attr.get('title')}' and " \
                          f"date_of_incident = '{data_attr.get('date_of_incident').strftime('%Y-%m-%d')}' and " \
                          f"timestamp_time = '{data_attr.get('timestamp_time')}' and duration = '' "

        query_on_duplicate = f"SELECT id from incidents where type = '{data_attr.get('type')}'  and " \
                             f"location = '{location_to_check}' and agency = '{data_attr.get('agency')}' and " \
                             f"title = '{data_attr.get('title')}' and " \
                             f"date_of_incident = '{data_attr.get('date_of_incident').strftime('%Y-%m-%d')}'"

        query_on_merge_check = f"SELECT * from incidents where type = '{data_attr.get('type')}' and " \
                               f"location = '{location_to_check}' and " \
                               f"title = '{data_attr.get('title')}' and " \
                               f"date_of_incident = '{data_attr.get('date_of_incident').strftime('%Y-%m-%d')}' "

        # print(query_on_merge_check)

        """ check for duplicates"""
        cur_insert.execute(query_on_duplicate)
        duplicate_id = list(cur_insert.fetchall())
        # print("================", len(duplicate_id) > 0, cur_insert.fetchall())
        if len(duplicate_id) > 0:
            print("duplicate values", duplicate_id[0][0], " skipping...")
            continue
        else:
            """query to check duplicate to merge"""
            cur_merge_check = conn.cursor()
            cur_merge_check.execute(query_on_merge_check)
            merge_check_element = list(cur_merge_check.fetchall())
            # print('================ merge_check_element ', merge_check_element)
            # print('\n', cur_merge_check.fetchall())

            """Query to check for active incident turned to recent"""
            cur_update.execute(query_on_active)
            id_to_update = list(cur_update.fetchall())
            # print('================ id_to_update ', id_to_update)

            """ check for duplicates ready to merge"""
            if len(merge_check_element) > 0:
                print("duplicates ready to merge ")
                final_duration = data_attr['duration'] if calculate_duration(
                    data_attr['duration']) > calculate_duration(merge_check_element[0][7]) else merge_check_element[0][
                    7]
                final_time_stamp_time = sooner_time_stamp_time(data_attr['timestamp_time'], merge_check_element[0][4])

                agency = data_attr['agency']
                for elem in data_contents_update:
                    if (elem[1] == data_attr['title'] and elem[3] == data_attr['location'] and elem[5] == data_attr.get(
                            'date_of_incident')):
                        if (elem[2] != agency):
                            data_attr['agency'] = data_attr['agency'] + "," + elem[2]
                        else:
                            continue
                        break
                else:
                    data_contents_update.append((merge_check_element[0][18],
                                                 data_attr['type'], data_attr['title'],
                                                 data_attr['agency'] + ',' + merge_check_element[0][2],
                                                 data_attr['location'],
                                                 final_time_stamp_time,
                                                 data_attr['date_of_incident'],
                                                 data_attr['description'] + ' ' + merge_check_element[0][6],
                                                 final_duration,
                                                 data_attr['incident_logo'], data_attr['agency_logo'],
                                                 data_attr['address'], data_attr['city'], data_attr['state'],
                                                 data_attr['address_2'],
                                                 data_attr['business'], data_attr['zip_code'],
                                                 data_attr['country']))

                """check for active incident turned to recent"""

            elif len(id_to_update) > 0:
                print("active incident turned to recent")
                agency = data_attr['agency']
                for elem in data_contents_update:
                    if (elem[1] == data_attr['title'] and elem[3] == data_attr['location'] and elem[5] == data_attr.get(
                            'date_of_incident')):
                        if (elem[2] != agency):
                            data_attr['agency'] = data_attr['agency'] + "," + elem[2]
                        else:
                            continue
                        break
                else:
                    data_contents_update.append((id_to_update[0][18], data_attr['type'], data_attr['title'],
                                                 data_attr['agency'], data_attr['location'],
                                                 data_attr['timestamp_time'],
                                                 data_attr['date_of_incident'], data_attr['description'],
                                                 data_attr['duration'],
                                                 data_attr['incident_logo'], data_attr['agency_logo'],
                                                 data_attr['address'], data_attr['city'], data_attr['state'],
                                                 data_attr['address_2'],
                                                 data_attr['business'], data_attr['zip_code'],
                                                 data_attr['country']))

            else:
                agency = data_attr['agency']
                for elem in data_contents_insert:
                    if (elem[1] == data_attr['title'] and elem[3] == data_attr['location'] and elem[5] == data_attr.get(
                            'date_of_incident')):
                        if (elem[2] != agency):
                            data_attr['agency'] = data_attr['agency'] + "," + elem[2]
                        else:
                            continue
                        break
                else:
                    for elem in data_contents_insert:
                        if (elem[1] == data_attr['title'] and elem[2] == data_attr['agency'] and elem[3] == data_attr[
                            'location'] and elem[5] == data_attr.get('date_of_incident')):
                            # print('duplicate found...#######################')
                            break
                    else:
                        data_contents_insert.append(
                            (data_attr['type'], data_attr['title'], data_attr['agency'], data_attr['location'],
                             data_attr['timestamp_time'],
                             data_attr['date_of_incident'], data_attr['description'], data_attr['duration'],
                             data_attr['incident_logo'], data_attr['agency_logo'],
                             data_attr['address'], data_attr['city'], data_attr['state'], data_attr['address_2'],
                             data_attr['business'], data_attr['zip_code'],
                             data_attr['country']))

    """
    to insert new incidents
    """
    # print('data_contents_insert', data_contents_insert)
    data_tuples_insert = tuple(data_contents_insert)
    print('Updated Length of incidents to insert', len(data_tuples_insert))
    if len(data_tuples_insert) > 0:
        print('populating into db...')
        args_str = b','.join(
            cur_insert.mogrify("(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", x) for x in
            data_tuples_insert)
        try:
            cur_insert.execute(b"INSERT INTO incidents VALUES " + args_str)
            conn.commit()
            print(cur_insert.rowcount, "Record inserted successfully into  table")
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    """
    to update active to recent incident 
    """
    # data_tuples_update = tuple(data_contents_update)
    print('Updated Length of incidents active to recent  : ', len(data_contents_update))

    if len(data_contents_update) > 0:
        print('updating................................................')

        # to update all the fields  , use this instead
        update_query = """UPDATE incidents
                           SET type = update_payload.type,
                            title = update_payload.title,
                            agency = update_payload.agency,
                            location = update_payload.location,
                            timestamp_time = update_payload.timestamp_time,
                            date_of_incident = update_payload.date_of_incident,
                            description = update_payload.description,
                            duration = update_payload.duration,
                            incident_logo = update_payload.incident_logo,
                            agency_logo = update_payload.agency_logo,
                            address = update_payload.address,
                            city = update_payload.city,
                            state = update_payload.state,
                            address_2 = update_payload.address_2,
                            business = update_payload.business,
                            zip_code = update_payload.zip_code,
                            country = update_payload.country
                           FROM (VALUES %s) AS update_payload (id, type,title,agency,location,timestamp_time,
                           date_of_incident,description,duration,incident_logo,agency_logo,address,city,state,address_2,business,zip_code,country)
                           WHERE incidents.id = update_payload.id"""

        # print('update_query ======================== ', update_query)

        try:
            execute_values(cur_update, update_query, data_contents_update)
            conn.commit()
            print(cur_update.rowcount, "Record updated successfully into  table")
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)


def check_agency():
    # driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=options,)
    # driver = webdriver.Chrome(service=s, options=options, seleniumwire_options=sw_options)
    # renew_connection()
    driver = webdriver.Chrome(service=s, options=options)

    # timeout
    wait = WebDriverWait(driver, 30)
    try:
        driver.get(url=URL_PULSEPOINT)
    except:
        time.sleep(10)
        while not internet():
            print("No internet!")
            time.sleep(5)
        time.sleep(10)
        driver.get(url=URL_PULSEPOINT)

    print('init...')
    time.sleep(0.5)
    # cur_insert, cur_update, conn = connect()

    try:
        # wait for visibility of product result section
        # wait.until(EC.presence_of_element_located((By.ID, "pp_wa_navbar_search_button")))
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dhxcombolist_material")))
    except TimeoutException as e:
        print("Wait Timed out")
        print(e)
    except NoSuchElementException as ne:
        print("No such element")
        print(ne)
    time.sleep(5)
    len_agency = len(driver.find_elements_by_xpath("/html/body/div[2]/div"))
    driver.close()
    driver.quit()
    return len_agency


def scraper_main(li_instance):
    start = timeit.default_timer()

    start_ins, end_ins = li_instance

    # driver = webdriver.Chrome(executable_path=CHROME_DRIVER_PATH, options=options,seleniumwire_options=sw_options,)
    # driver = webdriver.Chrome(service=s, options=options, seleniumwire_options=sw_options)
    # renew_connection()
    driver = webdriver.Chrome(service=s, options=options)

    # timeout
    wait = WebDriverWait(driver, 30)
    try:
        driver.get(url=URL_PULSEPOINT)

    except:
        time.sleep(10)
        while not internet():
            print("No internet!")
            time.sleep(5)
        time.sleep(10)
        driver.get(url=URL_PULSEPOINT)


    print('init...')
    time.sleep(0.5)
    cur_insert, cur_update, conn = connect()
    try:
        # wait for visibility of product result section
        # wait.until(EC.presence_of_element_located((By.ID, "pp_wa_navbar_search_button")))
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "dhxcombolist_material")))
    except TimeoutException as e:
        print("Wait Timed out")
        print(e)
    except NoSuchElementException as ne:
        print("No such element")
        print(ne)
    time.sleep(5)
    drop_down_agency = driver.find_element_by_xpath("/html/body/div[5]/div/div[1]/div[1]")
    drop_down_incident_types = driver.find_element_by_xpath("/html/body/div[5]/div/div[2]/div[1]")

    li_drop_down_incident_types = ['/html/body/div[1]/div[6]',
                                   '/html/body/div[1]/div[12]',
                                   '/html/body/div[1]/div[13]',
                                   '/html/body/div[1]/div[19]',
                                   '/html/body/div[1]/div[20]',
                                   '/html/body/div[1]/div[27]',
                                   '/html/body/div[1]/div[30]',
                                   '/html/body/div[1]/div[48]',
                                   '/html/body/div[1]/div[58]',
                                   '/html/body/div[1]/div[63]',
                                   '/html/body/div[1]/div[88]',
                                   '/html/body/div[1]/div[93]',
                                   '/html/body/div[1]/div[94]',
                                   '/html/body/div[1]/div[70]',
                                   '/html/body/div[1]/div[33]']

    # i = 96
    # li_drop_down_incident_types = ['/html/body/div[1]/div[' + str(i) + ']' for i in range(1, i)]
    for incident_type in li_drop_down_incident_types:
        drop_down_incident_types.click()
        driver.find_element_by_xpath(incident_type).click()
        time.sleep(0.3)

    agency_counter = start_ins
    agency_iterator = 15
    time.sleep(0.5)
    while agency_counter <= end_ins:
        print(f'Agency Counter : From {agency_counter} to {agency_counter + agency_iterator}')
        for i in range(agency_counter, agency_counter + agency_iterator):
            drop_down_agency.click()
            try:
                driver.find_element_by_xpath("/html/body/div[2]/div" + "[" + str(i) + "]").click()
            except TimeoutException as e:
                print("Wait Timed out")
                print(e)
            except NoSuchElementException as ne:
                print("No such element")
                print(ne)
            except ElementClickInterceptedException as ece:
                print("element is not clickable")
                print(ece)
            time.sleep(0.3)

        """find the button to display incidents"""
        try:
            element = driver.find_element_by_xpath("/html/body/div[5]/div/button")
            var = element.location_once_scrolled_into_view
            print(var)
        except TimeoutException as e:
            print("Wait Timed out")
            print(e)
        except NoSuchElementException as ne:
            print("No such element")
            print(ne)

        """click to find incidents"""
        try:
            # driver.find_element_by_class_name('pp_wa_large_button').click()
            driver.find_element_by_xpath('/html/body/div[5]/div/button').click()
        except TimeoutException as e:
            print("Wait Timed out")
            print(e)
        except NoSuchElementException as ne:
            print("No such element")
            print(ne)
        except ElementClickInterceptedException as ece:
            print("element is not clickable")
            print(ece)

        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pp_wa_tabs")))
        except TimeoutException as e:
            print("Wait Timed out")
            print(e)
        except NoSuchElementException as ne:
            print("No such element")
            print(ne)
        time.sleep(5)
        incident_element = None

        """incident info element"""
        try:
            incident_element = driver.find_element_by_class_name('pp_wa_incident_content').get_attribute(
                'innerHTML')
        except TimeoutException as e:
            print("Wait Timed out")
            print(e)
        except NoSuchElementException as ne:
            print("No such element")
            print(ne)
        time.sleep(1)

        """attr crawling start"""
        soup = BeautifulSoup(incident_element, 'html.parser')

        """ parse recent incidents"""
        try:
            # print(soup.select("section#recent_incidents_content h3.pp_no_incident_text"))
            if len(soup.select("section#recent_incidents_content h3.pp_no_incident_text")) == 1:
                print('No recent incident',
                      len(soup.select("section#recent_incidents_content h3.pp_no_incident_text")))
            else:
                recent_incident_contents = soup.select(
                    "section#recent_incidents_content dd.pp_incident_item_dd div.pp_incident_item_container")
                get_data_attr(recent_incident_contents, 'recent', cur_insert, cur_update, conn)

        except Exception as e:
            print(e)

        """ parse active incidents"""
        try:
            # print(soup.select("section#active_incidents_content h3.pp_no_incident_text"))
            if len(soup.select("section#active_incidents_content h3.pp_no_incident_text")) == 1:
                print('No active incident',
                      len(soup.select("section#recent_incidents_content h3.pp_no_incident_text")))
            else:
                active_incident_contents = soup.select(
                    "section#active_incidents_content dd.pp_incident_item_dd div.pp_incident_item_container")
                get_data_attr(active_incident_contents, 'active', cur_insert, cur_update, conn)

        except Exception as e:
            print(e)

        """click to show side bar"""
        try:
            driver.find_element_by_xpath('/html/body/div[3]/div').click()
        except TimeoutException as e:
            print("Wait Timed out")
            print(e)
        except NoSuchElementException as ne:
            print("No such element")
            print(ne)
        except ElementClickInterceptedException as ece:
            print("element is not clickable")
            print(ece)
        time.sleep(1)

        """clear previously selected agencies"""
        try:
            driver.find_element_by_xpath('/html/body/div[5]/div/div[1]/button').click()
        except TimeoutException as e:
            print("Wait Timed out")
            print(e)
        except NoSuchElementException as ne:
            print("No such element")
            print(ne)
        except ElementClickInterceptedException as ece:
            print("element is not clickable")
            print(ece)
        except ElementNotInteractableException as eni:
            print(eni)
            print('End of agency list...')
            break

        agency_counter = agency_counter + agency_iterator
        time.sleep(1)

    # close connection and cursor
    print('close db connection')
    cur_insert.close()
    cur_update.close()
    conn.close()

    driver.close()
    driver.quit()

    stop = timeit.default_timer()
    print('Time: ', stop - start)


def run_all(li_instance):
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(scraper_main, li_instance)


def main_func():
    # print('main func ...')
    agency_divider = 10
    # agency_divider = 1
    agency_count = check_agency()
    instance_number, remainder = divmod(agency_count, agency_divider)
    print(f'Total Agency: {agency_count}, Agency interval: {instance_number}')
    print(instance_number, remainder)

    total_li = []
    start = 1
    for i in range(1, agency_divider + 1):
        end = start + instance_number
        total_li.append([start, end - 1])
        start = end
    else:
        if not remainder == 0:
            total_li.append([end, end + remainder - 1])
    print(total_li)

    start_time = time.time()
    run_all(total_li)
    # run_all([[605,610],[80,85]])
    duration = time.time() - start_time
    print(f"Scraped {len(total_li)} in {duration} seconds")


main_func()
