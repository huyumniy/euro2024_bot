import os
import json
import ast
from urllib.parse import urlparse
import tempfile
import nodriver
import requests
import nodriver as uc
import random
from nodriver import cdp
import shutil
import sounddevice as sd
import soundfile as sf
import re
import undetected_chromedriver
import threading
from pyshadow.main import Shadow
import time
import sys, os
from twocaptcha import TwoCaptcha
from pydub import AudioSegment 
from nodriver.cdp.dom import Node
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from asyncio import iscoroutine, iscoroutinefunction
import logging
import json
import asyncio
import itertools

logger = logging.getLogger("uc.connection")

async def listener_loop(self):
    while True:
        try:
            msg = await asyncio.wait_for(
                self.connection.websocket.recv(), self.time_before_considered_idle
            )
        except asyncio.TimeoutError:
            self.idle.set()
            # breathe
            # await asyncio.sleep(self.time_before_considered_idle / 10)
            continue
        except (Exception,) as e:
            # break on any other exception
            # which is mostly socket is closed or does not exist
            # or is not allowed

            logger.debug(
                "connection listener exception while reading websocket:\n%s", e
            )
            break

        if not self.running:
            # if we have been cancelled or otherwise stopped running
            # break this loop
            break

        # since we are at this point, we are not "idle" anymore.
        self.idle.clear()

        message = json.loads(msg)
        if "id" in message:
            # response to our command
            if message["id"] in self.connection.mapper:
                # get the corresponding Transaction
                tx = self.connection.mapper[message["id"]]
                logger.debug("got answer for %s", tx)
                # complete the transaction, which is a Future object
                # and thus will return to anyone awaiting it.
                tx(**message)
                self.connection.mapper.pop(message["id"])
        else:
            # probably an event
            try:
                event = cdp.util.parse_json_event(message)
                event_tx = uc.connection.EventTransaction(event)
                if not self.connection.mapper:
                    self.connection.__count__ = itertools.count(0)
                event_tx.id = next(self.connection.__count__)
                self.connection.mapper[event_tx.id] = event_tx
            except Exception as e:
                logger.info(
                    "%s: %s  during parsing of json from event : %s"
                    % (type(e).__name__, e.args, message),
                    exc_info=True,
                )
                continue
            except KeyError as e:
                logger.info("some lousy KeyError %s" % e, exc_info=True)
                continue
            try:
                if type(event) in self.connection.handlers:
                    callbacks = self.connection.handlers[type(event)]
                else:
                    continue
                if not len(callbacks):
                    continue
                for callback in callbacks:
                    try:
                        if iscoroutinefunction(callback) or iscoroutine(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        logger.warning(
                            "exception in callback %s for event %s => %s",
                            callback,
                            event.__class__.__name__,
                            e,
                            exc_info=True,
                        )
                        raise
            except asyncio.CancelledError:
                break
            except Exception:
                raise
            continue
        
#call this after imported nodriver
#uc_fix(*nodriver module*)
def uc_fix(uc: uc):
    uc.core.connection.Listener.listener_loop = listener_loop

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SPREADSHEET_ID = '12Leg4iVj2rKwloYfrHWQZL9vRt1jwPgn2hBFdNsHB_o'


class ProxyExtension:
    manifest_json = """
    {
        "version": "1.0.0",
        "manifest_version": 2,
        "name": "Chrome Proxy",
        "permissions": [
            "proxy",
            "tabs",
            "unlimitedStorage",
            "storage",
            "<all_urls>",
            "webRequest",
            "webRequestBlocking"
        ],
        "background": {"scripts": ["background.js"]},
        "minimum_chrome_version": "76.0.0"
    }
    """

    background_js = """
    var config = {
        mode: "fixed_servers",
        rules: {
            singleProxy: {
                scheme: "http",
                host: "%s",
                port: %d
            },
            bypassList: ["localhost"]
        }
    };

    chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

    function callbackFn(details) {
        return {
            authCredentials: {
                username: "%s",
                password: "%s"
            }
        };
    }

    chrome.webRequest.onAuthRequired.addListener(
        callbackFn,
        { urls: ["<all_urls>"] },
        ['blocking']
    );
    """

    def __init__(self, host, port, user, password):
        self._dir = os.path.normpath(tempfile.mkdtemp())

        manifest_file = os.path.join(self._dir, "manifest.json")
        with open(manifest_file, mode="w") as f:
            f.write(self.manifest_json)

        background_js = self.background_js % (host, port, user, password)
        background_file = os.path.join(self._dir, "background.js")
        with open(background_file, mode="w") as f:
            f.write(background_js)

    @property
    def directory(self):
        return self._dir

    def __del__(self):
        shutil.rmtree(self._dir)
    

def download_wav(url, file_name):
    response = requests.get(url)

    # Check if the request was successful
    if response.status_code == 200:
        # Write the content of the response to a file
        with open(file_name, 'wb') as file:
            file.write(response.content)
        print(f"File downloaded successfully and saved as {file_name}")
    else:
        print(f"Failed to download the file. Status code: {response.status_code}")


def extract_numbers(code):
    # Define a mapping of number words to digits
    number_map = {
        "zero": "0", "one": "1", "on":"1", "two": "2", "to":"2", "three": "3", "tree": "3", "four": "4",
        "five": "5","fi":"5", "six": "6", "seven": "7", "eight": "8", "nine": "9"
    }
    
    # Use regex to find all number words in the code
    words = re.findall(r'\b(?:' + '|'.join(number_map.keys()) + r')\b', code)
    
    # Convert the words to their corresponding digits and join them
    result = ''.join(number_map[word] for word in words)
    
    return result


async def wait_for_captcha(page, driver):
    try:
        for i in range(1, 4):
            # iframe = await page.query_selector('')
            # print(iframe)
            # iframe_id = iframe.node_id
            # print(iframe_id)
            # el = await page.find('Ми хочемо переконатися, що це справді ви, а не робот.')
            # id =  await page.send(cdp.dom.perform_search('html'))
            iframe = await custom_wait(page, "iframe")
            # Get required tab. Not safe in case when tab not found
            iframe_tab: uc.Tab = next(
                filter(
                    lambda x: str(x.target.target_id) == str(iframe.frame_id), driver.targets
                )
            )
            # Fixing websocket url
            iframe_tab.websocket_url = iframe_tab.websocket_url.replace("iframe", "page")
            button = await iframe_tab.select(
                'button[id="captcha__audio__button"]'
            )
            await button.click()
            audio = await iframe_tab.select('audio[src]')
            print(audio)
            audio_attrs = audio.attrs
            audio_src = audio_attrs['src']
            print(audio_src)
            captcha_id = random.randint(1, 99)
            input_file = f"captcha{captcha_id}.wav"
            output_file = f"captcha{captcha_id}.mp3"
            download_wav(audio_src, input_file)
            sound = AudioSegment.from_wav(input_file) 
            sound.export(output_file, format="mp3")
            # el = await page.send(cdp.dom.Node.shadow_root_type(iframe))
            
            # print(audio_link)
            solver = TwoCaptcha('29ada3bf8a7df98cfa4265ea1145c77b')
            result = solver.audio(f'./{output_file}', lang='en')
            play_button = await iframe_tab.select('button[class="audio-captcha-play-button push-button"]')
            await play_button.click()
            time.sleep(6)
            print(result['code'])
            numbers = extract_numbers(result['code'])
            print(numbers)
            os.remove(input_file)
            os.remove(output_file)
            time.sleep(5)
            # govna = await iframe_tab.query_selector('div[class="audio-captcha-input-container"]')
            # await govna.send_keys(numbers)
            audio_input = await iframe_tab.query_selector_all('input[class="audio-captcha-inputs"]')
            print(audio_input)
            for i in range(0, 6):
                audio_input_el = await audio_input[i]
                await audio_input_el.focus()
                await audio_input_el.send_keys(numbers[i]) 
                time.sleep(1)
            # await audio_input.send_keys(numbers)
            time.sleep(20)
    except Exception as e:
        print('wait for captcha', e)


async def custom_wait(page, selector, timeout=10):
    for _ in range(0, timeout):
        try:
            element = await page.query_selector(selector)
            if element: return element
            time.sleep(1)
        except Exception as e: 
            time.sleep(1)
            print(selector, e)
    return False


async def custom_wait_elements(page, selector, timeout=10):
    print('in custom wait')
    for _ in range(0, timeout):
        try:
            element = await page.query_selector_all(selector)
            if element: return element
            time.sleep(1)
        except Exception as e: 
            time.sleep(1)
            print(selector, e)
    return False
    

async def check_for_element(page, selector, click=False, debug=False):
    try:
        element = await page.query_selector(selector)
        if click:
            await element.click()
        return element
    except Exception as e:
        if debug: print("selector", selector, '\n', e)
        return False
    

def get_data_from_google_sheets():
    try:
        # Authenticate with Google Sheets API using the credentials file
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)

            with open("token.json", "w") as token:
                token.write(creds.to_json())

        # Connect to Google Sheets API
        service = build("sheets", "v4", credentials=creds)

        # Define the range to fetch (assuming the data is in the first worksheet and starts from cell A2)
        range_name = "main!A2:I"

        # Fetch the data using batchGet
        request = service.spreadsheets().values().batchGet(spreadsheetId=SPREADSHEET_ID, ranges=[range_name])
        response = request.execute()

        # Extract the values from the response
        values = response['valueRanges'][0]['values']

        return values

    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None
    

