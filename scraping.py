from selenium import webdriver
from selenium.webdriver.firefox.service import Service
import time
from PIL import Image
import urllib.request

#Scraping mareas INA
urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png', "Marea.png")

#Scraping windguru
options = webdriver.FirefoxOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument("start-maximized")
options.add_argument('--user-agent=""Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36""') # user agent
options.binary_location = 'C:/Program Files/Mozilla Firefox/firefox.exe'

service = Service(executable_path="geckodriver.exe")
driver = webdriver.Firefox(options=options, service=service)
driver.get('https://www.windguru.cz/632702')
time.sleep(10)
driver.save_screenshot('screenshot_windguru.png')

x = 1  
y = 220  
width = 840 
height = 300 

full_screenshot = Image.open('screenshot_windguru.png')
cropped_area = full_screenshot.crop((x, y, x + width, y + height))
cropped_area.save('windguru.png')

driver.quit()