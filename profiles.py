from globals import DATA_DIR

import logging
import os

def get_home_directory():
	return os.path.expanduser('~')

def has_reactor3():	
	_config_directory = os.path.join(get_home_directory(),'.config','reactor-3')
	_worlds_directory = os.path.join(_config_directory, 'worlds')
	
	try:
		os.makedirs(_config_directory)
		logging.info('Created config directory: %s' % _config_directory)
	except OSError:
		if not os.path.exists(_config_directory):
			logging.exception('Could not create config directory at \'%s\'' % _config_directory)
			raise Exception('Could not create config directory.')
	
	try:
		os.mkdir(_worlds_directory)
		logging.info('Created worlds directory: %s' % _worlds_directory)
		return (_config_directory, _worlds_directory)
	except OSError:
		return (_config_directory, _worlds_directory)

def get_maps():
	_map_dir = os.path.join(DATA_DIR, 'maps')
	_maps = []
	
	for (dirpath, dirname, filenames) in os.walk(_map_dir):
		_maps.extend(filenames)
	
	return _maps

def get_worlds():
	_config_directory, _worlds_directory = has_reactor3()
	
	_dirs = []
	for (dirpath, dirname, filenames) in os.walk(_worlds_directory):
		_dirs.extend(dirname)
		break
	
	return _dirs

def create_world():
	_config_directory, _worlds_directory = has_reactor3()
	
	_world_name = str(len(get_worlds())+1)
	_world_directory = os.path.join(_worlds_directory, _world_name)
	
	try:
		os.mkdir(_world_directory)
		logging.info('Created world: %s' % _world_name)
		return _world_name
	except OSError:
		return False

def get_world(world):
	_config_directory, _worlds_directory = has_reactor3()
	_world_directory = os.path.join(_worlds_directory, str(world))
	
	return _world_directory