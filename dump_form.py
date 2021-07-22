import sys, argparse, copy
from datetime import *
from mrtparse import *
import configparser

peer = None

class BgpDump:
    __slots__ = [
        'verbose', 'output', 'ts_format', 'pkt_num', 'type', 'num', 'ts',
        'org_time', 'flag', 'peer_ip', 'peer_as', 'nlri', 'withdrawn',
        'as_path', 'origin', 'next_hop', 'local_pref', 'med', 'comm',
        'atomic_aggr', 'aggr', 'as4_path', 'as4_aggr', 'old_state', 'new_state',
    ]

    def __init__(self, file):
        self.output = sys.stdout
        f_handler=open(file,"w")
        self.output=f_handler
        self.type = ''
        self.flag = ''
        self.peer_ip = ''
        self.peer_as = 0
        self.nlri = []
        self.withdrawn = []
        self.as_path = []
        self.origin = ''
        self.next_hop = []
        self.as4_path = []
        self.as4_aggr = ''

    def close(self):
        self.output.close()
    
    def clear(self):
        self.type = ''
        self.flag = ''
        self.peer_ip = ''
        self.peer_as = 0
        self.nlri = []
        self.withdrawn = []
        self.as_path = []
        self.origin = ''
        self.next_hop = []
        self.as4_path = []
        self.as4_aggr = ''

    def print_line(self, prefix, next_hop):
        if self.flag == 'B' or self.flag == 'A':
            origin_as = self.merge_as_path().split(' ')[-1]       
            self.output.write('%s|%s\n' %(prefix, origin_as))
        elif self.flag == 'W':
            pass
        elif self.flag == 'STATE':
            pass

    def print_routes(self):
        for withdrawn in self.withdrawn:
            if self.type == 'BGP4MP':
                self.flag = 'W'
            self.print_line(withdrawn, '')
        for nlri in self.nlri:
            if self.type == 'BGP4MP':
                self.flag = 'A'
            for next_hop in self.next_hop:
                self.print_line(nlri, next_hop)

    def td(self, m, count):
        self.type = 'TABLE_DUMP'
        self.flag = 'B'
        # self.peer_ip = m['peer_ip']
        # self.peer_as = m['peer_as']
        self.nlri.append('%s/%d' % (m['prefix'], m['prefix_length']))
        for attr in m['path_attributes']:
            self.bgp_attr(attr)
        self.print_routes()

    def td_v2(self, m):
        global peer
        self.type = 'TABLE_DUMP2'
        self.flag = 'B'
        if m['subtype'][0] == TD_V2_ST['PEER_INDEX_TABLE']:
            peer = copy.copy(m['peer_entries'])
        elif (m['subtype'][0] == TD_V2_ST['RIB_IPV4_UNICAST']
            or m['subtype'][0] == TD_V2_ST['RIB_IPV4_MULTICAST']
            or m['subtype'][0] == TD_V2_ST['RIB_IPV6_UNICAST']
            or m['subtype'][0] == TD_V2_ST['RIB_IPV6_MULTICAST']):
            self.nlri.append('%s/%d' % (m['prefix'], m['prefix_length']))
            for entry in m['rib_entries']:
                # self.peer_ip = peer[entry['peer_index']]['peer_ip']
                # self.peer_as = peer[entry['peer_index']]['peer_as']
                self.as_path = []
                self.origin = ''
                self.next_hop = []
                self.as4_path = []
                self.as4_aggr = ''
                for attr in entry['path_attributes']:
                    self.bgp_attr(attr)
                self.print_routes()

    def bgp4mp(self, m, count):
        self.type = 'BGP4MP'
        # self.peer_ip = m['peer_ip']
        # self.peer_as = m['peer_as']
        if (m['subtype'][0] == BGP4MP_ST['BGP4MP_MESSAGE']
            or m['subtype'][0] == BGP4MP_ST['BGP4MP_MESSAGE_AS4']
            or m['subtype'][0] == BGP4MP_ST['BGP4MP_MESSAGE_LOCAL']
            or m['subtype'][0] == BGP4MP_ST['BGP4MP_MESSAGE_AS4_LOCAL']):
            if m['bgp_message']['type'][0] != BGP_MSG_T['UPDATE']:
                return
            for attr in m['bgp_message']['path_attributes']:
                self.bgp_attr(attr)
            for withdrawn in m['bgp_message']['withdrawn_routes']:
                self.withdrawn.append(
                    '%s/%d' % (
                        withdrawn['prefix'], withdrawn['prefix_length']
                    )
                )
            for nlri in m['bgp_message']['nlri']:
                self.nlri.append(
                    '%s/%d' % (
                        nlri['prefix'], nlri['prefix_length']
                    )
                )
            self.print_routes()

    def bgp_attr(self, attr):
        if attr['type'][0] == BGP_ATTR_T['NEXT_HOP']:
            self.next_hop.append(attr['value'])
        elif attr['type'][0] == BGP_ATTR_T['AS_PATH']:
            self.as_path = []
            for seg in attr['value']:
                if seg['type'][0] == AS_PATH_SEG_T['AS_SET']:
                    self.as_path.append('{%s}' % ','.join(seg['value']))
                elif seg['type'][0] == AS_PATH_SEG_T['AS_CONFED_SEQUENCE']:
                    self.as_path.append('(' + seg['value'][0])
                    self.as_path += seg['value'][1:-1]
                    self.as_path.append(seg['value'][-1] + ')')
                elif seg['type'][0] == AS_PATH_SEG_T['AS_CONFED_SET']:
                    self.as_path.append('[%s]' % ','.join(seg['value']))
                else:
                    self.as_path += seg['value']
        elif attr['type'][0] == BGP_ATTR_T['MP_REACH_NLRI']:
            self.next_hop = attr['value']['next_hop']
            if self.type != 'BGP4MP':
                return
            for nlri in attr['value']['nlri']:
                self.nlri.append(
                    '%s/%d' % (
                        nlri['prefix'], nlri['prefix_length']
                    )
                )
        elif attr['type'][0] == BGP_ATTR_T['MP_UNREACH_NLRI']:
            if self.type != 'BGP4MP':
                return
            for withdrawn in attr['value']['withdrawn_routes']:
                self.withdrawn.append(
                    '%s/%d' % (
                        withdrawn['prefix'], withdrawn['prefix_length']
                    )
                )
        elif attr['type'][0] == BGP_ATTR_T['AS4_PATH']:
            self.as4_path = []
            for seg in attr['value']:
                if seg['type'][0] == AS_PATH_SEG_T['AS_SET']:
                    self.as4_path.append('{%s}' % ','.join(seg['value']))
                elif seg['type'][0] == AS_PATH_SEG_T['AS_CONFED_SEQUENCE']:
                    self.as4_path.append('(' + seg['value'][0])
                    self.as4_path += seg['value'][1:-1]
                    self.as4_path.append(seg['value'][-1] + ')')
                elif seg['type'][0] == AS_PATH_SEG_T['AS_CONFED_SET']:
                    self.as4_path.append('[%s]' % ','.join(seg['value']))
                else:
                    self.as4_path += seg['value']
        elif attr['type'][0] == BGP_ATTR_T['AS4_AGGREGATOR']:
            self.as4_aggr = '%s %s' % (
                attr['value']['as'], attr['value']['id']
            )
        
    def merge_as_path(self):
        if len(self.as4_path):
            n = len(self.as_path) - len(self.as4_path)
            return ' '.join(self.as_path[:n] + self.as4_path)
        else:
            return ' '.join(self.as_path)

    def merge_aggr(self):
        if len(self.as4_aggr):
            return self.as4_aggr
        else:
            return self.aggr
