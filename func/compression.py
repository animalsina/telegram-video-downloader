"""
Module for compressing video files using ffmpeg.

"""
import asyncio
import subprocess
import os
import time

from pathlib import Path
from typing import Union, Callable, Awaitable

from func.messages import t

COMPRESSION_STATE_NOT_COMPRESSED = 0
COMPRESSION_STATE_COMPRESSED = 1
COMPRESSION_STATE_COMPRESSION_FAILED = 2
COMPRESSION_STATE_COMPRESSION_FAILED_NOT_OUTPUT_FILE = 3
COMPRESSION_STATE_NOT_COMPRESSED_EXCEED_COMPRESSION_SIZE = 4
COMPRESSION_STATE_COMPRESSION_FAILED_BAD_TRASH_FILE = 5


def is_valid_input_file(input_file: Path, min_size_mb: int) -> bool:
    """Check if input file exists and is large enough to be compressed."""
    if not input_file.exists() or not input_file.is_file():
        print(f"Input file does not exist or is not a valid file: {input_file}")
        return False
    file_size_mb = input_file.stat().st_size / (1024 * 1024)
    if file_size_mb < min_size_mb:
        print(t("file_too_small", file_size_mb, min_size_mb))
        return False
    return True


def remove_existing_output(output_file: Path) -> bool:
    """Attempt to remove an existing output file."""
    if output_file.exists():
        try:
            os.remove(output_file)
            print(f"Existing output file removed: {output_file}")
            return True
        except OSError as e:
            print(f"Failed to remove existing output file: {output_file}, Error: {e}")
            return False
    return True


def should_compress(file_size_mb: float, crf: int) -> bool:
    """Check if compression will actually reduce the file size."""

    estimated_output_size_mb = compression_ratio_calc(file_size_mb, crf)

    print(f"Estimated output size: {estimated_output_size_mb:.2f} MB")
    if estimated_output_size_mb >= file_size_mb:
        print("Compression would increase the file size. Skipping compression.")
        return False
    return True


def compression_ratio(crf: int) -> float:
    """
    Calculate the compression ratio.
    :param crf:
    :return:
    """
    if crf <= 18:
        compression_factor = 1.2
    elif crf <= 23:
        compression_factor = 1.0
    elif crf <= 28:
        compression_factor = 0.75
    else:
        compression_factor = 0.5

    return compression_factor


def compression_ratio_calc(file_size_mb: float, crf: int) -> float:
    """
    Calculate the compression ratio.
    :param file_size_mb:
    :param crf:
    :return:
    """
    return file_size_mb * compression_ratio(crf)


def get_file_size(file_path: Path) -> float:
    """
    Get the size of a file in MB.
    :param file_path:
    :return: file size in MB, or 0 if there is an error
    """
    # Verifica che il file esista
    if not file_path.exists():
        return 0

    return file_path.stat().st_size

