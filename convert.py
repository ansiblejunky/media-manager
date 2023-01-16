#!/usr/bin/env python

import json
import logging
import os
import subprocess
# Regular expression support for files and file content
import re
# Print dictionaries and JSON content in a pretty and human readable manner
import pprint
# Enable timers
import time
# Add ffmpeg progress bar https://github.com/althonos/ffpb
import ffpb
# Handle when user leverages Ctrl-C to terminate operations
import signal
# https://www.geeksforgeeks.org/print-colors-python-terminal/
from colorama import Fore, Back, Style
# Added to ensure target directory path exists
from pathlib import Path
# Search for files using glob function
from glob import glob

# TODO: Add the ability to entirely quit the whole program (Ctrl-C only causes encoding to stop and go to next file)

# TODO: Collect/Track file sizes as we detect files and then determine if target directory has enough free space
# but the problem might be if we upscale/etc, then file sizes will be bigger, but at least warn when its not enough
# or very close

# TODO: Collect/Track file sizes for each conversion task and at the end state "Previous storage: X, New storage: Y" to show storage savings

# TODO: ensure stdout of program goes into a log file
# https://docs.python.org/3/howto/logging.html
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#TODO: Add arguments
arg_verbose = True
arg_interactive = False # false (default), true (ask to continue after each file)
arg_convert = True # false (default, dryrun), true (convert files)
arg_recursive = False # false (default), true
arg_chapters = "copy" # copy (default), remove, duration, detect-scenes
arg_subtitles = "copy" # copy (default), remove
# --thumbnail = generate thumbnail inside container?
# --language = preferred language
arg_overwrite = False # false (default), true (overwrite files)
arg_upscaling = False # false (default), true
arg_downscaling = True # false (default), true

# Source information
#arg_source_directory = r"./media/"
arg_source_directory = r"/Volumes/VIDEOS/Movies_old/"
arg_source_formats = ["mkv", "divx", "mp4", "m4p", "m4v", "mov", "qt", "ogg", "avi", "mpg", "wmv", "flv", "m2ts", "mpeg"]
arg_source_subtitle_formats = ["idx", "srt"]
FFMETADATA_FILE = "/tmp/FFMETADATAFILE"

# Target information
# TODO: Careful when converting input to same output filename in same folder! 
# We should actually insist on a different output folder (maybe..)
#arg_target_directory = "~/Movies/_CONVERT_/"
arg_target_directory = r"/Volumes/VIDEOS/Movies/"

# https://developer.roku.com/docs/specs/media/streaming-specifications.md
target_container = "mkv" # MKV (Matrotska)
target_video_codec = "h264" # AVC (H.264)
target_video_quality = "21"
target_audio_codec = "aac" # AAC
target_subtitle_codec = "srt" # SRT (Subrip)
target_primary_language = "eng" # English
target_temp_dir = "/tmp"

def signal_handler(signal, frame):
    print('You pressed Ctrl+C! Exiting ... ')
    exit(0)

def print_error(msg):
    print(Fore.RED + msg + Style.RESET_ALL)

def print_dim(msg):
    print(Style.DIM + msg + Style.RESET_ALL)

def print_header(message: str):
    prefix = message
    size = os.get_terminal_size()
    line = prefix + " " + ("-" * (size.columns - len(prefix) - 5))
    print("\n")
    print(Fore.GREEN + line + Style.RESET_ALL)

def print_task(message: str):
    prefix = "\nTASK: " + message
    size = os.get_terminal_size()
    line = prefix + " " + ("*" * (size.columns - len(prefix) - 5))
    print(Fore.GREEN + line + Style.RESET_ALL)

def ffprobe(filepath):
    try:
        #TODO: Use args instead, to avoid issues with filepath having spaces and quotes in it
        prefix = "ffprobe -v quiet -print_format json"
        command = prefix + " -show_chapters -show_format -show_streams \"{}\"".format(filepath)
        if arg_verbose:
            print("    ... command: ", command)
        results = json.loads(subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True))
    except:
        return {}
    return results

