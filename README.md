# Multi-Video & Image Compressor

A simple tool to save disk space on your devices by compressing videos and images, while preserving metadata and directory structure.

## Key Features

*   **Video & Image Compression:** Compresses videos using `ffmpeg` and images using `Pillow`.
*   **Metadata Preservation:** Preserves video metadata and image EXIF data.
*   **Timestamp Preservation:** Copies file timestamps (modification time, access time) and optionally sets the creation date to the earliest available date from file metadata.
*   **Directory Structure Replication:** Replicates the source directory structure in the target directory for easy replacement of files on your devices.
*   **GUI Interface:** A simple graphical user interface built with `tkinter`.
*   **Configurable Compression:** Adjust video compression quality (CRF), resolution, and image compression settings.
*   **Incremental Processing:** Only processes new files that are not already present in the destination directory.

## How it Works

The application scans a source directory for video and image files, then compresses them according to your settings. The compressed files are saved in a target directory, maintaining the original folder structure. This allows you to easily copy the compressed files back to your device, replacing the original, larger files.

## Installation

1.  **Prerequisites:**
    *   **Python 3:** Make sure you have Python 3 installed.
    *   **FFmpeg:** You must have `ffmpeg` and `ffprobe` installed and available in your system's PATH. You can download it from [ffmpeg.org](https://ffmpeg.org/download.html).

2.  **Install Python Libraries:**
    Install the required Python libraries using pip:

    ```bash
    pip install Pillow pywin32
    ```

## Usage

1.  **Run the application:**
    ```bash
    python video_compressor.py
    ```

2.  **Using the GUI:**
    *   **Source Directory:** Select the folder containing the videos and images you want to compress.
    *   **Target Directory:** Select the folder where you want to save the compressed files.
    *   **Video Settings:**
        *   **Compression (CRF):** Adjust the Constant Rate Factor (CRF) for video compression. Lower values mean higher quality and larger file sizes (18-22 is high quality, 23-28 is a good compromise, 29+ is high compression).
        *   **Resolution (Height):** Choose the desired output resolution for videos. "Original" keeps the original resolution.
    *   **Image Settings:**
        *   **Compress images:** Enable or disable image compression.
        *   **Compress if > (MB):** Only compress images larger than this size.
        *   **Max Resolution (px):** The maximum height or width for resized images.
        *   **JPG Quality (%):** The quality of the compressed JPEG images (1-100).
    *   **Timestamp Settings:**
        *   **Use earliest available date...:** If checked, the application will try to find the earliest timestamp from the file's metadata (e.g., "Date Taken") and use it as the creation date for the new file.
    *   **Start Processing:** Click this button to begin the compression process.

## Contributing

Contributions are welcome! If you have any ideas, suggestions, or bug reports, please open an issue or create a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.