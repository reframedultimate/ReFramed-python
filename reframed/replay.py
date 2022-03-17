import zlib
import gzip
import json
import struct
import base64


class Replay:
	def __init__(self, filename):
		json_str = None
		for method in (self.__decompress_gz, self.__decompress_qt, self.__read_uncompressed):
			try:
				json_str = method(filename)
				break
			except Exception as e:
				print(e)

		self.__data = json.loads(json_str)
		self.__fix_types(self.__data)

		if self.__data["version"] == "1.2":
			self.__unpack_states_v1_2()
		elif self.__data["version"] == "1.3":
			self.__unpack_states_v1_3()
		elif self.__data["version"] == "1.4":
			self.__unpack_states_v1_4()
		else:
			raise RuntimeError(f"Unsupported version {self.__data['version']}")

	@staticmethod
	def __decompress_gz(filename):
		blob = open(filename, "rb").read()
		if blob[0] != 0x1f or blob[1] != 0x8b:
			raise RuntimeError("Not a gz compressed file")

		return gzip.decompress(blob).decode("utf-8")

	@staticmethod
	def __decompress_qt(filename):
		blob = open(filename, "rb").read()

		# Qt prepends 4 bytes describing the length, have to remove those first
		return zlib.decompress(blob[4:]).decode("utf-8")

	@staticmethod
	def __read_uncompressed(blob):
		return blob

	def __fix_types(self, data):
		# Have to convert keys back into integers
		data["mappinginfo"]["fighterid"] = {int(k): v for k, v in data["mappinginfo"]["fighterid"].items()}
		data["mappinginfo"]["fighterstatus"]["base"] = {int(k): v for k, v in data["mappinginfo"]["fighterstatus"]["base"].items()}
		data["mappinginfo"]["fighterstatus"]["specific"] = {int(k): v for k, v in data["mappinginfo"]["fighterstatus"]["specific"].items()}
		data["mappinginfo"]["hitstatus"] = {int(k): v for k, v in data["mappinginfo"]["hitstatus"].items()}
		data["mappinginfo"]["stageid"] = {int(k): v for k, v in data["mappinginfo"]["stageid"].items()}
		
	def __unpack_states_v1_2(self):
		# Playerstates are written to a buffer, which is then stored as a base64 encoded
		# string inside the json. Convert the buffer into a structure and replace that node
		# in the json with it
		data = base64.urlsafe_b64decode(self.__data["playerstates"] + "==")
		self.__data["playerstates"] = tuple(list() for p in range(self.player_count()))
		offset = 0
		for p in range(self.player_count()):
			state_count = struct.unpack_from("!I", data, offset)[0]
			offset += 4
			for i in range(state_count):
				state = struct.unpack_from("!IdddddHQBBB", data, offset)
				offset += 57
				self.__data["playerstates"][p].append(dict(
					frame=state[0],
					posx=state[1],
					posy=state[2],
					damage=state[3],
					hitstun=state[4],
					shield=state[5],
					status=state[6],
					motion=state[7],
					hit_status=state[8],
					stocks=state[9],
					attack_connected=True if state[10] & 0x01 else False,
					facing_direction=True if state[10] & 0x02 else False
				))

	def __unpack_states_v1_3(self):
		# Playerstates are written to a buffer, which is then stored as a base64 encoded
		# string inside the json. Convert the buffer into a structure and replace that node
		# in the json with it
		data = base64.urlsafe_b64decode(self.__data["playerstates"] + "==")
		self.__data["playerstates"] = tuple(list() for p in range(self.player_count()))
		offset = 0
		for p in range(self.player_count()):
			state_count = struct.unpack_from("<I", data, offset)[0]
			offset += 4
			for i in range(state_count):
				frame, posx, posy, damage, hitstun, shield, status, motion_l, motion_h, hit_status, stocks, flags = struct.unpack_from("<IfffffHIBBBB", data, offset)
				offset += 34
				motion = (motion_h << 32) | motion_l
				self.__data["playerstates"][p].append(dict(
					frame=frame,
					posx=posx,
					posy=posy,
					damage=damage,
					hitstun=hitstun,
					shield=shield,
					status=status,
					motion=motion,
					hit_status=hit_status,
					stocks=stocks,
					attack_connected=True if flags & 0x01 else False,
					facing_direction=True if flags & 0x02 else False
				))

	def __unpack_states_v1_4(self):
		# Playerstates are written to a buffer, which is then stored as a base64 encoded
		# string inside the json. Convert the buffer into a structure and replace that node
		# in the json with it
		data = base64.urlsafe_b64decode(self.__data["playerstates"] + "==")
		self.__data["playerstates"] = tuple(list() for p in range(self.player_count()))
		offset = 0
		for p in range(self.player_count()):
			state_count = struct.unpack_from("<I", data, offset)[0]
			offset += 4
			for i in range(state_count):
				frame_time_stamp_l, frame_time_stamp_h, frame, posx, posy, damage, hitstun, shield, status, motion_l, motion_h, hit_status, stocks, flags = struct.unpack_from("<IIIfffffHIBBBB", data, offset)
				offset += 42
				frame_time_stamp = (frame_time_stamp_h << 32) | frame_time_stamp_l
				motion = (motion_h << 32) | motion_l
				self.__data["playerstates"][p].append(dict(
					frame_time_stamp = frame_time_stamp,
					frame=frame,
					posx=posx,
					posy=posy,
					damage=damage,
					hitstun=hitstun,
					shield=shield,
					status=status,
					motion=motion,
					hit_status=hit_status,
					stocks=stocks,
					attack_connected=True if flags & 0x01 else False,
					facing_direction=True if flags & 0x02 else False
				))
		
	def __getitem__(self, key):
		return self.__data[key]
		
	def player_count(self):
		return len(self.__data["playerinfo"])
	
	def fighter_name(self, fighter_id):
		return self.__data["mappinginfo"]["fighterid"][str(fighter_id)]
	
	def stage_name(self, stage_id):
		return self.__data["mappinginfo"]["stageid"][str(stage_id)]
		
	def status_name(self, status_id, player_index=None):
		try:
			return self.__data["mappinginfo"]["fighterstatus"]["base"][str(status_id)][0]
		except KeyError:
			if player_index is None:
				raise

			fighter_id = str(self.__data["playerinfo"][player_index]["fighterid"])
			return self.__data["mappinginfo"]["fighterstatus"]["specific"][fighter_id][str(status_id)][0]

	def find_status(self, name, player_index=None):
		for statusid, statusnames in self.__data["mappinginfo"]["fighterstatus"]["base"].items():
			if statusnames[0] == name:
				return statusid

		if player_index is None:
			return None

		fighter_id = str(self.__data["playerinfo"][player_index]["fighterid"])
		for statusid, statusnames in self.__data["mappinginfo"]["fighterstatus"]["specific"][fighter_id].items():
			if statusnames[0] == name:
				return statusid

		return None


if __name__ == "__main__":
	rfr = Replay("2021-10-30 - Friendlies - Player 1 (Lucina) vs Player 2 (Pikachu) Game 2.rfr")
	
	stage = rfr.stage_name(rfr["gameinfo"]["stageid"])
	
	print(f"version: {rfr['version']}")
	print(f"date: {rfr['gameinfo']['date']}")
	print(f"format: {rfr['gameinfo']['format']}")
	print(f"set number: {rfr['gameinfo']['set']}")
	print(f"game number: {rfr['gameinfo']['number']}")
	print(f"Stage: {stage}")
	print("Players:")
	for i, player in enumerate(rfr["playerinfo"]):
		name = player["name"]
		fighter = rfr.fighter_name(player["fighterid"])
		state_count = len(rfr["playerstates"][i])
		print(f"  {name} ({fighter}) has {state_count} states")

	for player_index, states in enumerate(rfr['playerstates']):
		for state in states:
			pass
			# Do stuff with state["posx"] or state["status"] or state["damage"] etc.
			
			# This will print every status name
			#print(rfr.status_name(player_index, state["status"]))
	
