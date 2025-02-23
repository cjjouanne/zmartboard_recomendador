# !pip install -U sentence-transformers
# !pip install spacy
# !pip install transformers
# !pip install rake_nltk

# requerimientos:
# - lesson.csv en misma carpeta que este archivo.
# - se crean los archivos
#     - corpus_embeddings_base.txt
#     - corpus_embeddings_tags.txt
#     - json_data_sin_tags.json
#     - json_data_tags.json

from nltk.tokenize import RegexpTokenizer
from nltk.stem import SnowballStemmer
from rake_nltk import Rake
import nltk
nltk.download("stopwords")
from nltk.corpus import stopwords
import os
import re
from string import punctuation
import unicodedata
import json
import time
import pandas as pd
import numpy as  np
from sentence_transformers import SentenceTransformer, util
import torch
import pickle
import datetime
from init import engine

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)) + "/modelo"
now = datetime.datetime.now()
print (now, ":", "REC_SYS start in full in ............................",SCRIPT_PATH)

spanish_stopwords = stopwords.words('spanish')
STEMMER = SnowballStemmer('spanish')
TOKENIZER = RegexpTokenizer(r"\w+")
LESSON_PATH = "data.csv"
STEMMED = False
#embedder  = SentenceTransformer('bert-base-multilingual-uncased')
embedder  = SentenceTransformer('distilbert-multilingual-nli-stsb-quora-ranking')

class Recommender:

  def remove_html_tags(self, document):
    return re.sub('(<[^<]+?>|\d)', '', document)

  def tokenize_document(self, document):
    return TOKENIZER.tokenize(document)

  def remove_stopwords(self, tokenized_document):
    return [token for token in tokenized_document if token not in spanish_stopwords]

  def stem_document(self, tokenized_document):
    if STEMMED:
      return [STEMMER.stem(token) for token in tokenized_document]
    return [token for token in tokenized_document]

  def clean_document(self, document):
    removed_tags = self.remove_html_tags(document)
    lower_document = self.convert_to_lower(removed_tags)
    sin_tildes = self.elimina_tildes(lower_document)
    tokenized_document = self.tokenize_document(sin_tildes)
    big_words = filter(lambda x: len(x) > 1, tokenized_document)
    return self.clean_tokenized(big_words)

  def convert_to_lower(self, document):
    return document.lower()

  def clean_tokenized(self, tokenized_document):
    no_stopwords = self.remove_stopwords(tokenized_document)
    stemmed_document = self.stem_document(no_stopwords)
    return stemmed_document

  def remove_html_tags_names(self, doc):
    words = [
      "form", "img", "icon", "src", "assets",
      "svg", "class", "mb", "align", "top", "gt", "from", "the",
      "html", "tim", "tar", "nbsp"
    ]
    return re.sub('(?:[\s]|^)(' + "|".join(words) +')(?=[\s]|$)', '', " ".join(doc))

  def elimina_tildes(self, cadena):
    s = ''.join((c for c in unicodedata.normalize('NFD',cadena) if unicodedata.category(c) != 'Mn'))
    return s

  def extract_keywords(self, document):
    doc = self.clean_document(document)
    doc = self.remove_html_tags_names(doc)
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download("punkt", download_dir="./")
    spanish_rake = Rake(language="spanish", stopwords=spanish_stopwords)
    spanish_rake.extract_keywords_from_text(doc)
    keywords = list(spanish_rake.get_word_degrees().keys())
    return keywords

  def generate_data(self, new_data):
    new_data["name"] = new_data["name"].fillna("")
    new_data["problem"] = new_data["problem"].fillna("")
    new_data["solution"] = new_data["solution"].fillna("")
    new_data["name_keywords"] = new_data.apply(lambda x: self.extract_keywords(x["name"]), axis=1)
    new_data["problem_keywords"] = new_data.apply(lambda x: self.extract_keywords(x["problem"]), axis=1)
    new_data["solution_keywords"] = new_data.apply(lambda x: self.extract_keywords(x["solution"]), axis=1)
    new_data["tags_keywords"] = new_data.apply(lambda x: self.extract_keywords(x["tags"]), axis=1)
    new_data["full"] = new_data["name_keywords"] + new_data["problem_keywords"] + new_data["tags_keywords"]
    new_data["full_sin_tags"] = new_data["name_keywords"] + new_data["problem_keywords"]
    return new_data

  def clean_data(self, dataframe):
    inicio = time.time()
    full_clean = self.generate_data(dataframe)
    fin = time.time() - inicio
    print("Tiempo de limpieza", fin, "(s)")
    return full_clean

  def export_json(self, data, name):
    _da = data[["id", name]]
    da = {}
    for index, row in _da.iterrows():
     da[row["id"]] = " ".join(row[name])
    return json.dumps(da)

  def generate_clean_json_lessons(self, name="full"):
    query = "SELECT * FROM lesson;"
    lessons = pd.read_sql_query(query, engine)
    df = pd.DataFrame(lessons)
    df.to_csv(r'data.csv', index = False)
    lessons = pd.read_csv(LESSON_PATH, encoding="utf-8")

    lessons = lessons[["id", "name", "problem", "solution", "tags"]]
    clean_lessons = self.clean_data(lessons)
    return self.export_json(clean_lessons, name)

  def save_jsons(self):
    json_data_sin_tags = self.generate_clean_json_lessons("full_sin_tags")
    with open("json_data_sin_tags.json", "w") as outfile:
        outfile.write(json_data_sin_tags)
    json_data_tags = self.generate_clean_json_lessons(name="tags_keywords")
    with open("json_data_tags.json", "w") as outfile:
        outfile.write(json_data_tags)

  def train(self):
    with open('json_data_sin_tags.json', 'r') as openfile:
        json_data_sin_tags = json.load(openfile)
    corpus_base = list(json_data_sin_tags.values())
    with open('json_data_tags.json', 'r') as openfile:
        json_data_tags = json.load(openfile)
    corpus_tags= list(json_data_tags.values())

    corpus_embeddings_base = embedder.encode(corpus_base, convert_to_tensor=True)
    filename = 'corpus_embeddings_base.txt'
    pickle.dump(corpus_embeddings_base, open(filename, 'wb'))
    corpus_embeddings_tags = embedder.encode(corpus_tags, convert_to_tensor=True)
    filename = 'corpus_embeddings_tags.txt'
    pickle.dump(corpus_embeddings_tags, open(filename, 'wb'))

  def recommend(self, query):
    print(" q: ",query)
    query = " ".join(self.extract_keywords(query))
    query_embedding = embedder.encode(query, convert_to_tensor=True)

    scores_dic  = {}
