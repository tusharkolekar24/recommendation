import json
from typing import Dict
import pandas as pd
import time 

with open(r'json\config.json','r') as files:
    users = json.load(files)

def get_home_dropdwon_info()->Dict:
    return {
            'number_of_recommendation': ['3','5','10','15','25','30','45','50'],
            'similarity_score_limit'  : ['0.1', '0.2','0.3','0.4','0.5','0.6','0.7','0.8','0.9'],
            'user_awareness'          : ['All'],
            'report_paramerter'       : '',
            'issue_info'              : 'User experiences repeated failure while processing financial transactions due to unexpected system validation errors banking production system.',
            'recommandations'         : [],
            # 'original_similarity_info' : pd.DataFrame(),
            'similarity_info'         : pd.DataFrame(),
            'selected_recommandation' : '3',
            'selected_similarity'     : '0.2',
            'number_of_ticket'        : '0',
            'similarity_range'        : '0 to 1',
            'frequency_plot'          : None,
            'timestamp'               : int(time.time())
            }
