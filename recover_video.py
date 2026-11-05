"""Experimental Pocket4P salvage for the portrait HEVC profile used by clip 0153.
Recovered pictures only: audio and original timestamps are not reconstructed.
"""
import argparse
import mmap
import struct
import subprocess
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent


def ffmpeg_path():
    binaries = BASE / 'vendor' / 'imageio_ffmpeg' / 'binaries'
    matches = sorted(binaries.glob('ffmpeg-*.exe'))
    if not matches:
        raise RuntimeError('FFmpeg is missing. Run Установить.cmd first.')
    return matches[0]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', nargs='?')
    parser.add_argument('--preview-seconds', type=float)
    args = parser.parse_args()
    source = Path(args.source or input('Path to recovered MP4: ').strip().strip('"')).resolve()
    ffmpeg = ffmpeg_path()
    if not source.is_file() or source.suffix.lower() != '.mp4':
        raise ValueError('Select a recovered MP4 file, not LRF or TRINF.')
    if source.stat().st_size < 4096:
        raise ValueError('The input is too small for this recovery method.')
    folder = BASE / 'results' / (source.stem + '_' + uuid.uuid4().hex[:8])
    folder.mkdir(parents=True)
    raw, output = folder / 'extracted.hevc', folder / 'recovered_no_audio.mp4'
    print('Profile: portrait Pocket4P used by clip 0153. Other settings may not work.', flush=True)
    print('Reading input and searching for video packets...', flush=True)
    with source.open('rb') as handle, mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ) as data:
        events = []
        for marker in (b'\x28\x01', b'\x26\x01', b'\x02\x01'):
            position = 4096
            while True:
                position = data.find(marker, position)
                if position < 0:
                    break
                if position + 3 < len(data):
                    length = struct.unpack_from('>I', data, position - 4)[0]
                    flags = data[position + 2]
                    keyframe = marker != b'\x02\x01'
                    valid = flags & 0xe0 == 0xa0 if keyframe else flags & 0xf8 == 0xd0
                    if valid and 1000 < length < 2000000 and position + length <= len(data):
                        events.append((position, length, keyframe))
                position += 2
        end, selected, started = 0, 0, False
        with raw.open('xb') as dest:
            dest.write((BASE / 'portrait_0153.hevc').read_bytes())
            for position, length, keyframe in sorted(events):
                if position < end or (not started and not keyframe):
                    continue
                started = True
                dest.write(b'\x00\x00\x00\x01' + data[position:position + length])
                end = position + length
                selected += 1
    if not selected:
        raise ValueError('No candidate video packets found. This method cannot recover this file.')
    print(f'{selected} candidate packets. Encoding a playable copy...', flush=True)
    cmd = [str(ffmpeg), '-hide_banner', '-fflags', '+discardcorrupt',
           '-err_detect', 'ignore_err', '-r', '60000/1001', '-i', str(raw)]
    if args.preview_seconds is not None:
        cmd += ['-t', str(args.preview_seconds)]
    cmd += ['-vf', 'scale=-2:1920', '-c:v', 'libx264', '-preset', 'fast', '-crf', '20',
            '-pix_fmt', 'yuv420p', '-an', '-movflags', '+faststart', '-n', str(output)]
    with (folder / 'repair.log').open('wb') as log:
        result = subprocess.run(cmd, stdout=log, stderr=log)
    if result.returncode or not output.exists() or output.stat().st_size < 4096:
        raise RuntimeError(f'Recovery failed. Details: {folder / "repair.log"}')
    print('Checking the output...', flush=True)
    with (folder / 'validation.log').open('wb') as log:
        check = subprocess.run([str(ffmpeg), '-v', 'error', '-i', str(output),
                                '-map', '0:v:0', '-f', 'null', '-'], stdout=log, stderr=log)
    print('Output: ' + str(output), flush=True)
    print('Check: ' + ('decoded' if check.returncode == 0 else 'decoder errors; see validation.log'))
    print('Watch the video: successful encoding does NOT guarantee intact pictures.')
    print('No audio. Timing is approximate. Keep the original input.')

if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        print('ERROR: ' + str(error))
        raise SystemExit(1)