#     query_embedding = embedder.encode(query, convert_to_tensor=True)

    with open('json_data_sin_tags.json', 'r') as openfile:
    	json_data_sin_tags = json.load(openfile)
    corpus_base = list(json_data_sin_tags.values())
    corpus_base_ids = list(json_data_sin_tags.keys())

    dicti_id = {}
    i = 0
    for x in corpus_base_ids:
      dicti_id[int(x)] = i
      i += 1

    CANTIDAD = len(corpus_base)

    filename = 'corpus_embeddings_base.txt'
    corpus_embeddings_base = pickle.load(open(filename, 'rb'))

    filename = 'corpus_embeddings_tags.txt'
    corpus_embeddings_tags = pickle.load(open(filename, 'rb'))

    cos_scores_base = util.pytorch_cos_sim(query_embedding, corpus_embeddings_base)[0]
    cos_scores_base = cos_scores_base.cpu()

    cos_scores_tags = util.pytorch_cos_sim(query_embedding, corpus_embeddings_tags)[0]
    cos_scores_tags = cos_scores_tags.cpu()

#    We use torch.topk to find the highest 5 scores
    top_results = torch.topk(cos_scores_base, k=CANTIDAD)
    top_results_tags = torch.topk(cos_scores_tags, k=CANTIDAD)

    for _id in range(CANTIDAD):
      score = top_results[0][_id]
      id = top_results[1][_id]
      if id.item() not in scores_dic:
       	scores_dic[id.item()] = [id.item(), score.item(), 1, 1, 1]
      else:
        scores_dic[id.item()][1] = score

    for _id in range(CANTIDAD):
      score = top_results_tags[0][_id]
      id = top_results_tags[1][_id]
      if id.item() not in scores_dic:
        pass
      else:
        scores_dic[id.item()][2] = score.item()

