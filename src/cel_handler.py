import sys, os
from PIL import Image


def to_uint( bytes ): return int.from_bytes(bytes, sys.byteorder, signed=False)


def open_file( path ):
    return open(path, 'rb')


def get_cel_offsets_array( file ):
    file.seek(0)
    num_frames = to_uint(file.read(4))
    array = []
    for index in range(num_frames + 1):
        array.append(to_uint(file.read(4)))
    file.seek(0)
    return array


def extract_frame(file, offsets, index):
	if index >= len(offsets) - 1:
		raise Exception('Invalid frame index.')

	file.seek(offsets[index])
	return file.read(offsets[index + 1] - offsets[index])


def compute_frame_width(frame):
	# Since cel encode one line at a time its kinda easy to compute a frame width

	# Skip frame header if it exists
	index = 0 if frame[0] > 0x10 else 10

	width = 0
	while True:
		command = frame[index]
		index += 1
		if command <= 0x7f:
			# Regular command
			width += command
			if command < 0x7f:
				break
			index += command
		else:
			# Transparency command
			width += 0x100 - command
			if (0x100 - command) < 0x80:
				break
	
	return width


def describe_commands(frame):
	# Skip frame header if it exists
	index = 0 if frame[0] > 0x10 else 10

	while index < len(frame):
		command = frame[index]
		index += 1
		if command <= 0x7f: 
			# A regular command: read the next 'command' bytes as-is
			print("Regular command. Read the next ", command, " bytes.")
			index += command

		else: 
			# A transparency command: next (0x100 - command) pixels are transparent
			print("Transparency command. Next ", 0x100 - command, " pixels are transparent.")



def decompress_frame(frame):
	buffer = []

	# Skip frame header if it exists
	index = 0 if frame[0] > 0x10 else 10

	while(index < len(frame)):
		command = frame[index]
		index += 1
		if(command <= 0x7f): 
			# A regular command: read the next 'command' bytes as-is
			for i in range(command):
				buffer.append(frame[index])
				index += 1
		else: 
			# A transparency command: next (0x100 - command) pixels are transparent
			for i in range(0x100 - command):
				buffer.append(0xff)

	return buffer


def render_bitmap(buffer, width, name = "output.bmp"):
	height = int(len(buffer)/width)
	print(width, height)

	bmp = Image.new("P", (width, height))

	from palette_2 import palette

	for y in range(height):
		for x in range(width):
			pltt_i = buffer[y*width + x] * 3
			bmp.putpixel((x, y), (palette[pltt_i], palette[pltt_i + 1], palette[pltt_i + 2]))

	bmp.save(name)


def load_bitmap():
    return Image.load()
    pass


file_data = open_file("axe.cel")
offsets   = get_cel_offsets_array(file_data)
print(offsets)
frame     = extract_frame(file_data, offsets, 0)
buffer    = decompress_frame(frame)
width     = compute_frame_width(frame)
render_bitmap(buffer, width)