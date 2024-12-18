"""
Module for compressing video files using ffmpeg.

"""
import asyncio
import os
import time
import subprocess

from pathlib import Path
from typing import Union, Callable, Awaitable
import ffmpeg

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
    :return:
    """
    result = subprocess.run(
        ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'format=size', '-of',
         'default=noprint_wrappers=1', str(file_path)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True
    )

    size = result.stdout.decode().strip()
    return int(size)

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
    if not remove_existing_output(output_file):
        return COMPRESSION_STATE_COMPRESSION_FAILED_BAD_TRASH_FILE

    try:
        start_time = time.time()  # Tempo di inizio
        estimated_size = compression_ratio_calc(file_size_mb, crf)

        process = (
            ffmpeg
            .input(str(input_file))
            .output(str(output_file), vcodec='libx265', crf=crf,
                    preset='slow', tune='zerolatency', progress='pipe')
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        last_value_is_same = 0
        last_value = 0
        # Handle process output and progress
        while process.poll() is None:
            from func.main import operation_status
            # Calcola la dimensione attuale del file
            current_size = get_file_size(output_file)
            progress = progress_calc(output_file, estimated_size)
            remaining_time_value = remaining_time(output_file, start_time, estimated_size)

            if last_value_is_same >= 30:
                raise InterruptedError('Last value is same')

            if operation_status.quit_program is True:
                raise InterruptedError('Stop Compression')

            if last_value == current_size:
                last_value_is_same += 1
            else:
                last_value = current_size
                last_value_is_same = 0

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

            print('\r' + t('trace_compress_action',
                    f"{progress:.2f}%",
                    current_size, f"{remaining_time_value:.2f}"
                    ), end='', flush=True)

            if current_size / (1024 * 1024) >= estimated_size:
                return COMPRESSION_STATE_NOT_COMPRESSED_EXCEED_COMPRESSION_SIZE

            await asyncio.sleep(2)

        current_size = os.path.getsize(output_file)
        progress = progress_calc(output_file, estimated_size)
        remaining_time_value = remaining_time(output_file, start_time, estimated_size)

        if callback:
            if asyncio.iscoroutinefunction(callback):
                await callback(progress, current_size, remaining_time_value)
            else:
                callback(progress, current_size, remaining_time_value)

        # Check if the output file was successfully created
        if output_file.exists() and output_file.stat().st_size > 0:
            print(f"Compression completed successfully! File saved: {output_file}")
            return COMPRESSION_STATE_COMPRESSED

        print("Compression failed: Output file not created or is empty.")
        return COMPRESSION_STATE_COMPRESSION_FAILED_NOT_OUTPUT_FILE

    except Exception as exception:  # pylint: disable=broad-exception-caught
        print(f"Error during compression: {exception}")
        return COMPRESSION_STATE_COMPRESSION_FAILED


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