def get_chapter_count(info):
    # TODO: Use dict.get() operation for the rest of my code like below:
    x = len(info.get('chapters', []))
    return x

def get_stream_count(info):
    for k, v in info.items():
        if k == "streams":
            return len(v)
    return 0


def get_video_stream_count(info):
    count = 0
    for k, v in info.items():
        if k == "streams":
            for s in v:
                if s["codec_type"] == "video":
                    count = count + 1
    return count

def get_video_duration(info):
    x = info["format"]["duration"]
    return float(x) 

def get_video_codec(info):
    streams = info["streams"]
    for s in streams:
        if s["codec_type"] == "video":
            return s["codec_name"]
        else:
            return ""

def get_video_width(info):
    streams = info["streams"]
    for s in streams:
        if s["codec_type"] == "video":
            return s["width"]
        else:
            return 0

def get_video_height(info):
    streams = info["streams"]
    for s in streams:
        if s["codec_type"] == "video":
            return s["height"]
        else:
            return 0

def get_audio_stream_count(info):
    streams = info["streams"]
    count = 0
    for s in streams:
        if s["codec_type"] == "audio":
            count = count + 1
    return count


def get_audio_codec(info):
    streams = info["streams"]
    for s in streams:
        if s["codec_type"] == "audio":
            return s["codec_name"]


def get_subtitle_stream_count(info):
    streams = info["streams"]
    count = 0
    for s in streams:
        if s["codec_type"] == "subtitle":
            count = count + 1
    return count


def get_subtitle_codec(info):
    streams = info["streams"]
    for s in streams:
        if s["codec_type"] == "subtitle":
            return s["codec_name"]

def ffmpeg(*args):
    command = ["ffmpeg", "-hide_banner", "-nostdin", "-n"]

    command.extend(args)
    try:
        process = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        )
        return process.stdout
    except subprocess.CalledProcessError as e:
        raise RuntimeError(
            "command '{}' return with error (code {}): {}".format(
                e.cmd, e.returncode, e.output
            )
        )

def ffmpeg_ffmetadata(filepath):
    # map_chapters parameter ensures we ignore any existing chapter definitions
    # TODO: consider using /dev/stdout as filename: ffmpeg -i media/GOT_chapters.mkv -y -f ffmetadata /dev/stdout
    args = ["-i", filepath, "-map_chapters", "-1", "-f", "ffmetadata", FFMETADATA_FILE]
    result = ffmpeg(*args)
    return result

def ffmpeg_dispositions():
    args = ["-dispositions"]
    result = ffmpeg(*args)
    return result

# ffmpeg list of containers (formats)
def ffmpeg_formats():
    args = ["-formats"]
    result = ffmpeg(*args)
    return result

# ffmpeg list of codecs with the following key
# D..... = Decoding supported
# .E.... = Encoding supported
# ..V... = Video codec
# ..A... = Audio codec
# ..S... = Subtitle codec
# ...I.. = Intra frame-only codec
# ....L. = Lossy compression
# .....S = Lossless compression
def ffmpeg_codecs():
    args = ["-codecs"]
    result = ffmpeg(*args)
    return result

# ffmpeg list of encoders with the following key
# V..... = Video
# A..... = Audio
# S..... = Subtitle
# .F.... = Frame-level multithreading
# ..S... = Slice-level multithreading
# ...X.. = Codec is experimental
# ....B. = Supports draw_horiz_band
# .....D = Supports direct rendering method 1
def ffmpeg_encoders():
    args = ["-encoders"]
    result = ffmpeg(*args)
    return result

def ffmpeg_encoder_details(encoder: str):
    args = ["-h", "encoder=" + encoder]
    result = ffmpeg(*args)
    return result

def ffmpeg_decoders():
    args = ["-decoders"]
    result = ffmpeg(*args)
    return result

def ffmpeg_decoder_details(decoder: str):
    args = ["-h", "decoder=" + decoder]
    result = ffmpeg(*args)
    return result

def ffmpeg_simulate(filepath):
    args = ["-i", filepath, "-t", "00:00:01", "-f", "null", "-"]
    result = ffmpeg(*args)
    return result

