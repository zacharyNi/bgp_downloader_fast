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

    def __init__(self, output):
        cp = configparser.ConfigParser()
        cp.read('config/parseMRT.ini')
        verbose = cp.get('init','verbose')
        if verbose=='0':
            self.verbose = False
        else:
            self.verbose = True
        self.output = sys.stdout
        f_handler=open(output,"a")
        self.output=f_handler
        ts_format = cp.get('init','ts_format')
        if ts_format==0:
            self.ts_format = 'dump'
        else:
            self.ts_format = 'change'
        pkt_num = cp.get('init','pkt_num')
        if pkt_num=='0':
            self.pkt_num = False
        else:
            self.pkt_num = True
        self.type = ''
        self.num = 0
        self.ts = 0
        self.org_time = 0
        self.flag = ''
        self.peer_ip = ''
        self.peer_as = 0
        self.nlri = []
        self.withdrawn = []
        self.as_path = []
        self.origin = ''
        self.next_hop = []
        self.local_pref = 0
        self.med = 0
        self.comm = ''
        self.atomic_aggr = 'NAG'
        self.aggr = ''
        self.as4_path = []
        self.as4_aggr = ''
        self.old_state = 0
        self.new_state = 0

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
        cp = configparser.ConfigParser()
        cp.read('config/parseMRT.ini')
        as_path_only = cp.get('init','AS_PATH_ONLY')
        prefix_and_origin = cp.get('init','PREFIX_AND_ORIGIN')
        if self.ts_format == 'dump':
            d = self.ts
        else:
            d = self.org_time

        if self.verbose:
            d = str(d)
        else:
            d = datetime.utcfromtimestamp(d).strftime('%m/%d/%y %H:%M:%S')

        if self.pkt_num == True:
            d = '%d|%s' % (self.num, d)

        if self.flag == 'B' or self.flag == 'A':
            if as_path_only == '0':
                if prefix_and_origin == '0':
                    self.output.write(
                        '%s|%s|%s|%s|%s|%s|%s|%s' % (
                            self.type, d, self.flag, self.peer_ip, self.peer_as, prefix,
                            self.merge_as_path(), self.origin
                        )
                    )
                    if self.verbose == True:
                        self.output.write(
                            '|%s|%d|%d|%s|%s|%s|\n' % (
                                next_hop, self.local_pref, self.med, self.comm,
                                self.atomic_aggr, self.merge_aggr()
                            )
                        )
                    else:
                        self.output.write('\n')
                else:
                    origin_as = self.merge_as_path().split(' ')[-1]
                    self.output.write('%s|%s\n' %(prefix, origin_as))
            else:
                self.output.write('%s\n'%(self.merge_as_path()))
        elif self.flag == 'W':
            if as_path_only=='0' and prefix_and_origin=='0':
                self.output.write(
                    '%s|%s|%s|%s|%s|%s\n' % (
                        self.type, d, self.flag, self.peer_ip, self.peer_as,
                        prefix
                    )
                )
            else:
                pass
        elif self.flag == 'STATE':
            if as_path_only=='0' and prefix_and_origin=='0':
                self.output.write(
                    '%s|%s|%s|%s|%s|%d|%d\n' % (
                        self.type, d, self.flag, self.peer_ip, self.peer_as,
                        self.old_state, self.new_state
                    )
                )
            else:
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
        self.ts = m['timestamp'][0]
        self.num = count
        self.org_time = m['originated_time'][0]
        self.peer_ip = m['peer_ip']
        self.peer_as = m['peer_as']
        self.nlri.append('%s/%d' % (m['prefix'], m['prefix_length']))
        for attr in m['path_attributes']:
            self.bgp_attr(attr)
        self.print_routes()

    def td_v2(self, m):
        global peer
        self.type = 'TABLE_DUMP2'
        self.flag = 'B'
        self.ts = m['timestamp'][0]
        if m['subtype'][0] == TD_V2_ST['PEER_INDEX_TABLE']:
            peer = copy.copy(m['peer_entries'])
        elif (m['subtype'][0] == TD_V2_ST['RIB_IPV4_UNICAST']
            or m['subtype'][0] == TD_V2_ST['RIB_IPV4_MULTICAST']
            or m['subtype'][0] == TD_V2_ST['RIB_IPV6_UNICAST']
            or m['subtype'][0] == TD_V2_ST['RIB_IPV6_MULTICAST']):
            self.num = m['sequence_number']
            self.nlri.append('%s/%d' % (m['prefix'], m['prefix_length']))
            for entry in m['rib_entries']:
                self.org_time = entry['originated_time'][0]
                self.peer_ip = peer[entry['peer_index']]['peer_ip']
                self.peer_as = peer[entry['peer_index']]['peer_as']
                self.as_path = []
                self.origin = ''
                self.next_hop = []
                self.local_pref = 0
                self.med = 0
                self.comm = ''
                self.atomic_aggr = 'NAG'
                self.aggr = ''
                self.as4_path = []
                self.as4_aggr = ''
                for attr in entry['path_attributes']:
                    self.bgp_attr(attr)
                self.print_routes()

    def bgp4mp(self, m, count):
        self.type = 'BGP4MP'
        self.ts = m['timestamp'][0]
        self.num = count
        self.org_time = m['timestamp'][0]
        self.peer_ip = m['peer_ip']
        self.peer_as = m['peer_as']
        if (m['subtype'][0] == BGP4MP_ST['BGP4MP_STATE_CHANGE']
            or m['subtype'][0] == BGP4MP_ST['BGP4MP_STATE_CHANGE_AS4']):
            self.flag = 'STATE'
            self.old_state = m['old_state'][0]
            self.new_state = m['new_state'][0]
            self.print_line([], '')
        elif (m['subtype'][0] == BGP4MP_ST['BGP4MP_MESSAGE']
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
        if attr['type'][0] == BGP_ATTR_T['ORIGIN']:
            self.origin = ORIGIN_T[attr['value']]
        elif attr['type'][0] == BGP_ATTR_T['NEXT_HOP']:
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
        elif attr['type'][0] == BGP_ATTR_T['MULTI_EXIT_DISC']:
            self.med = attr['value']
        elif attr['type'][0] == BGP_ATTR_T['LOCAL_PREF']:
            self.local_pref = attr['value']
        elif attr['type'][0] == BGP_ATTR_T['ATOMIC_AGGREGATE']:
            self.atomic_aggr = 'AG'
        elif attr['type'][0] == BGP_ATTR_T['AGGREGATOR']:
            self.aggr = '%s %s' % (attr['value']['as'], attr['value']['id'])
        elif attr['type'][0] == BGP_ATTR_T['COMMUNITY']:
            self.comm = ' '.join(attr['value'])
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
