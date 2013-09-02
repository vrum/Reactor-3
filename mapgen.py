from globals import *

import libtcodpy as tcod

import maputils
import effects
import alife
import tiles
import zones
import maps

import logging
import random
import copy
import sys
import os

TOWN_DISTANCE = 25
TOWN_SIZE = 160
FOREST_DISTANCE = 25
OPEN_TILES = ['.']
DIRECTION_MAP = {'(-1, 0)': 'left', '(1, 0)': 'right', '(0, -1)': 'top', '(0, 1)': 'bot'}

tiles.create_all_tiles()

def create_building(buildings, building, chunk_size):
	_top = False
	_bot = False
	_left = False
	_right = False
	
	for y in range(chunk_size):
		for x in range(chunk_size):
			_tile = building[y][x]
			
			if x == 0 and (y>0 or y<chunk_size) and _tile in OPEN_TILES:
				_left = True
			
			if x == chunk_size-1 and (y>0 or y<chunk_size) and _tile in OPEN_TILES:
				_right = True
			
			if y == 0 and (x>0 or x<chunk_size) and _tile in OPEN_TILES:
				_top = True
			
			if y == chunk_size-1 and (x>0 or x<chunk_size) and _tile in OPEN_TILES:
				_bot = True
	
	_building_temp = {'open': {'top': _top, 'bot': _bot, 'left': _left, 'right': _right},
	                  'building': copy.deepcopy(building)}
	
	buildings.append(_building_temp)

def load_tiles(file_name, chunk_size):
	with open(os.path.join(TEXT_DIR, file_name), 'r') as f:
		_buildings = []
		_building = []
		_i = 0
		for line in f.readlines():
			_i += 1
			
			if line.startswith('//'):
				continue
			
			if len(line)>1 and (not len(line)-1 == chunk_size or len(_building)>chunk_size):
				logging.debug('Incorrect chunk size (%s) for tile on line %s' % (len(line), _i))
				print 'Incorrect chunk size %s (wanted %s) for tile on line %s' % (len(line)-1, chunk_size, _i)
				continue
			
			line = line.rstrip()
			
			if line:
				_building.append(line)
			elif _building:
				create_building(_buildings, _building, chunk_size)
				_building = []
		
		if _building:
			create_building(_buildings, _building, chunk_size)
	
	return _buildings

def generate_map(size=(300, 300, 10), detail=5, towns=4, forests=1, underground=True, skip_zoning=False):
	""" Size: Both width and height must be divisible by DETAIL.
	Detail: Determines the chunk size. Smaller numbers will generate more elaborate designs.
	Towns: Decides the amount of towns generated.
	Forests: Number of large forested areas.
	Underground: Flags whether buildings can be constructed beneath the surface.
	"""
	
	map_gen = {'size': size,
		'chunk_size': detail,
		'towns': towns,
		'forests': forests,
		'underground': underground,
		'chunk_map': {},
		'refs': {'towns': [], 'forests': [], 'roads': []},
		'buildings': load_tiles('buildings.txt', detail),
		'flags': {},
		'map': maps.create_map(size=size)}
	
	#logging.debug('Creating height map...')
	#generate_height_map(map_gen)
	logging.debug('Creating chunk map...')
	generate_chunk_map(map_gen)
	logging.debug('Drawing outlines...')
	generate_outlines(map_gen)
	print_chunk_map_to_console(map_gen)
	
	logging.debug('Creating roads...')
	create_roads(map_gen)
	
	logging.debug('Building towns...')
	for _town in map_gen['refs']['towns']:
		construct_town(map_gen, _town)
	#print_map_to_console(map_gen)
	
	WORLD_INFO.update(map_gen)
	
	_map_size = maputils.get_map_size(WORLD_INFO['map'])
	MAP_SIZE[0] = _map_size[0]
	MAP_SIZE[1] = _map_size[1]
	MAP_SIZE[2] = _map_size[2]
	
	if not skip_zoning:
		logging.debug('Creating zone map...')
		zones.create_zone_map()
		
		logging.debug('Connecting zone ramps...')
		zones.connect_ramps()
	
	maps.save_map('test2.dat')
	
	return map_gen

