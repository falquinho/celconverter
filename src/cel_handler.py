import sys, os
from PIL import Image


def to_uint( bytes ): return int.from_bytes(bytes, sys.byteorder, signed=False)


def open_cel( path ):
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
	# Note: cels are stored bottom-up
	
	height = int(len(buffer)/width)

	bmp = Image.new("P", (width, height))

	from palette_2 import palette

	for y in range(height):
		for x in range(width):
			pltt_i = buffer[y*width + x] * 3
			bmp.putpixel((x, height - y - 1), (palette[pltt_i], palette[pltt_i + 1], palette[pltt_i + 2]))

	bmp.save(name)


def get_file_extension(file_path):
	return file_path[-3:]


def load_bitmap(path):
    return Image.open(path)


def compress_bmp_row_block(block):
	compressed_row = []

	max_len = 0x80 if block[0] == 0xff else 0x7f

	while len(block) >= max_len:
		if max_len == 128:
			compressed_row.append(0x80)
		else:
			compressed_row.append(0x7f)
			compressed_row.extend(block[:max_len])

		block = block[max_len:]

	if max_len == 128:
		compressed_row.append(0x100 - len(block))
	else:
		compressed_row.append(len(block))
		compressed_row.extend(block)

	return compressed_row


def compress_bmp_row(row):
	compressed_row = []
	while len(row):
		slice_len = 1
		for i in range(1, len(row)):
			if row[slice_len] == 0xff and row[slice_len-1] != 0xff:
				break
			if row[slice_len] != 0xff and row[slice_len-1] == 0xff:
				break
			slice_len += 1

		block = row[:slice_len]
		row   = row[slice_len:]
		compressed_row.extend(compress_bmp_row_block(block))
		pass
	return compressed_row


def bmp_to_cel_frame(img):
	frame = []
	
	# Remember: cels are stored bottom-up
	for y in range(img.height - 1 , -1, -1):
		cel_row  = []
		for x in range(img.width):
			cel_row.append( img.getpixel((x, y)) )
		frame.extend( compress_bmp_row(cel_row) )

	return bytes(frame)


def bmp_frames_to_cel(frame_list):
	cel = bytearray()
	header_size = (len(frame_list) + 2) * 4 # in bytes. Times 4 bc its a uint32 for each  
	cel.extend(bytes(header_size)) # allocate the header space

	# Set the num of frames in the header(note: little endian):
	for i in range(4):
		cel[i] = (len(frame_list) >> 8*i) & 0xff

	# For each frame set its pos in the header and append its bytes in the cel  
	for index, frame in enumerate(frame_list):
		for j in range(4):
			cel[4*(index+1) + j] = (len(cel) >> 8*j) & 0xff
		cel.extend(frame)
	
	# Finalize by setting the last header uint32 as the cel size
	for i in range(4):
		cel[4*(len(frame_list) + 1) + i] = (len(cel) >> 8*i) & 0xff

	return cel


###################### START ######################

if len(sys.argv) <= 1:
	print("Too few arguments. Requires at least one file path.")
	exit

cels = []
bmps = []
for f_path in sys.argv[1:]:
	extension = get_file_extension(f_path).lower()
	if extension == "cel":
		cels.append(f_path)
	elif extension == "bmp":
		bmps.append(f_path)
	else:
		print("Invalid file type: ", extension)
	
print(cels, bmps)

for cel_path in cels:
	cel = open_cel(cel_path)
	offsets = get_cel_offsets_array(cel)
	for index in range(len(offsets) - 1):
		frame = extract_frame(cel, offsets, index)
		width = compute_frame_width(frame)
		decompressed = decompress_frame(frame)
		output_name  = cel_path.split('/')[-1] + ".frame" + str(index) + ".bmp"
		render_bitmap(decompressed, width, output_name)

if not len(bmps):
	exit

frames = []
for bmp_path in bmps:
	img = Image.open(bmp_path)
	frames.append(bmp_to_cel_frame(img))
	
new_file = open("output.cel", "wb")

cel = bmp_frames_to_cel(frames)

new_file.write(cel)
new_file.close()