# some of the oauth stuff was taken from lesson 4
# see https://github.com/udacity/ud330/blob/master/Lesson4/step2/project.py
from flask import Flask, render_template, request, redirect, \
                  jsonify, url_for, flash, abort
from flask.json import loads
from sqlalchemy import create_engine, desc, or_
from sqlalchemy.sql import functions as func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from setup_database import Base, Player, Server, Match, Player_Match, User
from flask import session as login_session
import string
import os
import random
import json
from flask import make_response, send_from_directory
import requests
from server_manager import ServerManager
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2

manager = ServerManager()
app = Flask(__name__)
engine = create_engine('sqlite:///ranks.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = json.loads(open('client_secrets.json', 'r').
                       read())['web']['client_id']


@app.context_processor
def utility_processor():
    user = None
    if 'email' in login_session:
        user = session.query(User).\
            filter_by(email=login_session['email']).first()
    if 'state' not in login_session:
        login_session['state'] = ''.join(
            random.choice(string.ascii_uppercase + string.digits)
            for x in xrange(32))
    return dict(state=login_session['state'],
                user=user,
                oauth_client_id=CLIENT_ID)


@app.route('/login', methods=['POST'])
def login():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        flash('Sorry, we couldn\'t log you in. Error Code 1')
        return '1'
    # Obtain authorization code
    code = request.data
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        flash('Sorry, we couldn\'t log you in. Error Code 2')
        return '2'

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v2/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        flash('Sorry, we couldn\'t log you in. %s' %
              json.dumps(result.get('error')))
        return '10'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        flash('Sorry, we couldn\'t log you in. Error Code 3')
        return '3'

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        flash('Sorry, we couldn\'t log you in. Error Code 4')
        return '4'

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        flash('You\'re already logged in')
        return '11'

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()
    login_session['email'] = data['email']

    user = session.query(User).filter_by(email=data['email']).first()
    if user is None:
        session.add(User(email=data['email'], admin=False))
        session.commit()

    flash('You are now logged in as %s' % data['name'])

    return data['email']


