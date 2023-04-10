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

		is_json = False
		try:
			# Old approach was compressed json
			self.__data = json.loads(json_str)
			is_json = True
			self.__fix_types(self.__data)
		except Exception as e:
			pass

		if not is_json:
			self.__unpack_modern_v1_0(filename)
			self.__fix_types(self.__data)
		elif self.__data["version"] == "1.2":
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

	def __unpack_modern_v1_0(self, filename):
		data = open(filename, "rb").read()
		# Starts off with "RFR1" then has number of entries in table.
		num_entries_in_table = int.from_bytes(data[4:5], "little")
		# Flag, like ("META", "MAPI", "FDAT", "VIDM", or "VIDE") to (offset, size) tuple.
		flag_to_bytes_offset = {}
		self.__data = {}
		for i in range(num_entries_in_table):
			start = 5 + (i * 12)
			flag = data[start : start + 4].decode("utf-8")
			offset = int.from_bytes(data[start + 4 : start + 8], "little")
			size = int.from_bytes(data[start + 8 : start + 12], "little")
			flag_to_bytes_offset[flag] = (offset, size)

		# TODO: "VIDE"
		for (flag, key) in [("MAPI", 'mappinginfo'), ("META", None), ("VIDM", 'videoinfo')]:
			# This is a typical json.
			offset, size = flag_to_bytes_offset[flag]
			json_bytes = data[offset : offset + size]
			if key:
				self.__data[key] = json.loads(json_bytes)
			else:
				self.__data.update(json.loads(json_bytes))

		# Frame Data
		if "FDAT" in flag_to_bytes_offset:
			# This is a typical json.
			offset, size = flag_to_bytes_offset["FDAT"]
			frame_data_bytes = data[offset : offset + size]

			# major_version = int.from_bytes(frame_data_bytes[0:1], "little")
			# minor_version = int.from_bytes(frame_data_bytes[1:2], "little")
			# uncompressed_size = int.from_bytes(frame_data_bytes[2:6], "little")

			# The data was compressed using zlib. Now decompress it.
			decompressed_frame_data_bytes = zlib.decompress(frame_data_bytes[6:])

			num_frames = int.from_bytes(decompressed_frame_data_bytes[0:4], "little")
			num_players = int.from_bytes(decompressed_frame_data_bytes[4:5], "little")

			offset = 5

			self.__data['playerstates'] = {}
			for p in range(num_players):
				if p not in self.__data['playerstates']:
					self.__data['playerstates'][p] = []

				# < = little endian
				# I = unsigned int
				for i in range(num_frames):
					(
						timestamp,
						frames_left,
						posx,
						posy,
						damage,
						hitstun,
						shield,
						status,
						motion_l,
						motion_h,
						hit_status,
						stocks,
						flags,
					) = struct.unpack_from(
						"<QIfffffHIBBBB", decompressed_frame_data_bytes, offset
					)
					offset += 42
					motion = (motion_h << 32) | motion_l
					self.__data['playerstates'][p].append(
						dict(
							frame_time_stamp=timestamp,
							# Hmm
							frame=i,
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
							facing_direction=True if flags & 0x02 else False,
						)
					)


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
	