def post_request(data):
    try:
        json_data = json.dumps(data)
        
    except Exception as e:
        print(e)
    # Set the headers to specify the content type as JSON
    headers = {
        "Content-Type": "application/json"
    }

    # Send the POST request
    try:
        response = requests.post(f"http://localhost:8000/book", data=json_data, headers=headers)
        print(response)
    except Exception as e:
        print(e)
    # Check the response status code
    if response.status_code == 200:
        print("POST request successful!")
    else:
        print("POST request failed.")


def parse_random_category(value):
    if value == '':
        return ['']
    elif '-' in value:
        return list(map(int, value.split('-')))
    else:
        return [int(value)]



async def main(data, reload_time, username=None, password=None, proxy=None, open_url=None):
    try:
        initial_link = 'https://euro2024-sales.tickets.uefa.com/'
        cwd= os.getcwd()
        directory_name = 'NopeCha'
        slash = "\\" if sys.platform == "win32" else "/"
        extension = os.path.join(cwd, directory_name)
        host, port = None, None
        if open_url:
            resp = requests.get(open_url).json()
            if resp["code"] != 0:
                print(resp["msg"])
                print("please check ads_id")
                sys.exit()
            host, port = resp['data']['ws']['selenium'].split(':')
        if host or port: config = nodriver.Config(user_data_dir=None, headless=False, browser_executable_path=None, \
        browser_args=None, sandbox=True, lang='en-US', host=host, port=int(port))
        else: config = nodriver.Config(user_data_dir=None, headless=False, browser_executable_path=None,\
        browser_args=None, sandbox=True, lang='en-US')
        config.add_extension(extension_path=extension)
        if proxy: 
            clear_proxy = proxy.split(':')
            clear_proxy[1] = int(clear_proxy[1])
            proxy_path = ProxyExtension(*clear_proxy)
            print(proxy_path)
            config.add_extension(extension_path=proxy_path.directory)
        driver = await uc.Browser.create(config=config)
        # print(uc.Browser.websocket_url)
        page = await driver.get('https://nopecha.com/setup#sub_1NnGb4CRwBwvt6ptDqqrDlul|keys=|enabled=true|disabled_hosts=|hcaptcha_auto_open=true|hcaptcha_auto_solve=true|hcaptcha_solve_delay=true|hcaptcha_solve_delay_time=3000|recaptcha_auto_open=true|recaptcha_auto_solve=true|recaptcha_solve_delay=true|recaptcha_solve_delay_time=1000|funcaptcha_auto_open=true|funcaptcha_auto_solve=true|funcaptcha_solve_delay=true|funcaptcha_solve_delay_time=0|awscaptcha_auto_open=true|awscaptcha_auto_solve=true|awscaptcha_solve_delay=true|awscaptcha_solve_delay_time=0|turnstile_auto_solve=true|turnstile_solve_delay=true|turnstile_solve_delay_time=1000|perimeterx_auto_solve=false|perimeterx_solve_delay=true|perimeterx_solve_delay_time=1000|textcaptcha_auto_solve=true|textcaptcha_solve_delay=true|textcaptcha_solve_delay_time=0|textcaptcha_image_selector=#img_captcha|textcaptcha_input_selector=#secret|recaptcha_solve_method=Image')
        page = await driver.get(initial_link)
        # time.sleep(1)
        # await wait_for_captcha(page, driver)
        input('continue?')
        print(username, password)
        while True:
            print('in while loop')
            is_captcha = await custom_wait(page, '#root_content', timeout=10)
            if is_captcha:
                if username and password:
                    try:
                        username_el = await page.query_selector('div.idp-static-page div.gigya-composite-control > input[name="username"]')
                        await username_el.scroll_into_view()
                        for i in username:
                            await username_el.send_keys(i)
                            time.sleep(.1)
                        password_el = await page.query_selector('div.idp-static-page div.gigya-composite-control > input[name="password"]')
                        await password_el.scroll_into_view()
                        for i in password:
                            await password_el.send_keys(i)
                            time.sleep(.1)
                        time.sleep(random.randint(1, 3))
                        
                        submit_el = await page.query_selector('div.idp-static-page div.gigya-composite-control > input[type="submit"]')
                        await submit_el.scroll_into_view()
                        await submit_el.mouse_click()
                        time.sleep(2)
                    except Exception as e: print(e)
                else: time.sleep(10)
            elif await custom_wait(page, 'form[id="form_captcha"]', timeout=5):
                try:
                    print('waiting for captcha to resolve...')
                    captcha_button_submit = await page.query_selector('div#form_input_buttons> #submit_button')
                    await captcha_button_submit.click()
                    enter_button = await custom_wait(page, '#action > #actionButtonSpan', timeout=10)
                    if enter_button: await enter_button.click()
                    continue
                except Exception as e: print(e)
            elif await custom_wait(page, '#isolated_header_iframe', timeout=10): break
        

        while True:
            matches = [match[0] for match in data]
            try:
                buy_button = await custom_wait(page, "a.btn-main", timeout=2)
                if buy_button:
                    await buy_button.mouse_click()
            except Exception as e: print(e)
            try: 
                inner_button = await custom_wait(page, 'span[class="button action_buttons_0"]', timeout=2)
                if inner_button: 
                    await inner_button.mouse_move()
                    await inner_button.mouse_click()
            except Exception as e: print(e)
            is_menu = await custom_wait(page, '#performance_container', timeout=5)
            if not is_menu: continue
            break

        
        print("After waiting")
        while True:
            await driver.get()
            await page.back()
            is_menu = await custom_wait(page, '#performance_container')
            if not is_menu: continue
            cookie_box = await custom_wait(page, 'div > #onetrust-reject-all-handler', timeout=1)
            if cookie_box: await cookie_box.mouse_click()
            checkbox = await custom_wait(page, "#toggle_unavailable_matches")
            if not checkbox: pass
            else: 
                await checkbox.mouse_move()
                await checkbox.mouse_click()
            ul_elements = await page.query_selector_all('ul[class="performances_group_container semantic-no-styling"]')
            necessary_matches = []
            
            product_id = ''
            for ul_element in ul_elements:
                lis = await ul_element.query_selector_all('li')
                for li in lis:
                    li_details = await li.query_selector('div[class="perf_details"]')
                    availability_el = await li_details.query_selector('div[class="ticket_availability"] span[class="availability_bullet"]')
                    availability = availability_el.attrs['aria-label']
                    if availability == "Sold out": continue
                    li_teams = await li_details.query_selector_all('p > span > span[class="name"]')
                    match = li_teams[0].text + ' vs ' + li_teams[1].text
                    if match in matches: necessary_matches.append({match: li})
                    
            if len(necessary_matches) == 0:
                print('No available match')
                time.sleep(random.randint(reload_time[0], reload_time[1]))
                continue
            random_match = random.choice(necessary_matches)
            random_match_key, random_match_value = None, None
            for match_key, match_value in random_match.items():
                random_match_value = match_value
                random_match_key = match_key
            await random_match_value.scroll_into_view()
            await random_match_value.mouse_click()
            break
        categories = None
        for i in data:
            print(i[0], random_match_key)
            if i[0] == random_match_key: categories = i[1]
        print(categories)
        while True:
            try:
                necessary_categories = []
                await driver.get()
                await page.back()
                event_form = await custom_wait(page, '#event_form', timeout=60)
                if not event_form: continue
                table_elements = await page.query_selector_all('table > tbody > tr[data-conditionalrateid]')

                is_empty_category = True
                for value in categories.values():
                    if value != '': is_empty_category = False

                last_seen_cat = None
                for index in range(0, len(table_elements)):
                    table_element = table_elements[index]
                    category = await table_element.query_selector('.category')
                    if category.text.strip(): last_seen_cat = table_element
                    if not category: continue
                    category_text = ''
                    if category.tag_name == 'td': 
                        category_text = last_seen_cat.text.strip()
                        print(category_text)
                    if 'category_unavailable' in table_element.attrs['class_']: continue
                    is_available = await table_element.query_selector('td.quantity > select')
                    if not is_available: continue
                    # print(category.text.strip().lower())
                    print(category.text.strip())
                    # category_el = categories[category.text.strip()]
                    if not category_text:
                        if category.text.strip() in [category for category in categories.keys()]:
                            # print(category)
                            if not is_empty_category:
                                if categories[category.text.strip()] != '':
                                    necessary_categories.append([table_element, categories[category.text.strip()]])
                            # else: necessary_categories.append([table_element, 0])
                    else:
                        if category_text in [category for category in categories.keys()]:
                            if not is_empty_category:
                                if categories[category_text] != '':
                                    necessary_categories.append([table_element, categories[category_text]])
                if necessary_categories == []: 
                    print('No available tickets')
                    time.sleep(random.randint(reload_time[0], reload_time[1]))
                    continue
                print('AFTER ALL THE SHIT')
                while necessary_categories:
                    random_category = random.choice(necessary_categories)
                    print(random_category)
                    await random_category[0].scroll_into_view()
                    quantity_selector = await random_category[0].query_selector('td.quantity > select')
                    await quantity_selector.scroll_into_view()
                    await quantity_selector.click()
                    parsed_values = parse_random_category(random_category[1])
                    option = None
                    
                    if parsed_values:
                        if len(parsed_values) > 1:  # This means we have a range
                            min_value = parsed_values[0]
                            max_value = parsed_values[1]
                            
                            options_len_element = await quantity_selector.query_selector_all('option')
                            options_len = len(options_len_element) - 1
                            if min_value <= options_len <= max_value:
                                option = await quantity_selector.query_selector(f'option[value="{str(options_len)}"]')
                            elif options_len >= max_value:
                                option = await quantity_selector.query_selector(f'option[value="{str(max_value)}"]')
                        else:  # Single digit case
                            single_value = parsed_values[0]
                            
                            if single_value != 0:
                                option = await quantity_selector.query_selector(f'option[value="{str(single_value)}"]')

                    if option:
                        # Break out of the loop if a valid option is found
                        break
                    else:
                        # Remove the current category from the list
                        necessary_categories.remove(random_category)
                        print('Not enough tickets in category. Trying another category.')
                        
                        if not necessary_categories:
                            # If no more categories are left, wait and then continue
                            print('No more categories left. Waiting before retrying.')
                            time.sleep(random.randint(reload_time[0], reload_time[1]))
                await option.scroll_into_view()
                await option.select_option()
                
                book_button = await page.query_selector('#book')
                await book_button.scroll_into_view()
                await book_button.mouse_click()
                sucess = None

                captcha_dialog = await custom_wait(page, 'div[aria-describedby="captcha_dialog"]', timeout=5)
                # print(captcha_dialog.attrs('class_'))
                if captcha_dialog: 
                    continue_button = await custom_wait(captcha_dialog, '#captcha_dialog_continue_invisible', timeout=1)
                    await continue_button.scroll_into_view()
                    await continue_button.mouse_move()
                    await continue_button.mouse_click()
                    sucess = await custom_wait(page, 'section[class="message success "]', timeout=50)
                else:
                    sucess = await custom_wait(page, 'section[class="message success "]', timeout=10)
                if sucess:
                    sound, fs = sf.read('notify.wav', dtype='float32')
                    sd.play(sound, fs)
                    status = sd.wait()
                    match_number = await custom_wait(page, 'span[class="match_round_name perf_info_list_content"]', timeout=1)
                    match_number_text = match_number.text
                    print(match_number_text)
                    match_amount = await custom_wait(page, 'td[class="stx_tfooter reservation_amount"] span[class="int_part"]', timeout=1)
                    match_amount_text = "€ " + match_amount.text
                    print(match_amount_text)
                    match_unit_price = await custom_wait(page, 'td[class="unit_price"] span[class="int_part"]',timeout=1)
                    match_unit_price_text = "€ " + match_unit_price.text
                    print(match_unit_price_text)
                    description = await custom_wait(page, 'p[class="semantic-no-styling-no-display description"]', timeout=1)
                    description_text = description.text.strip()
                    print(description_text)
                    data_to_post = {"match_number": match_number_text, "total_price": match_amount_text, \
                    "unit_price":match_unit_price_text, "category": description_text}
                    try: post_request(data_to_post)
                    except: pass
                    input('continue?')
                    await page.back()
                if random_category[1] != 0:
                    option = await quantity_selector.query_selector(f'option[value="0"]')
                    await option.scroll_into_view()
                    await option.select_option()
                time.sleep(random.randint(reload_time[0], reload_time[1]))
            except Exception as e: 
                print(e)
                time.sleep(60)
                
    except Exception as e: 
        print(e)
        time.sleep(60)


