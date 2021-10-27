from flask import request, jsonify, abort, redirect, url_for
import json
from init import application
from models import Lesson, User, Lesson_User_Vote, Tag, Config, Lesson_User_Rating
import recsys.recommender_engine as rs
import recsys.recommender_system as ry
import pandas as pd
import logging
from init import engine
from pandas import DataFrame
from recsys.utils.MLStripper import strip_tags
from datetime import datetime, date

##from flask import Flask
##application = Flask(__name__)

REC_ENG = rs.RecommendationEngine(model_path="lsa_lessons_keywords.model",
                                  dictionary_path="lessons_dict_keywords.dict",
                                  corpus_path="lessons_corpus_keywords.mm")

REC_SYS = ry.Recommender()

def print_recommendations(indices, as_json=True):
    try:
      if len(indices) == 0:
          return jsonify([])
      # If Lesson ids don't start with 1, we need to calculate an offset for retrieving correct results.
      #first_lesson_db = json.loads(Lesson.query.first().json)
      query = "SELECT min(id) FROM lesson;"
      min = pd.read_sql_query(query, engine)
      first_lesson_db = int(min["min"])
      if first_lesson_db is None:
          logging.error("The database is empty. There's nothing to recommend.")
          return jsonify([])
      logging.info(f"The first lesson in database is {first_lesson_db}")
      print(f"The first lesson in database is {first_lesson_db}")
      offset = first_lesson_db
      print(f"indices len: {len(indices)}")
      print("indices1:", indices)
      indices = indices[0:20]
      print("indices2:", indices)
      db_ids = [index + offset for index in indices]
      recommended_items = [Lesson.query.filter_by(id=lesson_id).first() for lesson_id in db_ids]
      #iitems_json = [json.loads(lesson.json) for lesson in recommended_items]
      items_json = [json.loads(lesson.json) for lesson in recommended_items if lesson]
      if as_json:
          return jsonify(items_json)
      return items_json
    except Exception as e:
           return(str(e))

def print_recommendations_nohtml(indices):
    try:
      if len(indices) == 0:
          return jsonify([])
      query = "SELECT min(id) FROM lesson;"
      min = pd.read_sql_query(query, engine)
      first_lesson_db = int(min["min"])
      if first_lesson_db is None:
          logging.error("The database is empty. There's nothing to recommend.")
          return jsonify([])
      logging.info(f"The first lesson in database is {first_lesson_db}")
      print(f"---->The first lesson in database is {first_lesson_db}")
      offset = first_lesson_db
      print(f"indices len: {len(indices)} offset: {offset}")
      indices = indices[0:40]
      db_ids = [index + offset for index in indices]
      recommended_items = [Lesson.query.filter_by(id=lesson_id).first() for lesson_id in db_ids]
      items_json = [json.loads(lesson.json) for lesson in recommended_items if lesson]
#      items_sort = [items_json]
#      print(sorted(items_sort, key=lambda lesson : lesson.votes))
#      print (items_json)

      for i in range(len(items_json)):
          items_json[i]['name']     = strip_tags(items_json[i]['name'])
          items_json[i]['problem']  = strip_tags(items_json[i]['problem'])
#         print ("-->",i,items_json[i]['name'], items_json[i]['problem'])
#         print ("-->",i, items_json[i]['solution'])
          if (items_json[i]['solution'] is not None):
             items_json[i]['solution'] = strip_tags(items_json[i]['solution'])
      return jsonify(items_json)
    except Exception as e:
           return(str(e))

@application.route('/')
def index():
    return '(Sysrec v20201129 2120) Hello world!! <br><a href="https://lessons.zmartboard.cl/train">Train</a> <br><a href="https://lessons.zmartboard.cl/recommend?query=react">react</a> <br><a href="https://lessons.zmartboard.cl/getlesson/12631">Lid 12631</a> <br><a href="https://lessons.zmartboard.cl/list_lessons">Lessons</a> <br><a href="https://lessons.zmartboard.cl/health">Health</a>'

@application.route('/health')
def health():
    return '200'

@application.route("/getlesson/<id_>")
def get_lesson_by_id(id_):
    try:
        lesson=Lesson.query.filter_by(id=id_).first()
        return jsonify(lesson.serialize())
    except Exception as e:
           return(str(e))

