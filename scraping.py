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
raw_table_data = []
if table:
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        cols = [ele.text.strip() for ele in cols]
        raw_table_data.append(cols)

print("Raw table data:", raw_table_data)

# Process the table data to associate each row with its port
processed_data = []
current_port = None
san_fernando_data = []
is_san_fernando = False

for row in raw_table_data:
    # Skip empty rows
    if not row:
        continue
    
    # If the first cell has a value, it's a port name
    if row[0]:
        current_port = row[0]
        # Check if this is San Fernando port
        is_san_fernando = "SAN FERNANDO" in current_port.upper()
    
    # Only add rows that have at least 4 elements (tide type, time, height, date)
    # and belong to San Fernando port
    if len(row) >= 4 and is_san_fernando:
        processed_row = [current_port if current_port else ""] + row[1:]
        processed_data.append(processed_row)
        san_fernando_data.append(row[1:])  # Store without port name

print("Processed data for San Fernando:", processed_data)

# Convert to text with proper formatting
table_text = ""
if processed_data:
    # Add the port name as a header
    table_text += f"{processed_data[0][0]}\n"
    # Add column headers
    table_text += "Tipo\tHora\tAltura\tFecha\n"
    # Add the data rows
    for row in san_fernando_data:
        if len(row) >= 4:  # Complete row with tide type, time, height, date
            tide_type = row[0]
            time = row[1]
            height = row[2]
            date = row[3]
            table_text += f"{tide_type}\t{time}\t{height}\t{date}\n"

with open('/home/facundol/deltix/table_data.txt', 'w') as file:
    file.write(table_text)

driver.quit()