def ffmpeg_convert(source_f_path, target_f_path, fprobe_results):
    item = {}

    #TODO: Generate the order of the audio map parameters by leveraging `target_primary_language`
    # https://askubuntu.com/a/1329506
    # https://askubuntu.com/a/1365329
    # https://trac.ffmpeg.org/wiki/Map
    # ffmpeg -i input.mkv -map 0:v:0 \
    #        -map 0:a:2 -map 0:a:0 -map 0:a:1 -map 0:a:3 \
    #        -map 0:s -c copy \
    #        -disposition:a:0 default \
    #        -disposition:a:1 0 \
    #        reordered.mkv
    # To unpack this a little:
    # -map 0:v:0: The first (and only) video stream is selected
    # -map 0:a:2 -map 0:a:1: The audio streams are individually placed. The final digit of each 'set' selects from the 4 audio streams with '0' being the first stream and '3' being the final audio stream. English is of course specified first and is stream 2.
    # -map 0:s: Select all of the subtitle files
    # -c copy: Copy the video, audio and subtitle streams with no re-encoding.
    # -disposition:a:0 default: This sets our required audio stream (English) as the default. Useful if this has been set on another, input audio stream.
    # -disposition:a:1 0 - means forget that the existing audio stream (now audio stream 1) was ever the default. This is likely not actually be needed(??) but does no harm.

    # args = [
    #     "-i", f_path, 
    #     "-c:v", target_codec, 
    #         "-map", "0:v:0",
    #     "-c:a", "aac", 
    #         "-map", "0:2",
    #         "-map", "0:1",
    #         "-disposition:a:0", "default",
    #         "-disposition:a:1", "0",
    #     "-c:s", "srt", 
    #         "-map", "0:5", 
    #         "-map", "0:4", 
    #         "-map", "0:3",
    #         "-disposition:5", "0",
    #         "-disposition:4", "0",
    #         "-disposition:3", "default+forced"
    # ]

    # SOURCE - INPUT
    args = ["-i", source_f_path]

    # SOURCE - VIDEO STREAMS
    item["source_video_codec"] = get_video_codec(fprobe_results)
    print("    ... video codec = %s" % item["source_video_codec"])
    item["source_video_duration"] = get_video_duration(fprobe_results)
    item["source_video_streams"] = get_video_stream_count(fprobe_results)
    #item["source_bframes"] = packed_b_frames(input_file=f_path, convert=False)
    item["source_video_width"] = get_video_width(fprobe_results)
    item["source_video_height"] = get_video_height(fprobe_results)
    print("    ... video width = %s" % item["source_video_width"])
    print("    ... video height = %s" % item["source_video_height"])

    # SOURCE - AUDIO STREAMS
    item["source_audio_streams"] = get_audio_stream_count(fprobe_results)
    print("    ... audio streams found = %s" % item["source_audio_streams"])

    # SOURCE - SUBTITLE STREAMS
    item["source_subtitle_streams"] = get_subtitle_stream_count(fprobe_results)
    print("    ... subtitle streams found = %s" % item["source_subtitle_streams"])

    # SOURCE - CHAPTERS
    item["source_chapters"] = get_chapter_count(fprobe_results)
    print("    ... chapters found = %s" % item["source_chapters"])

    # TARGET
    print("Target: '%s'" % target_f_path)

    # TARGET - DEFAULT PASSTHROUGH BEHAVIOR
    args.extend(["-c", "copy"])

    # TARGET - VIDEO STREAMS
    # https://write.corbpie.com/a-guide-to-upscaling-or-downscaling-video-with-ffmpeg/
    target_scaling_enabled = False
    if arg_upscaling and item['source_video_height'] < 1080:
        target_scaling_enabled = True
    if arg_downscaling and item['source_video_height'] > 1080:
        target_scaling_enabled = True
    print("    ... target scaling enabled: %s" % target_scaling_enabled)
    if target_scaling_enabled:
        # Force encoding when upscaling is enabled, otherwise we get the following error:
        # Filtering and streamcopy cannot be used together.
        args.extend(["-c:v", target_video_codec, "-crf", target_video_quality])
        args.extend(["-vf", "scale=-1:1080:flags=lanczos"])
    elif item["source_video_codec"] != target_video_codec:
        # Force encoding if source video codec is not the same as target codec
        args.extend(["-c:v", target_video_codec, "-crf", target_video_quality])

    # TARGET - AUDIO STREAMS
    # TODO: Determine if audio streams need to be encoded to target codec or not
    args.extend(["-c:a", "aac"])

    # TARGET - SUBTITLE STREAMS
    # TODO: Determine if subtitle streams need to be encoded to target codec or not
    args.extend(["-c:s", "srt"])
    # TODO: ffmpeg - detect local subtitles files to include with container
    # https://gist.github.com/kurlov/32cbe841ea9d2b299e15297e54ae8971
    # TODO: Handle subtitle errors when some subtitle streams are already 'srt' (codec_name = subrip) and some are not
    # error:
    # ffmpeg -i 'media/GOT_error.mkv'
    #   -c:v copy -map 0:v:0 -c:a aac -map 0:m:language:eng? -disposition:a:0 default 
    #   -c:s srt /Users/johnw/Movies/_CONVERT_/GOT_S05E01.mkv
    # Error initializing output stream 0:4 -- Subtitle encoding currently only possible from text to text or bitmap to bitmap
    # Stream mapping:
    #   Stream #0:0 -> #0:0 (copy)
    #   Stream #0:2 -> #0:1 (ac3 (native) -> aac (native))
    #   Stream #0:4 -> #0:2 (subrip (srt) -> subrip (srt))
    #   Stream #0:7 -> #0:3 (subrip (srt) -> subrip (srt))
    #   Stream #0:8 -> #0:4 (hdmv_pgs_subtitle (pgssub) -> subrip (srt))
    #     Last message repeated 1 times

    # TARGET - CHAPTERS
    #scenes = chapters_algorithm_scenes(item["filename"])
    #chapters_algorithm_duration(f_path, item["source_video_duration"])
    #if arg_verbose:
    #    print(markers)

    # TARGET - THUMBNAIL?

    # TARGET - OUTPUT
    args.append(target_f_path)
    if arg_verbose:
        print("    ... command: ffmpeg", ' '.join(args))
    if arg_convert:
        # TODO: Add error handling for ffpb
        # TODO: Capture what ffmpeg output shows on what will be the final stream structure
        ffpb.main(args)
        # TODO: Run ffprobe after conversion and show information and check health of video

    return item