def generate_height_map(map_gen):
	noise = tcod.noise_new(2)
	noise_dx = 0
	noise_dy = 0
	noise_octaves = 3.0
	noise_zoom = 12.0
	
	for y in range(map_gen['size'][1]):
		for x in range(map_gen['size'][0]):
			f = [noise_zoom * x / (2*map_gen['size'][0]) + noise_dx,
			     noise_zoom * y / (2*map_gen['size'][1]) + noise_dy]
			
			#value = tcod.noise_get_fbm(noise, f, noise_octaves, tcod.NOISE_PERLIN)
			#value = tcod.noise_get_turbulence(noise, f, noise_octaves, tcod.NOISE_PERLIN)
			#value = tcod.noise_get_fbm(noise, f, noise_octaves, tcod.NOISE_SIMPLEX)
			value = tcod.noise_get(noise, f, tcod.NOISE_PERLIN)
			height = int((value + 1.0) / 2.0 * map_gen['size'][2])
			
			for z in range(height):
				_tile = tiles.create_tile(random.choice(
						[tiles.TALL_GRASS_TILE, tiles.SHORT_GRASS_TILE, tiles.GRASS_TILE]))
				
				map_gen['map'][x][y][z] = _tile

def generate_chunk_map(map_gen):
	for y1 in xrange(0, map_gen['size'][1], map_gen['chunk_size']):
		for x1 in xrange(0, map_gen['size'][0], map_gen['chunk_size']):
			_chunk_key = '%s,%s' % (x1, y1)
			
			map_gen['chunk_map'][_chunk_key] = {'pos': (x1, y1),
				'ground': [],
				'life': [],
				'items': [],
				'control': {},
				'neighbors': [],
				'reference': None,
				'last_updated': None,
				'digest': None,
				'type': 'other'}
			
def generate_outlines(map_gen):
	logging.debug('Placing roads...')
	place_roads(map_gen)
	
	logging.debug('Placing towns...')
	while len(map_gen['refs']['towns'])<map_gen['towns']:
		place_town(map_gen)
	
	logging.debug('Placing forests...')
	while len(map_gen['refs']['forests'])<map_gen['forests']:
		place_forest(map_gen)

def place_roads(map_gen, start_pos=None, next_dir=None, turns=-1, can_create=True):
	_start_edge = random.randint(0, 3)
	
	if turns == -1:
		_max_turns = random.randint(3, 6)
	else:
		_max_turns = turns
	
	_pos = start_pos
	_next_dir = next_dir
	
	if not _pos:
		if not _start_edge:
			_pos = [random.randint(0, map_gen['size'][0]/map_gen['chunk_size']), 0]
			_next_dir = (0, 1)
		elif _start_edge == 1:
			_pos = [map_gen['size'][0]/map_gen['chunk_size'], random.randint(0, map_gen['size'][1]/map_gen['chunk_size'])]
			_next_dir = (-1, 0)
		elif _start_edge == 2:
			_pos = [random.randint(0, map_gen['size'][0]/map_gen['chunk_size']), map_gen['size'][1]/map_gen['chunk_size']]
			_next_dir = (0, -1)
		elif _start_edge == 3:
			_pos = [0, random.randint(0, map_gen['size'][1]/map_gen['chunk_size'])]
			_next_dir = (1, 0)
	
	while 1:
		for i in range(40, 40+random.randint(0, 20)):
			_pos[0] += _next_dir[0]
			_pos[1] += _next_dir[1]
			
			if _pos[0] >= map_gen['size'][0]/map_gen['chunk_size']:
				return False
			
			if _pos[1] >= map_gen['size'][1]/map_gen['chunk_size']:
				return False
			
			if _pos[0] < 0:
				return False
			
			if _pos[1] < 0:
				return False
		
			_chunk_key = '%s,%s' % (_pos[0]*map_gen['chunk_size'], _pos[1]*map_gen['chunk_size'])
			map_gen['chunk_map'][_chunk_key]['type'] = 'road'
			map_gen['refs']['roads'].append(_chunk_key)
		
		_possible_next_dirs = []
		if _pos[0]+1<map_gen['size'][0]/map_gen['chunk_size']:
			_possible_next_dirs.append((1, 0))
		
		if _pos[0]-1>0:
			_possible_next_dirs.append((-1, 0))
		
		if _pos[1]+1<map_gen['size'][1]/map_gen['chunk_size']:
			_possible_next_dirs.append((0, 1))
		
		if _pos[1]-1>0:
			_possible_next_dirs.append((0, -1))
		
		for _possible in _possible_next_dirs[:]:
			if not _next_dir[0]+_possible[0] or not _next_dir[1]+_possible[1]:
				_possible_next_dirs.remove(_possible)
		
		while _max_turns and can_create:
			_next_dir = random.choice(_possible_next_dirs)
			_possible_next_dirs.remove(_next_dir)
			
			for _turn in _possible_next_dirs:
				place_roads(map_gen, start_pos=_pos[:], next_dir=_turn, turns=random.randint(0, 2), can_create=False)
			
			break
		
		if _max_turns:
			_max_turns -= 1
			continue
		
		#take rest of _possible_next_dirs and make intersection?

