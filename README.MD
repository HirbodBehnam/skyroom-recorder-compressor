# Skyroom Recorder Compressor

A small GUI program I wrote to compress the skyroom recorded classes.

This program uses ffmpeg under the hood and uses these configs:

* h265 codec using libx265 and crf of 28
* Height of less than 720px
* Audio quality of less than 32kb/s and opus codec
* 10 frames per seconds

## Usage

At first install `ffmpeg` and `requirements.txt` dependencies using pip and then simply run `main.py` using python. I
developed this app with python3.10 not sure what is the minimum version of the app.

You can also drag and drop the input file into the py file in order to automatically select the
input file.