from selenium import webdriver
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from dotenv import load_dotenv
from random import randint
import pandas as pd 
import re, os, time, sys, csv, json
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from toolkit import ordergenerator as og
from toolkit import general_tools as gt
from toolkit import changeip

# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.chrome.service import Service



load_dotenv()


OUTPUT_FOLDER_PATH = os.environ.get('OUTPUT_FOLDER_PATH')
STATION_FOLDER_PATH = os.environ.get('STATION_FOLDER_PATH')
DESTINATION_PATH = os.environ.get('DESTINATION_PATH')
BUG_TRACK_PATH = os.environ.get('BUG_TRACK_PATH')
LOGS_FOLDER_PATH = os.environ.get('LOGS_FOLDER_PATH')

SYSTEM = os.environ.get('SYSTEM')

FILED_NAMES = [
                'web-scraper-order',
                'date_price',
                'date_debut', 
                'date_fin',
                'prix_init',
                'prix_actuel',
                'typologie',
                'n_offre',
                'nom',
                'localite',
                'date_debut-jour',
                'Nb semaines',
                'services',
                #25 10 2025 , ajout de l'id
                'establishment',
                #12 01 2026 , pour currency
                'currency'
            ] 

QUERY_ORDER = [
    "aid",
    "label",
    "sid",
    "age",
    "checkin",
    "checkout",
    "dest_id",
    "dest_type",
    "dist",
    "group_children",
    "hapos",
    "hpos",
    "no_rooms",
    "req_adults",
    "req_age",
    "req_children",
    "room1",
    "sb_price_type",
    "soh",
    "sr_order",
    "srepoch",
    "srpvid",
    "type",
    "ucfs"
]

