import os
from peewee import *

DB_HOST = os.environ.get("PG_DB_HOST", "127.0.0.1")
DB_PASSWORD = os.environ.get("PG_DB_PASSWORD")
DB_USER = os.environ.get("PG_DB_USER")
DB_DATABASE = os.environ.get("PG_DB_DATABASE")

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
    logo = CharField()
    kit_path = CharField()

    class Meta:
        table_name = 'squads'


class Player(BaseModel):
    id = CharField()
    name = CharField()
    nationality = CharField()
    number = IntegerField()
    position = CharField()
    image_path = CharField()
    team_id = ForeignKeyField(Squad, backref='squads', field='id')

    class Meta:
        table_name = 'players'


class Lineup(BaseModel):
    player_id = CharField()
    fixture_id = CharField()
    team_id = CharField()
    status = CharField()

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
    starts_by = IntegerField()

    class Meta:
        table_name = 'fixtures'


class Event(BaseModel):
    id = TextField()
    player_id = CharField()
    fixture_id = CharField()
    team_id = CharField()
    minute = IntegerField()
    type = CharField()
    points = IntegerField()

    class Meta:
        table_name = 'events'