def place_town(map_gen):
	_existing_towns = map_gen['refs']['towns']
	_avoid_chunk_keys = []
	
	for town in _existing_towns:
		_avoid_chunk_keys.extend(['%s,%s' % (t[0], t[1]) for t in town])
	
	while 1:
		while 1:
			_town_chunk = random.choice(map_gen['chunk_map'].values())
			if _town_chunk['pos'][0] == 0 or _town_chunk['pos'][1] == 0 or \
			   _town_chunk['pos'][1] == map_gen['size'][0]+map_gen['chunk_size'] or _town_chunk['pos'][1]+map_gen['chunk_size'] == map_gen['size'][1]:
				continue
			
			break
				
		if _avoid_chunk_keys and alife.chunks.get_distance_to_hearest_chunk_in_list(_town_chunk['pos'], _avoid_chunk_keys) < TOWN_DISTANCE:
			continue
		
		_walked = walker(map_gen,
			_town_chunk['pos'],
		     TOWN_SIZE,
			allow_diagonal_moves=False,
			avoid_chunks=_avoid_chunk_keys,
			avoid_chunk_distance=TOWN_DISTANCE)
			
		if not _walked:
			continue
		
		_restart = False
		while 1:
			clean_walker(map_gen, _walked, kill_range=(0, 1))
			
			if _walked:
				break
			
			_restart = True
			break
		
		if _restart:
			continue
		
		for pos in _walked:
			map_gen['chunk_map']['%s,%s' % (pos[0], pos[1])]['type'] = 'town'
		
		map_gen['refs']['towns'].append(_walked)
		break

def place_forest(map_gen):
	_existing_chunks = map_gen['refs']['forests']
	_avoid_chunk_keys = []
	
	for chunk in _existing_chunks:
		_avoid_chunk_keys.extend(['%s,%s' % (c[0], c[1]) for c in chunk])
	
	while 1:
		_chunk = random.choice(map_gen['chunk_map'].values())
				
		if _avoid_chunk_keys and alife.chunks.get_distance_to_hearest_chunk_in_list(_chunk['pos'], _avoid_chunk_keys) < FOREST_DISTANCE:
			continue
		
		_walked = walker(map_gen,
			_chunk['pos'],
		     60,
			allow_diagonal_moves=False,
			avoid_chunks=_avoid_chunk_keys,
			avoid_chunk_distance=FOREST_DISTANCE)
			
		if not _walked:
			continue
		
		for pos in _walked:
			map_gen['chunk_map']['%s,%s' % (pos[0], pos[1])]['type'] = 'forest'
		
		map_gen['refs']['forests'].append(_walked)
		break

def get_neighbors_of_type(map_gen, pos, chunk_type, diagonal=False, return_keys=True):
	_directions = [(0, -1), (-1, 0), (1, 0), (0, 1)]
	_keys = []
	_neighbors = 0
	
	if diagonal:
		_directions.extend([(-1, -1), (1, 1), (-1, 1), (1, 1)])
	
	for _dir in _directions:
		_next_pos = [pos[0]+(_dir[0]*map_gen['chunk_size']), pos[1]+(_dir[1]*map_gen['chunk_size'])]
		_next_key = '%s,%s' % (_next_pos[0], _next_pos[1])
		
		if _next_pos[0]<0 or _next_pos[0]>=map_gen['size'][0] or _next_pos[1]<0 or _next_pos[1]>=map_gen['size'][1]:
			continue
		
		if chunk_type == 'any' or map_gen['chunk_map'][_next_key]['type'] == chunk_type:
			_keys.append(_next_key)
			_neighbors += 1
	
	if return_keys:
		return _keys
	
	return _neighbors

