import matplotlib.pyplot as plt
import pickle as pl
import numpy as np
import sys

file = sys.argv[1]
# Load figure from disk and display
fig_handle = pl.load(open(file, 'rb'))
# import ipdb; ipdb.set_trace() # BREAKPOINT
plt.show()
# print('\nIgnore errors for now...\n--Caileigh')
