
import pandas as pd
user_experience = pd.read_csv('user_experience.csv')
user_experience['first_interaction'] = 'NaN'

user_experience['suscr_windguru_ofrecida'] = ''
user_experience['suscr_marea_ofrecida'] = ''

from datetime import datetime
datetime.now().strftime('%d-%m-%Y %H:%M')

user_experience.to_csv('user_experience.csv', index=False)



user_id= 672134330

user_id in user_experience['User ID'][user_experience['suscr_marea_ofrecida'].isna()].values

user_experience['suscr_marea_ofrecida'][user_experience['User ID']==user_id] = datetime.now().strftime('%d-%m-%Y %H:%M')

user_experience.loc[user_experience['User ID'] == user_id, 'suscr_marea_ofrecida'] =  datetime.now().strftime('%d-%m-%Y %H:%M')