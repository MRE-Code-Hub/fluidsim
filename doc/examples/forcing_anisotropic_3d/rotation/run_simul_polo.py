#!/usr/bin/env python
"""

For help, run

```
./run_simul_polo.py -h
```

"""
from fluidsim.util.scripts.turb_rotation_trandom_anisotropic import main

if __name__ == "__main__":

    params, sim = main(Ro=0.1, Re=100)