# Check for packed b-frames in AVI files
# Option:
#   Do not care about b-frames. Does it matter if we convert to MP4 ?
# Option:
#   Maybe simply use ffprobe output `has_b_frames: 1` property of a stream with `codec_type = video`?
#   Test this by converting a simple file and check the ffprobe output again!
# Error:
#   "Video uses a non-standard and wasteful way to store B-frames ('packed B-frames'). Consider using the mpeg4_unpack_bframes bitstream filter without encoding but stream copy to fix it."
# Remove:
#   https://superuser.com/questions/782634/ffmpeg-avidemux-fix-packed-b-frames
#   ffmpeg -i "input.avi" -codec copy -bsf:v mpeg4_unpack_bframes "input2.avi"
def packed_b_frames(input_file, convert=False, output_file="temp.avi"):
    msg = "Video uses a non-standard and wasteful way to store B-frames"

    # Packed b-frames only apply to AVI files
    f, ext = os.path.splitext(input_file)
    if ext != ".avi":
        return False

    # Scan video to check for packed b-frames
    data = ffmpeg_simulate(input_file)
    if data.find(msg) == 0:
        return False

    # Convert if requested
    if convert:
        args = [
            "-i",
            input_file,
            "-codec",
            "copy",
            "-bsf:v",
            "mpeg4_unpack_bframes",
            output_file,
        ]
        ffmpeg(*args)

    # Confirm packed b-frames exist
    return True

