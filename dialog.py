from globals import *

import graphics as gfx
import life as lfe

import language
import numbers
import drawing
import menus
import logic
import alife

import logging
import random

def create_dialog_with(life, target_id):
	_dialog = {'id': str(WORLD_INFO['dialogid']),
	           'messages': [],
	           'started_by': life['id'],
	           'target': target_id,
	           'choices': [],
	           'cursor_index': 0}
	
	life['dialogs'].append(_dialog['id'])
	
	WORLD_INFO['dialogs'][_dialog['id']] = _dialog
	WORLD_INFO['dialogid'] += 1
	
	return _dialog['id']

def get_dialog(dialog_id):
	return WORLD_INFO['dialogs'][dialog_id]

def end_dialog(dialog_id):
	_dialog = get_dialog(dialog_id)
	
	LIFE[_dialog['started_by']]['dialogs'].remove(dialog_id)
	LIFE[_dialog['target']]['dialogs'].remove(dialog_id)

	if SETTINGS['controlling'] in [_dialog['started_by'], _dialog['target']]:
		lfe.focus_on(LIFE[SETTINGS['controlling']])
	
	logging.debug('Dialog between %s and %s is over.' % (' '.join(LIFE[_dialog['started_by']]['name']), ' '.join(LIFE[_dialog['target']]['name'])))

def get_last_message(dialog_id):
	_dialog = get_dialog(dialog_id)
	
	if not _dialog['messages']:
		return None
	
	return _dialog['messages'][len(_dialog['messages'])-1]

def get_listener(dialog_id):
	_dialog = get_dialog(dialog_id)
	_last_message = get_last_message(dialog_id)
	
	if not _last_message:
		return _dialog['target']
	
	if _last_message['from'] == _dialog['started_by']:
		return _dialog['started_by']
	
	return _dialog['target']

def is_turn_to_talk(life, dialog_id):
	if not get_listener(dialog_id) == life['id']:
		return True
	
	return False

def execute_function(life, target, function):
	_function = function.lower()
	_pass = True
	_flags = {'true': True,
	          'self_call': False,
	          'no_args': False}
	_flag_map = {'!': {'true': False},
	             '@': {'self_call': True},
	             '%': {'no_args': True}}
	
	while 1:
		_flag = _function[0]
		
		if not _flag in _flag_map:
			break
		
		_function = _function[1:]
		_flags.update(_flag_map[_flag])
		
		break
	
	if not _function in FUNCTION_MAP:
		raise Exception('Function does not exist: %s' % _function)
	
	try:
		if _flags['self_call']:
			if not FUNCTION_MAP[_function](life) == _flags['true']:
				_pass = False
		elif _flags['no_args']:
			if not FUNCTION_MAP[_function]() == _flags['true']:
				_pass = False
		else:
			if not FUNCTION_MAP[_function](life, target) == _flags['true']:
				_pass = False
	except Exception, e:
		logging.critical('Function \'%s\' got invalid arugments. See exception below.' % _function)
		raise e
	
	if _pass:
		return True
	
	return False

def get_matching_message(life, dialog_id, gist):
	_dialog_choices = []
	_target = get_listener(dialog_id)
	
	for dialog_options in DIALOG_TOPICS[gist.upper()]:
		_pass = True
		
		for requirement in dialog_options['requirements']:
			if execute_function(life, _target, requirement):
				_dialog_choices.append(dialog_options)
	
	return _dialog_choices

def add_message(life, dialog_id, gist, text, result, loop=False):
	_dialog = get_dialog(dialog_id)
	
	if _dialog['started_by'] == life['id']:
		_target = _dialog['target']
	else:
		_target = _dialog['started_by']
	
	_message = {'from': life['id'],
	            'gist': gist,
	            'text': text,
	            'read': False,
	            'result': result.lower().split(','),
	            'next_gist': None,
	            'loop': loop}
	
	print ' '.join(life['name'])+':', text
	
	_dialog['messages'].append(_message)
	
	for result in _message['result']:
		if result.startswith('>'):
			_message['next_gist'] = result[1:]
		else:
			execute_function(life, _target, result)
	
	alife.speech.communicate(life, 'dialog', matches=[{'id': _target}], dialog_id=dialog_id)

