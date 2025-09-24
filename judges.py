import RHData
import gevent
from enum import Enum
import json
import random
from eventmanager import Evt
from EventActions import ActionEffect
from RHUI import UIField, UIFieldType, UIFieldSelectOption
from Database import PilotAttribute, Pilot, RaceClass, Heat, HeatNode, Profiles, HeatStatus
from RHAPI import RHAPI

class HeatPilot():
    class AssignationMethod(Enum):
        DVR = 0
        SAME_SYSTEM = 1
        RANDOM = 2

    def __init__(self, pilot: Pilot, channel: str, judge: Pilot):
        self.pilot = pilot
        self.channel = channel
        self.judge = judge
        self.judge_assignment_method = HeatPilot.AssignationMethod.DVR
        self.changed_channel = False

class LaLliguetaJudges():

    class JudgeAssignationError(Enum):
        OUT_OF_CANDIDATES = 0
        NO_JUDGE_SAME_VIDEO_SYSTEM = 1


    def __init__(self, rhapi: RHAPI):
        self._rhapi = rhapi
        self._pilot_system = {}

        self._channel_correspondence = {"Walksnail":{"R1": "R1", "R2": "R2", "R4": "R4", "R7":"WR6", "R8": "WR7"},
                                       "DJI":{"R1": "P1", "R2": "P2", "R4": "P4", "R7":"P6", "R8": "P7"},
                                       "DJIO3":{"R1": "P1", "R2": "P2", "R4": "P3", "R7":"P6", "R8":"P7"}}

    def assign_random_judge_pilot(self, heat_pilots_id: list, potential_judges: list):
        db = self._rhapi.db

        all_possible_judges = []
        # Remove heat pilots from possible judges
        for p in potential_judges:
            if p.id not in heat_pilots_id:
                all_possible_judges.append(p)

        if len(all_possible_judges) == 0:
            return self.JudgeAssignationError.OUT_OF_CANDIDATES

        return random.choice(all_possible_judges)

    def assign_judge_pilot_same_system(self, pilot: Pilot, heat_pilots_id: list, potential_judges: list):
        db = self._rhapi.db

        all_possible_judges = []
        # Remove heat pilots from possible judges
        for p in potential_judges:
            if p.id not in heat_pilots_id:
                all_possible_judges.append(p)

        # If all pilots are in this heat there is no available judge
        if len(all_possible_judges) == 0:
            return self.JudgeAssignationError.OUT_OF_CANDIDATES

        # The elegible judges are those that have the same system as the pilot
        elegible_judges = []

        # Filter the possible judges by the same system. Those will be elegible judges for this pilot
        possible_judge: Pilot
        for possible_judge in all_possible_judges:
            # If the possible judge has the same system as the pilot, it's an elegible judge
            if self._pilot_system[possible_judge.callsign] == self._pilot_system[pilot.callsign]:
                elegible_judges.append(possible_judge)

        # If we have more than one elegibe judge, randomly select one of them to avoid repeating judges
        if len(elegible_judges) > 0:
            return random.choice(elegible_judges)

        return self.JudgeAssignationError.NO_JUDGE_SAME_VIDEO_SYSTEM


    def find_judge_same_system(self, heat_pilots: list, heat_pilots_ids: list, potential_judges: list):
        heat_pilot: HeatPilot
        for heat_pilot in heat_pilots:
            # Try to assign someone with same video system
            judge_pilot = self.assign_judge_pilot_same_system(heat_pilot.pilot, heat_pilots_ids, potential_judges)

            if judge_pilot == self.JudgeAssignationError.NO_JUDGE_SAME_VIDEO_SYSTEM:
                print("No judge same video system for "+heat_pilot.pilot.callsign+", will try later")
            elif judge_pilot == self.JudgeAssignationError.OUT_OF_CANDIDATES:
                # If we are out of candidates just ask for DVR
                heat_pilot.judge = Pilot()
                heat_pilot.judge.callsign = "DVR"
                heat_pilot.judge_assignment_method = HeatPilot.AssignationMethod.DVR
            else:
                # Otherwise means that we have found a judge with the same video system
                heat_pilots_ids.append(judge_pilot.id)
                heat_pilot.judge = judge_pilot
                heat_pilot.judge_assignment_method = HeatPilot.AssignationMethod.SAME_SYSTEM

    def find_random_judge(self, heat_pilots: list, heat_pilots_ids: list, potential_judges: list):
        heat_pilot: HeatPilot
        for heat_pilot in heat_pilots:
            # If we have already assigned a judge to this pilot, skip
            if heat_pilot.judge is not None:
                continue

            # Otherwise randomly select another pilot in 3d person
            judge_pilot = self.assign_random_judge_pilot(heat_pilots_ids, potential_judges)

            if judge_pilot == self.JudgeAssignationError.OUT_OF_CANDIDATES:
                # If there are no more pilots available, ask for DVR
                heat_pilot.judge = Pilot()
                heat_pilot.judge.callsign = "DVR"
                heat_pilot.judge_assignment_method = HeatPilot.AssignationMethod.DVR
                print("We run out of judges in random, DVR for "+heat_pilot.pilot.callsign)
            else:
                # Judge randomly assigned
                heat_pilots_ids.append(judge_pilot.id)
                heat_pilot.judge = judge_pilot
                heat_pilot.judge_assignment_method = HeatPilot.AssignationMethod.RANDOM
                print("No judge same video system for "+heat_pilot.pilot.callsign+", but found "+ heat_pilot.judge.callsign)

    def draw_table(self, heat_pilots):
        table_md = []
        # By now everyone should have a judge, draw it
        heat_pilot: HeatPilot
        for heat_pilot in heat_pilots:
            # Get video system of the pilot
            pilot_video_system = self._pilot_system[heat_pilot.pilot.callsign]
            pilot = heat_pilot.pilot
            judge = heat_pilot.judge
            # If video system is in the correspondence change the freq print to match system
            channel_display = heat_pilot.channel
            if pilot_video_system in self._channel_correspondence:
                if heat_pilot.channel in self._channel_correspondence[pilot_video_system]:
                    # print("Pilot "+pilot.callsign+" raceband channel "+heat_pilot.channel+" may not correspond to it's system " +pilot_video_system)
                    channel_display = self._channel_correspondence[pilot_video_system][heat_pilot.channel]

            # Add * if pilot has changed channel from it's previous heat
            if heat_pilot.changed_channel:
                channel_display += "*"


            judge_display = judge.callsign
            # If judge was randomly selected add the (3rd)
            if heat_pilot.judge_assignment_method == HeatPilot.AssignationMethod.RANDOM:
                judge_display = judge.callsign+" (3rd)"

            table_md.append("<tr><td>"+channel_display+"</td><td>"+pilot.callsign+"</td><td>"+judge_display+"</td><td>"+pilot_video_system+"</td>\n")
        return table_md

    def get_heat_pilots_and_ids(self, heat: Heat, racechannels: list):
        db = self._rhapi.db

        heat_pilots = []
        heat_pilots_ids = []

        slot: HeatNode
        for slot in db.slots_by_heat(heat.id):
            pilot_slot: Pilot
            pilot_slot = db.pilot_by_id(slot.pilot_id)
            if pilot_slot is not None:
                channel = racechannels[slot.node_index]
                heat_pilot = HeatPilot(pilot_slot, channel, None)
                heat_pilots.append(heat_pilot)
                heat_pilots_ids.append(pilot_slot.id)

        return heat_pilots, heat_pilots_ids

    def get_pilots_involved_in_raceclass(self, rc: RaceClass):
        db = self._rhapi.db

        pilots_raceclass = []

        heat: Heat
        # For each heat in the raceclass
        for heat in db.heats_by_class(rc.id):
            # For each slot in the heat, get pilot
            slot: HeatNode
            for slot in db.slots_by_heat(heat.id):
                pilot_slot = db.pilot_by_id(slot.pilot_id)
                if pilot_slot is not None:
                    pilots_raceclass.append(pilot_slot)

        return pilots_raceclass


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
                                   UIFieldSelectOption("DJIO3", "DJI O3"), UIFieldSelectOption("DJIO4Race", "DJI O4 Race"),
                                   UIFieldSelectOption("Walksnail", "Walksnail"), UIFieldSelectOption("WalksnailRace", "Walksnail Race"),
                                   UIFieldSelectOption("HDZero", "HD Zero")]
        
        video_system_field = UIField('video_system', "Video System", UIFieldType.SELECT, options=supported_video_systems, value=supported_video_systems[0].value)
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
        ui.register_panel("judges", "Judges", "format")

        prev_pilot_channel = {}
        raceclass: RaceClass
        print("----------")
        # For each race class
        for raceclass in db.raceclasses:
            rc_name = raceclass.name
            print(rc_name)
            # Get all the pilots involved in this raceclass. They are the only ones that will be used as potential judges for this raceclass
            pilots_raceclass = self.get_pilots_involved_in_raceclass(raceclass)

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
                

                # Get heat pilots and it's id
                heat_pilots, heat_pilots_ids = self.get_heat_pilots_and_ids(heat, racechannels)

                # For heats with auto frequency and not confirmed we don't know the frequency
                if heat.auto_frequency and heat.status != HeatStatus.CONFIRMED:
                    heat_pilot: HeatPilot
                    for heat_pilot in heat_pilots:
                        heat_pilot.channel = "NC"
                        heat_pilot.judge = Pilot()
                        heat_pilot.judge.callsign = "NC"
                else:
                    # First try to assign with same video system
                    self.find_judge_same_system(heat_pilots, heat_pilots_ids, pilots_raceclass)

                    # If we couldn't find someone with same video system and we had candidates, randomly select someone
                    self.find_random_judge(heat_pilots, heat_pilots_ids, pilots_raceclass)

                    heat_pilot: HeatPilot
                    for heat_pilot in heat_pilots:
                        # If pilot is in the list, check if it's changed channel
                        if heat_pilot.pilot.callsign in prev_pilot_channel and prev_pilot_channel[heat_pilot.pilot.callsign] != heat_pilot.channel:
                            heat_pilot.changed_channel = True
                            print(heat_pilot.pilot.callsign+" has to change channel!")

                        # Update the previous channel
                        prev_pilot_channel[heat_pilot.pilot.callsign] = heat_pilot.channel
                    

                # Finally draw the table for this heat
                for line in self.draw_table(heat_pilots):
                    heat_md += line

                print("++++++++++++")
                # Close table
                heat_md += "</table>\n"
        
                # Add table as markdown
                ui.register_markdown("judges", "heat_"+str(heat.id), heat_md)
        print("----------")
        ui.broadcast_ui("format")
