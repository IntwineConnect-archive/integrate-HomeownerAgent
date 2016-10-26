# -*- coding: utf-8 -*- 
from __future__ import absolute_import
from datetime import datetime
import logging
import sys
from volttron.platform.vip.agent import Agent, Core 
from volttron.platform.agent import utils

import gevent

utils.setup_logging() 
_log = logging.getLogger(__name__)

class homeownerAgent(Agent): 
    price_hwA1 = []
    quantity_hwA = []
    
    def __init__(self, config_path, **kwargs): 
        super(homeownerAgent, self).__init__(**kwargs)
        self.config = utils.load_config(config_path)
        self._agent_id = self.config['agentid']
        #self.local_vip = self.config.get('local-vip')
        self.destination_platform = self.config['destination-platform']
        self.destination_vip = self.config.get('destination-vip')
       
    @Core.receiver("onstart") 
    def starting(self, sender, **kwargs): 
        '''Subscribes to the platform message bus 
        on the heatbeat/listeneragent topic 
        ''' 
        agent = Agent(identity=self.destination_platform, address=self.destination_vip)
        event = gevent.event.Event()
        _log.info('vip and platform %r and %r', self.destination_platform, self.destination_vip)    
        # agent.core.run set the event flag to true when agent is running
        gevent.spawn(agent.core.run, event)
        _log.info('gevent spawned')
            
            # Wait until the agent is fully initialized and ready to 
            # send and receive messages.
        event.wait()
        _log.info('event passed? wtf')

        self._target_platform = agent
        print(self._agent_id) 
        _log.info('still going')
        
        #agent2 = Agent(identity='2', address=self.local_vip)
        _log.info('still going')

        demandfilepath = "/opt/intwine/icg-data/volttron/homeownerAgent1/curve.txt"
        global price_hwA1
        global quantity_hwA
        price_hwA1, quantity_hwA = self.extractData(demandfilepath)
        _log.info("price is %r, quantity is %r", price_hwA1, quantity_hwA)
        #self._local_platform = agent2
        self._target_platform.vip.pubsub.subscribe('pubsub','', callback=self.on_heartbeat) 
        self.vip.pubsub.subscribe('pubsub', '', callback=self.on_heartbeat2)
        _log.info('whole method passed')
	#self.vip.pubsub.publish('pubsub', '', headers = '', message = 'testing')

    def on_heartbeat2(self, peer, sender, bus, topic, headers, message):
        _log.info('local pubsub working: %r', message)

    def extractData(self, filename):
        content = ""
        with open(filename) as fil:
            content = fil.readlines()
        fil.close()
        print content
        _log.info('content %r', content)
        stripped = [x.strip('\n') for x in content]
        if (len (stripped) != 2):
            raise ValueError("make sure agents curve file has 2 lines")
        stringPrices = stripped[0].split()
        stringQuantities = stripped[1].split()
        _log.info('strings %r . %r', stringPrices, stringQuantities)
        arrayedPrices = list(map(int, stringPrices))
        arrayedQuantities = list(map(int, stringQuantities))
        _log.info('values %r . %r', arrayedPrices, arrayedQuantities)
        return arrayedPrices, arrayedQuantities
            
    def on_heartbeat(self, peer, sender, bus, topic, headers, message):
        _log.info('heart is beating')
        if (topic=='request for bids'):
            _log.info("Bidding: q = %r, p = %r", quantity_hwA, price_hwA1)
            headers = {
                'AgentID': self._agent_id,
            }
            #Bidding curve
            #price_hwA1=range(5,0,-1)
            #quantity_hwA1=range(1,6)
            
            curve=['price', price_hwA1,'quantity',quantity_hwA]
            self._target_platform.vip.pubsub.publish('pubsub', 'Bidding', headers=headers, message=curve)
        elif (topic=='clearing price'):
            headers.items()
            clearing_p = message[0]
            clearing_q = message[1]
            status = ''
            _log.info('Got clearing price: %r', clearing_p)
            _log.info('Got clearing quantity: %r', clearing_q)
            #assume higher quantity <-> lower price
            assert all(quantity_hwA[i] <= quantity_hwA[i+1] for i in xrange (len(quantity_hwA)-1))
            maxLoad = quantity_hwA[-1]
            minLoad = quantity_hwA[0]
            cutOffInterval = (maxLoad-minLoad)*0.3
            dontShedBound = maxLoad - cutOffInterval
            smallShed = dontShedBound - cutOffInterval
            medShed = smallShed - cutOffInterval
            assert medShed > minLoad
            if (clearing_q > dontShedBound):
                status = 'dont need to shed'
            elif (clearing_q > smallShed):
                status = 'small shed'
            elif (clearing_q > medShed):
                status = 'medium shed'
            else:
                assert clearing_q <= medShed
                assert clearing_q > 0
                status = 'heavy shed'
            self.vip.pubsub.publish('pubsub', 'Load Status', headers=headers, message=status)
            _log.info('dontShed is %r, smallshed is %r, medshed is %r, load status is %r', dontShedBound, smallShed, medShed, status)
            
                                     
def main(argv=sys.argv): 
    '''Main method called by the executable.''' 
    try: 
        utils.vip_main(homeownerAgent) 
    except Exception as e: 
            _log.exception(e)
if __name__ == '__main__': 
    # Entry point for script 
    sys.exit(main())
