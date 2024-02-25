# -*- coding: utf-8 -*-
"""
Created on Sun Feb 25 15:24:45 2024

@author: founta
"""

import subprocess
from pathlib import Path

if __name__ == "__main__":
    output_fname = Path("dist") / "main.exe"
    desired_fname = Path("dist") / "vrc_show_hr.exe"
    subprocess.run(["pyinstaller", "main.py", "-F", "--collect-all=sanic", "--collect-all=tracerite"])
    
    with open(desired_fname, "wb") as f_out:
        with open(output_fname, "rb") as f_in:
            f_out.write(f_in.read())
    output_fname.unlink()