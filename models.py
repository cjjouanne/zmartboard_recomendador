import datetime
import json

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, select, and_, case, Integer
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.sql.expression import cast
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy import PrimaryKeyConstraint

from init import db

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Text)
    problem = db.Column(db.Text)
    solution = db.Column(db.Text)
    tags = db.Column(JSON)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    approved = db.Column(db.Boolean)
    approved_date = db.Column(db.DateTime)
    abuses = db.Column(db.Integer)
    user_publisher = db.Column(db.String(120), nullable=False)
    user_publisher_email = db.Column(db.String(120), nullable=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_at = datetime.datetime.now()
        self.updated_at = self.created_at
        self.abuses = 0
        self.approved = False

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            "problem": self.problem,
            "solution": self.solution,
            "tags": self.tags,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "approved": self.approved,
            "approved_date": str(self.approved_date),
            "views": str(self.views_count),
            "votes": str(self.votes_count),
            "user_publisher": str(self.user_publisher),
            "user_publisher_email": str(self.user_publisher_email),
            "abuses": str(self.abuses)
        }

    @property
    def json(self):
        return json.dumps({
            "id": str(self.id),
            "name": self.name,
            "problem": self.problem,
            "solution": self.solution,
            "tags": self.tags,
            "created_at": str(self.created_at),
            "updated_at": str(self.updated_at),
            "approved": self.approved,
            "approved_date": str(self.approved_date),
            "views": str(self.views_count),
            "votes": str(self.votes_count),
            "abuses": str(self.abuses),
            "user_publisher": str(self.user_publisher),
            "user_publisher_email": str(self.user_publisher_email)
        })

    @hybrid_property
    def views_count(self):
        return self.views.count()

    @views_count.expression
    def views_count(cls):
        return (select([func.count(Lesson_User_View.lesson_id)]).
                where(Lesson_User_View.lesson_id == cls.id).
                label("lesson_user_view_count")
                )

    @hybrid_property
    def pos_votes_count(self):
        return self.votes.filter_by(vote="+1").count()

    @pos_votes_count.expression
    def pos_votes_count(cls):
        return (select([func.count(case([((Lesson_User_Vote.vote == "+1"), 1)]))]).
                where(Lesson_User_Vote.lesson_id == cls.id).
                label("lesson_user_vote_pos_vote_count")
                )

    @hybrid_property
    def neg_votes_count(self):
        return self.votes.filter_by(vote="-1").count()

    @neg_votes_count.expression
    def neg_votes_count(cls):
        return (select([func.count(case([((Lesson_User_Vote.vote == "-1"), 1)]))]).
                where(Lesson_User_Vote.lesson_id == cls.id).
                label("lesson_user_vote_neg_vote_count")
                )

    @hybrid_property
    def votes_count(self):
        return self.pos_votes_count - self.neg_votes_count

    @votes_count.expression
    def votes_count(cls):
        return cls.pos_votes_count - cls.neg_votes_count

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        db.session.add(obj)
        db.session.commit()
        return obj

    @classmethod
    def read(cls, **kwargs):
        obj = cls.query.filter_by(id = kwargs['id']).first()
        return obj

    @classmethod
    def view(cls, **kwargs):
        obj = cls.query.filter_by(id = kwargs['id']).first()
        view = obj.views.filter_by(user_id = kwargs["user_id"]).first()
        if not view:
            Lesson_User_View.create(user_id=kwargs["user_id"], lesson_id=kwargs['id'])
            db.session.commit()
        return obj

    @classmethod
    def abuse(cls, **kwargs):
        obj = cls.query.filter_by(id = kwargs['id']).first()
        new_abuses = obj.abuses + 1
        setattr(obj, 'abuses', new_abuses)
        db.session.commit()
        return obj

    @classmethod
    def approve(cls, **kwargs):
        obj = cls.query.filter_by(id = kwargs['id']).first()
        setattr(obj, 'approved', True)
        obj.approved_date = datetime.datetime.now()
        db.session.commit()
        return obj

    @classmethod
    def disapprove(cls, **kwargs):
        obj = cls.query.filter_by(id = kwargs['id']).first()
        setattr(obj, 'approved', False)
        db.session.commit()
        return obj

    @classmethod
    def own_lessons(cls, user_id, page, per_page):
        objs = cls.query.filter_by(user_publisher=user_id).order_by(cls.created_at.desc()).paginate(page, per_page, error_out=True)
        return objs

    @classmethod
    def update(cls, **kwargs):
        obj = cls.query.filter_by(id=kwargs['id']).first()
        for i in kwargs.keys():
            setattr(obj, i, kwargs[i])
            obj.updated_at = datetime.datetime.now()
            db.session.commit()
        return obj

    @classmethod
    def delete(cls, **kwargs):
        obj = cls.query.filter_by(id=kwargs['id']).first()
        db.session.delete(obj)
        db.session.commit()
        return obj

    @classmethod
    def all(cls, page, per_page, filter_by, search, order_by, direction, only_published=False):
        order_dict = {
            "name": cls.name,
            "created_at": cls.created_at,
            "approved": cls.approved,
            "views": cls.views_count,
            "votes": cls.votes_count,
            "abuses": cls.abuses
        }
        if order_by:
            if direction == "asc":
                order_dict[order_by] = order_dict[order_by].asc()
            else:
                print("NOT HERE")
                order_dict[order_by] = order_dict[order_by].desc()
                print(order_by)
            order = order_dict[order_by]
        else:
            order = order_dict["created_at"].desc()
        if only_published:
            if not filter_by:
                filter_by = 'name'
            if filter_by == 'name':
                objs = cls.query.filter(Lesson.name.ilike(f'%{search}%'), Lesson.approved == True).order_by(order).paginate(page, per_page, error_out=True)
            else:
                objs = cls.query.filter(Lesson.approved == True).order_by(order).paginate(page, per_page, error_out=True)
        elif search:
            if not filter_by:
                filter_by = 'name'
            if filter_by == 'name':
                objs = cls.query.filter(Lesson.name.ilike(f'%{search}%')).order_by(order).paginate(page, per_page, error_out=True)
            elif filter_by == 'user_publisher_email':
                objs = cls.query.filter(Lesson.user_publisher_email.ilike(f'%{search}%')).order_by(order).paginate(page, per_page, error_out=True)
            elif filter_by == 'tags':
                objs = cls.query.filter(func.strpos(cast(Lesson.tags, db.String), search) >= 1).order_by(order).paginate(page, per_page, error_out=True)
            elif filter_by == 'date':
                search_list = search.split("--")
                fromDate = datetime.datetime.strptime(search_list[0], '%Y-%m-%d')
                toDate = datetime.datetime.strptime(search_list[1], '%Y-%m-%d')
                objs = cls.query.filter(Lesson.created_at.between(fromDate, toDate)).order_by(order).paginate(page, per_page, error_out=True)
            else:
                objs = cls.query.order_by(order).paginate(page, per_page, error_out=True)
        else:
            objs = cls.query.order_by(order).paginate(page, per_page, error_out=True)
        return objs

