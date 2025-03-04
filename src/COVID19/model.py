import logging
import enum
from itertools import chain
from typing import Union
import pandas as pd
import pkg_resources
import sys, time

import covid19
from COVID19.network import Network

LOGGER = logging.getLogger(__name__)


class ModelParameterException(Exception):
    pass

class ParameterException(Exception):
    pass

class ModelException(Exception):
    pass

PYTHON_SAFE_UPDATE_PARAMS = [
    "test_on_symptoms",
    "test_on_traced",
    "quarantine_on_traced",
    "traceable_interaction_fraction",
    "tracing_network_depth",
    "allow_clinical_diagnosis",
    "quarantine_household_on_positive",
    "quarantine_household_on_symptoms",
    "quarantine_household_on_traced_positive",
    "quarantine_household_on_traced_symptoms",
    "quarantine_household_contacts_on_positive",
    "quarantine_household_contacts_on_symptoms",
    "quarantine_days",
    "test_order_wait",
    "test_order_wait_priority",
    "test_result_wait",
    "test_result_wait_priority",
    "self_quarantine_fraction",
    "lockdown_on",
    "lockdown_elderly_on",
    "app_turned_on",
    "app_users_fraction",
    "trace_on_symptoms",
    "trace_on_positive",
    "lockdown_house_interaction_multiplier",
    "lockdown_random_network_multiplier",
    "lockdown_occupation_multiplier_primary_network",
    "lockdown_occupation_multiplier_secondary_network",
    "lockdown_occupation_multiplier_working_network",
    "lockdown_occupation_multiplier_retired_network",
    "lockdown_occupation_multiplier_elderly_network",
    "manual_trace_on",
    "manual_trace_on_hospitalization",
    "manual_trace_on_positive",
    "manual_trace_delay",
    "manual_trace_exclude_app_users",
    "manual_trace_n_workers",
    "manual_trace_interviews_per_worker_day",
    "manual_trace_notifications_per_worker_day",
    "manual_traceable_fraction_household",
    "manual_traceable_fraction_occupation",
    "manual_traceable_fraction_random",
    "relative_transmission_household",
    "relative_transmission_occupation",
    "relative_transmission_random",
    "priority_test_contacts_0_9",
    "priority_test_contacts_10_19",
    "priority_test_contacts_20_29",
    "priority_test_contacts_30_39",
    "priority_test_contacts_40_49",
    "priority_test_contacts_50_59",
    "priority_test_contacts_60_69",
    "priority_test_contacts_70_79",
    "priority_test_contacts_80",
    "test_release_on_negative",
    "fatality_fraction_0_9",
    "fatality_fraction_10_19",
    "fatality_fraction_20_29",
    "fatality_fraction_30_39",
    "fatality_fraction_40_49",
    "fatality_fraction_50_59",
    "fatality_fraction_60_69",
    "fatality_fraction_70_79",
    "fatality_fraction_80",
]


class EVENT_TYPES(enum.Enum):
    SUSCEPTIBLE = 0
    PRESYMPTOMATIC = 1 # Pre-symptompatic, severe disease (progressing to symptomatic severe)
    PRESYMPTOMATIC_MILD = 2 # Pre-symptompatic, mild disease (progressing to symptomatic mild)
    ASYMPTOMATIC = 3 # Asymptompatic (progressing to recovered)
    SYMPTOMATIC = 4 # Symptompatic, severe disease
    SYMPTOMATIC_MILD = 5 # Symptompatic, mild disease
    HOSPITALISED = 6
    CRITICAL = 7
    HOSPITALISED_RECOVERING = 8
    RECOVERED = 9
    DEATH = 10
    QUARANTINED = 11
    QUARANTINE_RELEASE = 12
    TEST_TAKE = 13
    TEST_RESULT = 14
    CASE = 15
    TRACE_TOKEN_RELEASE = 16
    NOT_IN_HOSPITAL = 17
    WAITING = 18
    GENERAL = 19
    ICU = 20
    MORTUARY = 21
    DISCHARGED = 22
    MANUAL_CONTACT_TRACING = 23
    N_EVENT_TYPES = 24



class OccupationNetworkEnum(enum.Enum):
    _primary_network = 0
    _secondary_network = 1
    _working_network = 2
    _retired_network = 3
    _elderly_network = 4

class NETWORK_CONSTRUCTIONS(enum.Enum):
    NETWORK_CONSTRUCTION_BESPOKE = 0,
    NETWORK_CONSTRUCTION_HOUSEHOLD = 1,
    NETWORK_CONSTRUCTION_WATTS_STROGATZ = 2,
    NETWORK_CONSTRUCTION_RANDOM_DEFAULT = 3,
    NETWORK_CONSTRUCTION_RANDOM = 4,
    N_NETWORK_CONSTRUCTIONS = 5

class AgeGroupEnum(enum.Enum):
    _0_9 = 0
    _10_19 = 1
    _20_29 = 2
    _30_39 = 3
    _40_49 = 4
    _50_59 = 5
    _60_69 = 6
    _70_79 = 7
    _80 = 8


class ChildAdultElderlyEnum(enum.Enum):
    _child = 0
    _adult = 1
    _elderly = 2


class ListIndiciesEnum(enum.Enum):
    _1 = 0
    _2 = 1
    _3 = 2
    _4 = 3
    _5 = 4
    _6 = 5


