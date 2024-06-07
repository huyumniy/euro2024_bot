import os
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
            iframe = await page.select("iframe")
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
    print('in custom wait')
    for _ in range(0, timeout):
        try:
            element = await page.query_selector(selector)
            if element: return element
            time.sleep(1)
        except Exception as e: 
            time.sleep(1)
            print(e)
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
            print(e)
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


async def main(link, categories, username, password):
    try:
        initial_link = 'https://euro2024-sales.tickets.uefa.com/'
        config = nodriver.Config(user_data_dir=None, headless=False, browser_executable_path=None, browser_args=None, sandbox=True, lang='en-US')
        config.add_extension(extension_path='./NopeCha')
        driver = await uc.start(config=config)
        page = await driver.get('https://nopecha.com/setup#sub_1NnGb4CRwBwvt6ptDqqrDlul|keys=|enabled=true|disabled_hosts=|hcaptcha_auto_open=true|hcaptcha_auto_solve=true|hcaptcha_solve_delay=true|hcaptcha_solve_delay_time=3000|recaptcha_auto_open=true|recaptcha_auto_solve=true|recaptcha_solve_delay=true|recaptcha_solve_delay_time=1000|funcaptcha_auto_open=true|funcaptcha_auto_solve=true|funcaptcha_solve_delay=true|funcaptcha_solve_delay_time=0|awscaptcha_auto_open=true|awscaptcha_auto_solve=true|awscaptcha_solve_delay=true|awscaptcha_solve_delay_time=0|turnstile_auto_solve=true|turnstile_solve_delay=true|turnstile_solve_delay_time=1000|perimeterx_auto_solve=false|perimeterx_solve_delay=true|perimeterx_solve_delay_time=1000|textcaptcha_auto_solve=true|textcaptcha_solve_delay=true|textcaptcha_solve_delay_time=0|textcaptcha_image_selector=#img_captcha|textcaptcha_input_selector=#secret|recaptcha_solve_method=Image')
        page = await driver.get(initial_link)
        input(f'\ncontinue?')
        while True:
            is_captcha = await custom_wait(page, '#root_content', timeout=10)
            if is_captcha:
                try:
                    username_el = await page.query_selector('div.idp-static-page div.gigya-composite-control > input[name="username"]')
                    for i in username:
                        await username_el.send_keys(i)
                        time.sleep(.1)
                    password_el = await page.query_selector('div.idp-static-page div.gigya-composite-control > input[name="password"]')
                    for i in password:
                        await password_el.send_keys(i)
                        time.sleep(.1)
                    time.sleep(random.randint(1, 3))
                    submit_el = await page.query_selector('div.idp-static-page div.gigya-composite-control > input[type="submit"]')
                    await submit_el.mouse_click()
                except: pass
            elif await custom_wait(page, 'form[id="form_captcha"]', timeout=5):
                try:
                    print('waiting for captcha to resolve...')
                    captcha_button_submit = await page.query_selector('div#form_input_buttons> #submit_button')
                    await captcha_button_submit.click()
                    enter_button = await custom_wait(page, '#action > #actionButtonSpan', timeout=10)
                    if enter_button: await enter_button.click()
                    continue
                except: pass
            elif await custom_wait(page, '#main_content_account_home_personal_offers', timeout=5): break
            print('no captcha and login')
                
        

        # await page.wait_for('#performance_container')
        # ul_elements = await page.query_selector_all('ul[class="performances_group_container semantic-no-styling"]')
        # necessary_matches = []
        
        # product_id = ''
        # for ul_element in ul_elements:
        #     lis = await ul_element.query_selector_all('li')
        #     for li in lis:
        #         li_details = await li.query_selector('div[class="perf_details"]')
        #         availability_el = await li_details.query_selector('div[class="ticket_availability"] span[class="availability_bullet"]')
        #         availability = availability_el.attrs['aria-label']
        #         if availability == "Sold out": continue
        #         li_teams = await li_details.query_selector_all('p > span > span[class="name"]')
        #         match = li_teams[0].text + ' vs ' + li_teams[1].text
        #         print(match, 'id', li.attrs['id'])
        #         if match in matches: necessary_matches.append(li)
        
        # random_match = random.choice(necessary_matches)
        # product_id = random_match.attrs['id']
        # print(product_id)
        
        # await random_match.scroll_into_view()
        # await random_match.mouse_click()

        while True:
            try:
                necessary_categories = []
                print('before page')
                page = await driver.get(link)
                print('after page')
                await page.wait_for('#event_form')
                table_elements = await page.query_selector_all('table > tbody > tr[data-conditionalrateid]')

                is_empty_category = True
                for value in categories.values():
                    if value != '': is_empty_category = False

                
                for table_element in table_elements:
                    category = await table_element.query_selector('th.category')
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
                    time.sleep(random.randint(20, 40))
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

                captcha_dialog = await custom_wait(page, 'div[aria-describedby="captcha_dialog"]', timeout=5)
                if captcha_dialog: 
                    continue_button = await captcha_dialog.query_selector('#captcha_dialog_continue_invisible')
                    await continue_button.scroll_into_view()
                    await continue_button.click()
                    sucess = await custom_wait(page, 'section[class="message success "]', timeout=50)
                else:
                    sucess = await custom_wait(page, 'section[class="message success "]', timeout=10)
                if sucess:
                    data, fs = sf.read('notify.wav', dtype='float32')  
                    sd.play(data, fs)
                    status = sd.wait()
                    input('continue?')
                time.sleep(random.randint(20, 40))
            except Exception as e: print(e)
                
    except Exception as e: 
        print(e)
        time.sleep(30)


