import os
import io
import base64
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings("ignore")

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from pydantic import BaseModel
from typing import Optional

from wordcloud import WordCloud
import matplotlib.pyplot as plt
import logging

def word_matching(search_key, sentences):
    search_key_list = search_key.split(",")
    length = [words for words in search_key_list if words.lower().strip() in sentences.lower().strip()]
    if len(length)!=0:
        status = True

    if len(length)==0:
        status = False

    return status

def create_log_files(user_name):

    # Define logger name per user
    logger = logging.getLogger(user_name)
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not logger.handlers:
        # File handler for each user logs\admin.log
        file_handler = logging.FileHandler(f"logs\{user_name}.log",encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # Log format
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger

class TicketDataModel(BaseModel):
      name             : Optional[str] = None
      similarity_score : Optional[float] = None
      other            : Optional[str] = None
      issue            : Optional[str] = None
      rca              : Optional[str] = None
      resolution       : Optional[str] = None
      short_description   : Optional[str] = None
      resolution_category : Optional[str] = None

def load_dataset():
    load_path = os.path.join("artifacts", "mergeset.xlsx")
    dataset = pd.read_excel(load_path)
    return dataset

def get_similarity_search(input_string,source):

    documents    = [str(row) for row in source['ResolutionLongText'].str.lower().values]
    all_texts    = [input_string] + documents

    vectorizer   = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    # Compute cosine similarity between input string and each document
    cosine_similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:])

    records = []

    for idx, score in zip(source['Number'].values,cosine_similarities[0]):
        # if score>=0.1:
            if idx not in records:
            # print(f"Document {idx}: {score:.4f}")
               records.append([idx,score])
    
    left_table  = pd.DataFrame(records,columns=['Number','Score'])
    merge_table = pd.merge(left_table,source,left_on=['Number'],right_on=['Number'],how='left')
    merge_table = merge_table.sort_values("Score",ascending=False)

    # Title >> ['Number', 'Score', 'Other', 'Issue', 'RCA', 'Resolution', 'Short description','Reported']
    return merge_table[['Number', 'Score', 'Title', 'Issue', 'RCA', 'Resolution', 'Short Description','Reported']]


def word_frequency_plot(username, dataset,columns = 'ResolutionLongText'):

    sentences    = ' '.join(dataset[columns].astype(str).tolist())
    word_buckets = ''.join(word for word in sentences)
    
    # plt.figure(figsize=(10, 5))
    wordcloud = WordCloud(width=800, height=300, background_color='white').generate(word_buckets)
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')  
    output_path = f'static/images/Issue_{username}.png'
    wordcloud.to_file(output_path)
    return output_path

def get_updated_dropdown_info(metadata,form_info):
    # recommandations    = form.get("number_of_recommendation")
    # similarity_score   = form.get("similarity_score_limit")

    # metadata['number_of_recommendation'] = recommandations
    # metadata['similarity_score_limit']   = similarity_score

    # metadata['selected_recommandation'] = recommandations
    # metadata['selected_similarity']     = similarity_score

    for columns in ['number_of_recommendation','similarity_score_limit']:

        original_dropdown = [row for row in metadata[columns] if row!=form_info[columns]]

        upgraded_dropdown = [form_info[columns]] + original_dropdown

        metadata[columns] = upgraded_dropdown

    return metadata