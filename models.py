import datetime
import os

from peewee import *

# DB_HOST = os.environ.get("PG_DB_HOST", "127.0.0.1")
# DB_PASSWORD = os.environ.get("PG_DB_PASSWORD")
# DB_USER = os.environ.get("PG_DB_USER")
# DB_DATABASE = os.environ.get("PG_DB_DATABASE")

DB_HOST = "localhost"
DB_PASSWORD = ""
DB_USER = "mathew"
DB_DATABASE = "supersub"

database = PostgresqlDatabase(
    DB_DATABASE, **{
        "user": DB_USER,
        "password": DB_PASSWORD,
        "host": DB_HOST,
        "port": 5432
    })


class BaseModel(Model):
    class Meta:
        database = database


class Squad(BaseModel):
    id = CharField()
    name = CharField()
    code = CharField()
    logo = CharField(null=True)
    kit_path = CharField(null=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        table_name = 'teams'


class Player(BaseModel):
    id = CharField()
    name = CharField()
    nationality = CharField()
    number = IntegerField()
    position = CharField()
    image_path = CharField(null=True)
    team_id = ForeignKeyField(Squad, backref='squads', field='id')
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        table_name = 'players'


class Lineup(BaseModel):
    id = AutoField()
    player_id = CharField()
    fixture_id = CharField()
    team_id = CharField()
    position = CharField()
    status = CharField()
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        table_name = 'lineups'


class Fixture(BaseModel):
    id = CharField()
    has_started = BooleanField()
    has_ended = BooleanField()
    current_minute = IntegerField()
    current_second = IntegerField()
    round = CharField()
    stadium = CharField()
    competition_id = IntegerField()
    localteam_id = CharField()
    visitorteam_id = CharField()
    localteam_score = IntegerField()
    visitorteam_score = IntegerField()
    starts_by = IntegerField()
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        table_name = 'fixtures'


class Event(BaseModel):
    id = TextField(unique=True)
    player_id = CharField()
    fixture_id = CharField()
    team_id = CharField()
    minute = IntegerField()
    type = CharField()
    points = IntegerField()
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        table_name = 'events'


class UserPick(BaseModel):
    id = IntegerField()
    user_id = IntegerField()
    fixture_id = TextField()
    player_id = TextField()
    price = DecimalField()
    minute_of_buy = IntegerField()
    minute_of_expiry = IntegerField()
    duration = IntegerField()
    is_local_team = BooleanField()
    is_active = BooleanField()
    points = IntegerField()
    player_position = TextField()
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    class Meta:
        table_name = 'user_picks'