class TransmissionTypeEnum(enum.Enum):
    _household = 0
    _occupation = 1
    _random = 2

class VaccineTypesEnum(enum.Enum):
    VACCINE_TYPE_FULL = 0
    VACCINE_TYPE_SYMPTOM = 1
    
    @classmethod
    def has_value(self, value):
        return value in self._value2member_map_ 
    
class VaccineStatusEnum(enum.Enum):
    NO_VACCINE = 0
    VACCINE_NO_PROTECTION = 1
    VACCINE_PROTECTED_FULLY = 2
    VACCINE_PROTECTED_SYMPTOMS = 3
    VACCINE_WANED = 4

def _get_base_param_from_enum(param):
    base_name, enum_val = None, None
    for en in chain(
        AgeGroupEnum, ChildAdultElderlyEnum, ListIndiciesEnum, TransmissionTypeEnum, OccupationNetworkEnum
    ):
        LOGGER.debug(f"{en.name} =={param[-1 * len(en.name) :]} ")
        if en.name == param[-1 * len(en.name) :]:
            base_name = param.split(en.name)[0]
            enum_val = en.value
            LOGGER.debug(f"Split to {base_name} and {enum_val}")
            break
    return base_name, enum_val

class VaccineSchedule(object):
    def __init__(
        self,
        frac_0_9   = 0,
        frac_10_19 = 0,
        frac_20_29 = 0,
        frac_30_39 = 0,
        frac_40_49 = 0,
        frac_50_59 = 0,
        frac_60_69 = 0,
        frac_70_79 = 0,
        frac_80    = 0,
        vaccine_type    = 0,
        efficacy        = 1.0,
        time_to_protect = 15,
        vaccine_protection_period = 365
    ):
        fraction_to_vaccinate = [
            frac_0_9,   frac_10_19, frac_20_29, frac_30_39, frac_40_49,
            frac_50_59, frac_60_69, frac_70_79, frac_80,
        ]
    
        self.c_fraction_to_vaccinate = covid19.doubleArray( len(AgeGroupEnum)  )
        for age in AgeGroupEnum:
            self.c_fraction_to_vaccinate[ age.value ] = fraction_to_vaccinate[ age.value ]
        
        self.vaccine_type    = vaccine_type
        self.efficacy        = efficacy
        self.time_to_protect = time_to_protect
        self.vaccine_protection_period = vaccine_protection_period
        
        self.c_total_vaccinated = covid19.longArray( len(AgeGroupEnum)  )
        for age in AgeGroupEnum:
            self.c_total_vaccinated[ age.value ] = 0
            
    def total_vaccinated (self):    
        
        total_vaccinated = [0]*len(AgeGroupEnum) 

        for age in AgeGroupEnum:
            total_vaccinated[ age.value ] = self.c_total_vaccinated[ age.value ]
            
        return total_vaccinated
    
    def fraction_to_vaccinate (self):    
        
        fraction_to_vaccinate = [0]*len(AgeGroupEnum) 

        for age in AgeGroupEnum:
            fraction_to_vaccinate[ age.value ] = self.c_fraction_to_vaccinate[age.value]
     
        return fraction_to_vaccinate
            
        
