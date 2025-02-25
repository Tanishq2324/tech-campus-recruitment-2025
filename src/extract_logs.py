import os
import sys
import datetime
import re
import argparse
from datetime import datetime, timedelta
import mmap

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Extract logs for a specific date from a large log file.')
    parser.add_argument('date', type=str, help='Date in format YYYY-MM-DD')
    parser.add_argument('--file', type=str, default='logs_2024.log', 
                        help='Path to the log file')
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Directory for output files')
    return parser.parse_args()

def validate_date(date_str):
    """Validate the input date string and convert to datetime object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Invalid date format. Please use YYYY-MM-DD format.")
        sys.exit(1)

def get_file_size(file_path):
    """Get the size of the file in bytes."""
    return os.path.getsize(file_path)

def estimate_position(file_size, target_date, start_date, end_date):
    """
    Estimate position in file based on date range.
    Since logs are evenly distributed, we can estimate the position based on dates.
    """
    # Calculate the total days in the log range
    total_days = (end_date - start_date).days
    
    # Calculate the target day's position in that range
    target_days = (target_date - start_date).days
    
    # Estimate the position in the file
    if total_days == 0:  # Avoid division by zero
        return 0
    
    estimated_position = int(file_size * (target_days / total_days))
    return max(0, estimated_position)  # Ensure we don't return negative values

def find_first_timestamp_in_chunk(file_obj, position, chunk_size=8192):
    """
    Search for the first complete timestamp in a chunk starting from the given position.
    Returns the position of the start of the line with the timestamp and the timestamp itself.
    """
    # Seek to the position
    file_obj.seek(max(0, position - chunk_size // 2))
    
    # Read a chunk
    chunk = file_obj.read(chunk_size)
    
    # Find the next newline
    newline_pos = chunk.find(b'\n')
    if newline_pos != -1:
        # Move to the start of the next line
        file_obj.seek(max(0, position - chunk_size // 2) + newline_pos + 1)
    
    # Read a line which should now start with a timestamp
    line = file_obj.readline()
    
    # Extract the timestamp using regex
    timestamp_match = re.match(rb'(\d{4}-\d{2}-\d{2})', line)
    
    if timestamp_match:
        timestamp_str = timestamp_match.group(1).decode('utf-8')
        try:
            timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d")
            return file_obj.tell() - len(line), timestamp
        except ValueError:
            # If the regex matched but the datetime parsing failed, try the next line
            return find_first_timestamp_in_chunk(file_obj, file_obj.tell(), chunk_size)
    else:
        # If no timestamp found, try another position
        return find_first_timestamp_in_chunk(file_obj, file_obj.tell(), chunk_size)

def binary_search_date(file_path, target_date, file_size, start_date, end_date):
    """
    Use binary search to find the approximate position where logs for the target date start.
    Returns the position in the file where to start reading.
    """
    with open(file_path, 'rb') as f:
        # Create memory-mapped file object for faster access
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
            # Initialize binary search bounds
            left = 0
            right = file_size
            
            # Binary search loop
            while left < right:
                mid = (left + right) // 2
                
                # Find a complete log entry near the middle
                try:
                    pos, date = find_first_timestamp_in_chunk(mm, mid)
                    
                    # Compare the found date with the target date
                    if date.date() < target_date.date():
                        left = pos + 1
                    else:
                        right = pos
                except Exception as e:
                    # If we encounter an error, adjust the search space
                    print(f"Warning: Error during binary search at position {mid}: {e}")
                    
                    # Estimate a new position based on the target date
                    estimated_pos = estimate_position(file_size, target_date, start_date, end_date)
                    
                    # Move the search space
                    if mid > estimated_pos:
                        right = mid - 1
                    else:
                        left = mid + 1
            
            # Once we've narrowed down the position, find the first log entry for the target date
            # Start searching a bit before the identified position to ensure we don't miss anything
            search_start = max(0, left - 100000)  # Look back ~100KB to be safe
            mm.seek(search_start)
            
            # Find the first line that starts with a date
            line = mm.readline()
            while line:
                timestamp_match = re.match(rb'(\d{4}-\d{2}-\d{2})', line)
                if timestamp_match:
                    timestamp_str = timestamp_match.group(1).decode('utf-8')
                    try:
                        entry_date = datetime.strptime(timestamp_str, "%Y-%m-%d")
                        # If we found an entry with a date before our target, keep searching
                        if entry_date.date() < target_date.date():
                            line = mm.readline()
                            continue
                        # If we found our target date or later, return this position
                        return search_start + (mm.tell() - len(line))
                    except ValueError:
                        pass
                
                line = mm.readline()
                search_start = mm.tell() - len(line)
            
            # If we couldn't find the exact start, return the estimated position
            return estimate_position(file_size, target_date, start_date, end_date)

def get_log_date_range(file_path):
    """
    Determine the date range of logs in the file.
    Returns tuple of (start_date, end_date).
    """
    start_date = None
    end_date = None
    
    with open(file_path, 'rb') as f:
        # Check the beginning of the file
        line = f.readline()
        timestamp_match = re.match(rb'(\d{4}-\d{2}-\d{2})', line)
        if timestamp_match:
            start_date_str = timestamp_match.group(1).decode('utf-8')
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        
        # Go to the end of the file and read the last few lines
        f.seek(max(0, os.path.getsize(file_path) - 50000))  # Read last ~50KB
        last_lines = f.read()
        last_timestamp_match = re.findall(rb'(\d{4}-\d{2}-\d{2})', last_lines)
        if last_timestamp_match:
            end_date_str = last_timestamp_match[-1].decode('utf-8')
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    # If we couldn't determine the date range, use reasonable defaults
    if not start_date:
        start_date = datetime.now() - timedelta(days=365*3)  # Assume 3 years of logs
    if not end_date:
        end_date = datetime.now()
    
    return start_date, end_date

def extract_logs_for_date(file_path, start_position, target_date, output_file):
    """
    Extract logs for the specified date starting from the given position.
    Writes matching logs to the output file.
    """
    target_date_str = target_date.strftime("%Y-%m-%d")
    next_date = (target_date + timedelta(days=1)).strftime("%Y-%m-%d")
    
    count = 0
    with open(file_path, 'rb') as f:
        with open(output_file, 'w', encoding='utf-8') as out:
            f.seek(start_position)
            
            # Read and process lines until we reach the next day
            for line in f:
                try:
                    line_decoded = line.decode('utf-8', errors='replace')
                    
                    # Check if the line starts with our target date
                    if line_decoded.startswith(target_date_str):
                        out.write(line_decoded)
                        count += 1
                    
                    # If we've reached the next day, we're done
                    elif line_decoded.startswith(next_date):
                        break
                    
                    # Skip lines that don't start with a date (might be continuation of a previous log)
                    # But check if we need to handle multiline logs that should be included
                    elif count > 0 and not re.match(r'^\d{4}-\d{2}-\d{2}', line_decoded):
                        out.write(line_decoded)
                except UnicodeDecodeError:
                    # Handle potential decode errors gracefully
                    continue
    
    return count

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Validate input date
    target_date = validate_date(args.date)
    
    # Set output directory to "output" regardless of args
    output_dir = "../output"
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Define output file path
    output_file = os.path.join(output_dir, f"output_{args.date}.txt")
    
    print(f"Extracting logs for {args.date} from {args.file}")
    
    # Check if file exists
    if not os.path.exists(args.file):
        print(f"Error: File {args.file} does not exist.")
        sys.exit(1)
    
    # Get file size
    file_size = get_file_size(args.file)
    print(f"Log file size: {file_size / (1024**3):.2f} GB")
    
    # Get log date range
    start_date, end_date = get_log_date_range(args.file)
    print(f"Log date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Check if target date is within range
    if target_date.date() < start_date.date() or target_date.date() > end_date.date():
        print(f"Warning: Target date {args.date} is outside the log date range.")
    
    # Find the start position for the target date
    print("Searching for target date position...")
    start_position = binary_search_date(args.file, target_date, file_size, start_date, end_date)
    print(f"Starting extraction from position {start_position}")
    
    # Extract logs for the target date
    count = extract_logs_for_date(args.file, start_position, target_date, output_file)
    
    print(f"Extracted {count} log entries for {args.date}")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main()