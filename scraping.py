from selenium import webdriver
from selenium.webdriver.firefox.service import Service
import time
from PIL import Image
import urllib.request

#Scraping mareas INA
urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png', "Marea.png")
print('Obtuvo mareas INA')
#Scraping windguru
options = webdriver.FirefoxOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument("start-maximized")
options.add_argument('--user-agent=""Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.157 Safari/537.36""') # user agent
options.binary_location = 'C://Program Files//Mozilla Firefox//firefox.exe'

service = Service(executable_path="C://Users//Usuario//Documents//GitHub//deltix//geckodriver.exe")
driver = webdriver.Firefox(options=options, service=service)
print('Abre navegador y va a wind guru')
driver.get('https://www.windguru.cz/632702')
time.sleep(10)
driver.save_screenshot('C://Users//Usuario//Documents//GitHub//deltix//screenshot_windguru.png')
print('Saca screenshot')
x = 1  
y = 220  
width = 840 
height = 300 

full_screenshot = Image.open('C://Users//Usuario//Documents//GitHub//deltix//screenshot_windguru.png')
cropped_area = full_screenshot.crop((x, y, x + width, y + height))
cropped_area.save('C://Users//Usuario//Documents//GitHub//deltix//windguru.png')
print('Lo corta y lo guarda')
driver.quit()