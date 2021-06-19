# import numpy as np, pandas as pd, matplotlib.pyplot as plt
# from os.path import join
# from IPython.core.display import display, HTML
# import plotting

# from COVID19.model import Model, Parameters, ModelParameterException
# import COVID19.simulation as simulation

# input_parameter_file = "../tests/data/baseline_parameters.csv"
# parameter_line_number = 1
# output_dir = "results"
# household_demographics_file = "../tests/data/baseline_household_demographics.csv"
# hospital_file = "../tests/data/hospital_baseline_parameters.csv"


# params = Parameters(
#     input_parameter_file, 
#     parameter_line_number, 
#     output_dir, 
#     household_demographics_file,
#     hospital_file)


# df_parameters = pd.read_csv(input_parameter_file)
# print(df_parameters['centralized_quarantine_length_traced_positive'])
# df_parameters_used = plotting.get_df_from_params(params, df_parameters.columns)
# print(df_parameters_used['centralized_quarantine_length_traced_positive'])



import example_utils as utils
params = utils.get_baseline_parameters()
params.set_param( "n_total", 100000 )

sim = utils.get_simulation( params )
sim.env.model.get_param('health_code_system_on')
sim.env.model.update_running_params('health_code_system_on', 1)
sim.steps( 100 )