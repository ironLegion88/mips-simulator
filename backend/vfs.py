class VirtualFileSystem:
    """
    Sandboxed Virtual File System to intercept SPIM/MARS file I/O syscalls.
    Prevents the simulator from accessing the host OS file system.
    """
    def __init__(self):
        self.files = {} # fd -> file object or mock
        self.next_fd = 3 # 0: stdin, 1: stdout, 2: stderr
        
        # We can simulate in-memory files using strings or byte arrays
        # For simplicity, we store the content as a string
        self.file_contents = {} # path -> content

    def open(self, filename, flags, mode):
        """Syscall 13: Open file"""
        fd = self.next_fd
        self.next_fd += 1
        
        if flags == 0: # Read
            content = self.file_contents.get(filename, "")
            self.files[fd] = {"content": content, "pos": 0, "mode": "r"}
        elif flags == 1: # Write
            self.files[fd] = {"content": "", "pos": 0, "mode": "w"}
        else: # Append or other
            content = self.file_contents.get(filename, "")
            self.files[fd] = {"content": content, "pos": len(content), "mode": "w"}
            
        return fd

    def read(self, fd, length):
        """Syscall 14: Read from file"""
        if fd == 0: # stdin not handled here usually
            return ""
        if fd not in self.files or self.files[fd]["mode"] != "r":
            return -1
            
        f = self.files[fd]
        pos = f["pos"]
        data = f["content"][pos:pos+length]
        f["pos"] += len(data)
        return data

    def write(self, fd, data):
        """Syscall 15: Write to file"""
        if fd == 1 or fd == 2:
            return len(data)
            
        if fd not in self.files or self.files[fd]["mode"] != "w":
            return -1
            
        f = self.files[fd]
        f["content"] += data
        f["pos"] += len(data)
        return len(data)

    def close(self, fd):
        """Syscall 16: Close file"""
        if fd in self.files:
            # If writing, we could optionally commit it to file_contents
            if self.files[fd]["mode"] == "w":
                 # Find filename? We don't track it in this simple dict, but we could.
                 pass
            del self.files[fd]
            return 0
        return -1
