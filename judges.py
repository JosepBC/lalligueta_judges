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


    def init_plugin(self, args):
        self.init_ui()
        self.get_pilot_video_systems()
        self.draw_judges_pannel()


    def get_pilot_video_systems(self, args=None):
        db = self._rhapi.db
        self._pilot_system = {}
        print("-----")
        pilot: Pilot
        for pilot in db.pilots:
            videosystem = db.pilot_attribute_value(pilot, "video_system")
            print(pilot.callsign+" uses video system " +videosystem)
            self._pilot_system[pilot.callsign] = videosystem
        print("-----")

        print(self._pilot_system)


    def init_ui(self):
        fields = self._rhapi.fields


        supported_video_systems = [UIFieldSelectOption("Analog", "Analog"), UIFieldSelectOption("DJI", "DJI"),
                                   UIFieldSelectOption("DJIO3", "DJI O3"), UIFieldSelectOption("Walksnail", "Walksnail"),
                                   UIFieldSelectOption("WalksnailRace", "Walksnail Race"), UIFieldSelectOption("HDZero", "HD Zero")]
        
        video_system_field = UIField('video_system', "Video System", UIFieldType.SELECT, options=supported_video_systems, value="Analog")
        fields.register_pilot_attribute(video_system_field)

    def getRaceChannels(self):
        frequencies = self._rhapi.race.frequencyset.frequencies
        freq = json.loads(frequencies)
        bands = freq["b"]
        channels = freq["c"]
        racechannels = []
        for i, band in enumerate(bands):
            racechannel = "0"
            if str(band) == 'None':
                racechannels.insert(i,racechannel)
            else:
                channel = channels[i]
                racechannel = str(band) + str(channel)
                racechannels.insert(i,racechannel)

        return racechannels

    def draw_judges_pannel(self, args=None):
        ui = self._rhapi.ui
        db = self._rhapi.db

        # Panel definition in format page, allways open
        ui.register_panel("judges", "Judges", "format", open=True)

        raceclass: RaceClass
        print("----------")
        # For each race class
        for raceclass in db.raceclasses:
            rc_name = raceclass.name
            print(rc_name)
            # Add section for that class
            ui.register_markdown("judges", "header_"+str(rc_name), "# "+str(rc_name))

            # Get all heats of that class
            heat: Heat
            for heat in db.heats_by_class(raceclass.id):
                print(heat.name)
                racechannels = self.getRaceChannels()


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
                        channel = racechannels[slot.node_index]
                        heat_pilots.append((pilot, channel))
                        heat_pilots_ids.append(pilot.id)

                pilot: Pilot
                for pilot, channel in heat_pilots:
                    # Get frequency of the pilot
                    freq_print = channel

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
                ui.register_markdown("judges", "heat_"+str(heat.id), heat_md)
        print("----------")
        ui.broadcast_ui("format")
