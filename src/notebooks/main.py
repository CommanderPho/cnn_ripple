import sys
import importlib
from pathlib import Path
from copy import deepcopy
# from numba import jit
import numpy as np
import pandas as pd
from cnn_ripple_ripple.PhoRippleDetectionTesting import ExtendedRippleDetection, main_compute_with_params_loaded_from_xml

if __name__ == '__main__':
	local_session_parent_path = Path(r'W:\Data\KDIBA\gor01\one')
	local_session_names_list = ['2006-6-07_11-26-53', '2006-6-08_14-26-15', '2006-6-09_1-22-43', '2006-6-09_3-23-37', '2006-6-12_15-55-31', '2006-6-13_14-42-6']
	local_session_paths_list = [local_session_parent_path.joinpath(a_name).resolve() for a_name in local_session_names_list]

	active_local_session_path: Path = local_session_paths_list[0] # completed: 0, 1, 2, 3, 4, 5 
	test_detector, ripple_df, out_all_ripple_results = main_compute_with_params_loaded_from_xml(active_local_session_path)
	print('ALL DONE.')


