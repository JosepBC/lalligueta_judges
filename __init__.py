import RHData
import gevent
import json
import random
from eventmanager import Evt
from EventActions import ActionEffect
from RHUI import UIField, UIFieldType, UIFieldSelectOption
from Database import PilotAttribute, Pilot, RaceClass, Heat, HeatNode, Profiles, HeatStatus
from RHAPI import RHAPI


class LaLliguetaJudges():
    def __init__(self, rhapi: RHAPI):
        self._rhapi = rhapi
        self._pilot_system = {}

    def assign_judge_pilot(self, pilot: Pilot, heat_pilots_id: list):
        judge = None
        randomly_selected = False
        db = self._rhapi.db

        all_possible_judges = []
        # Remove heat pilots from possible judges
        for p in db.pilots:
            if p.id not in heat_pilots_id:
                all_possible_judges.append(p)

        # If all pilots are in this heat there is no available judge
        if len(all_possible_judges) == 0:
            return None, False

        # Try to assign as judge a pilot with the same video system
        possible_judge: Pilot
        for possible_judge in all_possible_judges:
            if self._pilot_system[possible_judge.callsign] == self._pilot_system[pilot.callsign]:
                judge = possible_judge
                break
        
        # If no possible judge with the same video system, randomly select a pilot
        if judge is None:
            judge = random.choice(all_possible_judges)
            randomly_selected = True
            print("No judge with same video system for "+pilot.callsign)

        return judge, randomly_selected


    def register_handlers(self, args):
        fields = self._rhapi.fields
        ui = self._rhapi.ui
        db = self._rhapi.db

        supported_video_systems = [UIFieldSelectOption("Analog", "Analog"), UIFieldSelectOption("DJI", "DJI"),
                                   UIFieldSelectOption("DJIO3", "DJI O3"), UIFieldSelectOption("Walksnail", "Walksnail"),
                                   UIFieldSelectOption("WalksnailRace", "Walksnail Race"), UIFieldSelectOption("HDZero", "HD Zero")]
        
        video_system_field = UIField('video_system', "Video System", UIFieldType.SELECT, options=supported_video_systems, value=supported_video_systems[0].value)
        fields.register_pilot_attribute(video_system_field)
        
        print("----------")
        for pilot in self._rhapi.db.pilots:
            for atribute in self._rhapi.db.pilot_attributes(pilot):
                if atribute.name == "video_system":
                    print(pilot.callsign+" uses video system " +atribute.value)
                    self._pilot_system[pilot.callsign] = atribute.value
        print("----------")

        # Panel definition in format page, allways open
        ui.register_panel("testing", "Pilots With Video", "format", open=True)

        frequencies = json.loads(db.frequencysets[0].frequencies)
        num_frequencies = 0
        for band in frequencies["b"]:
            if band is not None:
                num_frequencies += 1


        raceclass: RaceClass
        print("----------")
        # For each race class
        for raceclass in db.raceclasses:
            rc_name = raceclass.name
            # Add section for that class
            ui.register_markdown("testing", "header_"+str(rc_name), "# "+str(rc_name))

            # Get all heats of that class
            heat: Heat
            for heat in db.heats_by_class(raceclass.id):
                freq_i = 0

                # Header of the heat
                heat_md = "## "+str(heat.name)+"\n"
                for e in ["<table>", "<tr>", "<th>Channel</th>", "<th>Pilot</th>", "<th>Judge</th>", "<th>Video System</th>", "</tr>"]:
                    heat_md += e+"\n"
                

                # Get all slots of the heat
                slot: HeatNode
                heat_pilots = []
                heat_pilots_ids = []
                for slot in db.slots_by_heat(heat.id):
                    pilot = db.pilot_by_id(slot.pilot_id)
                    if pilot is not None:
                        heat_pilots.append(pilot)
                        heat_pilots_ids.append(pilot.id)

                pilot: Pilot
                for pilot in heat_pilots:
                    # Get frequency of the pilot
                    freq_print = str(frequencies["b"][freq_i])+str(frequencies["c"][freq_i])
                    freq_i+=1
                    freq_i%num_frequencies

                    # For heats with auto frequency and not confirmed we don't know the frequency
                    if heat.auto_frequency and heat.status != HeatStatus.CONFIRMED:
                        freq_print = "NC"

                    # print(freq_print + " " + pilot.callsign)
                    judge_pilot, randomly_selected = self.assign_judge_pilot(pilot, heat_pilots_ids)
                    

                    if judge_pilot is not None:
                        judge = judge_pilot.callsign
                        # Add as heat pilot the judge
                        heat_pilots_ids.append(judge_pilot.id)
                    else:
                        judge = "DVR"

                    # If it has been randomly selected it means that needs to be in 3rd Person
                    if randomly_selected:
                        judge += " (3rd)"
                    heat_md += "<tr><td>"+freq_print+"</td><td>"+pilot.callsign+"</td><td>"+judge+"</td><td>"+self._pilot_system[pilot.callsign]+"</td>\n"
                print("++++++++++++")
                # Close table
                heat_md += "</table>\n"
        
                # Add table as markdown
                ui.register_markdown("testing", "heat_"+str(heat.id), heat_md)
        print("----------")



def initialize(rhapi):
    lalligueta = LaLliguetaJudges(rhapi)
    rhapi.events.on(Evt.ACTIONS_INITIALIZE, lalligueta.register_handlers)
