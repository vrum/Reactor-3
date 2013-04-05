from globals import *

import combat
import speech
import brain
import jobs

import logging

STATE = 'working'
ENTRY_SCORE = -1

def calculate_safety(life, alife_seen, alife_not_seen, targets_seen, targets_not_seen):
	return 0

def conditions(life, alife_seen, alife_not_seen, targets_seen, targets_not_seen, source_map):
	RETURN_VALUE = STATE_UNCHANGED

	if not life['job']:
		return False
	
	if not life['state'] == STATE:
		RETURN_VALUE = STATE_CHANGE

	return RETURN_VALUE

def tick(life, alife_seen, alife_not_seen, targets_seen, targets_not_seen, source_map):
	if life['task']['callback'](life):
		jobs.complete_task(life)
