# Video Converter

Python script to convert various types of video files to a standard format supported by [Roku](https://support.roku.com/article/208754908).

## Requirements

Install the latest version of [ffmpeg](https://ffmpeg.org/). For example, on macOS you can use homebrew:

```shell
brew install ffmpeg
```

## Subtitles

Leverage the [Subtitle Search](https://subdl.com/) website to find `srt` subtitle files.

## Container

Select best target video format container by reading through this [blog](https://www.notta.ai/en/blog/best-video-format), however we recommend using `mkv`.

## Notes

Convert DVD contents:

```shell
# Open the DVD folder using Handbrake to examine the streams
<open with handbrake>
# Merge VOB files
cat *.VOB > output.vob
# Probe output for streams
ffmpeg -analyzeduration 500M -probesize 500M -i output.vob
# Convert to mkv format and map specific streams
ffmpeg -analyzeduration 500M -probesize 500M -i output.vob -map 0:1 -map 0:2 -c:v h264 -crf 21 -c:a aac output.mkv
```

Merge multiple avi files:

```
ffmpeg -i "concat:CD1.avi|CD2.avi" -c copy output.avi
```

- `Roku` supports drives that are formatted with the FAT16, FAT32, NTFS, EXT2, EXT3, and HFS+ file systems.
- `Roku` supports video format H.264/AVC (.MKV, .MP4, .MOV) and audio format AAC (.MKV, .MP4, .MOV)
- `Roku` supports embedded subtitles in .mkv files. To choose a subtitle track use the Star button star button on your Roku remote while the video is playing. If you have a Roku TV, you also need to select Accessibility. Roku Media Player will automatically include subtitle tracks found in .SRT and .VTT files. The files must be saved in the same folder as the video. They must have the same name as the video and the .srt or .vtt extension.
- `Roku` allows you to select the format for viewing media files. If you want to see a "List View" format for all your media, then highlight/navigate to the folder "All" and press the * button. From there, you select "Display Format" and enable "List" (you should see options for List or Grid).
- `mkv` format supports embedded subtitles
- `mkv` format supports chapters (it is not standard for mp4)
- `HandBrake` can not add chapter markers if they do not already exist in the source
- `HandBrake` appears to recommend using x264 video encoder for best performance/quality balance

    ffmpeg -i input.avi \
        -hide_banner  \
        -c:v h264 -map 0:v \
        -c:a aac -profile:a aac_he \
            -map 0:a? \
            -map 0:a:m:language:eng? \
            -map 0:a:m:language:ger? \
            -disposition:a:0 default \
            -disposition:a:1 0 \
        -c:s srt \
            -map 0:s? \
            -map 0:s:m:language:eng? \
            -map 0:s:m:language:ger? \
            -disposition:s 0 \
        input.mkv

ffmpeg -i input.avi -xerror -err_detect careful -c:v h264 -c:a aac -c:s srt input.avi.mkv

ffmpeg -i input.avi -f null -

"Video uses a non-standard and wasteful way to store B-frames ('packed B-frames'). Consider using the mpeg4_unpack_bframes bitstream filter without encoding but stream copy to fix it."
https://superuser.com/questions/782634/ffmpeg-avidemux-fix-packed-b-frames
ffmpeg -i "input.avi" -codec copy -bsf:v mpeg4_unpack_bframes "input2.avi"

- Check code_name
codec_name=mpeg4
- Check codec_tag_string
codec_tag_string=XVID
- Check profile
profile=Advanced Simple Profile

- Detect number of b-frames
source_b_frames=`ffprobe -v error -select_streams v -show_entries stream=has_b_frames -of default=noprint_wrappers=1:nokey=1 $f`

## References

- [ffmpeg-progressbar-cli](https://github.com/sidneys/ffmpeg-progressbar-cli)
- [HandBrake appending numbers to file names unnecessarily](https://github.com/HandBrake/HandBrake/issues/2786)
- [How to use Roku Media Player to play your videos, music and photos](https://support.roku.com/article/208754908)
- [Handbrake - Performance](https://handbrake.fr/docs/en/latest/technical/performance.html)
- [Sample video files](https://file-examples.com/index.php/sample-video-files/)
- [ffmpeg - Selecting streams with the -map option](https://trac.ffmpeg.org/wiki/Map)
- [Roku Streaming Specifications](https://developer.roku.com/docs/specs/media/streaming-specifications.md)
- [Handbrake CLI](https://handbrake.fr/downloads2.php)
- [Handbrake CLI Reference](https://handbrake.fr/docs/en/latest/cli/command-line-reference.html)
- [ffmpeg scaling](https://trac.ffmpeg.org/wiki/Scaling)
- [ffmpeg - upscaling and downscaling](https://write.corbpie.com/upscaling-and-downscaling-video-with-ffmpeg/)
- [Subtitle Search](https://subdl.com/)
- [Best Video Format](https://www.notta.ai/en/blog/best-video-format)

mpv media player:

- [python-mpv](https://github.com/jaseg/python-mpv)
- [mpv documentation](https://mpv.io/manual/master/#environment-variables)

macos tips:

- [Choose default app to open file extension](https://support.apple.com/guide/mac-help/choose-an-app-to-open-a-file-on-mac-mh35597/mac)
- [Batch rename files](https://tidbits.com/2018/06/28/macos-hidden-treasures-batch-rename-items-in-the-finder/)

## License



## Author

John Wadleigh