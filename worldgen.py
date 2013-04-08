from globals import *

import threading
import logging
import logic
import items
import tiles
import life
import maps

import random
import time

RECRUIT_ITEMS = ['sneakers', 'leather backpack', 'glock', '9x19mm magazine', 'radio']
for i in range(10):
	RECRUIT_ITEMS.append('9x19mm round')

class Runner(threading.Thread):
	def __init__(self, function, source_map, amount):
		self.function = function
		self.source_map = source_map
		self.amount = amount
		self.running = True
		
		threading.Thread.__init__(self)
	
	def run(self):
		try:
			self.function(self.source_map, amount=self.amount)
		except Exception as e:
			logging.error('Crash: %s' % e)
			SETTINGS['running'] = False
			raise
		
		self.running = False


def draw_world_stats():	
	console_print(0, 0, 2, 'Simulating world: %s (%.2f t/s)' % (WORLD_INFO['ticks'], WORLD_INFO['ticks']/(time.time()-WORLD_INFO['inittime'])))
	console_print(0, 0, 3, 'Queued ALife actions: %s' % sum([len(alife['actions']) for alife in [LIFE[i] for i in LIFE]]))
	console_print(0, 0, 4, 'Total ALife memories: %s' % sum([len(alife['memory']) for alife in [LIFE[i] for i in LIFE]]))
	console_print(0, 0, 5, '%s %s' % (TICKER[int(WORLD_INFO['ticks'] % len(TICKER))], '=' * (WORLD_INFO['ticks']/50)))
	console_print(0, 0, 6, 'Time elapsed: %.2f' % (time.time()-WORLD_INFO['inittime']))
	console_flush()

def generate_world(source_map, life=1, simulate_ticks=1000):
	console_print(0, 0, 0, 'World Generation')
	console_flush()
	
	WORLD_INFO['inittime'] = time.time()
	
	generate_life(source_map, amount=life)
	randomize_item_spawns()
	
	console_rect(0,0,0,WINDOW_SIZE[0],WINDOW_SIZE[1],True,flag=BKGND_DEFAULT)
	_r = Runner(simulate_life, source_map, amount=simulate_ticks)
	_r.start()
	
	while _r.running:
		draw_world_stats()
		
		if not SETTINGS['running']:
			return False
	
	create_player(source_map)
	logging.info('World generation complete (took %.2fs)' % (time.time()-WORLD_INFO['inittime']))

def randomize_item_spawns():
	for building in REFERENCE_MAP['buildings']:
		_chunk_key = random.choice(building)
		_chunk = maps.get_chunk(_chunk_key)
		
		if not _chunk['ground']:
			continue
		
		_rand_pos = random.choice(_chunk['ground'])
		items.create_item(random.choice(RECRUIT_ITEMS), position=[_rand_pos[0], _rand_pos[1], 2])

def generate_life(source_map, amount=1):
	for i in range(amount):
		alife = life.create_life('Human',name=['test', str(i)],map=source_map,position=[30+(i*2),70+(i*15),2])
		
		for item in RECRUIT_ITEMS:
			life.add_item_to_inventory(alife, items.create_item(item))
		
		if i == 2:
			_wep = life.get_all_unequipped_items(alife, matches=[{'type': 'gun'}])
			life.equip_item(alife, _wep[0])

def simulate_life(source_map, amount=1000):
	for i in range(amount):
		logic.tick_all_objects(source_map)
		logic.tick_world()

def create_player(source_map):
	PLAYER = life.create_life('Human',
		name=['Tester','Toaster'],
		map=source_map,
		position=[15,50,2])
	PLAYER['player'] = True
	
	for item in RECRUIT_ITEMS:
		life.add_item_to_inventory(PLAYER, items.create_item(item))

	SETTINGS['controlling'] = PLAYER
	SETTINGS['following'] = PLAYER
