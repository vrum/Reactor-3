#This is intended to be an example of how the new ALife
#system works.
from globals import *

import life as lfe

import judgement
import movement
import combat

import logging

STATE = 'hidden'
INITIAL_STATE = 'hiding'
EXIT_SCORE = -75

def calculate_safety(life, alife_seen, alife_not_seen, targets_seen, targets_not_seen):
	_score = 0
	
	for entry in targets_not_seen:
		if judgement.is_target_dangerous(life, entry['who']['life']['id']):
			_score += entry['danger']
	
	return _score

def conditions(life, alife_seen, alife_not_seen, targets_seen, targets_not_seen, source_map):
	RETURN_VALUE = STATE_UNCHANGED

	if judgement.is_safe(life):
		return False
	
	if judgement.get_visible_threats(life):
		return False
	
	if life['state'] in ['combat']:
		return False	
	
	if not life['state'] == STATE:
		RETURN_VALUE = STATE_CHANGE
	
	return RETURN_VALUE

def tick(life, alife_seen, alife_not_seen, targets_seen, targets_not_seen, source_map):
	_weapon = combat.get_best_weapon(life)
	
	if _weapon:
		if not combat.weapon_equipped_and_ready(life):
			if _weapon:
				combat._equip_weapon(life, _weapon['weapon'], _weapon['feed'])