class User(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_at = datetime.datetime.now()

    @property
    def json(self):
        return json.dumps({
                "id": self.id,
                "name": self.name,
                "email": self.email
                })

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        db.session.add(obj)
        db.session.commit()
        return obj

    @classmethod
    def read(cls, **kwargs):
        obj = cls.query.filter_by(id=kwargs['id']).first()
        if obj == None:
            return cls.create(**kwargs)
        return obj

    @classmethod
    def update(cls, **kwargs):
        obj = cls.query.filter_by(id=kwargs['id']).first()
        for i in kwargs.keys():
            setattr(obj, i, kwargs[i])
            obj.updated_at = datetime.datetime.now()
            db.session.commit()
        return obj

    @classmethod
    def delete(cls, **kwargs):
        obj = cls.query.filter_by(id=kwargs['id']).first()
        db.session.delete(obj)
        db.session.commit()
        return obj

class Lesson_User_Vote(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.String(120), db.ForeignKey("user.id"))
    lesson_id = db.Column(db.Integer, db.ForeignKey("lesson.id"), nullable=False)
    vote = db.Column(db.String(120))

    @property
    def json(self):
        return json.dumps({
                "id": str(self.id),
                "userId": self.user_id,
                "lessonId": str(self.lesson_id),
                "vote": self.vote
                })

    @classmethod
    def create(cls, **kwargs):
        obj_read = cls.query.filter_by(lesson_id=kwargs['lesson_id'], user_id=kwargs['user_id']).first()
        if obj_read == None:
            obj = cls(**kwargs)
            db.session.add(obj)
            db.session.commit()
            return obj
        else:
            return obj_read

    @classmethod
    def read(cls, **kwargs):
        obj = cls.query.filter_by(lesson_id=kwargs['lesson_id'], user_id=kwargs['user_id']).first()
        positive_votes = cls.query.filter_by(lesson_id=kwargs['lesson_id'], vote='+1').count()
        negative_votes = cls.query.filter_by(lesson_id=kwargs['lesson_id'], vote='-1').count()
        net_votes = str(positive_votes - negative_votes)
        if obj == None:
            return json.dumps({"lessonVotes" : net_votes,
                               "userVoted": "0"})
        return json.dumps({"lessonVotes" : net_votes,
                "userVoted": obj.vote})

    @classmethod
    def update(cls, **kwargs):
        obj = cls.query.filter_by(user_id=kwargs['user_id'], lesson_id=kwargs['lesson_id']).first()
        for i in kwargs.keys():
            setattr(obj, i, kwargs[i])
            obj.updated_at = datetime.datetime.now()
            db.session.commit()
        return obj

    @classmethod
    def delete(cls, **kwargs):
        obj = cls.query.filter_by(lesson_id=kwargs['lesson_id'], user_id=kwargs['user_id']).first()
        db.session.delete(obj)
        db.session.commit()
        return obj

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Text, unique=True)

    @classmethod
    def create(cls, **kwargs):
        obj_read = cls.query.filter_by(name=kwargs['name']).first()
        if obj_read == None:
            obj = cls(**kwargs)
            db.session.add(obj)
            db.session.commit()
            return obj
        else:
            return obj_read

    @classmethod
    def read(cls, **kwargs):
        obj = cls.query.filter_by(name=kwargs['name']).first()
        if obj:
            return obj

    @classmethod
    def update(cls, **kwargs):
        obj = cls.query.filter_by(user_id=kwargs['name']).first()
        for i in kwargs.keys():
            setattr(obj, i, kwargs[i])
            obj.updated_at = datetime.datetime.now()
            db.session.commit()
        return obj

    @classmethod
    def delete(cls, **kwargs):
        obj = cls.query.filter_by(user_id=kwargs['name']).first()
        db.session.delete(obj)
        db.session.commit()
        return obj