class Parameters(object):
    def __init__(
            self,
            input_param_file: str = None,
            param_line_number: int = 1,
            output_file_dir: str = "./",
            input_households: Union[str, pd.DataFrame] = None,
            hospital_input_param_file: str = None,
            hospital_param_line_number: int = 1,
            read_param_file=True,
            read_hospital_param_file=False,
    ):
        """[summary]

        Arguments:
            object {[type]} -- [description]

        Keyword Arguments:
            input_param_file {str} -- [Parameters file path] (default: {None})
            param_line_number {int} -- [Which column of the input param file to read] (default: 1)
            output_file_dir {str} -- [Where to write output files to] (default: {"./"})
            input_households {str} -- [Household demographics file (required)] (default: {None})
            read_param_file {bool} -- [Read param file, all params can be set from python interface] (default: {True})

        Raises:
            ParameterException: [Warnings if parameters are not correctly set]
            Sys.exit(0): [Underlaying C code will exist if params are not viable]
        """
        self.c_params = covid19.parameters()
        covid19.initialize_params( self.c_params );
        
        # if no input_param_file is given use default
        if not input_param_file :
            input_param_file = pkg_resources.resource_filename('COVID19', 'default_params/baseline_parameters.csv')   
        if read_param_file :
            self.c_params.input_param_file = input_param_file
        else:
            LOGGER.info( "Have not passed input file for params, use set_param or set_param_dict" )
            
        if param_line_number:
            self.c_params.param_line_number = int(param_line_number)
       
        self.c_params.output_file_dir = output_file_dir
        
        if isinstance(input_households, pd.DataFrame):
            self.household_df = input_households
        else :
            if not input_households :
                input_households = pkg_resources.resource_filename('COVID19', 'default_params/baseline_household_demographics.csv')
            self.c_params.input_household_file = input_households
            self.household_df = None
            
        if hospital_param_line_number:
            self.c_params.hospital_param_line_number = int(hospital_param_line_number)

        # if no hospital_input_param_file is given use default
        if not hospital_input_param_file :
            hospital_input_param_file = pkg_resources.resource_filename('COVID19', 'default_params/hospital_baseline_parameters.csv') 
        if read_hospital_param_file:
            self.c_params.hospital_input_param_file = hospital_input_param_file
        else:
            LOGGER.info("Have not passed hospital input file for params, use set_param or set_param_dict// crick todo look into this")

        if read_hospital_param_file and hospital_input_param_file != None:
            self._read_hospital_param_file()


        if read_param_file and input_param_file != None:
            self._read_and_check_from_file()

        if output_file_dir:
            self.c_params.sys_write_individual = 1
        self.update_lock = False

    def _read_and_check_from_file(self):
        covid19.read_param_file(self.c_params)

    def _read_household_demographics(self):
        if self.household_df is None:
            self._read_household_demographics_file()
        else:
            self._read_household_demographics_df()

    def _read_household_demographics_file(self):
        """[summary]
        Try to read the reference household demographics file
        If we've not set the number of lines to read, parse the file in
        python and inset the line count to the params structure for initilisation
        """
        if self.get_param("N_REFERENCE_HOUSEHOLDS") != 0:
            covid19.read_household_demographics_file(self.c_params)
        else:
            n_ref_hh = -1
            with open(self.c_params.input_household_file, "r") as f:
                for _ in f.readlines():
                    n_ref_hh += 1
            self.set_param("N_REFERENCE_HOUSEHOLDS", n_ref_hh)
            self._read_household_demographics()

    def _read_household_demographics_df(self):
        """[summary]
        """
        if isinstance(self.household_df, pd.DataFrame):
            self.set_param("N_REFERENCE_HOUSEHOLDS", len(self.household_df))
            LOGGER.debug(
                f"setting up ref household memory for {getattr(self.c_params,'N_REFERENCE_HOUSEHOLDS')}"
            )
            covid19.set_up_reference_household_memory(self.c_params)
            LOGGER.debug("memory set up")
            _ = [
                covid19.add_household_to_ref_households(
                    self.c_params,
                    t[0],
                    t[1],
                    t[2],
                    t[3],
                    t[4],
                    t[5],
                    t[6],
                    t[7],
                    t[8],
                    t[9],
                )
                for t in self.household_df.itertuples()
            ]

    def _read_hospital_param_file(self):
        covid19.read_hospital_param_file(self.c_params)

    def set_param_dict(self, params):
        for k, v in params.items():
            self.set_param(k, v)

    def get_param(self, param):
        """[summary]
        Get the value of a param from the c_params object
        Arguments:
            param {[str]} -- [name of parameters]

        Raises:
            ParameterException: [description]

        Returns:
            [type] -- [value of param]
        """
        if hasattr(covid19, f"get_param_{param}"):
            return getattr(covid19, f"get_param_{param}")(self.c_params)
        elif hasattr(self.c_params, f"{param}"):
            return getattr(self.c_params, f"{param}")
        else:
            param, idx = _get_base_param_from_enum(param)
            LOGGER.debug(
                f"not found full length param, trying get_param_{param} with index getter"
            )
            if hasattr(covid19, f"get_param_{param}"):
                return getattr(covid19, f"get_param_{param}")(self.c_params, idx)
            else:
                LOGGER.debug(f"Could not find get_param_{param} in covid19 getters")
        raise ParameterException(
            f"Can not get param {param} as it doesn't exist in parameters object"
        )

    def set_param(self, param, value):
        """[summary]
        sets parameter on c_params
        Arguments:
            param {[string]} -- [parameter name]
            value {[float or int]} -- [value]

        Raises:
            ParameterException:
        """
        if self.update_lock:
            raise ParameterException(
                (
                    "Parameter set has been exported to model, "
                    "please use model.update_x functions"
                )
            )

        if hasattr(self.c_params, f"{param}"):
            if isinstance(getattr(self.c_params, f"{param}"), int):
                setattr(self.c_params, f"{param}", int(value))
            if isinstance(getattr(self.c_params, f"{param}"), float):
                setattr(self.c_params, f"{param}", float(value))
        elif hasattr(
                covid19, f"set_param_{_get_base_param_from_enum(param)[0]}"
        ):
            param, idx = _get_base_param_from_enum(param)
            setter = getattr(covid19, f"set_param_{param}")
            setter(self.c_params, value, idx)
        elif hasattr(covid19, f"set_param_{param}"):
            setter = getattr(covid19, f"set_param_{param}")
            setter(self.c_params, value)
        else:
            raise ParameterException(
                f"Can not set parameter {param} as it doesn't exist"
            )

    def set_demographic_household_table(self, df_demo_house):

        n_total = len( df_demo_house.index )
        if n_total != self.get_param( "n_total" ):
            raise ParameterException( "df_demo_house must have n_total rows" )

        if not 'ID' in df_demo_house.columns:
            raise ParameterException( "df_demo_house must have column ID" )

        if not 'age_group' in df_demo_house.columns:
            raise ParameterException( "df_demo_house must have column age_group" )

        if not 'house_no' in df_demo_house.columns:
            raise ParameterException( "df_demo_house must have column house_no" )

        n_households = df_demo_house['house_no'].max()+1

        ID       = df_demo_house["ID"].to_list()
        ages     = df_demo_house["age_group"].to_list()
        house_no = df_demo_house["house_no"].to_list()

        ID_c       = covid19.longArray(n_total)
        ages_c     = covid19.longArray(n_total)
        house_no_c = covid19.longArray(n_total)

        for idx in range(n_total):
            ID_c[idx]       = ID[idx]
            ages_c[idx]     = ages[idx]
            house_no_c[idx] = house_no[idx]

        covid19.set_demographic_house_table( self.c_params, int(n_total),int(n_households), ID_c, ages_c, house_no_c )

    def set_occupation_network_table(self, df_occupation_networks, df_occupation_network_properties):
        n_total = len(df_occupation_networks.index)
        if n_total != self.get_param("n_total"):
            raise ParameterException("df_occupation_networks must have n_total rows")

        n_networks = df_occupation_networks['network_no'].max() + 1
        covid19.set_occupation_network_table(self.c_params, int(n_total), int(n_networks))
        [covid19.set_indiv_occupation_network_property(
            self.c_params, int(row[0]),  int(row[1]), float(row[2]), float(row[3]), int(row[4]),
            str(row[5]))
            for row in df_occupation_network_properties[[
            'network_no',  'age_type', 'mean_work_interaction', 'lockdown_multiplier', 'network_id',
            'network_name']].values]

        ID         = df_occupation_networks['ID'].to_list()
        network_no = df_occupation_networks['network_no'].to_list()

        ID_c         = covid19.longArray(n_total)
        network_no_c = covid19.longArray(n_total)

        for idx in range(n_total):
            ID_c[idx]         = ID[idx]
            network_no_c[idx] = network_no[idx]

        covid19.set_indiv_occupation_network(self.c_params, n_total, ID_c, network_no_c)

    def return_param_object(self):
        """[summary]
        Run a check on the parameters and return if the c code doesn't bail
        Returns:
            [type] -- [description]
        """
        self._read_household_demographics()
        covid19.check_params(self.c_params)
        LOGGER.info(
            (
                "Returning self.c_params into Model object, "
                "future updates to parameters not possible"
            )
        )
        self.update_lock = True
        return self.c_params