if __name__ == '__main__':
    # data = get_data_from_google_sheets()
    threads = []
    matches = [
    ["Hungary vs Switzerland", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753867/contact-advantages/10229302961043/lang/en"],
    ["Slovenia vs Denmark", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753871/contact-advantages/10229302961043/lang/en"],
    ["Austria vs France", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753872/contact-advantages/10229302961043/lang/en"],
    ["Belgium vs Slovakia", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753873/contact-advantages/10229302961043/lang/en"],
    ["Romania vs Ukraine", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753874/contact-advantages/10229302961043/lang/en"],
    ["Croatia vs Albania", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753875/contact-advantages/10229302961043/lang/en"],
    ["Slovenia vs Serbia", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753880/contact-advantages/10229302961043/lang/en"],
    ["Poland vs Austria", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753883/contact-advantages/10229302961043/lang/en"],
    ["Slovakia vs Ukraine", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753886/contact-advantages/10229302961043/lang/en"],
    ["Belgium vs Romania", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753887/contact-advantages/10229302961043/lang/en"],
    ["Georgia vs Czechia", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753889/contact-advantages/10229302961043/lang/en"],
    ["England vs Slovenia", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753895/contact-advantages/10229302961043/lang/en"],
    ["Denmark vs Serbia", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753896/contact-advantages/10229302961043/lang/en"],
    ["Netherlands vs Austria", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753897/contact-advantages/10229302961043/lang/en"],
    ["France vs Poland", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753898/contact-advantages/10229302961043/lang/en"],
    ["Slovakia vs Romania", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753899/contact-advantages/10229302961043/lang/en"],
    ["Ukraine vs Belgium", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753900/contact-advantages/10229302961043/lang/en"],
    ["2A vs 2B", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753904/contact-advantages/10229302961043/lang/en"],
    ["1B vs 3A/D/E/F", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753905/contact-advantages/10229302961043/lang/en"],
    ["1F vs 3A/B/C", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753907/contact-advantages/10229302961043/lang/en"],
    ["2D vs 2E", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753908/contact-advantages/10229302961043/lang/en"],
    ["1E vs 3A/B/C/D", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753909/contact-advantages/10229302961043/lang/en"],
    ["W41 VS W42", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753912/contact-advantages/10229302961043/lang/en"],
    ["W43 VS W44", "https://euro2024-sales.tickets.uefa.com/secure/selection/event/seat/performance/101810753913/contact-advantages/10229302961043/lang/en"]
]

    
    for index, match in enumerate(matches):
        print(f"{index}: {match[0]}")
    while True:
        try:
            match_index = int(input('Введіть індекс матча, який хочете обрати: '))
            break
        except: pass
    
    link = matches[match_index][1]
    category1 = input('Category 1 (Або залиште порожнім): ')
    category2 = input('Category 2 (Або залиште порожнім): ')
    category3 = input('Category 3 (Або залиште порожнім): ')
    category4 = input('Category 4 (Або залиште порожнім): ')
    categories = {"Category 1": category1, "Category 2": category2, "Category 3": category3, "Category 4": category4}
    username = input('username: ')
    password = input('password: ')
    print(link)
    uc.loop().run_until_complete(main(link, categories, username, password))
    