def is_valid_category_input(value):
    if value == '':
        return True
    elif re.match(r'^[1-4]$', value):
        return True
    elif re.match(r'^[1-4]-[1-4]$', value):
        start, end = map(int, value.split('-'))
        return start < end
    return False


def is_valid_reload_time(value):
    if value == '':
        return True
    elif re.match(r'^\d+-\d+$', value):
        start, end = map(int, value.split('-'))
        return start < end
    return False


def get_valid_input(prompt, validation_func, default=''):
    while True:
        value = input(prompt).strip()
        if validation_func(value):
            return value if value else default
        print("Неправильне введення. Будь ласка, введіть одну цифру (1-4), діапазон (наприклад, 1-4) або залиште порожнім.")


def parse_reload_time(value):
    if value:
        start, end = map(int, value.split('-'))
        return [start, end]
    return [45, 60]


def gather_inputs():
    username = input('username: ').strip()
    password = input('password: ').strip()
    proxy = input('proxy: ').strip() if not adspower_link else None
    reload_time_input = get_valid_input('Reload time (Або залиште порожнім для [45, 60]): ', is_valid_reload_time, '45-60')
    reload_time = parse_reload_time(reload_time_input)
    
    data = []
    for row_index in row_indexes:
        match = matches[int(row_index)-1][0]
        print(match, "[НАЛАШТУВАННЯ]")

        categories = {}
        for i in range(1, 5):
            category_value = get_valid_input(f'Category {i} (Або залиште порожнім): ', is_valid_category_input)
            categories[f"Category {i}"] = category_value
        
        if input('Use same values for Restricted View categories? [yes/no]: ').strip().lower() == 'yes':
            for i in range(1, 5):
                categories[f"Cat. {i} Restricted View"] = categories[f"Category {i}"]
        else:
            for i in range(1, 5):
                categories[f"Cat. {i} Restricted View"] = get_valid_input(f'Cat. {i} Restricted View (Або залиште порожнім): ', is_valid_category_input)

        categories["Fans First"] = get_valid_input('Fans First (Або залиште порожнім): ', is_valid_category_input)
        categories["Prime Seats"] = get_valid_input('Prime Seats (Або залиште порожнім): ', is_valid_category_input)

        data.append([match, categories])
    return data, username, password, proxy, reload_time


