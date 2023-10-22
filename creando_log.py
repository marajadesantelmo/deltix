''' 
Este script genera el log de envios_diarios. Sirve para resetear el log.
'''

import pandas as pd
log_data = pd.DataFrame(columns=['Timestamp', 'User ID', 'user_name'])
log_data.to_csv('envio_diario_log.csv', index=False)