from globals import *
import graphics as gfx
import pathfinding
import logging
import items
import menus
import copy
import time
import json
import os

def load_life(life):
	with open(os.path.join(LIFE_DIR,life+'.json'),'r') as e:
		return json.loads(''.join(e.readlines()))

def calculate_base_stats(life):
	stats = {'arms': None,
		'legs': None,
		'melee': None,
		'speed_max': LIFE_MAX_SPEED}
	race_type = None
	
	_flags = life['flags'].split('|')
	
	for flag in _flags:
		if _flags.index(flag) == 0:
			race_type = flag
		
		elif flag.count('LEGS'):
			stats['legs'] = flag.partition('[')[2].partition(']')[0].split(',')
		
		elif flag.count('ARMS'):
			stats['arms'] = flag.partition('[')[2].partition(']')[0].split(',')
		
		elif flag.count('HANDS'):
			stats['hands'] = flag.partition('[')[2].partition(']')[0].split(',')
		
		elif flag.count('MELEE'):
			stats['melee'] = flag.partition('[')[2].partition(']')[0].split(',')
	
	stats['base_speed'] = LIFE_MAX_SPEED-(len(stats['legs']))
	stats['speed_max'] = stats['base_speed']
	
	return stats

def _get_max_speed(life,leg):
	#TODO: This will be used to calculate damage at some point...
	_speed_mod = 0
	
	for limb in leg['attached']:
		limb = get_limb(life['body'],limb)
		for item in limb['holding']:
			_i = get_inventory_item(life,item)
			
			if _i.has_key('speed_mod'):
				_speed_mod += _i['speed_mod']
		
		_speed_mod += _get_max_speed(life,limb)
	
	return _speed_mod

def get_max_speed(life):
	_speed_mod = 0
	for leg in life['legs']:
		_leg = get_limb(life['body'],leg)
		_speed_mod += _get_max_speed(life,_leg)
	
	return LIFE_MAX_SPEED-_speed_mod

def initiate_life(name):
	if name in LIFE_TYPES:
		logging.warning('Life type \'%s\' is already loaded. Reloading...' % name)
	
	life = load_life(name)
	
	if not 'icon' in life:
		logging.warning('No icon set for life type \'%s\'. Using default (%s).' % (name,DEFAULT_LIFE_ICON))
		_life['tile'] = DEFAULT_LIFE_ICON
	
	if not 'flags' in life:
		logging.error('No flags set for life type \'%s\'. Errors may occur.' % name)
	
	for key in life:
		if isinstance(life[key],unicode):
			life[key] = str(life[key])
	
	life.update(calculate_base_stats(life))
	
	LIFE_TYPES[name] = life
	
	return life

def initiate_limbs(body):
	for limb in body:
		#Unicode fix:
		_val = body[limb].copy()
		del body[limb]
		body[str(limb)] = _val
		body[limb] = body[str(limb)]
		
		_flags = body[limb]['flags'].split('|')
		
		if 'CANSTORE' in _flags:
			body[limb]['storing'] = []
		
		body[limb]['holding'] = []
		
		initiate_limbs(body[limb]['attached'])

def get_limb(body,limb):
	_limb = []
	
	for limb1 in body:
		if limb1 == limb:
			return body[limb1]
		
		_limbs = get_limb(body[limb1]['attached'],limb)
		if _limbs:
			_limb = _limbs
	
	return _limb

def get_all_limbs(body):
	_limbs = {}
	
	for limb in body:
		_limb = body[limb].copy()
		del _limb['attached']
		
		_limbs[limb] = _limb
		_limbs.update(get_all_limbs(body[limb]['attached']))
	
	return _limbs

def create_life(type,position=(0,0,2),name=('Test','McChuckski'),map=None):
	if not type in LIFE_TYPES:
		raise Exception('Life type \'%s\' does not exist.' % type)
	
	#TODO: Any way to get rid of this call to `copy`?
	_life = copy.deepcopy(LIFE_TYPES[type])
	_life['name'] = name
	_life['speed'] = _life['speed_max']
	_life['pos'] = list(position)
	_life['realpos'] = list(position)
	
	#TODO: We only need this for pathing, so maybe we should move this to
	#the `walk` function?
	_life['map'] = map
	
	_life['path'] = []
	_life['actions'] = []
	_life['item_index'] = 0
	_life['inventory'] = {}
	_life['flags'] = {}
	_life['gravity'] = 0
	
	initiate_limbs(_life['body'])
	LIFE.append(_life)
	
	return _life

def set_state(life,flag,state):
	life['flags'][flag] = state

def get_state(life,flag):
	if flag in life['flags']:
		return life['flags'][flag]
	
	raise Exception('State \'%s\' does not exist.' % flag)

def path_dest(life):
	if not life['path']:
		return None
	
	return tuple(life['path'][len(life['path'])-1])

