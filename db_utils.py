from peewee import *
from models import Lineup, Event


class DbUtils:
    def __init__(self):
        pass

    @staticmethod
    def set_starting_lineup(starting_lineup):
        try:
            Lineup.insert_many(starting_lineup).execute()
        except IntegrityError: # already inserted lineup
            return

    @staticmethod
    def set_event(event_dict):
        a = Event.get_or_create(**event_dict)