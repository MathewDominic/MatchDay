from peewee import *
from models import Lineup, Event, Fixture, UserPick


def set_starting_lineup(starting_lineup):
    Lineup.insert_many(starting_lineup).execute()


def delete_lineup(fixture_id):
    Lineup.delete().where(Lineup.fixture_id == fixture_id).execute()


def delete_events(fixture_id):
    Event.delete().where(Event.fixture_id == fixture_id).execute()

    
def reset_user_picks(fixture_id):
    UserPick.update(
        points=0,
        is_active=True
    ).where(
        UserPick.fixture_id == fixture_id,
    ).execute()


def set_event(event_dict):
    query = Event.get_or_create(**event_dict)
    if query[1] is True:
        update_points(event_dict["fixture_id"], event_dict["player_id"], event_dict["points"], event_dict["minute"])


def update_points(fixture_id, player_id, points, minute):
    UserPick.update(
        points=UserPick.points + points
    ).where(
        UserPick.fixture_id == fixture_id,
        UserPick.player_id == player_id,
        UserPick.minute_of_buy <= minute,
        UserPick.minute_of_expiry >= minute
    ).execute()


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


def set_current_fixture_state(current_minute, localteam_score, visitorteam_score, fixture_id):
    Fixture.update(
        current_minute=current_minute,
        localteam_score=localteam_score,
        visitorteam_score=visitorteam_score
    ).where(
        Fixture.id == fixture_id
    ).execute()


def set_game_started(fixture_id):
    Fixture.update(
        has_started=True
    ).where(
        Fixture.id == fixture_id
    ).execute()


def set_game_over(fixture_id):
    Fixture.update(
        has_ended=True
    ).where(
        Fixture.id == fixture_id
    ).execute()


def insert_fixtures(fixtures):
    Fixture.insert_many(fixtures).execute()


def set_expiry(fixture_id, minute):
    UserPick.update(
        is_active=False
    ).where(
        UserPick.is_active == True,
        UserPick.fixture_id == fixture_id,
        UserPick.minute_of_expiry < int(minute)
    ).execute()


def get_to_be_expired(fixture_id, minute):
    return UserPick.select().where(
        UserPick.is_active == True,
        UserPick.fixture_id == fixture_id,
        UserPick.minute_of_expiry < minute
    )