def walk(life,to):
	if life['speed']:
		life['speed'] -= 1
		return False
	elif life['speed']<=0:
		life['speed'] = life['speed_max']
	
	_dest = path_dest(life)
	
	if not _dest == tuple(to):
		#_stime = time.time()
		_path = pathfinding.astar(start=life['pos'],end=to,size=MAP_SIZE,omap=life['map'])
		life['path'] = _path.find_path(life['pos'])
		#print time.time()-_stime
	
	return walk_path(life)

def walk_path(life):
	if life['gravity']:
		return False
	
	if life['path']:
		_pos = list(life['path'].pop(0))
		
		if _pos[2] and abs(_pos[2])-1:
			if _pos[2]>0:
				logging.debug('%s is changing z-level: %s -> %s' % (life['name'][0],life['pos'][2],life['pos'][2]+(_pos[2]-1)))
				life['pos'][2] += _pos[2]-1
			
		life['pos'] = [_pos[0],_pos[1],life['pos'][2]]
		life['realpos'] = life['pos'][:]
		
		if life['path']:
			return False
		else:
			return True
	else:
		print 'here?'
		return False

def perform_collisions(life):
	#Gravity
	if not life['map'][life['pos'][0]][life['pos'][1]][life['pos'][2]]:
		if life['map'][life['pos'][0]][life['pos'][1]][life['pos'][2]-1]:
			life['pos'][2] -= 1
			
			return True
		
		if not life['gravity'] and life.has_key('player'):
			gfx.message('You begin to fall...')
		
		life['gravity'] = SETTINGS['world gravity']
			
	elif life['gravity']:
		life['gravity'] = 0
		
		if life.has_key('player'):
			gfx.message('You land.')
	
	if life['gravity']:
		life['realpos'][2] -= SETTINGS['world gravity']
		life['pos'][2] = int(life['realpos'][2])
		
		print life['pos'][2]

def get_highest_action(life):
	_actions = {'action': None,'lowest': -1}
	
	for action in life['actions']:
		if action['score'] > _actions['lowest']:
			_actions['lowest'] = action['score']
			_actions['action'] = action
	
	if _actions['action']:
		return _actions['action']
	else:
		return None

def clear_actions(life):
	#TODO: Any way to improve this?
	if life['actions'] and not life['actions'][0]['action']['action']=='move':
		_action = life['actions'][0]['action']['action']
		
		logging.debug('%s %s cancels %s' % (life['name'][0],life['name'][1],_action))
		
		if life.has_key('player'):
			gfx.message(MESSAGE_BANK['cancel'+_action])
		
	life['actions'] = []

def add_action(life,action,score,delay=0):
	_tmp_action = {'action': action,'score': score}
	
	if not _tmp_action in life['actions']:
		_tmp_action['delay'] = delay
		
		life['actions'].append(_tmp_action)
	
	return False

def perform_action(life):
	_action = get_highest_action(life)
	
	#TODO: What's happening here?
	if not _action in life['actions']:
		return False

	if _action['delay']:
		_action['delay']-=1
		
		return False

	_score = _action['score']
	_delay = _action['delay']
	_action = _action['action']
	
	if _action['action'] == 'move':
		if tuple(_action['to']) == tuple(life['pos']) or walk(life,_action['to']):
			life['actions'].remove({'action':_action,'score':_score,'delay':_delay})
	elif _action['action'] == 'pickupitem':
		direct_add_item_to_inventory(_action['life'],_action['item'],container=_action['container'])
		life['actions'].remove({'action':_action,'score':_score,'delay':_delay})
		
		if life.has_key('player'):			
			if _action.has_key('container'):
				gfx.message('You store %s in your %s.'
					% (items.get_name(_action['item']),_action['container']['name']))
	elif _action['action'] == 'pickupequipitem':
		if not can_wear_item(_action['life'],_action['item']):
			if life.has_key('player'):
				gfx.message('You can\'t equip this item!')
			
			life['actions'].remove({'action':_action,'score':_score,'delay':_delay})
			
			return False
		
		#TODO: Can we even equip this? Can we check here instead of later?
		_id = direct_add_item_to_inventory(_action['life'],_action['item'])
		
		equip_item(_action['life'],_id)
		
		life['actions'].remove({'action':_action,'score':_score,'delay':_delay})
		
		if life.has_key('player'):
			gfx.message('You equip %s from the ground.' % items.get_name(_action['item']))
	
	elif _action['action'] == 'pickupholditem':
		_hand = get_limb(life['body'],_action['hand'])
		
		if _hand['holding']:
			if life.has_key('player'):
				gfx.message('You\'re alreading holding something in your %s!' % _action['hand'])
		
			life['actions'].remove({'action':_action,'score':_score,'delay':_delay})
			
			return False
		
		_id = direct_add_item_to_inventory(_action['life'],_action['item'])
		_hand['holding'].append(_id)
		
		print _id
		
		gfx.message('You hold %s in your %s.' % (items.get_name(_action['item']),_action['hand']))
		
		life['actions'].remove({'action':_action,'score':_score,'delay':_delay})

