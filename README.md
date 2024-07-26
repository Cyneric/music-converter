# music-converter

A simple bash script to convert audio files to different formats and store them in a specified directory.
You can either use the bash script or the python script, they both do the same thing.

## Usage examples

### Using bash
#### Example

```bash
./convert.sh ~/Music ~/Music/converted mp3 320k
```

### Using Python
#### Example

```python
python convert.py ~/Music ~/Music/converted mp3 320k
```


## Requirements

- ffmpeg
- bash

## Allowed file types

- Audio files (mp3, flac, wav, m4a, ogg, opus, wma, aac)
- Images (jpg, jpeg, png, gif, bmp, webp)
- .nfo files

## Allowed music formats

- mp3
- flac
- wav
- m4a
- ogg
- opus
- wma
- aac

## Allowed bitrates

- 32k
- 64k
- 128k
- 192k
- 256k
- 320k

## Output format

The output format is determined by the music format and bitrate. For example, if the music format is mp3 and the bitrate is 320k, the output format will be mp3.320k.

## File conversion summary

After the script finishes running, it will print a summary of the file conversion process. This includes the number of files processed for each file type.

## License

This project is licensed under the MIT License.
