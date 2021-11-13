import os
from gensim import corpora, similarities
from gensim.corpora import Dictionary
from gensim.models import LsiModel
from .utils.text_processing_tools import clean_document, extract_keywords
import logging
import datetime
import pandas as pd


#from sqlalchemy import create_engine
#engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__)) + "/modelo"
now = datetime.datetime.now()
print (now, ":", "REC_ENG start in full in ",SCRIPT_PATH)


class RecommendationEngine:
    def __init__(self, model_path="lsa_lessons_full.model",
                 dictionary_path="lessons_dict_full.dict",
                 corpus_path="lessons_corpus_full.mm"):
        self.model_path = model_path
        self.dictionary_path = dictionary_path
        self.corpus_path = corpus_path

    @staticmethod
    def build_clean_recommendation_doc(x):
        return x["name_clean"] + x["problem_clean"] + x["solution_clean"] +\
            x["tags"]

    @staticmethod
    def build_clean_recommendation_doc_keywords(x):
        return x["name_keywords"] + x["problem_keywords"] +\
            x["solution_keywords"] + x["tags"]

    def prepare_corpus(self, cleaned_documents):
        dictionary = corpora.Dictionary(cleaned_documents)
        doc_term_matrix = [dictionary.doc2bow(
            doc) for doc in cleaned_documents]
        corpora.MmCorpus.serialize(os.path.join(
            SCRIPT_PATH, self.corpus_path), doc_term_matrix)
        dictionary.save(os.path.join(
            SCRIPT_PATH, self.dictionary_path))
        return dictionary, doc_term_matrix

    def train_model(self, cleaned_documents, topic_number):
        dictionary, doc_term_matrix = self.prepare_corpus(
            cleaned_documents)
        lsamodel = LsiModel(doc_term_matrix, num_topics=topic_number,
                            id2word=dictionary)
        return lsamodel

    def retrain(self, new_data):
        logging.info("Retraining model using full documents.")
        new_data["name"] = new_data["name"].fillna("")
        new_data["problem"] = new_data["problem"].fillna("")
        new_data["solution"] = new_data["solution"].fillna("")

        new_data["name_clean"] = new_data.apply(
            lambda x: clean_document(x["name"]), axis=1)
        new_data["problem_clean"] = new_data.apply(
            lambda x: clean_document(x["problem"]), axis=1)
        new_data["solution_clean"] = new_data.apply(
            lambda x: clean_document(x["solution"]), axis=1)
        new_data["final_doc_clean"] = new_data.apply(
            lambda x: RecommendationEngine.build_clean_recommendation_doc(x),
            axis=1)

        final_documents_clean = new_data["final_doc_clean"].tolist()
        model = self.train_model(final_documents_clean, 300)
        logging.info("Model succesfully retrained.")
        model.save(os.path.join(SCRIPT_PATH, "lsa_lessons_full.model"))
        logging.info(f"Model saved in {os.path.join(SCRIPT_PATH, 'lsa_lessons_full.model')}")
        print(f"Model saved in {os.path.join(SCRIPT_PATH, 'lsa_lessons_full.model')}")

    def retrain_with_keywords(self, new_data):
        logging.info("Retraining model using keyword extraction.")
        print("Retraining model using keyword extraction.")
        new_data["name"] = new_data["name"].fillna("")
        new_data["problem"] = new_data["problem"].fillna("")
        new_data["solution"] = new_data["solution"].fillna("")
        new_data["name_keywords"] = new_data.apply(lambda x: extract_keywords(x["name"]), axis=1)
        new_data["problem_keywords"] = new_data.apply(lambda x: extract_keywords(x["problem"]), axis=1)
        new_data["solution_keywords"] = new_data.apply(lambda x: extract_keywords(x["solution"]), axis=1)
        new_data["final_doc"] = new_data.apply(
            lambda x: RecommendationEngine.build_clean_recommendation_doc_keywords(x), axis=1)

        final_documents = new_data["final_doc"].tolist()

        model = self.train_model(final_documents, 200)
        logging.info("Model succesfully retrained.")
        model.save(os.path.join(SCRIPT_PATH, "lsa_lessons_keywords.model"))
        logging.info(f"Model saved in {os.path.join(SCRIPT_PATH, 'lsa_lessons_keywords.model')}")
        print(f"Model saved in {os.path.join(SCRIPT_PATH, 'lsa_lessons_keywords.model')}")

    def recommend(self, query, initial_range, final_range):
        logging.info("Cleaning query.")
        clean_query = clean_document(query)
        logging.info("Loading model.")
        model = LsiModel.load(os.path.join(SCRIPT_PATH, self.model_path))
        print("Model ...............................")
        print(model)
        dictionary = Dictionary.load(os.path.join(SCRIPT_PATH, self.dictionary_path))
        print("dictionary ................................................")
        print(dictionary)
        query_vector = dictionary.doc2bow(clean_query)
        print("query_vector ................................................")
        print(query_vector)
        query_lsi = model[query_vector]

        print("query_lsi ................................................")
        print(query_lsi)
        corpus = corpora.MmCorpus(os.path.join(SCRIPT_PATH, self.corpus_path))
        index = similarities.MatrixSimilarity(model[corpus])
        print("index ................................................")
        print(index)
        sims = index[query_lsi]
        if initial_range not in range(len(sims)) or final_range not in range(len(sims)):
            print("No recommendations in range: ", initial_range, ":",final_range)
            return []
        sims = sorted(enumerate(sims), key=lambda item: - item[1])[initial_range:final_range + 1]
        sims_indices = [index for index, cos_dist in sims]
        logging.info(f"-->The most similar lessons have the following indices: {sims_indices}")
        return sims_indices

    def clean_lessons(self, lessons):
        print("Clean lessons....")
        lessons = lessons.reset_index()
        df = pd.DataFrame(lessons)
        csv_file=lessons = os.path.join(SCRIPT_PATH, "lessons_clean.csv")

        df.to_csv(csv_file, index=False)
        return

if __name__ == '__main__':
    recsys = RecommendationEngine(
        "lsa_lessons_full.model", "lessons_dict_full.dict", "lessons_corpus_full.mm",
        "lessons_clean.csv")