def walker(map_gen, pos, moves, density=5, allow_diagonal_moves=True, avoid_chunks=[], avoid_chunk_distance=0):
	_pos = list(pos)
	_directions = [(0, -1), (-1, 0), (1, 0), (0, 1)]
	
	if allow_diagonal_moves:
		_directions.extend([(-1, -1), (1, 1), (-1, 1), (1, 1)])
	
	_walked = []
	_last_dir = {'dir': None, 'times': 0}
	for i in range(moves/map_gen['chunk_size']):
		_possible_dirs = []
		
		for _dir in _directions[:]:
			_next_pos = [_pos[0]+(_dir[0]*map_gen['chunk_size']), _pos[1]+(_dir[1]*map_gen['chunk_size'])]
			
			if _last_dir['times'] >= 3 and _next_pos == _last_dir['dir']:
				continue

			if _next_pos in _walked:
				continue
			
			if _next_pos[0]<=0 or _next_pos[0]>=map_gen['size'][0]-map_gen['chunk_size'] or _next_pos[1]<=0 or _next_pos[1]>=map_gen['size'][1]-map_gen['chunk_size']:
				continue
			
			if avoid_chunks and alife.chunks.get_distance_to_hearest_chunk_in_list(_next_pos, avoid_chunks) < avoid_chunk_distance:
				continue
			
			_possible_dirs.append(_next_pos)
			
		if not _possible_dirs:
			return False
		
		_chosen_dir = random.choice(_possible_dirs)
		if _chosen_dir == _last_dir['dir']:
			_last_dir['times'] += 1
		else:
			_last_dir['dir'] = _chosen_dir[:]
			_last_dir['times'] += 1
		
		_pos[0] = _chosen_dir[0]
		_pos[1] = _chosen_dir[1]
	
		_walked.append(list(_pos))
	
	return _walked

def clean_walker(map_gen, walker, kill_range=(-2, -1)):
	while 1:
		_changed = False
		
		for pos in walker[:]:
			_num = 0
			for neighbor in get_neighbors_of_type(map_gen, pos, 'other'):
				_neighbor_pos = list(map_gen['chunk_map'][neighbor]['pos'])
				if _neighbor_pos in walker:
					_num += 1
			
			if _num in range(kill_range[0], kill_range[1]+1):
				walker.remove(pos)
				_changed = True
		
		if not _changed:
			break

def direction_from_key_to_key(map_gen, key1, key2):
	_k1 = map_gen['chunk_map'][key1]['pos']
	_k2 = map_gen['chunk_map'][key2]['pos']
	
	if _k1 == _k2:
		return (0, 0)
	
	if _k1[0] == _k2[0] and _k1[1] < _k2[1]:
		return (0, 1)
	
	if _k1[0] == _k2[0] and _k1[1] > _k2[1]:
		return (0, -1)	
	
	if _k1[0] < _k2[0] and _k1[1] == _k2[1]:
		return (1, 0)
	
	if _k1[0] > _k2[0] and _k1[1] == _k2[1]:
		return (-1, 0)
	
	raise Exception('Invalid direction.')

