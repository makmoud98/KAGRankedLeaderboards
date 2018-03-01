import socket
import time
import threading
import math
import imageio
from enum import Enum
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from setup_database import Base, Player, Server, Match, Player_Match

engine = create_engine('sqlite:///ranks.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


class State(Enum):
    CONNECTED = 0
    CONNECTING = 1
    DISCONNECTED = 2
    STOPPING = 3
    STOPPED = 4


class Server(threading.Thread):
    def __init__(self, info):
        super(Server, self).__init__()
        self.info = info
        self.address = (socket.gethostbyname(str(self.info.host)),
                        self.info.port)
        self.setName('%s] [%s:%s' %
                     (self.info.id, self.address[0], self.address[1]))
        self.socket = socket.socket()
        self._stop_event = threading.Event()
        self._end_event = threading.Event()
        self.state = State.STOPPED
        self.condition = threading.Condition()
        self.map_data = []

    # called upon starting the thread
    def run(self):
        while 1:
            # if we are stopped...
            if self.stopped():
                if self._end_event.is_set():
                    break
                try:
                    self.condition.acquire()
                    self.state = State.STOPPED
                    # ...hang here until we are restarted
                    self.condition.wait()
                finally:
                    self.condition.release()
                # the condition must be released before
                # we can shut down the server
                if self.self.ended():
                    # this break will take us out of
                    # the main while loop; thus killing the thread
                    break
            try:
                self.log('connecting')
                self.state = State.CONNECTING
                self.socket = socket.socket()
                self.socket.connect(self.address)
                self.write(self.info.password)
                self.state = State.CONNECTED
                self.map_data = []
                self.log('connected')
                while 1:
                    # the last character is removed
                    # because it is a new line char (\n)
                    data = self.socket.recv(4096)[0:-1]

                    if self.stopped():
                        self.log('stopped')
                        break
                    elif data == '':
                        raise Exception('disconnected')

                    # sometimes the tcp server will combine
                    # multiple lines. this ensures that we
                    # never miss an important command
                    lines = data.split('\n')
                    for line in lines:
                        # the first 11 characters are just
                        # timestamps sent from the tcp server
                        tokens = data[11:].split(';')

                        if len(tokens) == 1:
                            if tokens[0] == 'minimap':
                                try:
                                    im = imageio.imread('https://api.kag2d.com\
                                                        /server/ip/%s/port/\
                                                        %s/minimap' %
                                                        self.address)
                                    self.map_data.append(im)
                                except:
                                    self.log('error getting minimap')

                        elif len(tokens) == 2:
                            # j stands for join, this is executed
                            # when a player joins the game server
                            if tokens[0] == 'j':
                                username = tokens[1]
                                player = Player(username=username,
                                                rank=1000, wins=0,
                                                losses=0, kills=0,
                                                deaths=0)
                                try:
                                    player = session.query(Player). \
                                        filter_by(username=username).one()
                                # if NoResultFound is the error,
                                # that means we have a new player!
                                except NoResultFound:
                                    session.add(player)
                                    session.commit()

                                # the tcp client send the
                                # tcp server the player's current
                                # rank according to the database
                                # cant split string into multiple lines
                                # or it wont compile on the game server
                                # this line cant follow pep8 guidlines
                                self.write("CBitStream p;p.write_string('%s');p.write_u32(%s);p.write_u32(%s);p.write_u32(%s);p.write_u32(%s);p.write_u32(%s);getRules().SendCommand(getRules().getCommandID('get_rank'),p)" %
                                           (player.username, player.rank,
                                            player.wins, player.losses,
                                            player.kills, player.deaths))

                        elif len(tokens) > 0:
                            # m stands for match,
                            # this is executed at the end of a match
                            if tokens[0] == 'm':
                                # winning team, team 0 or team 1
                                winner = int(tokens[1])
                                # change is how much rank a player
                                # will gain/lose after the match
                                # (depending on if they won or not)
                                change = int(tokens[2])
                                # avg rank of the winning team
                                avg_rank_winner = int(tokens[3])
                                avg_rank_loser = int(tokens[4])
                                # length of the match in seconds
                                match_length = int(tokens[5])
                                players = []
                                # create the match row in the database
                                match = Match(outcome=winner, change=change,
                                              winner_rank=avg_rank_winner,
                                              loser_rank=avg_rank_loser,
                                              server_id=self.info.id)
                                session.add(match)
                                session.commit()
                                # players' ranks are updated based on
                                # the 'change' and their team number
                                for i in range(6, len(tokens)-3, 4):
                                    # tokens[0] = username
                                    username = tokens[i]
                                    team = int(tokens[i+1])
                                    kills = int(tokens[i+2])
                                    deaths = int(tokens[i+3])

                                    player = session.query(Player). \
                                        filter_by(username=username).one()
                                    player_match = \
                                        Player_Match(player_id=player.id,
                                                     match_id=match.id,
                                                     rank=player.rank,
                                                     team=team,
                                                     kills=kills,
                                                     deaths=deaths)
                                    # winners gain rank and get a win
                                    if team == winner:
                                        player.rank += change
                                        player.wins += 1
                                    # losers lose rank and lose a win
                                    else:
                                        player.rank -= change
                                        player.losses += 1

                                    player.kills += kills
                                    player.deaths += deaths
                                    # ..update database
                                    session.add(player)
                                    session.add(player_match)
                                    session.commit()

                                imageio.mimsave('./static/assets/\
                                                match_gifs/%s.gif' %
                                                str(match.id), self.map_data)
                                self.map_data = []

            except Exception:
                self.log('disconnected')
            finally:
                self.state = State.DISCONNECTED
                self.socket.close()
                # wait 20 seconds before trying to reconnect,
                # unless we are trying to stop the server
                if not self.ended():
                    time.sleep(20)

    def get_state(self):
        return {
            State.CONNECTED: 'CONNECTED',
            State.CONNECTING: 'CONNECTING',
            State.DISCONNECTED: 'DISCONNECTED',
            State.STOPPING: 'STOPPING',
            State.STOPPED: 'STOPPED'
        }[self.state]

    # makes writing to the tcp server easier by
    # adding the mandatory new line character
    def write(self, msg):
        self.socket.send('%s\n' % msg)

    # easy log function that tells us
    # which thread is doing what
    def log(self, msg):
        # TODO: add a timestamp
        print('[%s] %s' % (threading.current_thread().getName(), msg))

    # this attempts to stop the tcp client by
    # shutting down and closing the socket
    def stop(self):
        try:
            self.socket.shutdown(socket.SHUT_WR)
        except:
            self.socket.close()
        finally:
            self.state = State.STOPPING
            self._stop_event.set()

    # this kills the thread
    # ONLY IF IT IS ALREADY STOPPED
    def end(self):
        self._end_event.set()
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()

    # this will restart the thread if it was stopped
    # no effect if it is aready running
    def restart(self):
        self._stop_event.clear()
        self.condition.acquire()
        self.condition.notify()
        self.condition.release()

    # shortcut
    def stopped(self):
        return self._stop_event.is_set()

    def ended(self):
        return self._end_event.is_set()