class BookingInitializer(object):

    def __init__(self, station_name:str, start_date:str, end_date:str, freq:int, dest_name:str) -> None:
        self.station_name = station_name
        self.start_date = datetime.strptime(start_date, "%d/%m/%Y")
        self.end_date = datetime.strptime(end_date, "%d/%m/%Y")
        self.freq = freq
        self.dest_name = f'{dest_name}{freq}_montreal' #comme ça on ne se trompera pas de nom de freq (10 02 2026)
        self.dest_url = []


    def load_stations(self) -> list | None:
        global STATION_FOLDER_PATH
        f""" load stations urls in json file from {STATION_FOLDER_PATH} and return it as list """
        print(" ==> reading station file")
        time.sleep(1)
        # try:
        station_url = json.load(open(f"{STATION_FOLDER_PATH}/{self.station_name}.json"))
        return station_url
        # except FileNotFoundError:
        #     show_message("File not found", "File not found or station file name incorrect", "error")
        #     sys.exit()

    def get_page_type(self, url:str) -> str:
        if '/hotel/' in url:
            return 'hotel'
        else:
            return 'list'

    def normalize_url_params(self, url:str, start:str, end:str) -> str:
        """ normalize url parameters as needed for data scraping format """
        # print(url)

        #24 10 2025 : vaut mieux nettoyer car parfois il y a des ?? dans les url
        url = url.replace("??",'')
        if not url.endswith('?'):
             url += '?'
        # print(f'url vrai = > {url}')
        
        url_params = parse_qs(urlparse(url).query)
        if "checkin" not in url_params:
            url += f"&checkin={start}"
        if "checkout" not in url_params:
            url += f"&checkout={end}"
        if "selected_currency" not in url_params:
            url += "&selected_currency=EUR"
        if "lang" not in url_params:
            #changé en es le 12 05 2025 car pour antequera c'est du es, A DEMANDER SI POUR MONTREAL C'est DU ES AUSSI
            #11 02 2026 : finalement montreal donc c'est en FR a dit Nicolas
            url += f"&lang=fr"
        if "selected_currency" in url_params: #MONTREAL devise CAD
            url += "&selected_currency=CAD"        
        return url

    def generate_url(self, stations_url:list) -> list:
        """generate dynamic urls for any station between interval of given dates {start_date and end_date}"""
        global QUERY_ORDER
        time.sleep(1)
        correct_dest_url = []
        if self.freq in [1, 3, 7]:
            date_space = int((self.end_date - self.start_date).days) + 1
            checkin = self.start_date
            checkout = checkin + timedelta(days=self.freq)  

            #pour antequera dont on les stations ne sont pas classifier par ID dans le fichier stations
            # for _ in range(date_space):
            #     for station_url in stations_url:
            #         page_type = self.get_page_type(station_url)
            #         url = self.normalize_url_params(station_url, checkin.strftime("%Y-%m-%d"), checkout.strftime("%Y-%m-%d"))
            #         if page_type == 'hotel':
            #             base_url = url.split('?')[0]
            #             params = url.split('?')[-1]
            #             formated_ordered_params = ""
            #             query_url = parse_qs(params)
            #             for query in QUERY_ORDER:
            #                 if bool(query_url.get(query)):
            #                     formated_ordered_params += f"{query}={query_url.get(query, '')[0]}&"
            #             parms_keys = list(query_url.keys())
            #             new_params = [i for i in parms_keys if i not in QUERY_ORDER]
            #             for query in new_params:
            #                 formated_ordered_params += f"{query}={query_url.get(query, '')[0]}&"
            #             url = f"{base_url}?{formated_ordered_params}"[:-1]
            #         correct_dest_url.append(url)

            #     checkin += timedelta(days=1)
            #     checkout += timedelta(days=1)
            # input(f'ireto ireo retourné aloha => {correct_dest_url}')

            #10 02 2026 : stations maintenant avec les ID depuis la base
            print('         ')
            print(' . . . loading . . .')
            print('         ')
            for _ in range(date_space):
                for name, details in stations_url.items():
                    page_type = self.get_page_type(details['url'])
                    url = self.normalize_url_params(details['url'], checkin.strftime("%Y-%m-%d"), checkout.strftime("%Y-%m-%d"))
                    if page_type == 'hotel':
                        base_url = url.split('?')[0]
                        params = url.split('?')[-1]
                        formated_ordered_params = ""
                        query_url = parse_qs(params)
                        for query in QUERY_ORDER:
                            if bool(query_url.get(query)):
                                formated_ordered_params += f"{query}={query_url.get(query, '')[0]}&"
                        parms_keys = list(query_url.keys())
                        new_params = [i for i in parms_keys if i not in QUERY_ORDER]
                        for query in new_params:
                            formated_ordered_params += f"{query}={query_url.get(query, '')[0]}&"
                        url = f"{base_url}?{formated_ordered_params}"[:-1]
                    #hoan'ilay type de fichier farany , car on a besoin de tous les details pour matcher à la fin mais aussi pour lier les id et les urls
                    correct_dest_url.append({
                         "name" : name,
                         "id": details['id'],
                         "url": url
                    })

                checkin += timedelta(days=1)
                checkout += timedelta(days=1)
            # input(f'ireto ireo retourné aloha => {correct_dest_url}')
            return correct_dest_url

        else:
            gt.show_message('Frequency not regular', "scrap frequency should be 1 or 3 or 7", 'error')

    def save_destination(self, data:list) -> None:
        """save destination urls in to json file"""
        print(" ==> saving destination")
        global DESTINATION_PATH
        folder_path = f"{DESTINATION_PATH}/{self.start_date.strftime('%d_%m_%Y')}"

        print(folder_path)

        dest_name = f"{folder_path}/{self.dest_name}.json"
        print(dest_name)
        if not Path(folder_path).exists():
            os.makedirs(folder_path)
        if not Path(dest_name).exists():
            with open(dest_name, "w") as openfile:
                openfile.write(json.dumps(data, indent=4))
        else:
            print(f"  ==> Destination with name {self.dest_name}.json already exist, do you want to overwrite this ? yes or no")
            response = input("  ==> your answer :")
            while response not in ['yes', 'no']:
                print(' ==> response unknown, please give correct answer!')
                print(f"  ==> Destination with name {self.dest_name}.json already exist, do you want to overwrite this ? yes or no")
                response = input("  ==> your answer :")
            match response:
                case 'yes':
                    with open(dest_name, "w") as openfile:
                        openfile.write(json.dumps(data))
                case 'no':
                    print(f'  ==> Destination {self.dest_name}.json kept')

        number_of_dest = len(json.load(open(dest_name)))

        print(f" ==> well done, {number_of_dest} destinations saved!")

    def execute(self) -> None:
        """ running Booking initalizer to setup booking scraping """
        print(" ==> initializing booking scraper ...")
        global BUG_TRACK_PATH
        stations = self.load_stations()
        new_correct_url = self.generate_url(stations)
        self.dest_url += new_correct_url

        self.save_destination(self.dest_url)

