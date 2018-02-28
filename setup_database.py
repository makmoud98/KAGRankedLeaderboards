from sqlalchemy import Column, ForeignKey, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class Server(Base):
    __tablename__ = 'server'

    id = Column(Integer, primary_key=True, index=True)
    host = Column(String(250), nullable=False)
    port = Column(Integer, nullable=False)
    password = Column(String(250), nullable=False)
    # TODO: add encrytion somewhere here. hashing will not work because
    # it needs to be retrieved in server.py

    @property
    def serialize(self):
        return {
            'id': self.id,
            'host': self.host,
            'port': self.port
        }


class Player(Base):
    __tablename__ = 'player'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(20), nullable=False)
    rank = Column(Integer, nullable=False)
    wins = Column(Integer, nullable=False)
    losses = Column(Integer, nullable=False)
    kills = Column(Integer, nullable=False)
    deaths = Column(Integer, nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'username': self.username,
            'rating': self.rank,
            'wins': self.wins,
            'losses': self.losses,
            'kills': self.kills,
            'deaths': self.deaths
        }


class Player_Match(Base):
    __tablename__ = 'player_match'
    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey('player.id'), nullable=False)
    match_id = Column(Integer, ForeignKey('match.id'), nullable=False)
    # rank before match result
    rank = Column(Integer, nullable=False)
    team = Column(Integer, nullable=False)
    kills = Column(Integer, nullable=False)
    deaths = Column(Integer, nullable=False)

    @property
    def serialize(self):
        return {
            'player_id': self.player_id,
            'match_id': self.match_id,
            'team': self.team,
            'kills': self.kills,
            'deaths': self.deaths
        }


class Match(Base):
    __tablename__ = 'match'

    id = Column(Integer, primary_key=True, index=True)
    # 0 or 1 (blue team or red team) depending on the winner
    outcome = Column(Integer, nullable=False)
    change = Column(Integer, nullable=False)
    # rank before winning/losing
    winner_rank = Column(Integer, nullable=False)
    loser_rank = Column(Integer, nullable=False)
    server_id = Column(Integer, ForeignKey('server.id'), nullable=False)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'host': self.host,
            'port': self.port
        }


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, index=True)
    # 254 is the maximum number of characters for an email address
    # http://www.rfc-editor.org/errata_search.php?rfc=3696&eid=1690
    email = Column(String(254), nullable=False)
    admin = Column(Boolean(), nullable=False)
    # linking in-game account will be optional
    player_id = Column(Integer, ForeignKey('player.id'), nullable=True)

    @property
    def serialize(self):
        return {
            'id': self.id,
            'email': self.host,
            'admin': self.admin
        }

engine = create_engine('sqlite:///ranks.db')
Base.metadata.create_all(engine)
