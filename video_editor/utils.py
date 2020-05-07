from video_editor._helpers import run_command, get_ffmpeg_binary


def join_video_list(list_file, output_file):
    cmd = '{ffmpeg} -y -safe 0 -f concat -i "{list_file}" "{o}"'.format(
        ffmpeg=get_ffmpeg_binary(),
        list_file=list_file,
        o=output_file
    )
    return run_command(cmd)
