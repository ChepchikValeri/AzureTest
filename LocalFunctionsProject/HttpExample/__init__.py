import logging
import requests
import base64
from requests.models import Response

import azure.functions as func
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.expected_conditions import presence_of_element_located
from selenium.webdriver.common.by import By
import logging

from twocaptcha import TwoCaptcha
MY2CAPTCHAKEY = "7d2cc7ff2b766ab67bb4b223d09c0c6d"
solver = TwoCaptcha(MY2CAPTCHAKEY)

#settings
wait_time = 10
def init_driver(WINDOW_SIZE):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'--window-size={WINDOW_SIZE}')

    USER_AGENT = requests.get("https://api.user-agent.io/?browser=chrome&os=windows")
    chrome_options.add_argument(f'user-agent={USER_AGENT}')
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--hide-scrollbars')
    chrome_options.add_argument('--ignore-certificate-errors')
    
    # The below options are necessary to prevent Chrome from crashing in Docker
    # Bypass OS security model
    chrome_options.add_argument('--no-sandbox')
    
    # Chrome uses /dev/shm drive for internal memory management
    # In Docker the size of the drive by default is 64mb - which is not enough and causes crashes
    # Either disable dev shm usage in options (slower option, as the temp directory is used) or
    # build the container with a specified size of /dev/shm.
    chrome_options.add_argument('--disable-dev-shm-usage')
    
    # Initiate the driver
    try:
        driver = webdriver.Chrome(
            "/usr/local/bin/chromedriver", chrome_options=chrome_options)
    except WebDriverException:
        logging.exception("Failed to initialize the browser driver.")
        
    return driver

def main(req: func.HttpRequest) -> func.HttpResponse:
    if req.url.endswith('.png'):
        with open ("screenshot.png") as file:
            func.HttpResponse(
                file,
                mimetype="image/png"
            )
    logging.info('Python HTTP trigger function processed a request.')
    driver = init_driver('1280,720')
    wait = WebDriverWait(driver, wait_time)
    url = req.params.get('url')
    response_data = "<!DOCTYPE html><html><head></head> <body> "
    response_code = ""
    if not url:
        try:
            req_body = req.get_json()
        except ValueError:
            response_data+="something wrong with your json request, we cannot process it"
            response_code=404
        else:
            url = req_body.get('url')

    if url:
        driver.get(url)
        res = wait.until(presence_of_element_located((By.TAG_NAME, "body"))).text
        #check captcha
        if driver.find_elements_by_css_selector("#rc-anchor-container"):
            response_data+= f"This site {url} has capthca </br>{res}"
            response_code=200
        else:
            response_data+= f"This site {url} has NO capthca </br>{res}"
            response_code=200
    else:
            response_data+= "This HTTP triggered function executed successfully. Pass a url in the query string or in the request body for a personalized response."
            response_code=200
    driver.save_screenshot("screenshot.png")
    with open ("screenshot.png", "rb") as file:
        scr64 = base64.b64encode(file.read())
    response_data+='</br> <img src="data:image/png;base64,'
    response_data+=str(scr64)[2:-1]
    response_data+='">' 
    response_data+="</body></html>"
    driver.quit()

    return func.HttpResponse(
             response_data,
             status_code=response_code,
             mimetype="text/html"
        )