if __name__ == '__main__':
    # data = get_data_from_google_sheets()
    threads = []
    matches = [
        ["Germany vs Scotland"],
        ["Hungary vs Switzerland"],
        ["Spain vs Croatia"],
        ["Italy vs Albania"],
        ["Serbia vs England"],
        ["Slovenia vs Denmark"],
        ["Poland vs Netherlands"],
        ["Austria vs France"],
        ["Belgium vs Slovakia"],
        ["Romania vs Ukraine"],
        ["Turkey vs Georgia"],
        ["Portugal vs Czech Republic"],
        ["Scotland vs Switzerland"],
        ["Germany vs Hungary"],
        ["Croatia vs Albania"],
        ["Spain vs Italy"],
        ["Denmark vs England"],
        ["Slovenia vs Serbia"],
        ["Poland vs Austria"],
        ["Netherlands vs France"],
        ["Slovakia vs Ukraine"],
        ["Belgium vs Romania"],
        ["Turkey vs Portugal"],
        ["Georgia vs Czechia"],
        ["Switzerland vs Germany"],
        ["Scotland vs Hungary"],
        ["Albania vs Spain"],
        ["Croatia vs Italy"],
        ["England vs Slovenia"],
        ["Denmark vs Serbia"],
        ["Netherlands vs Austria"],
        ["France vs Poland"],
        ["Slovakia vs Romania"],
        ["Ukraine vs Belgium"],
        ["Georgia vs Portugal"],
        ["Czech Republic vs Turkey"],
        ["1A vs 2C"],
        ["2A vs 2B"],
        ["1B vs 3A/D/E/F"],
        ["1C vs 3D/E/F"],
        ["1F vs 3A/B/C"],
        ["2D vs 2E"],
        ["1E vs 3A/B/C/D"],
        ["W39 vs W37"],
        ["W40 vs W38"],
        ["W41 vs W42"],
        ["W43 vs W44"],
        ["W45 vs W46"],
        ["W47 vs W48"],
        ["W49 vs W50"]
    ]
    
    for index, match in enumerate(matches, 1):
        print(f"{index}: {match[0]}")
    data = []
    row_indexes= input('Indexes (separated by + symbol): ').strip().split('+')


    while True:
        is_adspower = input('use adspower? [ yes / no ]: ').strip().lower()
        if is_adspower in ['yes', 'no']:
            adspower_link = None
            if is_adspower == 'yes':
                adspower = input('adspower api: ').strip()
                adspower_id = input('adspower id: ').strip()
                adspower_link = f"{adspower}/api/v1/browser/start?user_id={adspower_id}"
                print(adspower_link)

            data, username, password, proxy, reload_time = gather_inputs()
            uc_fix(nodriver)
            uc.loop().run_until_complete(main(data, reload_time, username, password, proxy, open_url=adspower_link))
        else:
            print('Введіть 1 з запропонованих варіантів [ yes / no ]')