@application.route('/list_lessons', methods=['GET'])
def list_lessons():
    try:
        lessons=Lesson.query.all()
        return  jsonify([e.serialize() for e in lessons])
    except Exception as e:
           return(str(e))


@application.route('/user', methods=['GET', 'POST', 'PUT', 'DELETE'])
def user():
    try: 
      if request.method == 'GET':
          user = User.read(**request.json)

      if request.method == 'POST':
          user = User.create(**request.json)

      if request.method == 'PUT':
          user = User.update(**request.json)

      if request.method == 'DELETE':
          user = User.delete(**request.json)

      return user.json
    except Exception as e:
      return(str(e))


@application.route('/lesson', methods=['GET', 'POST', 'PUT', 'DELETE'])
def lesson():
    try:
      if request.json is None:
          json = {'name': request.headers['Name'],
                  'problem': request.headers['Problem'],
                  'solution': request.headers['Solution'],
                  'tags': request.headers['Tags'],
                  'user_publisher': request.headers['User-publisher'],
                  'user_publisher_email': request.headers['User-publisher-email']
                  }
      else:
          json = request.json
          # json['user_publisher'] = json['userPublisher']
          # del json['userPublisher']

      if request.method == 'GET':
          lesson = Lesson.read(**json)

      if request.method == 'POST':
          # user = User.read(id=json['user_publisher'])
          for i in json['tags']:
              Tag.create(name=i)
          lesson = Lesson.create(**json)

      if request.method == 'PUT':
          for i in json['tags']:
              Tag.create(name=i)
          lesson = Lesson.update(**json)

      if request.method == 'DELETE':
          # user = User.read(id=request.json['user_publisher'])
          lesson = Lesson.delete(**json)

      return lesson.json
    except Exception as e:
      return(str(e))

@application.route('/my_lessons', methods=['GET'])
def my_lessons():
    per_page = 5
    try:
        page = request.args.get("page")
        if not page:
            page = 1
        else:
            page = int(page)
        user_id = request.headers['User-publisher']
        if not user_id:
            raise Exception
        lessons = Lesson.own_lessons(user_id, page, per_page)
        result = []
        for lesson in lessons.items:
            result.append({
                "id": str(lesson.id),
                "name": lesson.name,
                "problem": lesson.problem,
                "solution": lesson.solution,
                "tags": lesson.tags,
                "approved": lesson.approved,
                "votes": str(lesson.votes_count),
                "created_at": str(lesson.created_at),
                "updated_at": str(lesson.updated_at)
            })
        return json.dumps({
            "pages": int(lessons.pages),
            "lessons": result
        })
    except Exception as e:
        raise e

@application.route('/search_lessons', methods=['GET'])
def search_lessons():
    per_page = 10
    search = request.args.get("search")
    page = request.args.get("page")
    filter_by = request.args.get("filter_by")
    order_by = request.args.get("order_by")
    direction = request.args.get("direction")
    published = request.args.get("only_published")
    if not page:
        page = 1
    else:
        page = int(page)
    lessons = Lesson.all(
        page,
        per_page,
        filter_by,
        search,
        order_by,
        direction,
        only_published=published=="true",
    )
    result = []
    for lesson in lessons.items:
        result.append({
            "id": str(lesson.id),
            "name": lesson.name,
            "problem": lesson.problem,
            "solution": lesson.solution,
            "tags": lesson.tags,
            "created_at": str(lesson.created_at),
            "updated_at": str(lesson.updated_at),
            "approved": lesson.approved,
            "approved_date": str(lesson.approved_date),
            "views": str(lesson.views_count),
            "votes": str(lesson.votes_count),
            "abuses": str(lesson.abuses),
            "user_publisher": lesson.user_publisher,
            "user_publisher_email": lesson.user_publisher_email
        })
    return json.dumps({
        "pages": int(lessons.pages),
        "lessons": result
    })