def create_roads(map_gen):
	for chunk_key in map_gen['refs']['roads']:
		chunk = map_gen['chunk_map'][chunk_key]
		_directions = []
		
		for neighbor_key in get_neighbors_of_type(map_gen, chunk['pos'], 'road'):
			_directions.append(direction_from_key_to_key(map_gen, chunk_key, neighbor_key))
		
		#for _direction in _directions:
		if len(_directions) == 2 and (-1, 0) in _directions and (1, 0) in _directions:
			for x in range(0, map_gen['chunk_size']):
				for y in range(0, map_gen['chunk_size']):
					if (y == 0 or y == map_gen['chunk_size']-1) and not random.randint(0, 2):
						_tile = random.choice(tiles.GRASS_TILES)
					elif y == round(map_gen['chunk_size']/2) and x % 2:
						_tile = random.choice(tiles.ROAD_STRIPES)
					else:
						_tile = random.choice(tiles.CONCRETE_TILES)
						
					map_gen['map'][chunk['pos'][0]+x][chunk['pos'][1]+y][2] = maps.create_tile(_tile)
		elif len(_directions) == 2 and (0, -1) in _directions and (0, 1) in _directions:
			for x in range(0, map_gen['chunk_size']):
				for y in range(0, map_gen['chunk_size']):
					if (x == 0 or x == map_gen['chunk_size']-1) and not random.randint(0, 2):
						_tile = random.choice(tiles.GRASS_TILES)
					else:
						_tile = random.choice(tiles.CONCRETE_TILES)
						
					map_gen['map'][chunk['pos'][0]+x][chunk['pos'][1]+y][2] = maps.create_tile(_tile)
		elif len(_directions) == 2 and (0, -1) in _directions and (-1, 0) in _directions:
			for x in range(0, map_gen['chunk_size']):
				for y in range(0, map_gen['chunk_size']):
					if (y == map_gen['chunk_size']-1 or x == map_gen['chunk_size']-1) and not random.randint(0, 2):
						_tile = random.choice(tiles.GRASS_TILES)
					else:
						_tile = random.choice(tiles.CONCRETE_TILES)
						
					map_gen['map'][chunk['pos'][0]+x][chunk['pos'][1]+y][2] = maps.create_tile(_tile)
		elif len(_directions) == 3 and (0, -1) in _directions and (-1, 0) in _directions and (1, 0) in _directions:
			for x in range(0, map_gen['chunk_size']):
				for y in range(0, map_gen['chunk_size']):
					if y == map_gen['chunk_size']-1 and not random.randint(0, 2):
						_tile = random.choice(tiles.GRASS_TILES)
					else:
						_tile = random.choice(tiles.CONCRETE_TILES)
						
					map_gen['map'][chunk['pos'][0]+x][chunk['pos'][1]+y][2] = maps.create_tile(_tile)
		elif len(_directions) == 3 and (0, 1) in _directions and (-1, 0) in _directions and (1, 0) in _directions:
			for x in range(0, map_gen['chunk_size']):
				for y in range(0, map_gen['chunk_size']):
					if y == 0 and not random.randint(0, 2):
						_tile = random.choice(tiles.GRASS_TILES)
					else:
						_tile = random.choice(tiles.CONCRETE_TILES)
						
					map_gen['map'][chunk['pos'][0]+x][chunk['pos'][1]+y][2] = maps.create_tile(_tile)
		elif len(_directions) == 3 and (0, -1) in _directions and (0, 1) in _directions and (1, 0) in _directions:
			for x in range(0, map_gen['chunk_size']):
				for y in range(0, map_gen['chunk_size']):
					if x == 0 and not random.randint(0, 2):
						_tile = random.choice(tiles.GRASS_TILES)
					else:
						_tile = random.choice(tiles.CONCRETE_TILES)
						
					map_gen['map'][chunk['pos'][0]+x][chunk['pos'][1]+y][2] = maps.create_tile(_tile)
		elif len(_directions) == 3 and (0, -1) in _directions and (0, 1) in _directions and (-1, 0) in _directions:
			for x in range(0, map_gen['chunk_size']):
				for y in range(0, map_gen['chunk_size']):
					if x == map_gen['chunk_size']-1 and not random.randint(0, 2):
						_tile = random.choice(tiles.GRASS_TILES)
					else:
						_tile = random.choice(tiles.CONCRETE_TILES)
						
					map_gen['map'][chunk['pos'][0]+x][chunk['pos'][1]+y][2] = maps.create_tile(_tile)
		elif len(_directions) == 4:
			for x in range(0, map_gen['chunk_size']):
				for y in range(0, map_gen['chunk_size']):
					_tile = random.choice(tiles.CONCRETE_TILES)
						
					map_gen['map'][chunk['pos'][0]+x][chunk['pos'][1]+y][2] = maps.create_tile(_tile)