###
    INTERACTIONS_PATH = "user_lessons.csv"
    try:
      filename = 'interactions_embeddings.txt'
      interactions = pd.read_csv(INTERACTIONS_PATH, encoding="utf-8")
      interactions_distance_json = pickle.load(open(filename, 'rb'))
    except Exception as e:
      print(str(e))
      interactions = None

#    interactions = None
    if (interactions is not None):
      for row in interactions.itertuples(index=False):
        try:
          _lesson_id = row.lesson_id
          _rating = row.points
          _query = row.querytext
          _query = " ".join(self.extract_keywords(_query))
          distance = util.pytorch_cos_sim(query_embedding, interactions_distance_json[_query])[0]
          distance = distance.cpu()
          id_l = dicti_id[_lesson_id]
          if (5 >= _rating >= 1 and distance > 0.5):
             score = distance[0]
             calc = score * (_rating - 2.5) / 5
             n_div = scores_dic[id_l][4]
             scores_dic[id_l][3] = (scores_dic[id_l][2] * n_div  + calc) / n_div
             scores_dic[id_l][4] += 1
        except Exception as e:
#         print(str(e))
             continue
###

    for value in scores_dic.values():
      value.append(value[1] + value[2] + 1 + value[3])

    lista_ordenada = sorted(scores_dic.values(),key=lambda x: x[-1], reverse=True)

    return [{ "id": corpus_base_ids[x[0]], "keywords": corpus_base[x[0]] } for x in lista_ordenada[:10]]

##  @staticmethod
##  def train_interactions():
  def train_interactions(self):
    try:
      query = "SELECT * FROM user_lesson;"
      user_lessons = pd.read_sql_query(query, engine)
      df = pd.DataFrame(user_lessons)
      df.to_csv(r'user_lessons.csv', index = False)
      INTERACTIONS_PATH = "user_lessons.csv"
      try:
        interactions = pd.read_csv(INTERACTIONS_PATH, encoding="utf-8")
      except Exception as e:
        interactions = None
        print("No hay interacciones ", INTERACTIONS_PATH)
        return

      with open('json_data_sin_tags.json', 'r') as openfile:
        json_data_sin_tags = json.load(openfile)
      corpus_base = list(json_data_sin_tags.values())
      corpus_base_ids = list(json_data_sin_tags.keys())

      filename = 'corpus_embeddings_base.txt'
      corpus_embeddings_base = pickle.load(open(filename, 'rb'))

      interactions_distance_json = {}

      if (interactions is not None):
        for row in interactions.itertuples(index=False):
          try:
            _lesson_id = row.lesson_id
            _rating = row.points
            _query = row.querytext
            _query = " ".join(self.extract_keywords(_query))
            if _query not in interactions_distance_json:
              _query_embedding = embedder.encode(_query, convert_to_tensor=True)
              interactions_distance_json[_query] = _query_embedding
          except Exception as e:
            print(str(e))
            continue
      filename = 'interactions_embeddings.txt'
      pickle.dump(interactions_distance_json, open(filename, 'wb'))
    except Exception as e:
      print(str(e))
      return

  def train_lessons(self):
      try:
        ini = time.time()
        print("Train lessons...........--------")
        self.save_jsons()
        self.train()
        self.train_interactions()
        f = time.time() - ini
        return f
      except Exception as e:
        print("Exception train_lessons >> "+str(e))
        return

if __name__ == '__main__':
    recsys = Recommender()


# PARA ENTRENAR:
# train_lessons()

# PARA RECOMENDAR, se genera "recomendaciones", una lista con diccionarios que contienen el id de la lección.

# queries = ['aprender react','partir react','desarrollo de software','github','ayuda frontend','opciones de deploy','hablame de django','quiero aprender sobre elastic beanstalk']
# for x in queries:
#   recomendaciones = recommend(x)
#   print("Recomendaciones para '", x, "':\n")
#   for rec in recomendaciones:
#     print(rec["id"], "-", rec["keywords"])
#   print("\n")
