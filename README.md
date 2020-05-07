# Python Video Editor

This is a simple and illustrative example of a video editor with interface in Python. PyQt5 framework 
was used to build the GUI and video manipulation is done via [FFMPEG](https://www.ffmpeg.org/).

## Dependencies

- Python 3.0+
- PyQt5
- FFMPEG

Note that FFMPEG binary (version 4.1) is included for Windows users so no additional installation 
is required.

## Supported platforms

As for now, I have only tested on Windows, but Linux and Mac users should be able to use it too.

## Supported functions

- Split video in multiple parts
- Edit each split individually
  - Reencode video and audio
  - Compress video and audio quality
  - Silence audio
  - Speed up and slow down
- Save a single split
- Save the whole video joining all selected splits

## Future improvements

- Remember when a split is selected after adding a new split
- Add an option to move slider position just before and after a selected split

## Contributions

Feel free to create a PR for improvements or bug fixes in the code. If you just find a bug but don't 
want to dig in the code to fix it, open an issue and I will try to take a look at it.