# Chapter algorithm using scene detection
def chapters_algorithm_scenes(filepath):

    try:
        command = "ffprobe -v quiet -print_format json -show_frames -of compact=p=0 -f lavfi movie='" + filepath + "',select=gt(scene\,0.6) {}".format(filepath)
        results = json.loads(subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True))
    except:
        return {}
    return results

# Chapter algorithm using duration of video
def chapters_algorithm_duration(filepath: str, duration: float):
    # Generate ffmetadata
    # TODO: create the file in same folder as output directory and same filename as media file but with txt extension
    ffmpeg_ffmetadata(filepath)

    # Generate chapters by slicing video
    markers = []
    start = 0
    end = duration

    if (duration / 60) / 60 > 1:
        step = 10 * 60
    else:
        step = 5 * 60
    i = start
    x = 1
    while i < end:
        item = {
            "start": str(i * 1000),
            "end": str((i + step) * 1000),
            "title": "Chapter " + str(x),
        }
        markers.append(item)
        i += step
        x += 1

    item = {
        "start": str((i - step) * 1000),
        "end": end * 1000,
        "title": "Chapter " + str(x),
    }
    markers.append(item)
    print(markers)

    # Append chapter information into ffmetadata file
    text = ""
    for i in range(len(markers)-1):
        chap = markers[i]
        title = chap['title']
        start = chap['start']
        end = int(markers[i+1]['start'])-1
        text += f"""
[CHAPTER]
TIMEBASE=1/1000
START={start}
END={end}
title={title}
"""
    with open(FFMETADATA_FILE, "a") as f:
        f.write(text)

    return markers

# Capture chapter information from ffmpeg output using regex
def ffmpeg_parse_chapters(filepath):
  chapters = []
  command = [ "ffmpeg", '-i', filepath]
  output = ""
  m = None
  title = None
  chapter_match = None
  
  try:
    output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
  except subprocess.CalledProcessError as e:
    output = e.output

  num = 1

  for line in iter(output.splitlines()):
    x = re.match(r".*title.*: (.*)", line)
    print("x:")
    pprint.pprint(x)

    print("title:")
    pprint.pprint(title)

    if x == None:
      m1 = re.match(r".*Chapter #(\d+:\d+): start (\d+\.\d+), end (\d+\.\d+).*", line)
      title = None
    else:
      title = x.group(1)

    if m1 != None:
      chapter_match = m1

    print("chapter_match:")
    #pprint.pprint(chapter_match)

    if title != None and chapter_match != None:
      m = chapter_match
      pprint.pprint(title)
    else:
      m = None

    if m != None:
      chapters.append({ "name": str(num) + " - " + title, "start": m.group(2), "end": m.group(3)})
      num += 1

  print(chapters)
  return chapters


def scanner():
    media_list = []
    batch_total = 0

    # Validate source directory
    print("Source directory: '%s'" % arg_source_directory)
    print("    ... validating directory")
    source_dir = validate_directory(arg_source_directory)

    # Traverse source directory for matching media files
    print("    ... traverse directory")
    files = []
    for ext in arg_source_formats:
        pattern = os.path.join(source_dir, '**/*.' + ext)
        for y in glob(pattern, recursive=True):
            files.append(y)
    files.sort()
    for f in files:
        print("    ... found: '" + f + "'")

    for source_f_path in files:
        # Start
        task_start = time.time()
        print_task("Convert media")
        print("Source: '%s'" % source_f_path)

        # Get source media file information
        print("    ... get media information")
        fprobe_results = ffprobe(source_f_path)
        if fprobe_results == {}:
            print_error("    ... ERROR, skipping due to ffprobe was not able to read file")
            continue

        # Generate target file path with new extension
        print("    ... determine target path")
        f_rel_path = os.path.relpath(source_f_path, source_dir)
        temp_f_path = os.path.join(arg_target_directory, f_rel_path)
        f_base, f_ext = os.path.splitext(temp_f_path)
        target_f_path = f_base + "." + target_container
        target_f_dir = os.path.dirname(target_f_path)
        validate_directory(target_f_dir, True)

        # Convert media
        item = ffmpeg_convert(source_f_path, target_f_path, fprobe_results)
        media_list.append(item)

        # Stop Timer
        task_stop = time.time()

        # Aggregate Timer
        task_total = round(task_stop - task_start, 2)
        task_total_minutes = round(task_total/60, 2)
        batch_total = round(batch_total + task_total, 2)
        batch_total_minutes = round(batch_total/60, 2)
        print("Elapsed: %s seconds [%s minutes]" % (task_total, task_total_minutes))

    if files:
        print("\nTotal files converted: %s" % (len(files)))
        print("Total elapsed: %s seconds [%s minutes]"% (batch_total, batch_total_minutes))
        print("")
    return media_list