def say_via_gist(life, dialog_id, gist, loop=False):
	_chosen_message = random.choice(get_matching_message(life, dialog_id, gist))
	_target = get_listener(dialog_id)
	_loop = False

	while _chosen_message['text'].startswith('>') and not loop:
		_chosen_message = random.choice(get_matching_message(life, dialog_id, _chosen_message['text'][1:]))
		_loop = True
	
	if 'player' in life:
		logic.show_event(_chosen_message['text'], life=life)
	
	add_message(life, dialog_id, _chosen_message['gist'], _chosen_message['text'], _chosen_message['result'], loop=_loop)

def select_choice(dialog_id):
	_dialog = get_dialog(dialog_id)
	_choice = _dialog['choices'][_dialog['cursor_index']]
	
	_loop = False
	if _choice in _dialog['loop_choices']:
		_loop = True
	
	add_message(LIFE[SETTINGS['controlling']], _dialog['id'], _choice['gist'], _choice['text'], _choice['result'], loop=_loop)

def process_dialog_for_player(dialog_id, loop=False):
	_dialog = get_dialog(dialog_id)
	_dialog['choices'] = []
	_dialog['loop_choices'] = []
	_dialog['cursor_index'] = 0	
	_dialog['max_cursor_index'] = len(_dialog['choices'])
	_last_message = get_last_message(dialog_id)
	
	if loop:
		end_dialog(dialog_id)
		return False
	
	for response in get_matching_message(LIFE[SETTINGS['controlling']], dialog_id, _last_message['next_gist']):
		_to_check = [response]
		while _to_check:
			_response = _to_check.pop()
			
			if _response['text'].startswith('>'):
				_to_check.extend(get_matching_message(LIFE[SETTINGS['controlling']], dialog_id, _response['text'][1:]))
				_dialog['loop_choices'].extend(_to_check)
			else:
				_dialog['choices'].append(_response)

def process(life, dialog_id):
	if not is_turn_to_talk(life, dialog_id):
		return False
	
	_last_message = get_last_message(dialog_id)
	
	if _last_message['next_gist'] == 'end':
		end_dialog(dialog_id)
	elif 'player' in life:
		process_dialog_for_player(dialog_id, loop=_last_message['loop'])
	else:
		say_via_gist(life, dialog_id, _last_message['next_gist'], loop=_last_message['loop'])

def draw_dialog(dialog_id):
	_dialog = get_dialog(dialog_id)
	_last_message = get_last_message(dialog_id)
	_x = MAP_WINDOW_SIZE[0]/2-len(_last_message['text'])/2
	_y = 10
	_line_of_sight = drawing.diag_line(LIFE[_dialog['started_by']]['pos'], LIFE[_dialog['target']]['pos'])
	_center_pos = list(_line_of_sight[len(_line_of_sight)/2])
	_center_pos.append(2)
	_lines = []
	                                   
	gfx.camera_track(_center_pos)
	gfx.blit_string(_x, _y, _last_message['text'], 'overlay')
	
	for choice in _dialog['choices']:
		_text = choice['text']
		
		if _text.startswith('>'):
			_text = _text[1:]
		
		if _dialog['cursor_index'] == _dialog['choices'].index(choice):
			_text = '> '+_text
		
		_n_x = MAP_WINDOW_SIZE[0]/2-len(_text)/2
		
		if _n_x < _x:
			_x = _n_x
		
		_lines.append(_text.title())
	
	for line in _lines:
		gfx.blit_string(_x, _y+3, line, 'overlay')
		_y += 2