@application.route('/all_lessons', methods=['GET'])
def all_lessons():
    per_page = 10
    search = request.args.get("search")
    if Config.is_sysrec():
        return redirect(url_for("recommend", query=search, _external=True, _scheme="https"))
    else:
        print("Simple search enabled")
    page = request.args.get("page")
    filter_by = request.args.get("filter_by")
    order_by = request.args.get("order_by")
    direction = request.args.get("direction")
    published = request.args.get("only_published")
    if not page:
        page = 1
    else:
        page = int(page)
    lessons = Lesson.all(
        page,
        per_page,
        filter_by,
        search,
        order_by,
        direction,
        only_published=published=="true",
    )
    result = []
    for lesson in lessons.items:
        result.append({
            "id": str(lesson.id),
            "name": lesson.name,
            "problem": lesson.problem,
            "solution": lesson.solution,
            "tags": lesson.tags,
            "created_at": str(lesson.created_at),
            "updated_at": str(lesson.updated_at),
            "approved": lesson.approved,
            "approved_date": str(lesson.approved_date),
            "views": str(lesson.views_count),
            "votes": str(lesson.votes_count),
            "abuses": str(lesson.abuses),
            "user_publisher": lesson.user_publisher,
            "user_publisher_email": lesson.user_publisher_email
        })
    return json.dumps({
        "pages": int(lessons.pages),
        "lessons": result
    })

@application.route('/lesson_user_vote', methods=['GET', 'POST', 'PUT', 'DELETE'])
def lesson_user_vote():
    if request.json is None:
        json = {'vote': request.headers['Vote'],
                'user_id': request.headers['Userid'],
                'lesson_id': request.headers['Lessonid']}
    else:
        json = request.json
        json['user_id'] = json['userId']
        del json['userId']
        json['lesson_id'] = json['lessonId']
        del json['lessonId']

    if request.method == 'GET':
        lesson_user_vote = Lesson_User_Vote.read(**json)
        return lesson_user_vote

    if request.method == 'POST':
        user = User.read(id=json['user_id'])
        lesson_user_vote = Lesson_User_Vote.create(**json)

    if request.method == 'PUT':
        lesson_user_vote = Lesson_User_Vote.update(**json)

    if request.method == 'DELETE':
        # user = User.read(id=json['user_publisher'])
        # lesson = Lesson.create(**json)
        lesson_user_vote = Lesson_User_Vote.delete(**json)
    return lesson_user_vote.json

@application.route('/view_lesson', methods=["PUT"])
def view_lesson():
    return Lesson.view(**request.json).json

@application.route('/abuse_lesson', methods=["PUT"])
def abuse_lesson():
    return Lesson.abuse(**request.json).json

@application.route('/approve_lesson', methods=["POST", "DELETE"])
def approve_lesson():
    json = request.json
    if request.method == 'POST':
        lesson = Lesson.approve(**json)
    if request.method == 'DELETE':
        lesson = Lesson.disapprove(**json)
    return lesson.json

@application.route('/clean_lessons', methods=["GET"])
def clean_lesonss():
    print("Generating clean_lessons.csv")
    print("----------------------------")
    query = Lesson.query.all()
    query_json = [json.loads(lesson.json) for lesson in query]
    query_df = pd.DataFrame(data=query_json)
    query_df = query_df[["name", "problem", "solution", "tags"]]
    print("query_df................................................")
    print (query_df)
    REC_ENG.clean_lessons(query_df)
    return jsonify("200 - csv created Successful")

@application.route('/retrain_model_keywords', methods=["GET"])
def retrain_model_keywords():
    print("Trains LSA model with keywords.")
    print("-------------------------------")
    query = Lesson.query.all()
    query_json = [json.loads(lesson.json) for lesson in query]
    query_df = pd.DataFrame(data=query_json)
    query_df = query_df[["name", "problem", "solution", "tags"]]
    print("query_df................................................")
    print (query_df)
    if len(query) == 0:
        return jsonify("There are no lessons to retrain model.")
    else:
        REC_ENG.retrain_with_keywords(query_df)
        return jsonify("200 - Retrained Keywords Successful")

@application.route('/retrain_model_full', methods=["GET"])
def retrain_model_full():
    print("Trains LSA model with full lessons in DB ")
    print("------------------------------------------")
    query = Lesson.query.all()
    query_json = [json.loads(lesson.json) for lesson in query]
    query_df = pd.DataFrame(data=query_json)
    query_df = query_df[["name", "problem", "solution", "tags"]]
    print("query_df................................................")
    print (query_df)
    if len(query) == 0:
        return jsonify("There are no lessons to retrain model.")
    else:
        REC_ENG.retrain(query_df)
        return jsonify("200 - Retrained full Successful")

@application.route('/lesson_recommend', methods=["GET"])
def lesson_recommend():
    query = request.args.get("query")
