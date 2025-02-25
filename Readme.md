# Problem Statement: Efficient Log Retrieval from a Large File

### Run This Command in the terminal:

```bash
python3 src/extract_logs.py 2024-10-4
```

## Overview

This tool efficiently extracts log entries for a specific date from extremely large log files (up to 1TB in size). It was designed to handle massive log archives while optimizing for both speed and memory usage.

The tool uses a sophisticated binary search approach combined with memory mapping to quickly locate relevant sections of the log file without having to scan the entire file sequentially. This makes it practical to work with log files that would otherwise be too large to process efficiently.

## Features

- **Efficient Extraction**: Extract logs for a specific date from a 1TB file in minutes, not hours
- **Memory-Optimized**: Designed to work with minimal RAM requirements
- **Simple Interface**: Easy command-line usage with minimal parameters
- **Robust Error Handling**: Gracefully handles various error conditions
- **Flexible Output**: Creates organized output files in a dedicated directory

## Problem Being Solved

Many organizations maintain massive log archives spanning multiple years. When troubleshooting or analyzing issues, engineers often need to extract logs from a specific date. With traditional tools, this can be prohibitively slow or resource-intensive when dealing with terabyte-scale log files.

This tool addresses that challenge by implementing a smart search strategy that can pinpoint the relevant section of logs without scanning the entire file.

## Requirements

- Python 3.6 or higher
- Read access to the log file
- Sufficient disk space for output files
- Standard Python libraries (no additional packages required)

## Installation

1. Clone the repository or download the script:

```bash
git clone https://github.com/Tanishq2324/tech-campus-recruitment-2025.git
# OR 
```

2. Make the script executable:

```bash
chmod +x src/extract_logs.py
```

## Usage

### Basic Usage

Extract logs for a specific date:

```bash
python src/extract_logs.py 2024-12-01
```

This will:
- Extract all logs from December 1, 2024
- Save the results to `output/output_2024-12-01.txt`

### Advanced Usage

Specify a custom log file path:

```bash
python extract_logs.py 2024-12-01 --file /path/to/your/logfile.log
```

### Expected Log Format

The tool expects logs to follow this format:

```
YYYY-MM-DD [additional timestamp info] [log level] [message]
```

For example:

```
2024-12-01 12:34:56 INFO User login successful
2024-12-01 12:35:12 ERROR Database connection failed
```

The timestamp format at the beginning of each line is critical for the binary search algorithm to work correctly.

## How It Works

1. **Date Range Discovery**: The tool first examines the beginning and end of the log file to determine the overall date range.

2. **Position Estimation**: Since logs are assumed to be evenly distributed across days, the tool calculates an estimated position in the file based on the target date's position in the date range.

3. **Binary Search**: Starting from the estimated position, the tool uses binary search to narrow down the exact position where logs for the target date begin.

4. **Extraction**: Once the starting position is found, the tool extracts all logs for the target date and saves them to an output file.

5. **Multiline Handling**: The tool properly handles multiline log entries to ensure they are extracted correctly.

## Performance Considerations

- **Time Complexity**: O(log n) for finding the start position, where n is the file size
- **Space Complexity**: O(m) where m is the size of the extracted logs for the target date
- **Disk I/O**: The tool minimizes disk reads by using targeted searches rather than sequential scans

## Example

For a 1TB log file covering 3 years of logs:

```bash
$ python extract_logs.py 2024-12-01
Extracting logs for 2024-12-01 from /var/log/large_log_file.log
Log file size: 1024.00 GB
Log date range: 2022-02-25 to 2025-02-25
Searching for target date position...
Starting extraction from position 984301934592
Extracted 2893742 log entries for 2024-12-01
Results saved to output/output_2024-12-01.txt
```

## Limitations

- The tool assumes logs are roughly evenly distributed by date
- Logs must have a consistent timestamp format at the beginning of each line
- The tool is optimized for date-based extraction, not for other query parameters

