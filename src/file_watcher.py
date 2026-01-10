"""
File Watcher Module
Handles file system events for new XML files.
"""
import time
from watchdog.events import FileSystemEventHandler

class XMLFileHandler(FileSystemEventHandler):
    """Watch for new/modified/deleted XML files."""
    
    def __init__(self, on_file_callback, on_delete_callback=None):
        self.on_file_callback = on_file_callback
        self.on_delete_callback = on_delete_callback
        self.last_path = None
        self.last_time = 0
    
    def _process_file_event(self, event):
        if event.is_directory:
            return
        
        filename = event.src_path
        if not filename.lower().endswith('.xml'):
            return
            
        current_time = time.time()
        
        # Simple debounce (avoid duplicate events within 1.0 second)
        if filename == self.last_path and (current_time - self.last_time) < 1.0:
            return
            
        self.last_path = filename
        self.last_time = current_time
        self.on_file_callback(filename)

    def on_created(self, event):
        self._process_file_event(event)
        
    def on_modified(self, event):
        self._process_file_event(event)
        
    def on_moved(self, event):
        """Handle file moved INTO the monitored folder."""
        if event.is_directory:
            return
        
        # Use dest_path since that's where the file ended up
        filename = event.dest_path
        if not filename.lower().endswith('.xml'):
            return
        
        current_time = time.time()
        
        # Apply same debounce logic
        if filename == self.last_path and (current_time - self.last_time) < 1.0:
            return
        
        self.last_path = filename
        self.last_time = current_time
        self.on_file_callback(filename)
    
    def on_deleted(self, event):
        """Handle file deletion."""
        if event.is_directory:
            return
        
        filename = event.src_path
        if not filename.lower().endswith('.xml'):
            return
        
        if self.on_delete_callback:
            self.on_delete_callback(filename)
