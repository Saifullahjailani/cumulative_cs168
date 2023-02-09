"""
Your awesome Distance Vector router for CS 168

Based on skeleton code by:
  MurphyMc, zhangwen0411, lab352
"""

from pickle import TRUE
from struct import pack
import sim.api as api
from cs168.dv import (
    RoutePacket,
    Table,
    TableEntry,
    DVRouterBase,
    Ports,
    FOREVER,
    INFINITY,
)


class DVRouter(DVRouterBase):

    # A route should time out after this interval
    ROUTE_TTL = 15

    # -----------------------------------------------
    # At most one of these should ever be on at once
    SPLIT_HORIZON = False
    POISON_REVERSE = False
    # -----------------------------------------------

    # Determines if you send poison for expired routes
    POISON_EXPIRED = False

    # Determines if you send updates when a link comes up
    SEND_ON_LINK_UP = False

    # Determines if you send poison when a link goes down
    POISON_ON_LINK_DOWN = False

    def __init__(self):
        """
        Called when the instance is initialized.
        DO NOT remove any existing code from this method.
        However, feel free to add to it for memory purposes in the final stage!
        """
        assert not (
            self.SPLIT_HORIZON and self.POISON_REVERSE
        ), "Split horizon and poison reverse can't both be on"

        self.start_timer()  # Starts signaling the timer at correct rate.

        # Contains all current ports and their latencies.
        # See the write-up for documentation.
        self.ports = Ports()

        # This is the table that contains all current routes
        self.table = Table()
        self.table.owner = self
        
        # This is the map from (host, port) touple to advertisements
        self.history = {}

    def add_static_route(self, host, port):
        """
        Adds a static route to this router's table.

        Called automatically by the framework whenever a host is connected
        to this router.

        :param host: the host.
        :param port: the port that the host is attached to.
        :returns: nothing.
        """
        # `port` should have been added to `peer_tables` by `handle_link_up`
        # when the link came up.
        assert port in self.ports.get_all_ports(), "Link should be up, but is not."

        # TODO: fill this in!
        latency = self.ports.get_latency(port)
        entry = TableEntry(dst=host, port=port, latency=latency, expire_time=FOREVER)
        self.table[host] = entry
        
        

    def handle_data_packet(self, packet, in_port):
        """
        Called when a data packet arrives at this router.

        You may want to forward the packet, drop the packet, etc. here.

        :param packet: the packet that arrived.
        :param in_port: the port from which the packet arrived.
        :return: nothing.
        """
        # TODO: fill this in!
        # fetch the table entry for the dstination in current router
        entry = self.table.get(packet.dst)
        
        # if the latency is greater or equal to Infinity drop the packet 
        # if the entry for the dst does not exist in current router drop the package
        # do not send something
        if not entry or  entry.latency >= INFINITY or packet.dst == in_port:
            return
        
        self.send(packet,entry.port, flood=False)
        
    
    def send_routes(self, force=False, single_port=None):
        """
        Send route advertisements for all routes in the table.

        :param force: if True, advertises ALL routes in the table;
                      otherwise, advertises only those routes that have
                      changed since the last advertisement.
               single_port: if not None, sends updates only to that port; to
                            be used in conjunction with handle_link_up.
        :return: nothing.
        """
        # TODO: fill this in!
        #iterate over all ports from the current route 
        for port in self.ports.get_all_ports():
            for host, entry in self.table.items():
                # add (host, entry) to the history
                cachedEntry = self.history.get((host, port))


                if self.SPLIT_HORIZON and entry.port == port:
                    continue
                if self.POISON_REVERSE and entry.port == port:
                    self.send_this_route(entry, cachedEntry, host, port, INFINITY, force)
                    continue
                self.send_this_route(entry, cachedEntry, host, port, entry.latency, force)
                
                

    def expire_routes(self):
        """
        Clears out expired routes from table.
        accordingly.
        """
        # TODO: fill this in!
        # if use the traditional self.table.items() iterator will face dictionary changed
        # size during iteration error, so, get the keys and iterate on them 
        # get each entry one by one 
        
        hosts = list(self.table.keys())
        for host in hosts:
            # use the simple [] instead of get because inclusion is guranteed at this point
            entry = self.table[host]
            if entry.expire_time == FOREVER:
                continue
            
            elif self.POISON_EXPIRED and entry.expire_time <= api.current_time():
                # set the latency of the entry to Infinity instead of removing it
                # since we can not modify the entry we should create a new entry coppy the entry and 
                # set the latency of the new entry to Infinity
                # also your router should make sure to advertise poisoned routes periodically for at least ROUTE_TTL seconds (15 s by default)
                self.table[host] = TableEntry(dst=host, port=entry.port, latency=INFINITY, expire_time=self.ROUTE_TTL)
                           
            elif entry.expire_time <= api.current_time():
                del self.table[host]
            

    def handle_route_advertisement(self, route_dst, route_latency, port):
        """
        Called when the router receives a route advertisement from a neighbor.

        :param route_dst: the destination of the advertised route.
        :param route_latency: latency from the neighbor to the destination.
        :param port: the port that the advertisement arrived on.
        :return: nothing.
        """
        # TODO: fill this in!
        current_entry = self.table.get(route_dst)
        
        
        #If a poisoned advertisement (latency INFINITY) matches the destination and port of a current route
        #replace it with the poisoned entry for poison propagation
        if route_latency >= INFINITY and current_entry.port == port:
            self.table[route_dst] = TableEntry(dst=route_dst, port=port, latency=INFINITY, expire_time=current_entry.expire_time)
            self.send_routes(force=False)
            return
            
        
        new_entry = TableEntry(dst=route_dst, port=port,latency=self.ports.get_latency(port) + route_latency, expire_time=api.current_time() + self.ROUTE_TTL)       
        
        #increase the cost of a route if you receive an advertisement from the same port.
        if not current_entry or port == current_entry.port or new_entry.latency < current_entry.latency:
            self.table[route_dst] = new_entry
            self.send_routes(force=False)
            return

        # something changed dow
    def handle_link_up(self, port, latency):
        """
        Called by the framework when a link attached to this router goes up.

        :param port: the port that the link is attached to.
        :param latency: the link latency.
        :returns: nothing.
        """
        self.ports.add_port(port, latency)

        # TODO: fill in the rest!
        
        for host, entry in self.table.items():
            if self.SEND_ON_LINK_UP:
                cached = self.history.get((host, port))
                self.send_this_route(entry, cached, host, port, latency)
            

    def handle_link_down(self, port):
        """
        Called by the framework when a link attached to this router goes down.

        :param port: the port number used by the link.
        :returns: nothing.
        """
        self.ports.remove_port(port)
        for h, p in list(self.history.keys()):
            if p == port:
                del self.history[(h,p)]
        
        for dst in list(self.table.keys()):
            entry = self.table[dst]
            if entry.port == port:
                if self.POISON_ON_LINK_DOWN:
                    self.table[dst] = TableEntry(dst, port, INFINITY, entry.expire_time)
                    self.send_routes()
                else:
                    del self.table[dst] 
        
        # TODO: fill this in!

    # Feel free to add any helper methods!

    def send_route(self, port, dst, latency):
        """
        Creates a control packet from dst and lat and sends it.
        """

        pkt = RoutePacket(destination=dst, latency=latency)
        self.history[(dst, port)] = pkt
        super().send_route(port, dst, latency)

    def send_this_route(self, entry, cachedEntry, host, port, latency, force=False):
        if not force:
            if cachedEntry is None:
                self.send_route(port, host, latency)
                return
            if cachedEntry.destination != host or cachedEntry.latency != latency:
                self.send_route(port, host, latency)
                return
        else:
            self.send_route(port, host, latency)