def clean_filename(f_base):
    # Generate target file path
    # TODO: Consider renaming the target using this algorithm:
    # - find regex like SXXEYY in the source filename
    # - if found, move it to the front so files are sorted correctly
    # - if not found, just convert as is... (weird filename)
    # - remove things we know are useless (create an array of items)... 
    #      [DivX], [TVRip], [PDTV], [Grand Designs], [DD, MM, YYYY], [MM, DD, YYYY]
    return f

def validate_directory(path, create=False):
    p = os.path.expanduser(path)
    
    if not os.path.exists(p):
        if arg_convert:
            if create:
                try:
                    os.makedirs(path)
                    print("    ... creating target directory")
                except FileExistsError:
                    # directory already exists
                    pass
        else:
            print("    ... not creating target directory (dry run mode)")
    return p

def main():
    signal.signal(signal.SIGINT, signal_handler)

    print_header("Video Converter (by John Wadleigh)")

    media_list = scanner()
    print("Found " + str(len(media_list)) + " media files\n\n")


if __name__ == "__main__":
    main()

# ffmpeg - detect chapters
# https://ikyle.me/blog/2020/add-mp4-chapters-ffmpeg
# IDEA: generate the chapter metadata file and import into Handbrake to do the work
# step 1: extract metadata from video
#   ffmpeg -i input.mp4 -f ffmetadata FFMETADATAFILE
# step 2: create example chapters.txt
#   media/chapters.txt
# step 3: use helper script to convert chapters.txt and append to FFMETADATAFILE
#   python helper.py
# step 4: create new video file and write metadata to video
#   ffmpeg -i input.mp4 -i FFMETADATAFILE -map_metadata 1 -codec copy output.mp4
# official ffmpeg metadata formatting
# https://ffmpeg.org/ffmpeg-formats.html#toc-Metadata-1

# python code to generate chapters into mp4
# https://gist.github.com/Elenesgu/ba4e5cd81f9c98ab5979b3db62aea7cc

# detect chapters/scenes using black detection algorithm:
#   ffmpeg -i input.avi -vf blackdetect=d=0.232:pix_th=0.1 -an -f null - 2>&1 | findstr black_duration > output.txt
#   ffmpeg -i input.avi -vf blackdetect=d=0.232:pix_th=0.1 -an -f null - 2>&1
#   ffprobe -f lavfi -i "movie=input.mp4,blackdetect[out0]" -show_entries tags=lavfi.black_start,lavfi.black_end -of default=nw=1 -v quiet
#   ffmpeg -i input.handbrake.mkv -vf blackdetect=d=0.232:pix_th=0.1 -an -f null - 2>&1 | grep black_duration > output3.txt

# detect chapters/scenes using scene detection algorithm:
#   ffmpeg -hide_banner -i input.avi -filter_complex "select='gt(scene,0.5)',metadata=print:file=time.txt" -vsync vfr img%03d.png

# TODO: Progress bar over all files (1 of 150) perhaps displayed after each file? how to make this persistent

# TODO: Queues: run multiple `convert` sessions where each time I run the program it adds to the "queue"
#           allow pause, cancel and continue the queue

# TODO: Fix media filenames and search IMDB or something for the episode titles
# GOT_S01E01.mkv would be converted to 'S01E01 - <episode title>.mkv"

# TODO: Add healthcheck task to ensure output video is playable
# add a command line param for this (--validate)
# use ffprobe after conversion to see if ffprobe can read it, and ensure there are at least 1 video and 1 audio stream
