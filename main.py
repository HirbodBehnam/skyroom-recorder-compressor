import tkinter
from tkinter import Tk, ttk
from tkinter import filedialog as fd
import re
import ffmpeg
import threading
import subprocess

MAX_FRAME_RATE = 10
MAX_HEIGHT = 720
MAX_AUDIO_BITRATE = 32


class ToChangeParams:
    def __init__(self, frame_rate: bool, resolution: bool, v_codec: bool, a_codec: bool, total_seconds: int):
        self.frame_rate = frame_rate
        self.resolution = resolution
        self.v_codec = v_codec
        self.a_codec = a_codec
        self.total_seconds = total_seconds

    def __str__(self):
        return f"fps: {self.frame_rate} - res: {self.resolution} - v_codec: {self.v_codec} - a_codec: {self.a_codec}"

    def generate_parameters(self) -> list:
        result = ['-y']  # overwrite
        # Check framerate
        if self.frame_rate:
            result.extend(['-r', str(MAX_FRAME_RATE)])
        # Check format and resolution
        if self.resolution:
            result.extend(['-vf', 'scale=-2:' + str(MAX_HEIGHT), '-c:v', 'libx265', '-crf', '28'])
        elif self.v_codec:
            result.extend(['-c:v', 'libx265', '-crf', '28'])
        else:
            result.extend(['-vcodec', 'copy'])
        # Check audio
        if self.a_codec:
            result.extend(['-c:a', 'libopus', '-b:a', str(MAX_AUDIO_BITRATE) + 'K'])
        else:
            result.extend(['-acodec', 'copy'])
        # Append other flags
        result.extend(['-strict', 'experimental', '-progress', '-', '-nostats'])
        return result


def time_to_seconds(string_time: str, prefix: str) -> int:
    length = re.findall(prefix + '([0-9]{2}:[0-9]{2}:[0-9]{2})', string_time)[-1].split(':')
    return int(length[0]) * 3600 + int(length[1]) * 60 + int(length[2])


def format_seconds(seconds: int) -> str:
    sec = seconds % 60
    minute = (seconds // 60) % 60
    hour = seconds // 3600
    return f"{hour:02}:{minute:02}:{sec:02}"


def sizeof_fmt(num, suffix="B") -> str:
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Yi{suffix}"


def select_input():
    filetypes = (
        ('WebM', '*.webm'),
        ('All files', '*.*')
    )
    filename = fd.askopenfilename(
        title='Open input',
        filetypes=filetypes)
    if filename == "":
        return  # Do nothing
    # Select output
    filetypes = [("mp4", '*.mp4')]
    out_name = fd.asksaveasfilename(
        title='Save',
        filetypes=filetypes
    )
    if not out_name.endswith('.mp4'):
        out_name += '.mp4'
    convert_file(filename, out_name)


def convert_file(input_file: str, output_file: str):
    to_change = analyze_file(input_file)
    command = ['ffmpeg', '-i', input_file]
    command.extend(to_change.generate_parameters())
    command.append(output_file)
    print('detected configs:', to_change)
    threading.Thread(target=final_convert_spawn, args=(command, to_change.total_seconds)).start()


def analyze_file(input_file: str) -> ToChangeParams:
    probe = ffmpeg.probe(input_file)
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
    framerate = float(eval(video_stream['r_frame_rate']))
    height = int(video_stream['height'])
    video_codec = str(video_stream['codec_name'])
    needs_audio_encode = False
    running_time = 0
    if audio_stream is not None:
        audio_bitrate, running_time = get_audio_bitrate_and_running_time(input_file)
        needs_audio_encode = audio_bitrate > MAX_AUDIO_BITRATE + 5  # Small offset
    return ToChangeParams(
        framerate >= MAX_FRAME_RATE + 1,
        height > MAX_HEIGHT + 20,
        video_codec != "hevc",
        needs_audio_encode,
        running_time)


def get_audio_bitrate_and_running_time(input_file: str) -> (int, int):
    out = subprocess.run(['ffmpeg', '-i', input_file, '-c', 'copy', '-f', 'null', '-'],
                         stderr=subprocess.PIPE).stderr.decode('utf-8')
    audio_size = int(re.search('audio:([0-9]+)kB', out).groups()[0])
    running_time = time_to_seconds(out, 'time=')
    return audio_size * 8 // running_time, running_time


def final_convert_spawn(args: list, total_seconds: int):
    proc = subprocess.Popen(args, stdout=subprocess.PIPE)
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        line = line.rstrip().decode("utf-8")
        if line.startswith('out_time='):
            completed_seconds = time_to_seconds(line, 'out_time=')
            progress_label.config(text=format_seconds(completed_seconds) + "/" + format_seconds(total_seconds))
            progress_bar['value'] = completed_seconds / total_seconds * 100
        elif line.startswith('total_size='):
            size_label.config(text=sizeof_fmt(int(re.findall('([0-9]+)', line)[0])))

    progress_bar['value'] = 100
    progress_label.config(text="Done")


root = Tk()
root.resizable(False, False)
root.title('Convertor')
frm = ttk.Frame(root)
frm.grid(pady=10)
select_file_button = ttk.Button(frm, text="Select File", command=select_input)
select_file_button.grid(column=0, row=0, padx=10, pady=10)
progress_bar = ttk.Progressbar(frm, orient=tkinter.HORIZONTAL, length=200, mode='determinate', maximum=100)
progress_bar.grid(column=0, row=1, padx=10, pady=10)
progress_label = ttk.Label(frm, text='Select File...')
progress_label.grid(column=0, row=2)
size_label = ttk.Label(frm)
size_label.grid(column=0, row=3)
root.mainloop()