def tick(life):
	perform_collisions(life)
	perform_action(life)

def attach_item_to_limb(body,item,limb):
	for limb1 in body:
		if limb1 == limb:
			body[limb1]['holding'].append(item)
			logging.debug('%s attached to %s' % (item,limb))
			return True
		
		attach_item_to_limb(body[limb1]['attached'],item,limb)

def remove_item_from_limb(body,item,limb):
	for limb1 in body:
		if limb1 == limb:
			try:
				body[limb1]['holding'].remove(item)
			except:
				print body[limb1]['holding'],item
				raise Exception('Cant find that item...')
			logging.debug('%s removed from %s' % (item,limb))
			return True
		
		remove_item_from_limb(body[limb1]['attached'],item,limb)

def get_all_storage(life):
	_storage = []
	
	for item in [life['inventory'][item] for item in life['inventory']]:
		if 'max_capacity' in item:
			_storage.append(item)
	
	return _storage

def can_put_item_in_storage(life,item):
	#Whoa...
	for _item in [life['inventory'][_item] for _item in life['inventory']]:
		if 'max_capacity' in _item and _item['capacity']+item['size'] < _item['max_capacity']:
			return _item
		else:
			pass
	
	return False

def add_item_to_storage(life,item,container=None):
	if not container:
		container = can_put_item_in_storage(life,item)
	
	if not container:
		return False
	
	container['storing'].append(item['id'])
	
	return True

def remove_item_in_storage(life,item):
	item = int(item)
	
	for _container in [life['inventory'][_container] for _container in life['inventory']]:
		if not 'max_capacity' in _container:
			continue

		if item in _container['storing']:
			_container['storing'].remove(item)
			logging.debug('Removed item #%s from %s' % (item,_container['name']))
			
			return _container
	
	return False

def item_is_stored(life,item):
	for _container in [life['inventory'][_container] for _container in life['inventory']]:
		if not 'max_capacity' in _container:
			continue

		if item in _container['storing']:
			return _container
	
	return False

def can_wear_item(life,item):
	for limb in item['attaches_to']:
		_limb = get_limb(life['body'],limb)
		
		for _item in [life['inventory'][str(i)] for i in _limb['holding']]:
			if not 'CANSTACK' in _item['flags']:
				logging.warning('%s will not let %s stack.' % (_item['name'],item['name']))
				return False

	return True

def get_inventory_item(life,id):
	if not life['inventory'].has_key(str(id)):
		raise Exception('Life \'%s\' does not have item of id #%s'
			% (life['name'][0],id))
	
	return life['inventory'][str(id)]

def direct_add_item_to_inventory(life,item,container=None):
	#Warning: Only use this if you know what you're doing!
	life['item_index'] += 1
	_id = life['item_index']
	item['id'] = _id
	
	life['inventory'][str(_id)] = item
	
	if 'max_capacity' in item:
		logging.debug('Container found in direct_add')
		
		for uid in item['storing'][:]:
			logging.debug('\tAdding uid %s' % uid)
			_item = items.get_item_from_uid(uid)

			item['storing'].remove(uid)
			item['storing'].append(direct_add_item_to_inventory(life,_item))
	
	#Warning: `container` refers directly to an item instead of an ID.
	if container:
		#Warning: No check is done to make sure the container isn't full!
		add_item_to_storage(life,item,container=container)
	
	return _id

def add_item_to_inventory(life,item):
	life['item_index'] += 1
	_id = life['item_index']
	item['id'] = _id
	
	if not add_item_to_storage(life,item):
		if not can_wear_item(life,item):
			life['item_index'] -= 1
			del item['id']
			
			return False
		else:
			life['inventory'][str(_id)] = item
			equip_item(life,_id)
	else:
		life['inventory'][str(_id)] = item
	
	if 'max_capacity' in item:
		for uid in item['storing'][:]:
			_item = items.get_item_from_uid(uid)
			
			item['storing'].remove(uid)
			item['storing'].append(direct_add_item_to_inventory(life,_item))
	
	logging.debug('%s got \'%s\'.' % (life['name'][0],item['name']))
	
	return _id

