from selenium import webdriver
import time
from PIL import Image
import urllib.request

#Scraping mareas INA
urllib.request.urlretrieve('https://alerta.ina.gob.ar/ina/42-RIODELAPLATA/productos/Prono_SanFernando.png',
                            "/home/facundol/deltix/marea.png")
print('Obtuvo mareas INA')
#Scraping windguru
options = webdriver.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--headless")
options.add_argument("--disable-gpu")
driver = webdriver.Chrome(options=options)
print('Abriendo navegador, yendo a Windguru y esperando 20 segundos')
driver.get('https://www.windguru.cz/632702')
time.sleep(20)
driver.save_screenshot('/home/facundol/deltix/screenshot_windguru.png')
print('Taking screenshot')
x = 1
y = 220
width = 840
height = 320

full_screenshot = Image.open('/home/facundol/deltix/screenshot_windguru.png')
cropped_area = full_screenshot.crop((x, y, x + width, y + height))
cropped_area.save('/home/facundol/deltix/windguru.png')
print('Cropping and saving the image')
driver.quit()
