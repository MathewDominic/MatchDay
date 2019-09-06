from peewee import *
from models import Lineup, Event, Fixture, UserPick


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
        Event.get_or_create(**event_dict)
        UserPick.update(
            points=UserPick.points + event_dict["points"]
        ).where(
            UserPick.fixture_id == event_dict["fixture_id"],
            UserPick.player_id == event_dict["player_id"],
            UserPick.minute_of_buy <= event_dict["minute"],
            UserPick.minute_of_expiry >= event_dict["minute"]
        ).execute()


    @staticmethod
    def set_substitution(in_player, out_player, fixture_id):
        Lineup.update(
            status='active'
        ).where(
            Lineup.fixture_id == fixture_id,
            Lineup.player_id == in_player
        ).execute()

        Lineup.update(
            status='inactive'
        ).where(
            Lineup.fixture_id == fixture_id,
            Lineup.player_id == out_player
        ).execute()

    @staticmethod
    def set_current_time(current_minute, fixture_id):
        Fixture.update(
            current_minute=current_minute
        ).where(
            Fixture.id == fixture_id
        ).execute()

    @staticmethod
    def set_game_started(fixture_id):
        Fixture.update(
            has_started=True
        ).where(
            Fixture.id == fixture_id
        ).execute()

    @staticmethod
    def set_game_over(fixture_id):
        Fixture.update(
            has_ended=True
        ).where(
            Fixture.id == fixture_id
        ).execute()