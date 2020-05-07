from video_editor.actions import CutAction, CompressAction, RemoveAudioAction, SpeedupAction
from video_editor.utils import join_video_list
import tempfile
from shutil import copyfile


class VideoEditor:

    def __init__(self, video_path, video_length):
        self.video_path = video_path
        self.video_length = video_length
        self.splits = [Split(video_path, 0, video_length)]

    def add_split(self, time):
        # Find new split position
        k = len(self.splits)
        for i, split in enumerate(self.splits):
            if split.end_time > time:
                k = i
                break

        # Create the new split
        split = self.splits[k]
        new_split = split.copy()
        new_split.end_time = time
        self.splits.insert(k, new_split)

        # Edit affected split
        split.start_time = time

    def update_split(self, split_id, config):
        split = self.splits[split_id]
        split.config = config

    def get_splits(self):
        return self.splits

    def get_split_config(self, split_id):
        return self.splits[split_id].config

    def merge_split_with_next(self, split_id):
        split = self.splits[split_id]
        removed_split = self.splits.pop(split_id + 1)
        split.end_time = removed_split.end_time

    def merge_split_with_previous(self, split_id):
        split = self.splits[split_id]
        removed_split = self.splits.pop(split_id - 1)
        split.start_time = removed_split.start_time

    def export_split(self, split_id, output_file):
        self.splits[split_id].export(output_file)

    def export_and_join_splits(self, split_ids, output_file):
        *_, video_extension = self.video_path.split('/')[-1].split(".")

        with tempfile.TemporaryDirectory() as dir_path:
            dir_path = dir_path.replace("\\", "/")
            list_file_path = "{}/list_file.txt".format(dir_path)

            with open(list_file_path, "wt") as list_file:

                for split_id in split_ids:
                    split_tmp_output = "{}/{}.{}".format(dir_path, split_id, video_extension)
                    self.splits[split_id].export(split_tmp_output, force_reencode=True)
                    list_file.write('file {}.{}\n'.format(split_id, video_extension))

            succ, msg = join_video_list(list_file_path, output_file)
            if not succ:
                print("JOIN SPLITS FAILED\n", msg)


class Split:

    """
    Example config
    {
      'reencode': False,
      'compress': True,
      'removeaudio': False,
      'speedup': {
        'factor': 2,
        'dropframes': True,
      }
    }
    """

    def __init__(self, video_path, start_time, end_time):
        self.video_path = video_path
        self.start_time = start_time
        self.end_time = end_time
        self.config = dict()

    @property
    def duration(self):
        return self.end_time - self.start_time

    def export(self, output_path, force_reencode=False):
        def add_extension(path):
            return "{}.{}".format(path, video_extension)

        # Get config values
        conf_reencode = True if force_reencode else self.config.get('reencode', False)
        conf_compress = self.config.get('compress', False)
        conf_remove_audio = self.config.get('removeaudio', False)
        conf_speedup = self.config.get('speedup', False)

        # Get video extension and name
        *video_name, video_extension = self.video_path.split('/')[-1].split(".")
        video_name = ".".join(video_name)

        # Create temp folder
        with tempfile.TemporaryDirectory() as dir_path:
            dir_path = dir_path.replace("\\", "/")
            tmp_output_path = "{}/{}_{}_{}".format(dir_path, video_name, self.start_time, self.end_time)

            # Cut split
            action = CutAction(self.video_path, add_extension(tmp_output_path),
                               self.start_time, self.end_time, reencode=conf_reencode)
            succ, msg = action.run()
            if not succ:
                return print("CUT ACTION FAILED\n", msg)

            # Compress split
            if conf_compress:
                input_path = add_extension(tmp_output_path)
                tmp_output_path += '_C'
                action = CompressAction(input_path, add_extension(tmp_output_path))
                succ, msg = action.run()
                if not succ:
                    return print("COMPRESS ACTION FAILED\n", msg)

            # Remove audio from split
            if conf_remove_audio:
                input_path = add_extension(tmp_output_path)
                tmp_output_path += '_NA'
                action = RemoveAudioAction(input_path, add_extension(tmp_output_path))
                succ, msg = action.run()
                if not succ:
                    return print("REMOVE AUDIO ACTION FAILED\n", msg)

            # Speedup split
            if conf_speedup and isinstance(conf_speedup, dict):
                factor = self.config['speedup'].get('factor', 1)
                drop_frames = self.config['speedup'].get('dropframes', True)
                input_path = add_extension(tmp_output_path)
                tmp_output_path += '_SU'
                action = SpeedupAction(input_path, add_extension(tmp_output_path), factor, drop_frames)
                succ, msg = action.run()
                if not succ:
                    return print("SPEEDUP ACTION FAILED\n", msg)

            # Copy final video to output path
            copyfile(add_extension(tmp_output_path), output_path)

    def copy(self):
        split_copy = Split(self.video_path, self.start_time, self.end_time)
        split_copy.config = self.config
        return split_copy