class Model:
    """
    OpenABM-Covid19 is an agent-based model of an epidemic using realistic networks, viral dynamics, 
    disease progression and both non-pharmaceutical and pharmaceutical interventions.
    
    Example:
        import COVID19.model as abm
        model = abm.Model( params = { "n_total" : 10000, "end_time": 20 } )
        model.run()
        print( model.results )    
    """
    def __init__(self, params_object = None, params = None):
        """
        Initializes a new model with either specified or default parameters
        
        Arguments: 
            params_object{[Parameters()]} - a Parameter object, if None specified uses the default parameters 
            params{[dict]}                - overrides to default/specified parameters 
        """
        # use default params if none are given
        if not params_object :
            params_object = Parameters()
        if params :
            if not isinstance( params, dict ) :
                raise ModelParameterException( "params must be a dictionary if specified")
                
            params_object.set_param_dict( params )
        
        # Store the params object so it doesn't go out of scope and get freed
        self._params_obj = params_object
        # Create C parameters object
        self.c_params = params_object.return_param_object()
        self.c_model = None
        self._create()
        self._is_running = False
        self.nosocomial = bool(self.get_param("hospital_on"))
        self._results = []

    def __del__(self):
        self._destroy()

    def get_param(self, name):
        """[summary]
        Get parameter by name
        Arguments:
            name {[str]} -- [name of param]

        Raises:
            ModelParameterException: [description]

        Returns:
            [type] -- [value of param stored]
        """
        value = None
        try:
            LOGGER.info(f"Getting param {name}")
            split_param, idx = _get_base_param_from_enum(f"get_model_param_{name}")
            if split_param is not None:
                if hasattr(covid19, split_param):
                    value = getattr(covid19, split_param)(self.c_model, idx)
                    LOGGER.info(f"Got {split_param} at index {idx} value {value}")
                else:
                    raise ModelParameterException(f"Parameter {name} not found")
            elif hasattr(covid19, f"get_model_param_{name}"):
                value = getattr(covid19, f"get_model_param_{name}")(self.c_model)
            else:
                raise ModelParameterException(f"Parameter {name} not found")
            if value < 0:
                return False
            else:
                return value
        except AttributeError:
            raise ModelParameterException(f"Parameter {name} not found")

    def update_running_params(self, param, value):
        """[summary]
        a subset of parameters my be updated whilst the model is evaluating,
        these correspond to events

        Arguments:
            param {[str]} -- [name of parameter]
            value {[type]} -- [value to set]

        Raises:
            ModelParameterException: [description]
            ModelParameterException: [description]
            ModelParameterException: [description]
        """
        if param not in PYTHON_SAFE_UPDATE_PARAMS:
            raise ModelParameterException(f"Can not update {param} during running")
        split_param, index = _get_base_param_from_enum(f"set_model_param_{param}")
        if split_param:
            setter = getattr(covid19, split_param)
        elif hasattr(covid19, f"set_model_param_{param}"):
            setter = getattr(covid19, f"set_model_param_{param}")
        else:
            raise ModelParameterException(f"Setting {param} to {value} failed")
        if callable(setter):
            if index is not None:
                args = [self.c_model, value, index]
            else:
                args = [self.c_model, value]
            LOGGER.info(
                f"Updating running params with {args} split_param {split_param} param {split_param}"
            )
            if not setter(*args):
                raise ModelParameterException(f"Setting {param} to {value} failed")

    def get_risk_score(self, day, age_inf, age_sus):
        value = covid19.get_model_param_risk_score(self.c_model, day, age_inf, age_sus)
        if value < 0:
            raise  ModelParameterException( "Failed to get risk score")
        return value

    def get_risk_score_household(self, age_inf, age_sus):
        value = covid19.get_model_param_risk_score_household(self.c_model, age_inf, age_sus)
        if value < 0:
            raise  ModelParameterException( "Failed to get risk score household")
        return value

    def add_user_network(
            self, 
            df_network, 
            interaction_type = covid19.OCCUPATION, 
            skip_hospitalised = True, 
            skip_quarantine = True,
            construction = covid19.NETWORK_CONSTRUCTION_BESPOKE,
            daily_fraction = 1.0, 
            name = "user_network" ):
        
        """[summary]
        adds as bespoke user network from a dataframe of edges
        the network is static with the exception of skipping
        hospitalised and quarantined people

        Arguments:
            df_network {[dataframe]}      -- [list of edges, with 2 columns ID_1 and ID_2]
            interaction {[int]}           -- [type of interaction (e.g. household/occupation/random)]
            skip_hospitalised {[boolean]} -- [skip interaction if either person is in hospital]
            skip_quarantine{[boolean]}    -- [skip interaction if either person is in quarantined]
            construction{[int]}           -- [the method used for network construction]
            daily_fraction{[double]}      -- [the fraction of edges on the network present each day (i.e. down-sampling the network)]
            name{[char]}                  -- [the name of the network]

        """

        n_edges = len( df_network.index )
        n_total = self._params_obj.get_param("n_total")

        if not 'ID_1' in df_network.columns:
            raise ParameterException( "df_network must have column ID_1" )

        if not 'ID_2' in df_network.columns:
            raise ParameterException( "df_network must have column ID_2" )

        if not interaction_type in [0,1,2]:
            raise ParameterException( "interaction_type must be 0 (household), 1 (occupation) or 2 (random)" )

        if (daily_fraction > 1) or( daily_fraction < 0):
            raise ParameterException( "daily fraction must be in the range 0 to 1" )

        if not skip_hospitalised in [ True, False ]:
            raise ParameterException( "skip_hospitalised must be True or False" )

        if not skip_quarantine in [ True, False ]:
            raise ParameterException( "skip_quarantine must be True or False" )

        ID_1 = df_network[ "ID_1" ].to_list()
        ID_2 = df_network[ "ID_2" ].to_list()

        if (max( ID_1 ) >= n_total) or (min( ID_1 ) < 0):
            raise ParameterException( "all values of ID_1 must be between 0 and n_total-1" )

        if (max( ID_2 ) >= n_total) or (min( ID_2  ) < 0):
            raise ParameterException( "all values of ID_2 must be between 0 and n_total-1" )

        ID_1_c = covid19.longArray(n_edges)
        ID_2_c = covid19.longArray(n_edges)

        for idx in range(n_edges):
            ID_1_c[idx] = ID_1[idx]
            ID_2_c[idx] = ID_2[idx]

        id = covid19.add_user_network(self.c_model,interaction_type,skip_hospitalised,skip_quarantine,construction,daily_fraction, n_edges,ID_1_c, ID_2_c, name)
        return  Network( self, id )
    
    def add_user_network_random(
            self, 
            df_interactions, 
            skip_hospitalised = True, 
            skip_quarantine = True,
            name = "user_network" ):
             
        """[summary]
        adds a bespoke user random network from a dataframe of people and number of interactions
        the network is regenerates each day, but the number of interactions per person is statitc
        hospitalsed and quarantined people can be skipped

        Arguments:
            df_interactions {[dataframe]} -- [list of indviduals and interactions, with 2 columns ID and N]
            skip_hospitalised {[boolean]} -- [skip interaction if either person is in hospital]
            skip_quarantine{[boolean]}    -- [skip interaction if either person is in quarantined]
            name{[char]}                  -- [the name of the network]

        """
        
        n_indiv = len( df_interactions.index )
        n_total = self._params_obj.get_param("n_total")

        if not 'ID' in df_interactions.columns:
            raise ParameterException( "df_interactions must have column ID" )

        if not 'N' in df_interactions.columns:
            raise ParameterException( "df must have column N" )

        if not skip_hospitalised in [ True, False ]:
            raise ParameterException( "skip_hospitalised must be True or False" )

        if not skip_quarantine in [ True, False ]:
            raise ParameterException( "skip_quarantine must be True or False" )

        ID = df_interactions[ "ID" ].to_list()
        N  = df_interactions[ "N" ].to_list()

        if (max( ID) >= n_total) or (min( ID ) < 0):
            raise ParameterException( "all values of ID must be between 0 and n_total-1" )

        if ( min( N ) < 1):
            raise ParameterException( "all values of N must be greater than 0" )

        ID_c = covid19.longArray(n_indiv)
        N_c  = covid19.intArray(n_indiv)

        for idx in range(n_indiv):
            ID_c[idx] = ID[idx]
            N_c[idx]  = N[idx]

        id = covid19.add_user_network_random(self.c_model,skip_hospitalised,skip_quarantine, n_indiv,ID_c, N_c, name)
        return  Network( self, id )
    
    def get_network_by_id(self, network_id ):
        return Network( self, network_id )
    
    def delete_network(self, network):   
        res = covid19.delete_network( self.c_model, network.c_network )
        return res 
    
    def set_risk_score(self, day, age_inf, age_sus, value):
        ret = covid19.set_model_param_risk_score(self.c_model, day, age_inf, age_sus, value)
        if ret == 0:
            raise  ModelParameterException( "Failed to set risk score")

    def set_risk_score_household(self, age_inf, age_sus, value):
        ret = covid19.set_model_param_risk_score_household(self.c_model, age_inf, age_sus, value)
        if ret == 0:
            raise  ModelParameterException( "Failed to set risk score household")

    def get_app_users(self):
        
        n_total = self.c_model.params.n_total
        users   = covid19.longArray(n_total)
        res     = covid19.get_app_users(self.c_model,users)
        
        if res == 0:
            raise ModelParameterException( "Failed to get risk")
        
        list_users = [None]*n_total
        for idx in range(n_total):
            list_users[idx]=users[idx]
        
        df_users = pd.DataFrame( {'ID':range(n_total), 'app_user':list_users})
        
        return df_users
    
    def set_app_users(self,df_app_users):
        
        if {'ID', 'app_user'}.issubset(df_app_users.columns) == False:
            raise ModelParameterException( "df_app_user must contain the columns ID and app_user")
        
        # first turn on the users in the list
        app_on  = df_app_users[df_app_users["app_user"]==True]["ID"].to_list()
        n_users = len(app_on) 
        if n_users > 0 :
            users   = covid19.longArray(n_users)
            for idx in range(n_users):
                users[idx]=app_on[idx]
            res = covid19.set_app_users(self.c_model,users,n_users,True)
            if res == False :
                raise ModelParameterException( "Failed to update new app_users" )
        
        # first turn off the users in the list
        app_off = df_app_users[df_app_users["app_user"]==False]["ID"].to_list()
        n_users = len(app_off) 
        if n_users > 0 :
            users   = covid19.longArray(n_users)
            for idx in range(n_users):
                users[idx]=app_off[idx]
            res = covid19.set_app_users(self.c_model,users,n_users,False)
            if res == False :
                raise ModelParameterException( "Failed to remove old app_users" )
    
    def seed_infect_by_idx(self, ID, strain_multiplier = 1, network_id = -1 ):
        
        n_total = self._params_obj.get_param("n_total")

        if ( ID < 0 ) | ( ID >= n_total ) :
            raise ModelParameterException( "ID out of range (0<=ID<n_total)")

        if strain_multiplier < 0 :
            raise ModelParameterException( "strain_multiplier must be positive")

        return covid19.seed_infect_by_idx( self.c_model, ID, strain_multiplier, network_id );

    def get_network_info(self, max_ids= 1000):
           
        if max_ids > 1e6 :
            raise ModelException( "Maximum number of allowed network is 1e6" )
        ids_c = covid19.intArray( max_ids )
        n_ids = covid19.get_network_ids( self.c_model, ids_c, max_ids )
        
        if n_ids == -1 :
            return self.get_network_info( max_ids = max_ids * 10 )
        
        ids        = [None] * n_ids
        names      = [None] * n_ids
        n_edges    = [None] * n_ids
        n_vertices = [None] * n_ids
        type       = [None] * n_ids
        skip_hospitalised = [None] * n_ids
        skip_quarantined  = [None] * n_ids
        daily_fraction    = [None] * n_ids
        
        for idx in range( n_ids ) :
            network = Network( self, ids_c[idx] )
            
            ids[idx]        = ids_c[idx]
            names[idx]      = network.name()
            n_edges[idx]    = network.n_edges()
            n_vertices[idx] = network.n_vertices()  
            type[idx]       = network.type()
            skip_hospitalised[idx] = network.skip_hospitalised()
            skip_quarantined[idx]  = network.skip_quarantined()
            daily_fraction[idx]    = network.daily_fraction()      
            
        return pd.DataFrame( {
                'id'                : ids,
                'name'              : names,
                'n_edges'           : n_edges,
                'n_vertices'        : n_vertices,
                'type'              : type,
                'skip_hospitalised' : skip_hospitalised,
                'skip_quarantined'  : skip_quarantined,
                'daily_fraction'    : daily_fraction
            } )
       
    def vaccinate_individual(self, ID, vaccine_type = 0, efficacy = 1.0, time_to_protect = 14, vaccine_protection_period = 1000 ):
        """
        Vaccinates an individual by ID of individual
        
        """
        n_total = self.c_model.params.n_total

        if ( ID < 0 ) | ( ID >= n_total ) :
            raise ModelParameterException( "ID out of range (0<=ID<n_total)")

        if ( efficacy < 0 ) | ( efficacy > 1 ) :
            raise ModelParameterException( "efficacy must be between 0 and 1")
        
        if time_to_protect < 1 :
            raise ModelParameterException( "vaccine must take at least one day to take effect" )
        
        if vaccine_protection_period <= time_to_protect :
            raise ModelParameterException( "vaccine must protect for longer than it takes to by effective" )
    
        if not VaccineTypesEnum.has_value(vaccine_type) :
            raise ModelParameterException( "vaccine type must be listed in VaccineTypesEnum" )

        return covid19.intervention_vaccinate_by_idx( self.c_model, ID, vaccine_type, efficacy, time_to_protect, vaccine_protection_period );

    def vaccinate_schedule(self, schedule ):

        if not isinstance( schedule, VaccineSchedule ) :
            ModelException( "argument VaccineSchedule must be an object of type VaccineSchedule")
            
        return covid19.intervention_vaccinate_age_group( 
            self.c_model, 
            schedule.c_fraction_to_vaccinate, 
            schedule.vaccine_type,
            schedule.efficacy,
            schedule.time_to_protect,
            schedule.vaccine_protection_period,
            schedule.c_total_vaccinated
        )   
    
    def get_individuals(self):
        """
        Return dataframe of population
        """
        n_total = self.c_model.params.n_total
        
        ids   = covid19.longArray(n_total)
        statuses   = covid19.intArray(n_total)
        age_groups   = covid19.intArray(n_total)
        occupation_networks   = covid19.intArray(n_total)
        house_ids = covid19.longArray(n_total)
        infection_counts = covid19.intArray(n_total)
        vaccine_statuses = covid19.shortArray(n_total)
        
        n_total = covid19.get_individuals(
            self.c_model, ids, statuses, age_groups, occupation_networks, 
            house_ids, infection_counts, vaccine_statuses)
        
        list_ids = [None]*n_total
        list_statuses = [None]*n_total
        list_age_groups = [None]*n_total
        list_occupation_networks = [None]*n_total
        list_house_ids = [None]*n_total
        list_infection_counts = [None]*n_total
        list_vaccine_statuses = [None]*n_total
        
        for idx in range(n_total):
            list_ids[idx] = ids[idx]
            list_statuses[idx] = statuses[idx]
            list_age_groups[idx] = age_groups[idx]
            list_occupation_networks[idx] = occupation_networks[idx]
            list_house_ids[idx] = house_ids[idx]
            list_infection_counts[idx] = infection_counts[idx]
            list_vaccine_statuses[idx] = vaccine_statuses[idx]
        
        df_popn = pd.DataFrame( {
            'ID': list_ids, 
            'current_status': list_statuses,
            'age_group': list_age_groups,
            'occupation_network': list_occupation_networks,
            'house_no': list_house_ids,
            'infection_count' : list_infection_counts,
            'vaccine_status' : list_vaccine_statuses
        })
        
        return df_popn
    
    def _create(self):
        """
        Call C function new_model (renamed create_model)
        """
        LOGGER.info("Started model creation")
        self.c_model = covid19.create_model(self.c_params)
        LOGGER.info("Successfuly created model")

    def _destroy(self):
        """
        Call C function destroy_model and destroy_params
        """
        LOGGER.info("Destroying model")
        covid19.destroy_model(self.c_model)

    def one_time_step(self):
        """
        Steps the simulation forward one time step
        """  
        covid19.one_time_step(self.c_model)
        self._results.append( self.one_time_step_results() )
        
    @property
    def results(self):
        """
        A dataframe of all the time-series results in the simulation so far.
        Concatanates the return of one_time_step_results from all steps so far.
        
        Returns:
            Panda DataFrame
        """
        
        return pd.DataFrame(self._results)
        
    def run(self, verbose = True):
        """
        Runs simulation to the end (specified by the parameter end_time)
        
        Arguments:
            verbose{[boolean]} - whether to display progress information (DEFAULT=True)
            
        Returns: 
            None
        """
        n_steps  = self.c_params.end_time - self.c_model.time
        step     = 0
        
        if verbose :
            print( "Start simulation")
            start_time = time.process_time()
                
        while step < n_steps :
            step = step + 1;
                    
            if verbose : 
               print("\rStep " + str( step ) + " of " + str( n_steps ), end = "\r", flush = True )
               
            self.one_time_step()
            
        if verbose :
            print( "")
            print( "End simulation in " + "{0:.4g}".format( time.process_time() - start_time ) + "s" )
        
    def one_time_step_results(self):
        """
        Get results from one time step
        """
        results = {}
        results["time"] = self.c_model.time
        results["lockdown"] = self.c_params.lockdown_on
        results["test_on_symptoms"] = self.c_params.test_on_symptoms
        results["app_turned_on"] = self.c_params.app_turned_on
        results["total_infected"] = (
                int(covid19.utils_n_total(self.c_model, covid19.PRESYMPTOMATIC))
                + int(covid19.utils_n_total(self.c_model, covid19.PRESYMPTOMATIC_MILD))
                + int(covid19.utils_n_total(self.c_model, covid19.ASYMPTOMATIC))
        )
        for age in AgeGroupEnum:
            key = f"total_infected{age.name}"
            results[key] = sum(
                [
                    covid19.utils_n_total_age(self.c_model, ty, age.value)
                    for ty in [
                        covid19.PRESYMPTOMATIC,
                        covid19.PRESYMPTOMATIC_MILD,
                        covid19.ASYMPTOMATIC,
                    ]
                ]
            )
        results["total_case"] = covid19.utils_n_total(self.c_model, covid19.CASE)
        for age in AgeGroupEnum:
            key = f"total_case{age.name}"
            value = covid19.utils_n_total_age(self.c_model, covid19.CASE, age.value)
            results[key] = value
        results["total_death"] = covid19.utils_n_total(self.c_model, covid19.DEATH)
        for age in AgeGroupEnum:
            key = f"total_death{age.name}"
            value = covid19.utils_n_total_age(self.c_model, covid19.DEATH, age.value)
            results[key] = value

        results["daily_death"] = covid19.utils_n_daily(
                self.c_model, covid19.DEATH, self.c_model.time
            )
        
        for age in AgeGroupEnum:
            key = f"daily_death{age.name}"
            value = covid19.utils_n_daily_age(self.c_model, covid19.DEATH, self.c_model.time, age.value)
            results[key] = value
        
        

        results["n_presymptom"] = covid19.utils_n_current(
            self.c_model, covid19.PRESYMPTOMATIC
        ) + covid19.utils_n_current(self.c_model, covid19.PRESYMPTOMATIC_MILD)
        results["n_asymptom"] = covid19.utils_n_current(
            self.c_model, covid19.ASYMPTOMATIC
        )
        results["n_quarantine"] = covid19.utils_n_current(
            self.c_model, covid19.QUARANTINED
        )
        results["n_tests"] = covid19.utils_n_total_by_day(
            self.c_model, covid19.TEST_RESULT, int(self.c_model.time) 
        )
        results["n_symptoms"] = covid19.utils_n_current(
            self.c_model, covid19.SYMPTOMATIC
        ) + covid19.utils_n_current(self.c_model, covid19.SYMPTOMATIC_MILD)
        results["n_hospital"] = covid19.utils_n_current( self.c_model, covid19.HOSPITALISED )
        results["n_hospitalised_recovering"] = covid19.utils_n_current( self.c_model, covid19.HOSPITALISED_RECOVERING )
        results["n_critical"] = covid19.utils_n_current(self.c_model, covid19.CRITICAL)
        results["n_death"] = covid19.utils_n_current(self.c_model, covid19.DEATH)
        results["n_recovered"] = covid19.utils_n_current(
            self.c_model, covid19.RECOVERED
        )
        if self.nosocomial:
            results["hospital_admissions"]  = covid19.utils_n_daily(
                self.c_model, covid19.GENERAL, self.c_model.time
            )
            results["hospital_admissions_total"]  = covid19.utils_n_total(
                self.c_model, covid19.GENERAL
            )
            results["hospital_to_critical_daily"] = covid19.utils_n_daily(
                self.c_model, covid19.CRITICAL, self.c_model.time
            )
            results["hospital_to_critical_total"] = covid19.utils_n_total(
                self.c_model, covid19.CRITICAL
            )
        else:
            results["hospital_admissions"]  = covid19.utils_n_daily(
                self.c_model, covid19.TRANSITION_TO_HOSPITAL, self.c_model.time
            )
            results["hospital_admissions_total"]  = covid19.utils_n_total(
                self.c_model, covid19.TRANSITION_TO_HOSPITAL
            )
            results["hospital_to_critical_daily"] = covid19.utils_n_daily(
                self.c_model, covid19.TRANSITION_TO_CRITICAL, self.c_model.time
            )
            results["hospital_to_critical_total"] = covid19.utils_n_total(
                self.c_model, covid19.TRANSITION_TO_CRITICAL
            )


        results["n_quarantine_infected"] = self.c_model.n_quarantine_infected
        results["n_quarantine_recovered"] = self.c_model.n_quarantine_recovered
        results["n_quarantine_app_user"] = self.c_model.n_quarantine_app_user
        results["n_quarantine_app_user_infected"] = self.c_model.n_quarantine_app_user_infected
        results["n_quarantine_app_user_recovered"] = self.c_model.n_quarantine_app_user_recovered
        results["n_quarantine_events"] = self.c_model.n_quarantine_events
        results["n_quarantine_release_events"] = self.c_model.n_quarantine_release_events
        results["n_quarantine_events_app_user"] = self.c_model.n_quarantine_events_app_user
        results["n_quarantine_release_events_app_user"] = \
            self.c_model.n_quarantine_release_events_app_user
            
        results["R_inst"] = covid19.calculate_R_instanteous( self.c_model, self.c_model.time, 0.5 )
        results["R_inst_05"] = covid19.calculate_R_instanteous( self.c_model, self.c_model.time, 0.05 )
        results["R_inst_95"] = covid19.calculate_R_instanteous( self.c_model, self.c_model.time, 0.95 )

        return results

    def write_output_files(self):
        """
        Write output files
        """
        covid19.write_output_files(self.c_model, self.c_params)

    def write_individual_file(self):
        covid19.write_individual_file(self.c_model, self.c_params)

    def write_interactions_file(self):
        covid19.write_interactions(self.c_model)

    def write_trace_tokens_timeseries(self):
        covid19.write_trace_tokens_ts(self.c_model)

    def write_trace_tokens(self):
        covid19.write_trace_tokens(self.c_model)

    def write_transmissions(self):
        covid19.write_transmissions(self.c_model)

    def write_quarantine_reasons(self):
        covid19.write_quarantine_reasons(self.c_model, self.c_params)

    def write_occupation_network(self, idx):
        covid19.write_occupation_network(self.c_model, self.c_params, idx)

    def write_household_network(self):
        covid19.write_household_network(self.c_model, self.c_params)

    def write_random_network(self):
        covid19.write_random_network(self.c_model, self.c_params)

    def print_individual(self, idx):
        covid19.print_individual(self.c_model, idx)
