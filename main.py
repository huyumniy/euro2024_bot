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


async def main(data, username=None, password=None, proxy=None, open_url=None):
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
                if not buy_button: continue
                await buy_button.mouse_click()
            except Exception as e: print(e)
            try: 
                inner_button = await custom_wait(page, 'span[class="button action_buttons_0"]', timeout=2)
                if not inner_button: pass
                else:
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
                time.sleep(random.randint(45,60))
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

                
                for table_element in table_elements:
                    category = await table_element.query_selector('th.category')
                    if not category: continue
                    if 'category_unavailable' in table_element.attrs['class_']: continue
                    # print(category.text.strip().lower())
                    print(category.text.strip())
                    # category_el = categories[category.text.strip()]
                    
                    if category.text.strip() in [category for category in categories.keys()]:
                        # print(category)
                        if not is_empty_category:
                            if categories[category.text.strip()] != '':
                                necessary_categories.append([table_element, categories[category.text.strip()]])
                        # else: necessary_categories.append([table_element, 0])
                if necessary_categories == []: 
                    print('No available tickets')
                    time.sleep(random.randint(45, 60))
                    continue
                random_category = random.choice(necessary_categories)
                await random_category[0].scroll_into_view()
                quantity_selector = await random_category[0].query_selector('td.quantity > select')
                await quantity_selector.scroll_into_view()
                await quantity_selector.click()
                if random_category[1] != 0:
                    option = await quantity_selector.query_selector(f'option[value="{str(random_category[1])}"]')
                # else: option = await quantity_selector.query_selector(f'option[value="{str(random.randint(1, 4))}"]')
                await option.scroll_into_view()
                await option.select_option()

                book_button = await page.query_selector('#book')
                await book_button.scroll_into_view()
                await book_button.mouse_click()
                sucess = None
                captcha_dialog = await custom_wait(page, 'div[aria-describedby="captcha_dialog"]', timeout=5)
                # print(captcha_dialog.attrs('class_'))
                if captcha_dialog: 
                    continue_button = await captcha_dialog.query_selector('#captcha_dialog_continue_invisible')
                    await continue_button.scroll_into_view()
                    await continue_button.click()
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
                time.sleep(random.randint(45, 60))
            except Exception as e: 
                print(e)
                time.sleep(60)
                
    except Exception as e: 
        print(e)
        time.sleep(60)


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
        is_adspower = input('use adspower? [ yes / no ]: ')
        if is_adspower.lower().strip() in ['yes', 'no']:
            if is_adspower.lower().strip() == 'yes':
                adspower = input('adspower api: ')
                adspower_id = input('adspower id: ')
                adspower_link = adspower + '/api/v1/browser/start?user_id=' + adspower_id
                print(adspower_link)
                username = input('username: ')
                password = input('password: ')
                proxy = None
                for row_index in row_indexes:
                    match = matches[int(row_index)-1][0]
                    print(match, "[НАЛАШТУВАННЯ]")
                    category1 = input('Category 1 (Або залиште порожнім): ')
                    category2 = input('Category 2 (Або залиште порожнім): ')
                    category3 = input('Category 3 (Або залиште порожнім): ')
                    category4 = input('Category 4 (Або залиште порожнім): ')
                    fansFirst = input('Fans First (Або залиште порожнім): ')
                    primeSeats = input('Prime Seats (Або залиште порожнім): ')
                    categories = {"Category 1": category1, "Category 2": category2, "Category 3": category3, "Category 4": category4, "Fans First": fansFirst, "Prime Seats": primeSeats}
                    data.append([match, categories])

            else:
                username = input('username: ')
                password = input('password: ')
                proxy = input('proxy: ')
                adspower_link = None
                for row_index in row_indexes:
                    match = matches[int(row_index)-1][0]
                    print(match, "[НАЛАШТУВАННЯ]")
                    category1 = input('Category 1 (Або залиште порожнім): ')
                    category2 = input('Category 2 (Або залиште порожнім): ')
                    category3 = input('Category 3 (Або залиште порожнім): ')
                    category4 = input('Category 4 (Або залиште порожнім): ')
                    fansFirst = input('Fans First (Або залиште порожнім): ')
                    primeSeats = input('Prime Seats (Або залиште порожнім): ')
                    categories = {"Category 1": category1, "Category 2": category2, "Category 3": category3, "Category 4": category4, "Fans First": fansFirst, "Prime Seats": primeSeats}
                    data.append([match, categories])
            uc.loop().run_until_complete(main(data, username, password, proxy, open_url=adspower_link))
        else:
            print('Введіть 1 з запропонованих варіантів [ yes / no ]')
