from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from typing import List, Tuple, Any

def condense_data_points(records: List[Any], timestamp_attr: str = 'timestamp', value_attr: str = 'reached_life', window: str = 'day') -> List[Tuple[datetime, float]]:
    """
    Condense time series data points by averaging values within time windows.
    
    Args:
        records: List of records with timestamp and value attributes
        timestamp_attr: Name of the timestamp attribute on records
        value_attr: Name of the value attribute to average
        window: Time window to group by ('day', 'week', or 'month')
    
    Returns:
        List of (timestamp, average_value) tuples
    """
    # Group records by time window
    grouped_data = defaultdict(list)
    for record in records:
        timestamp = getattr(record, timestamp_attr)
        value = getattr(record, value_attr)
        
        if window == 'day':
            key = timestamp.date()
        elif window == 'week':
            # Get start of week (Monday)
            key = timestamp.date() - timedelta(days=timestamp.weekday())
        elif window == 'month':
            key = timestamp.replace(day=1).date()
        else:
            raise ValueError(f"Invalid window type: {window}")
        
        grouped_data[key].append(value)
    
    # Calculate averages for each window
    condensed_records = []
    for date, values in sorted(grouped_data.items()):
        avg_value = np.mean(values)
        timestamp = datetime.combine(date, datetime.min.time())
        condensed_records.append((timestamp, avg_value))
    
    return condensed_records

def get_condensed_data(records: List[Any], max_points: int = 100, timestamp_attr: str = 'timestamp', value_attr: str = 'reached_life') -> List[Tuple[datetime, float]]:
    """
    Get condensed data points, automatically choosing the appropriate time window
    to keep the number of points under max_points.
    
    Args:
        records: List of records with timestamp and value attributes
        max_points: Maximum number of points to return
        timestamp_attr: Name of the timestamp attribute on records
        value_attr: Name of the value attribute to average
    
    Returns:
        List of (timestamp, average_value) tuples
    """
    # Start with raw data points
    condensed_data = [(getattr(record, timestamp_attr), getattr(record, value_attr)) 
                      for record in records]
    
    # Condense data if needed
    windows = ['day', 'week', 'month']
    window_idx = 0
    while len(condensed_data) > max_points and window_idx < len(windows):
        condensed_data = condense_data_points(records, timestamp_attr, value_attr, windows[window_idx])
        window_idx += 1

    condensed_data_list = []
    for data_point in condensed_data:
        condensed_data_list.append([data_point[0].isoformat(), data_point[1]])

    return condensed_data_list