class Lesson_User_View(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.String(120), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey("lesson.id"), nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created_at = datetime.datetime.now()
        self.updated_at = self.created_at

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        db.session.add(obj)
        db.session.commit()
        return obj

class Config(db.Model):
    key = db.Column(db.Text, primary_key=True, nullable=False)
    value = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

    @classmethod
    def create(cls, **kwargs):
        raise Exception()

    @classmethod
    def is_sysrec(cls):
        config_status = cls.query.filter_by(key="sys_rec_status").first()
        if config_status == None:
            raise Exception()
        return int(config_status.value) == 1

    @classmethod
    def update_config(cls, item, new_value):
        config_status = cls.query.filter_by(key=item).first()
        setattr(config_status, "value", new_value)
        db.session.commit()
        return config_status

    @classmethod
    def get_full_config(cls):
        full_config = cls.query.all()
        full_config_dict = dict()
        for config in full_config:
            full_config_dict[config.key] = config.value
        return json.dumps(full_config_dict)



Lesson.views = db.relationship(
    "Lesson_User_View",
    backref="lesson",
    foreign_keys=[Lesson_User_View.lesson_id],
    cascade="delete",
    lazy="dynamic",
)

Lesson.votes = db.relationship(
    "Lesson_User_Vote",
    backref="lesson",
    foreign_keys=[Lesson_User_Vote.lesson_id],
    cascade="delete",
    lazy="dynamic",
)

class clean(db.Model):
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    name = db.Column(db.Text)
    problem = db.Column(db.Text)
    solution = db.Column(db.Text)
    tags = db.Column(JSON)
#    session_id = db.Column(db.Text, primary_key=True, nullable=False)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
#        self.session_id = global_sesson_id
        self.approved = False

    def serialize(self):
        return {
            'id': self.id,
            'name': self.name,
            "problem": self.problem,
            "solution": self.solution,
            "tags": self.tags
        }

    @property
    def json(self):
        return json.dumps({
            "id": str(self.id),
            "name": self.name,
            "problem": self.problem,
            "solution": self.solution,
            "tags": self.tags
        })

class Lesson_User_Rating(db.Model):

    __tablename__ = 'user_lesson'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    user_id = db.Column(db.String(120), db.ForeignKey("user.id"))
    lesson_id = db.Column(db.Integer, db.ForeignKey("lesson.id"), nullable=False)
    points = db.Column(db.Integer)
    attemps = db.Column(db.Integer)
    querytext = db.Column(db.String(250))
    created = db.Column(db.DateTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = datetime.datetime.now()

    @property
    def json(self):
        return json.dumps({
            "id": str(self.id),
            "userId": self.user_id,
            "lessonId": str(self.lesson_id),
            "points": self.points,
            "querytext": self.querytext
        })

    @classmethod
    def create(cls, **kwargs):
#        obj_read = cls.query.filter_by(lesson_id=kwargs['lesson_id'], user_id=kwargs['user_id']).first()
        obj_read = None
        if obj_read == None:
            obj = cls(**kwargs)
            db.session.add(obj)
            db.session.commit()
            return obj
        else:
            return obj_read

class User_Query(db.Model):

    __tablename__ = 'user_query'
    id = db.Column(db.Integer, primary_key=True, nullable=False)
    querytext = db.Column(db.String(250))
    id_list = db.Column(db.String(250))
    created = db.Column(db.DateTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.created = datetime.datetime.now()

    @property
    def json(self):
        return json.dumps({
            "id": str(self.id),
            "querytext": self.querytext,
            "id_list" : self.id_list
        })

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        db.session.add(obj)
        db.session.commit()
        return obj