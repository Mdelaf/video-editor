from video_editor._helpers import get_ffmpeg_binary, run_command
from abc import ABC, abstractmethod
from math import log2, floor


class BaseAction(ABC):

    def __init__(self, input_path, output_path):
        self.input = input_path
        self.output = output_path

    @abstractmethod
    def run(self):
        pass


class CutAction(BaseAction):

    def __init__(self, input_path, output_path, start_time, end_time, reencode=False):
        super().__init__(input_path, output_path)
        self.reencode = reencode
        self.start_time = start_time
        self.end_time = end_time

    def run(self):
        cmd = '{ffmpeg} -y -ss {s:.2f} -t {d:.2f} -i "{fn}" -async 1 {re} "{o}"'.format(
            ffmpeg=get_ffmpeg_binary(),
            fn=self.input,
            s=self.start_time/1000,
            d=(self.end_time-self.start_time)/1000,
            re="" if self.reencode else "-c copy",
            o=self.output,
        )
        return run_command(cmd)


class CompressAction(BaseAction):

    def __init__(self, input_path, output_path):
        super().__init__(input_path, output_path)

    def run(self):
        cmd = '{ffmpeg} -y -i "{fn}" -vcodec h264 -acodec aac "{o}"'.format(
            ffmpeg=get_ffmpeg_binary(),
            fn=self.input,
            o=self.output,
        )
        return run_command(cmd)


class RemoveAudioAction(BaseAction):

    def __init__(self, input_path, output_path):
        super().__init__(input_path, output_path)

    def run(self):
        cmd = '{ffmpeg} -y -i "{fn}" -c:v copy -af volume=0 "{o}"'.format(
            ffmpeg=get_ffmpeg_binary(),
            fn=self.input,
            o=self.output,
        )
        return run_command(cmd)


class SpeedupAction(BaseAction):

    def __init__(self, input_path, output_path, speed_factor, drop_frames=True):
        super().__init__(input_path, output_path)
        self.factor = speed_factor
        self.drop_frames = drop_frames

    def get_complex_filter(self):
        rep = floor(log2(self.factor))
        additional = round(self.factor / (2 ** rep), 2)
        atempo_filters = ["atempo=2.0"] * rep + ["atempo={}".format(additional)]
        return '[0:v]setpts=PTS/{factor}[v];[0:a]{atempo}[a]'.format(
            factor=self.factor,
            atempo=",".join(atempo_filters),
        )

    def run(self):
        cmd = '{ffmpeg} -y -i "{fn}" -filter_complex "{filter}" -map "[v]" -map "[a]" "{o}"'.format(
            ffmpeg=get_ffmpeg_binary(),
            fn=self.input,
            filter=self.get_complex_filter(),
            o=self.output,
        )
        return run_command(cmd)