class BookingScraper(object):

    "last update 17/07/2024"

    def __init__(self, dest_name:str, name:str, week_date:str) -> None:

        self.dest_name = dest_name
        self.name = name

        self.destinations = []
        self.history = {}
        self.week_scrap = datetime.strptime(week_date, "%d/%m/%Y").strftime("%d_%m_%Y")
        self.exception_count = 0
        self.code = og.create_code()
        self.order_index = 1
        self.driver_cycle = 0

        #25 10 2025 pour l'id de l'etablissement
        self.establishment_id : str = ""

        self.chrome_options = webdriver.ChromeOptions()
        self.chrome_options.add_argument('--ignore-certificate-errors')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        # self.chrome_options.add_argument('--headless')  
        self.chrome_options.add_argument('--incognito')
        #11/04/2025 ajout lang=es forcé car parfois ça prend le fr toujours
        # self.chrome_options.add_argument('--lang=es')

        #pour linux on a besoin de ça car les driver ont été mise à jour sinon pas besoin de mettre le parms service dans le 11
        #pour linux on a besoin de ça car les driver ont été mise à jour sinon pas besoin de mettre le parms service dans le 11
        if SYSTEM == "windows":
             self.driver = webdriver.Chrome(options=self.chrome_options)
        elif SYSTEM == "linux":
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()),options=self.chrome_options)
        self.driver.maximize_window()

    def create_log(self) -> None:
        print("  ==> creating log")
        log = { "last_index": 0, "week_scrap": self.week_scrap }
        if not Path(f"{LOGS_FOLDER_PATH}/{self.week_scrap}").exists():
            os.makedirs(f"{LOGS_FOLDER_PATH}/{self.week_scrap}")
        gt.create_log_file(log_file_path=f"{LOGS_FOLDER_PATH}/{self.week_scrap}/{self.name}.json", log_value=log)

    def load_destinations(self) -> None:
        print("  ==> loading all destinations")
        self.destinations = gt.load_json(f"{DESTINATION_PATH}/{self.week_scrap}/{self.dest_name}.json")

        print(f"  ==> {len(self.destinations)} destination loaded")

    def load_history(self) -> None:
        print("  ==> loading history")
        self.history = gt.load_json(f"{LOGS_FOLDER_PATH}/{self.week_scrap}/{self.name}.json")
        self.week_scrap = self.history['week_scrap']

    def set_history(self) -> None:
        current_dest = self.history['last_index']
        self.history['last_index'] = current_dest + 1
        gt.save_history(f"{LOGS_FOLDER_PATH}/{self.week_scrap}/{self.name}.json", self.history)
        print('  ==> set history')

    def use_new_driver(self) -> None:
        time.sleep(1)
        try:
            self.driver.close()
            self.driver.quit()
        except:
            pass
        self.driver = webdriver.Chrome(self.chrome_options)
        self.driver.maximize_window()
        self.driver_cycle = 0

    def close_modal(self) -> None:
        try:
            if self.driver.find_element(By.ID, 'onetrust-accept-btn-handler'):
                self.driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
                print("button1 clicked")
        except:
            pass
        try:
            if self.driver.find_element(By.XPATH, "//button[@aria-label='Ignorer les infos relatives à la connexion']"):
                self.driver.find_element(By.XPATH, "//button[@aria-label='Ignorer les infos relatives à la connexion']").click()
                print("button2 clicked")
        except:
            pass
        try:
            if self.driver.find_element(By.CSS_SELECTOR, "dba1b3bddf.e99c25fd33.aabf155f9a.f42ee7b31a.a86bcdb87f.b02ceec9d7"):
                self.driver.find_element(By.CSS_SELECTOR, "dba1b3bddf.e99c25fd33.aabf155f9a.f42ee7b31a.a86bcdb87f.b02ceec9d7").click()
                print("button3 clicked")
        except:
            pass



    def goto_page(self, url:str) -> None:
        # test = "https://www.booking.com/hotel/es/chamartin.fr.html?checkin=2025-09-28&checkout=2025-09-30&selected_currency=EUR&lang=es"
        # print(f"  ==> load page {test}")
        print(f"  ==> load page {url}")

        #28 10 2025 : il y a encore quelques url sans https://
        if "https://" not in url:
            url = "https://" + url
            print(f'url modifiée car n\'a pas eu de https:// => {url}')

        if self.exception_count == 10:
            gt.show_message("Timeout Exception Error", "max exception reached, please check it before continue", "warning")
        if self.driver_cycle == 15:
            self.driver.close()
            # changeip.refresh_connection()
            self.use_new_driver()
        try:
            # self.driver.get(test)
            self.driver.get(url)
            time.sleep(3) #14 01 2026 changer en time.sleep car j'ai remarqué que parfois le code saute le premier url chargé en ouvrant le navigateur en premiere fois
            self.close_modal()
            self.exception_count = 0
        except Exception as e:
            gt.report_bug(f"{BUG_TRACK_PATH}/bug_{self.week_scrap}.txt", {"error": e, "bug_url":self.driver.current_url})
            time.sleep(2)
            self.exception_count += 1
            self.use_new_driver()
            self.goto_page(url)
        
    def create_output_file(self) -> None:
        global FILED_NAMES
        if not Path(f"{OUTPUT_FOLDER_PATH}/{self.week_scrap}").exists():
            os.makedirs(f"{OUTPUT_FOLDER_PATH}/{self.week_scrap}")
        gt.create_file(f"{OUTPUT_FOLDER_PATH}/{self.week_scrap}/{self.name}.csv", FILED_NAMES)

    def get_dates(self, url:str) -> tuple:
            """ function to get dates in url """
            url_params = parse_qs(urlparse(url).query)
            sep = '/'
            try:
                return sep.join(url_params['checkin'][0].split('-')[::-1]), sep.join(url_params['checkout'][0].split('-')[::-1])
            except KeyError:
                return f"{url_params['checkin_monthday'][0]}/{url_params['checkin_month'][0]}/{url_params['checkin_year'][0]}", f"{url_params['checkout_monthday'][0]}/{url_params['checkout_month'][0]}/{url_params['checkout_year'][0]}"

    def get_cards(self) -> tuple:
        card_count = 0
        cards = []
        try:
            cards = self.driver.find_elements(By.XPATH, "//div[@data-testid='property-card']")
            card_count = len(cards)
            return cards, card_count 
        except NoSuchElementException:
            return cards, card_count 

    def scroll_to_last_card(self) -> None:
        self.close_modal()
        cards, count = self.get_cards()
        if cards:
            try:
                self.driver.execute_script('arguments[0].scrollIntoView({ behavior: "smooth", block: "center", inline: "center" })', cards[-1])
            except:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        time.sleep(3)

    def scroll_down(self):
        self.close_modal()
        cards, current_card_count = self.get_cards()
        if cards:
            self.scroll_to_last_card()
            while True:
                cards, new_card_count = self.get_cards()
                if new_card_count == current_card_count:
                    break
                if new_card_count > current_card_count:
                    self.scroll_to_last_card()
                current_card_count = new_card_count

    def load_page_content(self):
        self.scroll_down()
        while True:
            try:
                btn_vew_more = self.driver.find_element(By.XPATH, '//span[contains(text(), "Afficher plus de résultats") or contains(text(), "Load more results")]')
                if btn_vew_more:
                    self.driver.execute_script('arguments[0].scrollIntoView({ behavior: "smooth", block: "center", inline: "center" })', btn_vew_more)
                    time.sleep(1)
                    try:
                        btn_vew_more.click()
                    except:
                        pass
            except NoSuchElementException:
                print("\t ===> page loaded")
                break

        soupe = BeautifulSoup(self.driver.page_source, 'lxml')
        print(f"""\t===>  card diplayed : {len(soupe.find_all('div', {'data-testid':"property-card"}))}""")

    def is_valid_data(self, data:dict) -> bool:
        for key in data.keys():
            if key in ['n_offre', 'date_debut-jour']:
                continue
            if not data[key] or data[key] is None or data[key] == '':
                return False
            if key == 'prix_init' or key == 'prix_actuel':
                try:
                    float(data[key])
                except:
                    print('prix init or actuel invalid')
                    return False
        return True

    def get_page_type(self) -> str:
        soupe = BeautifulSoup(self.driver.page_source, 'lxml')
        if soupe.find('div', {'class':'d4924c9e74', 'role':'list'}):
            return 'list'
        if soupe.find('div', {'id':'hotelTmpl'}):
            return 'detail'
        return 'undefined'

    def extract_data_list(self) -> list:
        print("  ==> extracting data")
        data_container = []
        soupe = BeautifulSoup(self.driver.page_source.encode('utf-8').decode('utf-8'), 'html.parser')
        cards = []
        try:
            cards = soupe.find_all('div', {'data-testid':"property-card"})
        except:
            pass
        if len(cards) > 0:
            print(f"  \t==> {len(cards)} cards found")
            for card in cards:
                try:
                    nom = card.find('div', {'data-testid':"title"}).text.replace('\n', '').replace(',', '-').replace('"', "'") \
                        if card.find('div', {'data-testid':"title"}) else ''
                    localite = card.find('span', {'data-testid':"address"}).text.replace('\n', '') \
                        if card.find('span', {'data-testid':"address"}) else ''

                    taxe_text = card.find('div', {'data-testid':"availability-rate-wrapper"}).find('div', {'data-testid':'taxes-and-charges'}).text.replace('€', '').replace('QAR', '').replace(u'\xa0', u'').replace(' ', '')
                    taxe = 0
                    try:
                        taxe = float(taxe_text.split(':')[-1])
                    except:
                        pass
                    prix_init = 0
                    prix_actual = 0
                    try:
                        print('         ')
                        print('Check current price')
                        print('         ')
                        prix_actual = card.find('div', {'data-testid':"availability-rate-wrapper"}).find('span', {'data-testid':'price-and-discounted-price'}).text.replace('€', '').replace('QAR', '').replace(u'\xa0', u'') \
                        if card.find('div', {'data-testid':"availability-rate-wrapper"}).find('span', {'data-testid':'price-and-discounted-price'}) else 0
                        
                        input(f'prix actual avec le currency PAGE LIST à débogger => {prix_actual}')
                        #14 01 2026 pour le DOllar Canadien de montreal
                        if prix_actual.split(' ')[0] == 'CAD':
                            currency = prix_actual.split(' ')[0]
                            prix_actual = prix_actual.split(' ')[1]
                            input(f'Prix => {currency} {prix_actual}')

                        if prix_actual and float(prix_actual) > 0:
                            prix_actual = float(prix_actual)
                        prix_actual += taxe
                    except:
                        print('prix actuel not found')
                    try:
                        print('         ')
                        print('Check init price')
                        print('         ')
                        prix_init = card.find('div', {'data-testid':"availability-rate-wrapper"}).find('div', {'tabindex':'0'}).find('span', {'class':'f018fa3636 d9315e4fb0'}).text.replace('€', '').replace('QAR', '').replace(u'\xa0', u'').replace(' ', '') \
                        if card.find('div', {'data-testid':"availability-rate-wrapper"}).find('div', {'tabindex':'0'}).find('span', {'class':'f018fa3636 d9315e4fb0'}) else 0
                        if prix_init and float(prix_init) > 0:
                            prix_init = float(prix_init)
                        prix_init += taxe
                    except:
                        prix_init = prix_actual
                        
                    typologie = card.find('h4').text.replace(u'\xa0', ' ').replace('\n', '') 
                    date_prix = (datetime.now() + timedelta(days=-datetime.now().weekday())).strftime('%d/%m/%Y')
                    date_debut, date_fin = self.get_dates(self.driver.current_url)
                    
                    data = {
                        'nom': nom,
                        'n_offre': '',
                        'date_debut': date_debut,
                        'date_fin': date_fin,
                        'localite': localite,
                        'prix_actuel': int(prix_actual),
                        'prix_init': int(prix_init),
                        'typologie': typologie,
                        'date_price': date_prix,
                        'Nb semaines': datetime.strptime(date_debut, '%d/%m/%Y').isocalendar()[1],
                        'date_debut-jour': '',
                        'web-scraper-order': og.get_fullcode(self.code, self.order_index),
                        'establishment': self.establishment_id,
                        'currency': currency
                    }

                    if self.is_valid_data(data):
                        data_container.append(data)
                    else:
                        print(f'invalid data for {data}')
                except:
                    print('failed to extract')
                    pass
        return data_container
    
    def extract_data_detail(self) -> list:
        page = BeautifulSoup(self.driver.page_source.encode('utf-8').decode('utf-8'), 'html.parser')
        data_container = []

        try:
            # availability = page.find('p', {'class':'bui-alert__text'}).text.strip()
            # if 'sélectionner des dates' in availability or "Indica las fechas para" in availability:
            #     return []
            #MAJ code du 23 09 2025
            availability = page.find('div', {'class':'bui-alert__description'}).text.strip()
            if 'sélectionner des dates' in availability or "Indica las fechas para" in availability or "Selecciona otras fechas para ver más disponibilidad" in availability:
                # input("NON DISPONIBLE, ON SORT")
                return []
        except Exception as e:
            try:
                #deuxieme possibilité de check des données si vraiment ils sont available:
                check_availability = page.findAll('div', {'div':'b99b6ef58f b6e8474a49'})
                for check in check_availability:
                    if 'No disponible en nuestra' in check.text.strip():
                        # input("NON DISPONIBLE, ON SORT")
                        return []
            except:
                pass
            print(f"==> data available")

        # nom = page.find('h2', {'class':'d2fee87262 pp-header__title'}).text
        #nom testé et OK
        try:
            nom = page.find('div', {'id':'hp_hotel_name'}).find('h2').text
        except:
            try:
                print("2nd check the nom")
                #28 10 2025 maj selector
                nom = page.find('div', {'data-testid':'PropertyHeaderDesktop-wrapper'}).find('h2').text
            except:
                print('nom not found, la page va se recharger')
                try:
                    #MAJ 13 11 2025
                    input('error chargement de la page, rechargement et go')
                    self.driver.refresh()
                    time.sleep(randint(2,3))
                except:
                    input('le nom a vraiment changé de seleceur, check et MAJ')
                    pass
        # localite = page.find('div', {'class':'a53cbfa6de f17adf7576'})
        # localite_other_content = localite.find('div', {'class':'ac52cd96ed'}).text
        # localite = localite.text.split(localite_other_content)[0].strip().replace(',', ' -')
        #code le 23 09 2025
        try:
            localite_base = page.find('div', {'class':'b99b6ef58f cb4b7a25d9 b06461926f'}).text
        except:
            input('localite_base not found, please check')
            pass
        try:
            extra_localite = page.find('div', {'class':'b99b6ef58f cb4b7a25d9 b06461926f'}).find('div').text
        except:
            input('extra_localite not found, please check')
            input('CHECK le naviguateur et met à jour les selecteurs puis relance')
        #code avant 23 09 2025
        # localite_base = page.find('div', {'class':'b99b6ef58f cb4b7a25d9'}).text
        # extra_localite = page.find('div', {'class':'b99b6ef58f cb4b7a25d9'}).find('div').text
        localite = localite_base.replace(extra_localite, '').replace(',', ' -')

        container = page.find('table', {'id':'hprt-table'})

        if bool(container):
            t_body = container.find('tbody')
            rows = t_body.find_all('tr')
            print(f"{len(rows)} typology found")
            typologie = ""
            for row in rows:
                try:
                    if row.find('span', {'class':'hprt-roomtype-icon-link'}):
                        typologie = row.find('span', {'class':'hprt-roomtype-icon-link'}).text.replace('\n', '').split('(')[0].strip()
                        print(f"typologie = {typologie}")
                    taxe_value = 0
                    taxe_text = ""
                    check_taxe = False
                    try:
                        #MAJ 15 01 2026
                        # taxe = row.find('td', {'class':'hp-price-left-align hprt-table-cell hprt-table-cell-price'}) #avant 14 01 2026
                        while check_taxe == False:
                            # taxe = row.select_one('td.hp-price-left-align.hprt-table-cell-price.droom_seperator') 
                            taxe = row.select_one('td.hp-price-left-align') #OK satria bdb ilay karazany dia io no class hiraisany  15 01 2026
                            if taxe:
                                # input('taxe existe')
                                check_taxe = True
                            else:
                                sortir = input('taxe n\'existe pas, écriver A pour continuer la boucle') #je met ça là car je ne veux pas de boucle infinit mais si ça va dans ce sens , c'est l'input()
                                while sortir != 'A':
                                    sortir = input('taxe n\'existe pas, écriver A pour continuer la boucle') #comme ça pas de touche appuyer par hasard, c'est pour le déboggage, on laisse là 
                                check_taxe = False
                            # (f'taxe tokony misy => {taxe}')
                        # taxe_text = taxe.find('div', class_='prd-taxes-and-fees-under-price').text #avant 14 01 2026
                        # taxe_text = taxe.find_all('div', {'class':'prd-taxes-and-fees-under-price prco-inline-block-maker-helper on-hpage blockuid-37193301_298917328_2_34_0'}).text.strip() #ne fonctionne pas car une partie de la class change à chaque tr
                        try:
                            #montreal in ES
                            taxe_text = taxe.find('div', string=re.compile("impuestos", re.IGNORECASE)).text.strip() #OK
                            #Par précaution, on va revériier la langue ici car en local parfois ça revient en ES je ne sais pa spourquoi alors que dans le paramètre c'est strictement FR 19 02 2026
                            # check_langage = input(f"Le langage est en ES,check le navigateur et stop car ce n'est pas normal")
                            # if check_langage == "M":
                            #     input('STOP LE PROGRAMME')
                        except:
                            taxe_text = taxe.find('div', string=re.compile("et frais", re.IGNORECASE)).text.strip()
                        print(f'taxe_text en ce moment => {taxe_text}')
                        if "Taxes et frais compris" not in taxe_text or "Incluye impuestos y cargos" in taxe_text:
                            print('TAXE présente sur site') 
                            print('             ')
                            print(f'Taxe inscrit = {taxe_text}')
                            taxe_text = taxe_text.split('CAD')[1]
                            print('         ')
                            print('taxe prise en compte')
                        else:
                            print('TAXE compris dans le prix affiché')
                            taxe_text = 0 #c'est maintenant du int donc il faut tester son type en bas et non plus comme la condition du haut là
                    except Exception as e:
                        input(f'taxe not found => {e}')
                        pass

                    #09 02 2026Prix init = prix barré si ça existe comme Nicolas l'a demandé
                    try:
                        prix_actual_sans_taxe = int(row["data-hotel-rounded-price"]) #ça prend le prix dans l'attribut
                    except:
                        print('prix actuel not found in attribute, on va rechercher dans le div')
                        #09 02 2026, parfois le prix n'est pas dans l'attribut n donc forcé de le prende dans le divs
                        try:
                            container_price_actual_sans_taxe = row.find('td', {'class':'ws-table-cell hprt-table-cell hprt-table-cell-price droom_seperator wholesalers_table__price hp-price-left-align'})
                            prix_actual_sans_taxe = container_price_actual_sans_taxe.find('span', {'class':'prco-valign-middle-helper'}).text.strip().replace('€','')
                            print(f'prix actual sans taxe trouvé dans les divs => {prix_actual_sans_taxe}')
                        except Exception as e:
                            input(f'prix actuel sans taxe not found in divs aussi, check and update selector si besoin => {e}')

                    #Optimisation 19 02 2026 : content_prix_barre peut être None on va directement gérer pas de Try
                    content_prix_barre = row.find('div', 'bui-f-color-destructive js-strikethrough-price prco-inline-block-maker-helper bui-price-display__original')
                    # prix_init = prix_init['data-strikethrough-value'] #19 02 2026 : dans l'attribut il y a des virgule parfois, on va maintenant prendre le texte brut
                    #19 02 2026 : Bien se mettre en question que le prix barré existe
                    if content_prix_barre != None:
                        try:
                            # input(f'Le contenu en texte {content_prix_barre.text}')
                            prix_init = content_prix_barre.text.strip().split('CAD')[1].strip()
                            print('         ')
                            print(f'Current price real exist (prix barré), prix init = {prix_init}')
                            print('         ')
                        except Exception as e:
                            input(f'Erreur dans l\'extraction du prix barré => {e}')
                            
                    elif content_prix_barre == None: #recherche de moyen de gérer si le prix barré est là mais que son selecteur est fausse, pour l'instant je mets ça en except mais il faudrait trouver un moyen de check si le prix barré existe vraiment ou pas pour éviter de tomber dans cet except à chaque fois alors que le prix barré existe mais que le selecteur a juste changé
                        print('Pas de prix barré, on prend le prix actuel comme prix init')
                        prix_init = prix_actual_sans_taxe
                    
                    #fin 09 02 2026

                    if type(taxe_text) == str: #15 01 2026 MAJ 09 02 2026
                        # input('TAXE EXISTE')
                        taxe_value = int(taxe_text)
                        prix_actual = prix_actual_sans_taxe + taxe_value  
                        print(f'taxe value {taxe_value} , prix actual avec taxe {prix_actual}')
                    if taxe_text == 0:
                        # input('TAXE = 0')
                        # prix_actual = prix_init
                        print('Pas de taxe, pas de changement de prix actuel')
                        prix_actual = prix_actual_sans_taxe
                        print(f"prix actual = {prix_actual_sans_taxe}")

                    date_prix = (datetime.now() + timedelta(days=-datetime.now().weekday())).strftime('%d/%m/%Y')
                    date_debut, date_fin = self.get_dates(self.driver.current_url)

                    try:
                        currency = self.driver.find_element(By.CSS_SELECTOR, 'button[data-testid="header-currency-picker-trigger"]').text.strip()
                        # input(f'Currency => {currency}')
                    except:
                        input('selector currency not found, stop and check it')

                    # try: #avant 14 01 2026
                    #     prix_init = int(row.find('div', {'class':'bui-f-color-destructive js-strikethrough-price prco-inline-block-maker-helper bui-price-display__original'})['data-strikethrough-value']) + taxe_value
                    #     print(f"prix init = {prix_init}")
                    # except:
                    #     pass
                    
                    #extraction des services 06 10 2025
                    try:
                        # services_container = row.find('ul', {'class' : 'hprt-conditions-bui bui-list bui-list--text bui-list--icon bui-f-font-caption'}).find_all('li')
                        # input('li all found')
                        services_container = row.find('ul', {'class' : 'hprt-conditions-bui bui-list bui-list--text bui-list--icon bui-f-font-caption'}).find_all('li')
                        # input(f"services_container => {services_container}")
                        services = ""
                        num = 1
                        for service in services_container:
                            # input(f"ity no service num {num}=>{service.text.strip()}")
                            num += 1
                            # service.find('span' : {'class' : 'bui-text bui-text--variant-small_1 bui-text--color-constructive'}).text.strip()
                            services = services + service.text.strip() + " / "
                        
                        #nettoyer les services
                        # input(f'services brut = {services}')
                        service_clean = services.replace(',', '.')
                        
                        # input(f'service = {service_clean}')
                    except Exception as e:
                        input(f'erreur => {e}')
                    data = {
                        'nom': nom,
                        'n_offre': '',
                        'date_debut': date_debut,
                        'date_fin': date_fin,
                        'localite': localite,
                        'prix_actuel': prix_actual,
                        'prix_init': prix_init,
                        'typologie': typologie,
                        'date_price': date_prix,
                        'Nb semaines': datetime.strptime(date_debut, '%d/%m/%Y').isocalendar()[1],
                        'date_debut-jour': '',
                        'services' : service_clean,
                        'web-scraper-order': og.get_fullcode(self.code, self.order_index),
                        # 25 10 2025 , ID de l'etablissement
                        'establishment': self.establishment_id,
                        'currency': currency
                    }
                    print(data)
                    if self.is_valid_data(data):
                        data_container.append(data)
                    else:
                        print(f'invalid data for {data}')
                except Exception as e:
                    print(f"Error ==> {e}")
        return data_container

    def execute(self) -> None:
        global FILED_NAMES
        print("  ==> scraping start")
        self.create_log()
        self.create_output_file()
        self.load_destinations()
        self.load_history()
        if self.destinations:
            for x in range(self.history['last_index'], len(self.destinations)):
                print(f"  ==> {self.history['last_index'] + 1} / {len(self.destinations)} / ID Etablissement = {self.destinations[x]['id']}")

                #24 10 2025 changement ici car on a maintenant une liste de dictionnaire et non plus une simple liste d'url
                # input(f'{self.destinations[x]}')
                self.goto_page(self.destinations[x]['url'])

                self.establishment_id = self.destinations[x]['id']

                page_type = self.get_page_type()
                data_container = []
                match page_type:
                    case 'list':
                        self.load_page_content()
                        try:
                            data_container = self.extract_data_list()
                        except Exception as e:
                            print("failed to extract page list")
                            print(f"Eror => {e}")
                    case 'detail':
                        try:
                            data_container = self.extract_data_detail()
                        except Exception as e:
                            print("failed to extract page detail")
                            print(f"Eror => {e}")
                print(f"  ==> {len(data_container)} data extracted ")
                gt.save_data(f"{OUTPUT_FOLDER_PATH}/{self.week_scrap}/{self.name}.csv", data_container, FILED_NAMES)
                self.set_history()
                self.driver_cycle += 1
            print("  ==> scrap finished")
        else:
            print("  ==> destination empty! ")

