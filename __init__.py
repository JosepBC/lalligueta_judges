import RHData
import gevent
import json
import random
from eventmanager import Evt
from EventActions import ActionEffect
from RHUI import UIField, UIFieldType, UIFieldSelectOption
from Database import PilotAttribute, Pilot, RaceClass, Heat, HeatNode, Profiles, HeatStatus
from RHAPI import RHAPI
from .judges import LaLliguetaJudges



def initialize(rhapi: RHAPI):
    lalligueta = LaLliguetaJudges(rhapi)
    rhapi.events.on(Evt.STARTUP, lalligueta.init_plugin)
    
    rhapi.events.on(Evt.PILOT_ADD, lalligueta.get_pilot_video_systems)
    rhapi.events.on(Evt.PILOT_ALTER, lalligueta.get_pilot_video_systems)
    rhapi.events.on(Evt.PILOT_DELETE, lalligueta.get_pilot_video_systems)
    
    rhapi.events.on(Evt.CLASS_ADD, lalligueta.draw_judges_pannel)
    rhapi.events.on(Evt.CLASS_ALTER, lalligueta.draw_judges_pannel)
    rhapi.events.on(Evt.CLASS_DUPLICATE, lalligueta.draw_judges_pannel)
    rhapi.events.on(Evt.CLASS_DELETE, lalligueta.draw_judges_pannel)

    rhapi.events.on(Evt.HEAT_ADD, lalligueta.draw_judges_pannel)
    rhapi.events.on(Evt.HEAT_ALTER, lalligueta.draw_judges_pannel)
    rhapi.events.on(Evt.HEAT_DUPLICATE, lalligueta.draw_judges_pannel)
    rhapi.events.on(Evt.HEAT_DELETE, lalligueta.draw_judges_pannel)