# pylint: disable=all
async def compress_video_h265(
        input_file: Path,
        output_file: Path,
        crf: int = 28,
        min_size_mb: int = 50,
        callback:
        (Union[Callable[[float, float, float], None],
        Callable[[float, float, float], Awaitable[None]]])
        | None = None
) -> (
        COMPRESSION_STATE_COMPRESSION_FAILED |
        COMPRESSION_STATE_COMPRESSED |
        COMPRESSION_STATE_NOT_COMPRESSED |
        COMPRESSION_STATE_COMPRESSION_FAILED_NOT_OUTPUT_FILE |
        COMPRESSION_STATE_NOT_COMPRESSED_EXCEED_COMPRESSION_SIZE |
        COMPRESSION_STATE_COMPRESSION_FAILED_BAD_TRASH_FILE
):
    """
    Compress a video file from H.264 to H.265 using ffmpeg.
    """

    # Pre-compression checks
    if not is_valid_input_file(input_file, min_size_mb):
        return COMPRESSION_STATE_NOT_COMPRESSED

    # File size and compression check
    file_size_mb = input_file.stat().st_size / (1024 * 1024)
    if not should_compress(file_size_mb, crf):
        return COMPRESSION_STATE_NOT_COMPRESSED_EXCEED_COMPRESSION_SIZE

    # Ensure output path is writable
    #if not remove_existing_output(output_file):
    #    return COMPRESSION_STATE_COMPRESSION_FAILED_BAD_TRASH_FILE

    try:
        start_time = time.time()  # Start time

        # Calculate the estimated size of the compressed file
        file_size_mb = get_file_size(input_file)
        estimated_size = compression_ratio_calc(file_size_mb, crf)

        # Retrieve the current size of the compressed file
        current_size = get_file_size(output_file)

        # Determine the resumption point
        if current_size > 0:
            time_offset = calculate_offset(current_size, estimated_size, output_file)
            print(f"Resuming compression from {time_offset:.2f} seconds...")
        else:
            time_offset = 0

        process_completed = False

        # Start the ffmpeg process
        process = (
            subprocess.Popen(
                [
                    'ffmpeg', '-y', '-i', str(input_file),
                    '-ss', str(time_offset),
                    '-vcodec', 'libx265', '-crf', str(crf),
                    '-preset', 'slow', '-tune', 'zerolatency',
                    str(output_file)
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
        )

        last_value_is_same = 0
        last_value = get_file_size(output_file)

        # Progress monitoring
        while True:
            output = await asyncio.to_thread(process.stderr.read, 4096)
            output = output.decode('utf-8') if output else ''
            if output:
                # Get the current size of the file
                current_size = get_file_size(output_file)
                progress = (current_size / estimated_size) * 100
                remaining_time_value = (time.time() - start_time) / (progress / 100) if progress > 0 else 0

                if last_value_is_same >= 30:
                    raise InterruptedError('Last value is same')

                if last_value == current_size:
                    last_value_is_same += 1
                else:
                    last_value = current_size
                    last_value_is_same = 0

                # Callback to update status
                if callback:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(
                            progress,
                            current_size,
                            remaining_time_value)
                    else:
                        callback(
                            progress,
                            current_size,
                            remaining_time_value)

                print(
                    f"\rProgress: {progress:.2f}%, Size: {current_size:.2f} MB, Remaining Time: {remaining_time_value:.2f}s",
                    end='', flush=True)

                if current_size >= estimated_size:
                    return COMPRESSION_STATE_NOT_COMPRESSED_EXCEED_COMPRESSION_SIZE

            if process.poll() is not None:
                process_completed = True
                break

        # Verify the final file
        if output_file.exists() and output_file.stat().st_size > 0 and process_completed:
            print(f"Compression successfully completed! File saved: {output_file}")
            return COMPRESSION_STATE_COMPRESSED

        print("Compression failed: Output file not created or is empty.")
        return COMPRESSION_STATE_COMPRESSION_FAILED_NOT_OUTPUT_FILE

    except Exception as e:
        print(f"Error during compression: {e}")
        return COMPRESSION_STATE_COMPRESSION_FAILED

def get_video_duration(input_file: Path) -> float:
    """
    Get the total duration of a video file in seconds using ffprobe.
    :param input_file: Input video file
    :return: Duration in seconds
    """
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', str(input_file)],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
        )
        duration = float(result.stdout.decode().strip())
        return duration
    except Exception as e:
        print(f"Error retrieving video duration: {e}")
        return 0

def calculate_offset(current_size, estimated_size, input_file):
    """
    Calculate the time offset (in seconds) based on the current compressed size.
    :param current_size: Current size of the compressed file
    :param estimated_size: Estimated size of the compressed file
    :param input_file: Input video file
    :return: Time offset (in seconds)
    """
    total_duration = get_video_duration(Path(input_file))
    if estimated_size == 0:
        return 0
    return (current_size / estimated_size) * total_duration

def progress_calc(output_file: Path, estimated_size: float) -> float:
    """ Calculate the progress of the compression. """
    current_size = get_file_size(output_file)
    current_size_mb = current_size / (1024 * 1024)
    return (current_size_mb / estimated_size) * 100


def elapsed_time(start_time: float) -> float:
    """ Calculate the elapsed time. """
    return time.time() - start_time


def remaining_time(output_file: Path, start_time: float, estimated_size: float) -> float:
    """ Calculate the remaining time. """
    progress = progress_calc(output_file, estimated_size)
    return (elapsed_time(start_time) / progress) * (100 - progress) if progress > 0 else 0
