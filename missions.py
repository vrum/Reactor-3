from globals import MISSION_DIR, MISSIONS, FUNCTION_MAP

import graphics as gfx

import copy
import os

def load_mission(mission_file):
	_mission = {'name': mission_file.rpartition(os.sep)[2].replace('_', ' ').split('.')[0].title(),
	            'stages': {},
	            'stage_index': 1,
	            'flags': {}}
	_stage = {}
	_current_stage = None

	with open(mission_file, 'r') as _file:
		for line in _file.readlines():
			if line.startswith('#'):
				continue
			
			line = line.rstrip()
			
			if not line:
				continue
			
			if line.startswith('='):
				if _current_stage:
					_step_id = len(_mission['stages'][str(_current_stage)]['steps'])+1
					_mission['stages'][str(_current_stage)]['steps'][str(_step_id)] = _step.copy()
				
				_current_stage = int(line.split('=')[1])
				_mission['stages'][str(_current_stage)] = {'steps': {},
				                                      'step_index': 1}
				continue
			
			#elif line.startswith('COMPLETE'):
			#	_step_id = len(_mission['stages'][_current_stage]['steps'])+1
			#	_mission['stages'][_current_stage]['steps'][_step_id] = _step.copy()
			#	_current_stage = None
			#	
			#	continue
			
			_args = [l.lower() for l in line.split(' ')]
			
			if _args[0] == 'set':
				_step = {'mode': 'set',
				         'flag': _args[1],
				         'func': _args[2],
				         'args': _args[3:]}

			elif _args[0] in ['exec', 'wait']:
				_step = {'mode': _args[0],
				         'func': _args[1],
				         'args': _args[2:]}
			
			elif _args[0] == 'jump':
				_step = {'mode': 'jump',
				         'stage': int(_args[1]),
				         'args': []}
			
			elif _args[0] == 'jumpif':
				_step = {'mode': 'jumpif',
				         'stage': int(_args[1]),
				         'func': _args[2],
				         'args': _args[3:]}
			
			elif _args[0] == 'loop':
				_step = {'mode': 'loop'}
			
			elif _args[0] == 'complete':
				_step = {'mode': 'complete'}
			
			if not _current_stage:
				raise Exception('No stage set: Missing stage tag.')
			
			_step_id = len(_mission['stages'][str(_current_stage)]['steps'])+1
			_mission['stages'][str(_current_stage)]['steps'][str(_step_id)] = _step.copy()
	
	MISSIONS[mission_file.rpartition(os.sep)[2].split('.')[0]] = _mission

def load_all_missions():
	for (dirpath, dirnames, filenames) in os.walk(MISSION_DIR):
		for filename in [f for f in filenames if f.endswith('.dat')]:
			load_mission(os.path.join(dirpath, filename))

def create_mission(mission_name, **kwargs):
	if not mission_name in MISSIONS:
		raise Exception('Mission does not exist: %s' % mission_name)
	
	_mission = copy.deepcopy(MISSIONS[mission_name])
	_mission['flags'].update(kwargs)
	
	return _mission

def remember_mission(life, mission):
	life['missions'][str(len(life['missions'])+1)] = mission

def activate_mission(life, mission_id):
	life['mission_id'] = mission_id
	
	if 'player' in life:
		gfx.glitch_text('Mission: %s' % life['missions'][life['mission_id']]['name'])

def complete_mission(life, mission_id):
	if 'player' in life:
		gfx.glitch_text('Mission complete: %s' % life['missions'][life['mission_id']]['name'])
	
	if life['mission_id'] == mission_id:
		life['mission_id'] = None
	
	del life['missions'][mission_id]

def exec_func(life, func, *args):
	try:
		return FUNCTION_MAP[func](life, *args)
	except:
		raise Exception('Failed to execute: %s' % func)

def do_mission(life, mission_id):
	_mission = life['missions'][mission_id]
	
	while 1:
		_stage = _mission['stages'][str(_mission['stage_index'])]
		_step = _stage['steps'][str(_stage['step_index'])]
		_args = []
		
		if _step['mode'] == 'complete':
			complete_mission(life, mission_id)
			
			break
		
		elif _step['mode'] in ['jump', 'loop']:
			_stage['step_index'] = 1
			
			if _step['mode'] == 'jump':
				_mission['stage_index'] = _step['stage']
				
				continue
			else:
				break
		
		for arg in _step['args']:
			if arg.startswith('%'):
				_args.append(_mission['flags'][arg[1:len(arg)-1]])
			elif arg.count('.'):
				_args.append(float(arg))
			else:
				_args.append(arg)
		
		_func = exec_func(life, _step['func'], *_args)
		
		if _step['mode'] in ['wait', 'jumpif']:
			if _func:
				if _step['mode'] == 'wait':
					_stage['step_index'] += 1
				else:
					_stage['step_index'] = 1
					_mission['stage_index'] = _step['stage']
					
					continue
			elif _step['mode'] == 'jumpif':
				_stage['step_index'] += 1
				
				continue
			else:
				break
		
		elif _step['mode'] == 'set':
			_mission['flags'][_step['flag']] = _func
			_stage['step_index'] += 1
		
		elif _step['mode'] == 'exec':
			_stage['step_index'] += 1
		
		else:
			break
