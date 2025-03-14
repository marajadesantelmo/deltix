from selenium import webdriver
import time
#from PIL import Image
import urllib.request
from bs4 import BeautifulSoup

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
driver.save_screenshot('/home/facundol/deltix/windguru.png')

driver.get('https://www.hidro.gov.ar/oceanografia/pronostico.asp')

time.sleep(10)
html = driver.page_source
soup = BeautifulSoup(html, 'html.parser')

# Find the table
table = soup.find('table')

# Extract table data
table_data = []
if table:
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        table_data.append(cols)

print(table_data)

table_text = '\n'.join(['\t'.join(row) for row in table_data])

with open('/home/facundol/deltix/table_data.txt', 'w') as file:
    file.write(table_text)

driver.quit()