def remove_item_from_inventory(life,id):
	item = get_inventory_item(life,id)
	
	_holding = holding_item(life,id)
	if _holding:
		_holding['holding'].remove(id)
		logging.debug('%s stops holding a %s' % (life['name'][0],item['name']))
		
	elif item_is_equipped(life,id):
		logging.debug('%s takes off a %s' % (life['name'][0],item['name']))
	
		for limb in item['attaches_to']:
			remove_item_from_limb(life['body'],item['id'],limb)
		
		item['pos'] = life['pos'][:]
	elif item_is_stored(life,id):
		remove_item_in_storage(life,id)
	
	if 'max_capacity' in item:
		logging.debug('Dropping container storing:')
		
		for _item in item['storing'][:]:
			logging.debug('\tdropping %s' % _item)
			item['storing'].remove(_item)
			item['storing'].append(get_inventory_item(life,_item)['uid'])
			
			del life['inventory'][str(_item)]
	
	life['speed_max'] = get_max_speed(life)
	
	logging.debug('Removed from inventory: %s' % item['name'])
	
	del life['inventory'][str(item['id'])]
	del item['id']
	
	return item

def equip_item(life,id):
	if not id:
		return False
	
	item = get_inventory_item(life,id)
	
	if not can_wear_item(life,item):
		return False
	
	_limbs = get_all_limbs(life['body'])
	
	#TODO: Faster way to do this with sets
	for limb in item['attaches_to']:
		if not limb in _limbs:
			logging.warning('Limb not found: %s' % limb)
			return False
	
	remove_item_in_storage(life,id)
	
	logging.debug('%s puts on a %s' % (life['name'][0],item['name']))
	
	if item['attaches_to']:			
		for limb in item['attaches_to']:
			attach_item_to_limb(life['body'],item['id'],limb)
	
	life['speed_max'] = get_max_speed(life)
	
	if life['speed'] > life['speed_max']:
		life['speed'] = life['speed_max']
	
	return True

def drop_item(life,id):
	item = remove_item_from_inventory(life,id)
	item['pos'] = life['pos'][:]

def pick_up_item_from_ground(life,uid):
	_item = items.get_item_from_uid(uid)
	_id = add_item_to_inventory(life,_item)
	
	if _id:
		return _id

	return False

	raise Exception('Item \'%s\' does not exist at (%s,%s,%s).'
		% (item,life['pos'][0],life['pos'][1],life['pos'][2]))

def holding_item(life,id):
	for _hand in life['hands']:
		_limb = get_limb(life['body'],_hand)
		
		if id in _limb['holding']:
			return _limb
	
	return False

def item_is_equipped(life,id):
	for _limb in get_all_limbs(life['body']):
		if int(id) in get_limb(life['body'],_limb)['holding']:
			return True
	
	return False

def show_life_info(life):
	for key in life:
		if key == 'body':
			continue
		
		logging.debug('%s: %s' % (key,life[key]))
	
	return True

def draw_life():
	for life in LIFE:
		#if not life['pos'][2] <= CAMERA_POS[2]:
		#	continue
		
		if life['pos'][0] >= CAMERA_POS[0] and life['pos'][0] < CAMERA_POS[0]+MAP_WINDOW_SIZE[0] and\
			life['pos'][1] >= CAMERA_POS[1] and life['pos'][1] < CAMERA_POS[1]+MAP_WINDOW_SIZE[1]:
			_x = life['pos'][0] - CAMERA_POS[0]
			_y = life['pos'][1] - CAMERA_POS[1]
			gfx.blit_char(_x,_y,life['icon'],white,None)

def get_fancy_inventory_menu_items(life):
	_inventory = []
	
	_title = menus.create_item('title','Equipped',None,enabled=False)
	_inventory.append(_title)
	
	#TODO: Time it would take to remove
	for entry in life['inventory']:
		item = get_inventory_item(life,entry)
		
		if item_is_equipped(life,entry):
			_menu_item = menus.create_item('single',
				item['name'],
				'Equipped',
				icon=item['icon'],
				id=int(entry))
		
			_inventory.append(_menu_item)
	
	for container in get_all_storage(life):
		_title = menus.create_item('title',container['name'],None,enabled=False)
		_inventory.append(_title)
		for _item in container['storing']:
			item = get_inventory_item(life,_item)
			_menu_item = menus.create_item('single',
				item['name'],
				'Not equipped',
				icon=item['icon'],
				id=int(entry))
			
			_inventory.append(_menu_item)
	
	return _inventory

def draw_visual_inventory(life):
	_inventory = {}
	_limbs = get_all_limbs(life['body'])
	
	for limb in _limbs:
		if _limbs[limb]['holding']:
			_item = get_inventory_item(life,_limbs[limb]['holding'][0])
			console_set_default_foreground(0,white)
			console_print(0,MAP_WINDOW_SIZE[0]+1,_limbs.keys().index(limb)+1,'%s: %s' % (limb,_item['name']))
		else:
			console_set_default_foreground(0,Color(125,125,125))
			console_print(0,MAP_WINDOW_SIZE[0]+1,_limbs.keys().index(limb)+1,'%s: None' % limb)
	
	console_set_default_foreground(0,white)

def tick_all_life():
	for life in LIFE:
		tick(life)