#    initial_range = int(request.args.get("initial_range"))
#    final_range = int(request.args.get("final_range"))
    initial_range = 1
    final_range = 1400
    recommended_indices = REC_ENG.recommend(query, initial_range, final_range)
    #logging.info(f"Recommended indices: {recommended_indices}")
    return print_recommendations(recommended_indices)

@application.route('/lesson_recnohtml', methods=["GET"])
def lesson_recnohtml():
    print(request.args)
    query = request.args.get("query")
#    initial_range = int(request.args.get("initial_range"))
#    final_range = int(request.args.get("final_range"))
    initial_range = 1
    final_range = 1400
    recommended_indices = REC_ENG.recommend(query, initial_range, final_range)
    logging.info(f"Recommended indices: {recommended_indices}")
    print(f"Recommended indices: {recommended_indices}")
    return print_recommendations_nohtml(recommended_indices)

@application.route("/config", methods=["GET", "PATCH"])
def lesson_update_config():
    if request.method == "PATCH":
        body = request.get_json() or dict()
        if body.get("sys_rec_status") == 1:
            Config.update_config("sys_rec_status", 1)
        elif body.get("sys_rec_status") == 0:
            Config.update_config("sys_rec_status", 0)
    return Config.get_full_config()

#########################################################################################
@application.route('/one_lesson', methods=['GET'])
def one_lesson():
    lessonId = request.args.get("search")
    params = { "id": lessonId }
    print (" params: ", params)
    lesson = Lesson.read(**params)
    result = []
    result.append({
        "id": str(lesson.id),
        "name": lesson.name,
        "problem": lesson.problem,
        "solution": lesson.solution,
        "tags": lesson.tags,
        "created_at": str(lesson.created_at),
        "updated_at": str(lesson.updated_at),
        "approved": lesson.approved,
        "approved_date": str(lesson.approved_date),
        "views": str(lesson.views_count),
        "votes": str(lesson.votes_count),
        "abuses": str(lesson.abuses),
        "user_publisher": lesson.user_publisher,
        "user_publisher_email": lesson.user_publisher_email
    })
    return json.dumps({
        "lessons": result
    })
@application.route('/lesson_user_rating', methods=['POST'])
def lesson_user_rating():
    if request.json is None:
        json = {'points': request.headers['Points'],
                'user_id': request.headers['Userid'],
                'lesson_id': request.headers['Lessonid'],
                'querytext': request.headers['Querytext'],
                'attemps': request.headers['Attemps']}
    else:
        json = request.json
        json['user_id'] = json['userId']
        del json['userId']
        json['lesson_id'] = json['lessonId']
        del json['lessonId']

    if request.method == 'POST':
        lesson_user_rating = Lesson_User_Rating.create(**json)

    return lesson_user_rating.json

def print_recos(lista):
    if len(lista) == 0:
        return jsonify([])
    db_ids = [int(i) for i in lista]
    logging.info(f"db_ids: {db_ids}")
    recommended_items = [Lesson.query.filter_by(id=lesson_id).first() for lesson_id in db_ids]
    items_json = [json.loads(lesson.json) for lesson in recommended_items if lesson]
    return jsonify({
        "pages": 1,
        "lessons": items_json
    })

@application.route('/train', methods=["GET"])
####@application.route('/train')
def train():
    print("Training model: "+str(datetime.now()))
    print("--------------")
    try:
      t=REC_SYS.train_lessons()
      s="200 - Trained model Successful   t:"+str(t)+" [s]   Time: "+str(datetime.now())
      print (s)
      return s 
    except Exception as e:
      return(str(datetime.now())+"Exception in /train >>"+str(e))

@application.route('/recommend', methods=["GET"])
def recommend():
    try:
      query = request.args.get("query")
      recommended_list = REC_SYS.recommend(query)
      logging.info(f"Recommended list: {recommended_list}")
      #print("Recomendaciones para ", recommended_list, "':\n")
      lista=[]
      for rec in recommended_list:
         # st = str(rec["id"])
          st = str(rec["id"])
          lista = lista+[st]
      return (print_recos(lista))
    except Exception as e:
      return(str(e))

if __name__ == '__main__':
#    import logging
#    logging.basicConfig(filename='error.log',level=logging.INFO)
    application.run(host='0.0.0.0')

