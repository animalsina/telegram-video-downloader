"""
Module for compressing video files using ffmpeg.

"""
import asyncio
import os
import re
from pathlib import Path
from typing import Union, Callable, AnyStr, Awaitable
import ffmpeg

from func.messages import t

COMPRESSION_STATE_NOT_COMPRESSED = 0
COMPRESSION_STATE_COMPRESSED = 1
COMPRESSION_STATE_COMPRESSION_FAILED = 2

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

    if crf <= 18:
        compression_factor = 1.2
    elif crf <= 23:
        compression_factor = 1.0
    elif crf <= 28:
        compression_factor = 0.75
    else:
        compression_factor = 0.5

    estimated_output_size_mb = file_size_mb * compression_factor

    print(f"Estimated output size: {estimated_output_size_mb:.2f} MB")
    if estimated_output_size_mb >= file_size_mb:
        print("Compression would increase the file size. Skipping compression.")
        return False
    return True

async def compress_video_h265(
    input_file: Path,
    output_file: Path,
    crf: int = 28,
    min_size_mb: int = 50,
    callback: Union[Callable[[AnyStr], None], Callable[[AnyStr], Awaitable[None]]] | None = None
) -> COMPRESSION_STATE_COMPRESSION_FAILED | COMPRESSION_STATE_COMPRESSED | COMPRESSION_STATE_NOT_COMPRESSED:
    """
    Compress a video file from H.264 to H.265 using ffmpeg.
    """

    # Pre-compression checks
    if not is_valid_input_file(input_file, min_size_mb):
        return COMPRESSION_STATE_NOT_COMPRESSED

    # File size and compression check
    file_size_mb = input_file.stat().st_size / (1024 * 1024)
    if not should_compress(file_size_mb, crf):
        return COMPRESSION_STATE_NOT_COMPRESSED

    # Ensure output path is writable
    if not remove_existing_output(output_file):
        return COMPRESSION_STATE_COMPRESSION_FAILED

    try:
        process = (
            ffmpeg
            .input(str(input_file))
            .output(str(output_file), vcodec='libx265', crf=crf,
                    preset='slow', tune='zerolatency', progress='pipe')
            .run_async(pipe_stdout=True, pipe_stderr=True)
        )

        # Handle process output and progress
        while True:
            output = await asyncio.to_thread(process.stderr.read, 4096)
            output = output.decode('utf-8') if output else ''
            if output:
                lines = output.splitlines()
                last_line = lines[-1]
                match = re.search(r'time=(\d{2}:\d{2}:\d{2}\.\d{2})', last_line)
                time_value = match.group(1) if match else None

                if time_value is not None and callback:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(time_value)
                    else:
                        callback(time_value)
                elif time_value is not None:
                    print(f"Progress: {time_value}")

            if process.poll() is not None:
                break

        # Check if the output file was successfully created
        if output_file.exists() and output_file.stat().st_size > 0:
            print(f"Compression completed successfully! File saved: {output_file}")
            return COMPRESSION_STATE_COMPRESSED

        print("Compression failed: Output file not created or is empty.")
        return COMPRESSION_STATE_COMPRESSION_FAILED

    except Exception as exception: # pylint: disable=broad-exception-caught
        print(f"Error during compression: {exception}")
        return COMPRESSION_STATE_COMPRESSION_FAILED
