import signal
import subprocess
from pathlib import Path


def mount(path: Path, write=False):
    return f"-v {path}:{path}:{'rw' if write else 'ro'}"

def run_shell_command(command:str, shell=False):
    try:
        p = subprocess.Popen(command, shell=shell)
        while p.returncode == None:
            try:
                p.wait(1)
            except subprocess.TimeoutExpired:
                continue
        if p.returncode != 0:
            raise RuntimeError(f"Error running command {command}")
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait(10)
        raise KeyboardInterrupt()