import os
import subprocess
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# TODO: import srt file into mkv
# https://gist.github.com/kurlov/32cbe841ea9d2b299e15297e54ae8971

# TODO: Add check-mode to look at a batch of files and show what changes would be made

def ffprobe(*args):
    command = ['ffprobe', '-v', 'quiet', '-print_format', 'json']

    for arg in args:
        command.append(arg)
    process = subprocess.Popen(command,
                        stdout=subprocess.PIPE)
    data, err = process.communicate()
    if process.returncode == 0:
        return json.loads(data)
    else:
        print("Error:", err)
    return ""

def get_info(filepath):
    return ffprobe('-show_chapters', '-show_format', '-show_streams', '-i', filepath)

def get_stream_count(info):
    streams = info['streams']
    return len(streams)

def get_video_stream_count(info):
    streams = info['streams']
    count = 0
    for s in streams:
        if s['codec_type'] == 'video':
            count = count + 1
    return count

def get_video_codec(info):
    streams = info['streams']
    for s in streams:
        if s['codec_type'] == 'video':
            return s['codec_name']

def get_audio_stream_count(info):
    streams = info['streams']
    count = 0
    for s in streams:
        if s['codec_type'] == 'audio':
            count = count + 1
    return count

def get_audio_codec(info):
    streams = info['streams']
    for s in streams:
        if s['codec_type'] == 'audio':
            return s['codec_name']

def get_subtitle_stream_count(info):
    streams = info['streams']
    count = 0
    for s in streams:
        if s['codec_type'] == 'subtitle':
            count = count + 1
    return count

def get_subtitle_codec(info):
    streams = info['streams']
    for s in streams:
        if s['codec_type'] == 'subtitle':
            return s['codec_name']

def ffmpeg(*args):
    command = ['ffmpeg', '-hide_banner', '-nostdin', '-n']

    for arg in args:
        command.append(arg)

    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=True)
    if process.returncode == 0:
        return process.stdout
    else:
        return ""

def ffmpeg_simulate(filepath):
    args = ['-i', filepath, '-t', '00:00:01', '-f', 'null', '-']
    data = ffmpeg(*args)
    return data

def detect_packed_b_frames(filepath):
    error_msg = "Video uses a non-standard and wasteful way to store B-frames"
    data = ffmpeg_simulate(filepath)
    if data.find(error_msg) > 0:
        print("Has packed b-frames")

source_directory = r'.'
target_default_codec = 'copy'
target_container = 'mkv'
target_video_codec = 'h264'
target_audio_codec = 'aac'
target_audio_profile = 'aac_he'
target_subtitle_codec = 'srt'

for subdir, dirs, files in os.walk(source_directory):
    for filename in files:
        filepath = subdir + os.sep + filename
        f, file_extension = os.path.splitext(filepath)
        if (file_extension in ['.mkv', '.avi', '.mp4']):
            print ("File: " + filepath)
            info = get_info(filepath)
            source_video_streams_count = get_video_stream_count(info)
            if source_video_streams_count > 0:
                print("Detected video streams: %i", source_video_streams_count)
                source_video_codec = get_video_codec(info)
                if source_video_codec == target_video_codec:
                    print("Target video stream: " + "<copy>")
                    video_codec = target_default_codec
                else:
                    print("Target video stream: " + target_video_codec)
                    video_codec = target_video_codec

            source_audio_streams_count = get_audio_stream_count(info)
            if source_audio_streams_count > 0:
                print("Detected audio streams: %i", source_audio_streams_count)

            source_subtitle_streams_count = get_subtitle_stream_count(info)
            if source_subtitle_streams_count > 0:
                print("Detected subtitle streams: %i", source_subtitle_streams_count)
            
            # Check for packed b-frames in AVI files
            # "Video uses a non-standard and wasteful way to store B-frames ('packed B-frames'). Consider using the mpeg4_unpack_bframes bitstream filter without encoding but stream copy to fix it."
            # https://superuser.com/questions/782634/ffmpeg-avidemux-fix-packed-b-frames
            # ffmpeg -i "input.avi" -codec copy -bsf:v mpeg4_unpack_bframes "input2.avi"
            if file_extension == '.avi':
                detect_packed_b_frames(filepath)

            print("\n")