def construct_town(map_gen, town):
	_open = ['%s,%s' % (pos[0], pos[1]) for pos in town[:]]
	
	while _open:
		_start_key = _open.pop(random.randint(0, len(_open)-1))
		_occupied_chunks = random.randint(1, len(_open)+1)
		_build_on_chunks = [_start_key]
		_door = {'chunk': None, 'direction': None, 'created': False}
		
		while len(_build_on_chunks) < _occupied_chunks:
			_center_chunk = random.choice(_build_on_chunks)
			
			_possible_next_chunk = random.choice(get_neighbors_of_type(map_gen, map_gen['chunk_map'][_center_chunk]['pos'], 'town'))
			if _possible_next_chunk in _build_on_chunks:
				continue
			
			_build_on_chunks.append(_possible_next_chunk)
		
		if len(_build_on_chunks) == 1:
			break
		
		_make_door = False
		for _chunk in _build_on_chunks:
			if _chunk in _open:
				_open.remove(_chunk)
			
			_directions = []
			_avoid_directions = []
			for _neighbor in get_neighbors_of_type(map_gen, map_gen['chunk_map'][_chunk]['pos'], 'any'):
				if _neighbor in _build_on_chunks:
					_directions.append(str(direction_from_key_to_key(map_gen, _chunk, _neighbor)))
				else:
					if _neighbor in _open:
						_open.remove(_neighbor)
						
						if not _door['chunk']:
							_door['chunk'] = _neighbor[:]
							_door['direction'] = str(direction_from_key_to_key(map_gen, _chunk, _neighbor))
							_directions.append(str(direction_from_key_to_key(map_gen, _chunk, _neighbor)))
							continue
					
					_avoid_directions.append(str(direction_from_key_to_key(map_gen, _chunk, _neighbor)))
			
			_possible_buildings = []
			_direction_keys = [DIRECTION_MAP[d] for d in _directions]
			_avoid_direction_keys = [DIRECTION_MAP[d] for d in _avoid_directions]
			
			for building in map_gen['buildings']:
				_continue = False
				for _dir in _direction_keys:
					if not building['open'][_dir]:
						_continue = True
						break
				
				if _continue:
					continue
				
				for _dir in _avoid_direction_keys:
					if building['open'][_dir]:
						_continue = True
						break
				
				if _continue:
					continue
				
				_possible_buildings.append(building['building'])
			
			_chunk_pos = map_gen['chunk_map'][_chunk]['pos']
			_building = random.choice(_possible_buildings)
			for _y in range(map_gen['chunk_size']):
				y = _chunk_pos[1]+_y
				for _x in range(map_gen['chunk_size']):
					x = _chunk_pos[0]+_x
					
					for i in range(3):
						if _building[_y][_x] == '#':
							map_gen['map'][x][y][2+i] = tiles.create_tile(tiles.WALL_TILE)
						elif (not i or i == 2) and _building[_y][_x] == '.':
							map_gen['map'][x][y][2+i] = tiles.create_tile(random.choice(tiles.CONCRETE_FLOOR_TILES))
							
							if not i and random.randint(0, 500) == 500:
								effects.create_light((x, y, 2), (255, 0, 255), 5, 0.1)

MAP_KEY = {'o': '.',
           't': 't'}

def print_chunk_map_to_console(map_gen):
	for y1 in xrange(0, map_gen['size'][1], map_gen['chunk_size']):
		for x1 in xrange(0, map_gen['size'][0], map_gen['chunk_size']):
			_chunk_key = '%s,%s' % (x1, y1)
			_key = map_gen['chunk_map'][_chunk_key]['type'][0]
			
			if _key in  MAP_KEY:
				print MAP_KEY[_key],
			else:
				print _key,
		
		print 

def print_map_to_console(map_gen):
	for y1 in xrange(0, map_gen['size'][1]):
		for x1 in xrange(0, map_gen['size'][0]):
			print tiles.get_raw_tile(map_gen['map'][x1][y1][2])['icon'],
		
		print

if __name__ == '__main__':
	generate_map(skip_zoning=True)