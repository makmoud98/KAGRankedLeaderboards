from server import Server, State
import threading
import socket


class ServerManager:
    def __init__(self):
        self.servers = []

    # create a new server with the given info and then start it
    def create_server(self, info):
        server = self.get_server_by_info(info)
        if server is None:
            server = Server(info)
            self.servers.append(server)
            server.start()

    # stop the server with the given info, only if it is in the list
    def stop_server(self, info):
        server = self.get_server_by_info(info)
        if server.state != State.STOPPING and server.state != State.CONNECTING:
        	server.stop()

    # start the server with the given info, only if it is in the list
    def start_server(self, info):
        server = self.get_server_by_info(info)
        server.restart()

    # stop the server, then remove it from the list
    def remove_server(self, info):
        for i in range(len(self.servers)):
            server = self.servers[i]
            if server.address[1] == info.port and server.address[0] == info.host:
                server.stop()
                server.end()
                server.join()
                del self.servers[i]

    # shutdown all servers (this is done when the httpserver shuts down)
    def exit(self):
        for server in self.servers:
            server.stop()
            server.end()
            server.join()

    # resolve ip addresses and then check for server with the same ip and port
    def get_server_by_info(self, info):
        for server in self.servers:
            if server.address[1] == info.port and server.address[0] == info.host:
                return server
        return None