@app.route('/logout')
def logout():
    access_token = login_session['access_token']
    if access_token is None:
        response = make_response(json.dumps('Access Token is None'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = ('https://accounts.google.com/o/oauth2/revoke?token=%s' %
           login_session['access_token'])
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['email']
        flash('You have successfully logged out')
        return redirect(request.url_root)
    else:
        flash('Sorry, we couldn\'t log you out. Try again later')
        return redirect(request.url_root)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/assets'),
                               'favicon.ico',
                               mimetype='image/vnd.microsoft.icon')


@app.route('/player/<string:username>/json/')
def json_player(username):
    player = session.query(Player).\
        filter(Player.username.like(username)).first()
    if player is None:
        return jsonify({'status_code': 404, 'status': 'player not found'})
    else:
        return jsonify(player.serialize)


@app.route('/match/<int:id>/json/')
def json_match(id):
    match = session.query(Match).filter_by(id=id).first()
    if match is None:
        abort(404)
    else:
        players = session.query(Player_Match, Player).\
            order_by(desc(Player_Match.rank)).\
            filter(Player_Match.match_id == match.id).\
            filter(Player_Match.player_id == Player.id).all()
        blue_team = [i for i in players if i[0].team == 0]
        red_team = [i for i in players if i[0].team == 1]
        return jsonify(match=match.serialize,
                       blue_team=[player.serialize for player in blue_team],
                       red_team=[player.serialize for player in red_team])


@app.route('/server/<int:id>/json/')
def json_server_info(id):
    try:
        server = session.query(Server).filter_by(id=id).one()
    except NoResultFound:
        return jsonify({'status_code': 404, 'status': 'server not found'})
    return jsonify(server.serialize)


@app.route('/servers/json/')
def json_all_server_info():
    servers = session.query(Server).all()
    return jsonify(servers=[server.serialize for server in servers])


@app.route('/ladder/json/')
def json_ladder():
    players = session.query(Player).order_by(desc(Player.rank)).\
        filter(or_(Player.wins > 0, Player.losses > 0)).all()
    return jsonify(players=[player.serialize for player in players])


@app.route('/recent/json/')
def json_matches():
    matches = session.query(Match).order_by(desc(Match.id)).all()
    return jsonify(matches=[match.serialize for match in matches])


@app.route('/player/<string:username>/')
def show_player(username):
    player = session.query(Player).\
        filter(Player.username.like(username)).first()
    if player is None:
        abort(404)
    else:
        return render_template('player.html', player=player,
                               avatar=get_avatar_url(username))


@app.route('/player/<int:id>/edit/', methods=['GET', 'POST'])
def edit_player(id):
    if is_admin():
        if request.method == 'POST':
                player = session.query(Player).filter(Player.id == id).first()
                if player is None:
                    abort(404)
                else:
                    player.rank = request.form['rating']
                    player.wins = request.form['wins']
                    player.losses = request.form['losses']
                    player.kills = request.form['kills']
                    player.deaths = request.form['deaths']
                    session.add(player)
                    session.commit()
                    flash('You have successfully edited %s' % player.username)
                    return redirect(url_for('show_player',
                                    username=player.username))

        elif request.method == 'GET':
            player = session.query(Player).filter(Player.id == id).first()
            if player is None:
                abort(404)
            else:
                return render_template('player.html', player=player,
                                       avatar=get_avatar_url(player.username),
                                       edit=True)
        else:
            abort(404)
    else:
        abort(401)


@app.route('/player/<int:id>/delete/')
def delete_player(id):
    if is_admin():
        player = session.query(Player).filter(Player.id == id).first()
        if player is None:
            abort(404)
        else:
            session.delete(player)
            session.commit()
            flash('You have successfully deleted %s' % player.username)
            return redirect(request.url_root)
        abort(401)


@app.route('/match/<int:id>/')
def show_match(id):
    match = session.query(Match).filter_by(id=id).first()
    if match is None:
        abort(404)
    else:
        players = session.query(Player_Match, Player).\
            order_by(desc(Player_Match.rank)).\
            filter(Player_Match.match_id == match.id).\
            filter(Player_Match.player_id == Player.id).all()
        blue_team = [i for i in players if i[0].team == 0]
        red_team = [i for i in players if i[0].team == 1]
        server = session.query(Server).filter_by(id=match.server_id).one()
        return render_template('match.html', match=match, blue=blue_team,
                               red=red_team, server=server)


@app.route('/match/<int:id>/delete/', methods=['POST'])
def delete_match(id):
    if request.method == 'POST':
        if is_admin():
            match = session.query(Match).filter_by(id=id).first()
            if match is None:
                abort(404)
            else:
                player_matches = session.query(Player_Match).\
                    filter_by(match_id=match.id).all()
                for player_match in player_matches:
                    session.delete(player_match)
                session.delete(match)
                session.commit()
                os.remove(os.path.dirname(os.path.realpath(__file__)) +
                          url_for('static',
                          filename='assets/match_gifs/%s.gif' % match.id))
                flash('You have successfully deleted match #%s' % match.id)
                return redirect(url_for('recent_matches'))
        else:
            abort(401)
    else:
        abort(404)


@app.route('/server/<int:id>/')
def show_server(id):
    if is_admin():
        server = session.query(Server).filter_by(id=id).first()
        if server is None:
            abort(404)
        else:
            return render_template('server.html', server=server)
    else:
        abort(401)


@app.route('/server/new/', methods=['GET', 'POST'])
def new_server():
    if is_admin():
        if request.method == 'GET':
            return render_template('new_server.html')
        elif request.method == 'POST':
            server = Server(host=request.form['host'],
                            port=int(request.form['port']),
                            password=request.form['password'])
            session.add(server)
            session.commit()
            manager.create_server(server)
            flash('You have successfully created a new server')
            return redirect(url_for('admin_panel'))
    else:
        abort(401)


@app.route('/server/<int:id>/edit/', methods=['GET', 'POST'])
def edit_server(id):
    if is_admin():
        server = session.query(Server).filter_by(id=id).first()
        if server is None:
            abort(404)
        if request.method == 'POST':
            server.host = request.form['host']
            server.port = int(request.form['port'])
            server.password = request.form['password']
            session.add(server)
            session.commit()
            manager.remove_server(server)
            manager.create_server(server)
            flash('You have successfully edited server #%s' %
                  server.id)
            return redirect(url_for('show_server', id=server.id))
        elif request.method == 'GET':
            return render_template('server.html', server=server, edit=True)
        else:
            abort(404)
    else:
        abort(401)


@app.route('/server/<int:id>/delete/', methods=['POST'])
def delete_server(id):
    if is_admin():
        server = session.query(Server).filter_by(id=id).first()
        if server is None:
            abort(404)
        session.delete(server)
        session.commit()
        manager.remove_server(server)
        flash('You have successfully deleted server #%s' % server.id)
        return redirect(url_for('admin_panel'))
    else:
        abort(401)


@app.route('/')
@app.route('/ladder/')
def show_ladder():
    players = session.query(Player).order_by(desc(Player.rank)).\
        filter(or_(Player.wins > 0, Player.losses > 0)).limit(25)
    return render_template('ladder.html', players=players)


@app.route('/search/', methods=['POST'])
def search():
    return redirect(url_for('show_player', username=request.form['username']))


@app.route('/recent/')
def recent_matches():
    matches = session.query(Match).order_by(desc(Match.id)).limit(20)
    servers = []
    counts = []
    for match in matches:
        server = session.query(Server).filter_by(id=match.server_id).one()
        servers.append(server)
        players_blue = session.query(Player_Match).\
            filter_by(match_id=match.id, team=0).count()
        players_red = session.query(Player_Match).\
            filter_by(match_id=match.id, team=1).count()
        counts.append((players_blue, players_red))
    return render_template('recent_matches.html', matches=matches,
                           servers=servers, counts=counts)


@app.route('/admin/', methods=['GET', 'POST'])
def admin_panel():
    if is_admin():
        if request.method == 'GET':
            servers = session.query(Server).all()
            status = []
            for server in servers:
                tcp_client = manager.get_server_by_info(server)
                if tcp_client:
                    status.append(tcp_client.get_state())
                else:
                    status.append('ERROR')

            return render_template('admin.html',
                                   servers=servers, status=status)
        elif request.method == 'POST':
            email = request.form['email']
            user = session.query(User).filter_by(email=email).first()
            if user is None:
                flash('A user with that email was not found')
            else:
                user.admin = True
                flash('You have successfully promoted %s to admin' %
                      user.email)
            return redirect(url_for('admin_panel'))
    else:
        abort(401)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404


@app.errorhandler(401)
def page_not_found(error):
    return render_template('not_authorized.html'), 401


def is_admin():
    if 'email' in login_session:
        user = session.query(User).\
            filter_by(email=login_session['email']).first()
        if user is not None and user.admin:
            return True
    return False


def get_avatar_url(username):
    r = requests.get('https://api.kag2d.com/v1/player/%s/avatar' % username)
    avatar = '/static/assets/avatar.jpg'
    if r.status_code == 200:
        data = loads(r.text)['medium']
        img = requests.get(data)
        if img.status_code == 200:
            avatar = data
    return avatar

if __name__ == '__main__':
    servers = session.query(Server).all()
    if len(servers) == 0:
        print('no servers')
    for server in servers:
        manager.create_server(server)

    app.secret_key = 'change me'
    app.run(host='0.0.0.0', port=80)
    # this ensures that the other threads and sockets
    # are safely stopped before closing the application
    manager.exit()
