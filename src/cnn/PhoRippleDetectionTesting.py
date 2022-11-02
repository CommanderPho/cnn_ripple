import os
import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import itertools # for list unpacking
from neuropy.utils.load_exported import LoadXml, find_session_xml # for compute_with_params_loaded_from_xml

from .load_data import generate_overlapping_windows
from .format_predictions import get_predictions_indexes
import tensorflow.keras.backend as K
import tensorflow.keras as kr



## Define the .ui file path
_path = os.path.dirname(os.path.abspath(__file__))
_modelDirectory = os.path.join(_path, '../../model')


## Save result if wanted:
class ExtendedRippleDetection(object):
    """docstring for ExtendedRippleDetection.

    Usage:
        from src.cnn.PhoRippleDetectionTesting import ExtendedRippleDetection, main_compute_with_params_loaded_from_xml

    """
    def __init__(self, learning_rate=0.001, beta_1=0.9, beta_2=0.999, epsilon=1e-07, amsgrad=False):
        super(ExtendedRippleDetection, self).__init__()
        self.active_session_folder = None
        self.active_session_eeg_data_filepath = None
        self.loaded_eeg_data = None
        self.out_all_ripple_results = None
        self.ripple_df = None

        print("Loading CNN model...", end=" ")
        self.optimizer = kr.optimizers.Adam(learning_rate=learning_rate, beta_1=beta_1, beta_2=beta_2, epsilon=epsilon, amsgrad=amsgrad)
        # relative:
        # model_path = "../../model"
        # model_path = r"C:\Users\pho\repos\cnn-ripple\model"
        model_path = _modelDirectory
        self.model = kr.models.load_model(model_path, compile=False)
        self.model.compile(loss="binary_crossentropy", optimizer=self.optimizer)
        print("Done!")


    def compute(self, active_session_folder=Path('/content/drive/Shareddrives/Diba Lab Data/KDIBA/gor01/one/2006-6-08_14-26-15'), numchannel = 96,
            srLfp = 1250, downsampled_fs = 1250, 
            overlapping = True, window_size = 0.0128, window_stride = 0.0064, # window parameters
            ripple_detection_threshold=0.7,
            active_shank_channels_lists = [[72,73,74,75,76,77,78,79], [81,82,83,84,85,86,87,88]],
            **kwargs
            ):
        self.active_session_folder = active_session_folder
        self.loaded_eeg_data, self.active_session_eeg_data_filepath, self.active_session_folder = self.load_eeg_data(active_session_folder=active_session_folder, numchannel=numchannel)
        self.out_all_ripple_results = self.compute_ripples(self.model, self.loaded_eeg_data, srLfp=srLfp, downsampled_fs=downsampled_fs, overlapping=overlapping, window_size=window_size, window_stride=window_stride, ripple_detection_threshold=ripple_detection_threshold, active_shank_channels_lists=active_shank_channels_lists, out_all_ripple_results=None, **(dict(debug_trace_computations_output=True, debug_print=False)|kwargs))

        out_all_ripple_results_filepath = active_session_folder.joinpath('out_all_ripple_results.pkl')
        with open(out_all_ripple_results_filepath, 'wb') as f:
            print(f'saving results to {str(out_all_ripple_results_filepath)}...')
            pickle.dump(self.out_all_ripple_results, f)
        print(f'done.')
        flattened_pred_ripple_start_stop_times = np.vstack([a_result['pred_times'] for a_result in self.out_all_ripple_results['results'].values() if np.size(a_result['pred_times'])>0])
        print(f'flattened_pred_ripple_start_stop_times: {np.shape(flattened_pred_ripple_start_stop_times)}') # (6498, 2)
        ripple_df = pd.DataFrame({'start':flattened_pred_ripple_start_stop_times[:,0], 'stop': flattened_pred_ripple_start_stop_times[:,1]})
        self.ripple_df = ripple_df
        print(f'Saving ripple_df to csv: {self.predicted_ripples_dataframe_save_filepath}')
        ripple_df.to_csv(self.predicted_ripples_dataframe_save_filepath)
        return ripple_df, self.out_all_ripple_results

    @property
    def predicted_ripples_dataframe_save_filepath(self):
        """The predicted_ripples_dataframe_save_filepath property."""
        return self.active_session_folder.joinpath('pred_ripples.csv')

    @classmethod
    def readmulti(cls, fname, numchannel:int, chselect=None, *args):
        """ reads multi-channel recording file to a matrix
        % 
        % function [eeg] = function readmulti(fname,numchannel,chselect)
        % last argument is optional (if omitted, it will read all the 
        % channels

        function [eeg] = readmulti(fname,numchannel,chselect,subtract_channel)

        if nargin == 2
        datafile = fopen(fname,'r');
        eeg = fread(datafile,[numchannel,inf],'int16');
        fclose(datafile);
        eeg = eeg';
        return
        end

        if nargin == 3

        % the real buffer will be buffersize * numch * 2 bytes
        % (short = 2bytes)
        
        buffersize = 4096;
        
        % get file size, and calculate the number of samples per channel
        fileinfo = dir(fname);
        numel = ceil(fileinfo(1).bytes / 2 / numchannel);
        
        datafile = fopen(fname,'r');
        
        mmm = sprintf('%d elements',numel);
        %  disp(mmm);  
        
        eeg=zeros(length(chselect),numel);
        numel=0;
        numelm=0;
        while ~feof(datafile),
            [data,count] = fread(datafile,[numchannel,buffersize],'int16');
            if count~=0
                numelm = count/numchannel;
                eeg(:,numel+1:numel+numelm) = data(chselect,:);
                numel = numel+numelm;
            end
        end
        fclose(datafile);
        end

        if nargin == 4

        % the real buffer will be buffersize * numch * 2 bytes
        % (short = 2bytes)
        
        buffersize = 4096;
        
        % get file size, and calculate the number of samples per channel
        fileinfo = dir(fname);
        numel = ceil(fileinfo(1).bytes / 2 / numchannel);
        
        datafile = fopen(fname,'r');
        
        mmm = sprintf('%d elements',numel);
        %  disp(mmm);  
        
        eeg=zeros(length(chselect),numel);
        numel=0;
        numelm=0;
        while ~feof(datafile),
            [data,count] = fread(datafile,[numchannel,buffersize],'int16');
            if count~=0
                numelm = count/numchannel;
                eeg(:,numel+1:numel+numelm) = data(chselect,:)-repmat(data(subtract_channel,:),length(chselect),1);
                numel = numel+numelm;
            end
        end
        fclose(datafile);
        end


        eeg = eeg';
        """
        assert chselect is None, "Not all functionality from the MATLAB version is implemented!"
        assert len(args) == 0, "Not all functionality from the MATLAB version is implemented!"
        with open(fname, 'rb') as fid:
            loaded_eeg_data = np.fromfile(fid, np.int16).reshape((-1, numchannel)) #.T
        return loaded_eeg_data

    @staticmethod
    def _downsample_data(data, fs, downsampled_fs):
        # Dowsampling
        if fs > downsampled_fs:
            print("Downsampling data from %d Hz to %d Hz..."%(fs, downsampled_fs), end=" ")
            downsampled_pts = np.linspace(0, data.shape[0]-1, int(np.round(data.shape[0]/fs*downsampled_fs))).astype(int)
            downsampled_data = data[downsampled_pts, :]

        # Upsampling
        elif fs < downsampled_fs:
            print("Original sampling rate below 1250 Hz!")
            return None
        else:
            # print("Original sampling rate equals 1250 Hz!")
            downsampled_data = data

        # Change from int16 to float16 if necessary
        # int16 ranges from -32,768 to 32,767
        # float16 has ±65,504, with precision up to 0.0000000596046
        if downsampled_data.dtype != 'float16':
            downsampled_data = np.array(downsampled_data, dtype="float16")

        return downsampled_data

    @staticmethod
    def _z_score_normalization(data):
        channels = range(np.shape(data)[1])
        for channel in channels:
            # Since data is in float16 type, we make it smaller to avoid overflows
            # and then we restore it.
            # Mean and std use float64 to have enough space
            # Then we convert the data back to float16
            dmax = np.amax(data[:, channel])
            dmin = abs(np.amin(data[:, channel]))
            dabs = dmax if dmax>dmin else dmin
            m = np.mean(data[:, channel] / dmax, dtype='float64') * dmax
            s = np.std(data[:, channel] / dmax, dtype='float64') * dmax
            s = 1 if s == 0 else s # If std == 0, change it to 1, so data-mean = 0
            data[:, channel] = ((data[:, channel] - m) / s).astype('float16')

        return data

    @classmethod
    def _run_single_shank_computation(cls, model, loaded_eeg_data, active_shank, active_shank_channels, srLfp, downsampled_fs, overlapping, window_size, window_stride, ripple_detection_threshold, debug_trace_computations_output=False, debug_print=False):
        """ Runs a single set of 8 channels (from one 8-channel probe)
        """
        ## Begin:
        if isinstance(active_shank_channels, list):
            active_shank_channels = np.array(active_shank_channels) # convert to a numpy array
        
        # Subtract 1 from each element to get a channel index
        active_shank_channels = active_shank_channels - 1

        fs = srLfp

        # Get the subset of the data corresponding to only the active channels 
        loaded_data = loaded_eeg_data[:,active_shank_channels]
        if debug_print:
            print("Shape of loaded data: ", np.shape(loaded_data))
        # Downsample data (if needed)
        data = cls._downsample_data(loaded_data, fs, downsampled_fs)
        if debug_print:
            print("Done!")

        # Normalize it with z-score
        print("Normalizing data...", end=" ")
        data = cls._z_score_normalization(data)
        print("Done!")

        print("Shape of loaded data after downsampling and z-score: ", np.shape(data))
        
        print("Generating windows...", end=" ")
        if overlapping:
            # Separate the data into 12.8ms windows with 6.4ms overlapping
            X = generate_overlapping_windows(data, window_size, window_stride, downsampled_fs)
        else:
            window_stride = window_size
            X = np.expand_dims(data, 0)
        print("Done!")

        print("Detecting ripples...", end=" ")
        predictions = model.predict(X, verbose=True)
        print("Done!")

        print("Getting detected ripples indexes and times...", end=" ")
        pred_indexes = get_predictions_indexes(data, predictions, window_size=window_size, stride=window_stride, fs=downsampled_fs, threshold=ripple_detection_threshold)
        pred_times = pred_indexes / downsampled_fs
        print("Done!")

        ## Single result output
        curr_shank_computations = {'shank':active_shank, 'channels': active_shank_channels, 'time_windows': X, 'predictions': predictions, 'pred_indexes': pred_indexes, 'pred_times': pred_times}
        if debug_trace_computations_output:
            curr_shank_computations['data'] = data

        return curr_shank_computations


    ## Batch
    # Do Once:
    @classmethod
    def load_eeg_data(cls, active_session_folder=Path('/content/drive/Shareddrives/Diba Lab Data/KDIBA/gor01/one/2006-6-08_14-26-15'), numchannel:int=96):
        # active_session_folder = Path('/content/drive/Shareddrives/Diba Lab Data/KDIBA/gor01/one/2006-6-08_14-26-15')
        active_session_stem = active_session_folder.stem # '2006-6-08_14-26-15'
        active_session_eeg_data_filepath = active_session_folder.joinpath(active_session_stem).with_suffix('.eeg')
        print(f'active_session_folder: {active_session_folder}')
        print(f'active_session_eeg_data_filepath: {active_session_eeg_data_filepath}')
        assert active_session_eeg_data_filepath.exists() and active_session_eeg_data_filepath.is_file()
        # nChannels = session.extracellular.nChannels
        # srLfp = session.extracellular.srLfp  
        # numchannel = 96
        # srLfp = 1250
        loaded_eeg_data = cls.readmulti(active_session_eeg_data_filepath, numchannel)
        return loaded_eeg_data, active_session_eeg_data_filepath, active_session_folder

    @classmethod
    def compute_ripples(cls, model, loaded_eeg_data, active_shank_channels_lists, 
        srLfp = 1250, downsampled_fs = 1250, 
        overlapping = True, window_size = 0.0128, window_stride = 0.0064, # window parameters
        ripple_detection_threshold=0.7, debug_trace_computations_output=False, out_all_ripple_results=None, debug_print=False):
        
        ## Create Empty Output:
        computation_params = None

        ## Create new global result containers IFF they don't already exists
        if computation_params is None:
            computation_params = dict(overlapping = True, window_size = 0.0128, stride=0.0064, threshold=ripple_detection_threshold, learning_rate=0.001, beta_1=0.9, beta_2=0.999, epsilon=1e-07, amsgrad=False)
        if out_all_ripple_results is None:
            out_all_ripple_results = {'computation_params': computation_params, 'results': dict()}


        ## Pre-process the data

        # flattened_channels_list is a flat list of channels (not partitioned into lists of 8 channels corresponding to a single probe)
        flattened_channels_list = list(itertools.chain.from_iterable(active_shank_channels_lists))

        print("Shape of loaded data: ", np.shape(loaded_eeg_data))
        # Downsample data
        downsampled_loaded_eeg_data = cls._downsample_data(loaded_eeg_data, srLfp, downsampled_fs)
        post_downsampling_srLfp = downsampled_fs # after downsampling data, the passed srLfp should be set to the downsampled rate so it isn't downsampled again

        out_all_ripple_results['preprocessed_data'] = {'data':downsampled_loaded_eeg_data, 'post_downsampling_srLfp': post_downsampling_srLfp, 'flattened_channels_list': flattened_channels_list}
        print("Done!")


        # shank = 0
        # active_shank_channels = [72,73,74,75,76,77,78,79]
        # shank = 1
        # active_shank_channels = [81,82,83,84,85,86,87,88]
        # ...
        
        for active_shank, active_shank_channels in enumerate(active_shank_channels_lists):
            print(f'working on shank {active_shank} with channels: {active_shank_channels}...')
            try:
                out_result = cls._run_single_shank_computation(model, downsampled_loaded_eeg_data, active_shank, active_shank_channels, srLfp=post_downsampling_srLfp, downsampled_fs=downsampled_fs,
                    overlapping=overlapping, window_size=window_size, window_stride=window_stride, ripple_detection_threshold=ripple_detection_threshold,
                    debug_trace_computations_output=debug_trace_computations_output, debug_print=debug_print)
                out_all_ripple_results['results'][active_shank] = out_result
            except ValueError as e:
                out_result = {} # empty output result
                print(f'skipping shank {active_shank} with too many values ({len(active_shank_channels)}, expecting exactly 8).') 

        print(f'done with all!')
        return out_all_ripple_results


# ==================================================================================================================== #
# Start MAIN                                                                                                           #
# ==================================================================================================================== #

def main_compute_with_params_loaded_from_xml(local_session_path, **kwargs):
    """Loads the session recording info from the XML located in the local_session_path (session folder), and the computes the ripples from that data

    Args:
        local_session_path (_type_): _description_

    Returns:
        _type_: _description_

    Usage:
        from src.cnn.PhoRippleDetectionTesting import ExtendedRippleDetection, main_compute_with_params_loaded_from_xml

        # local_session_path = Path(r'W:\Data\KDIBA\gor01\one\2006-6-08_14-26-15')
        # local_session_path = Path(r'W:\Data\KDIBA\gor01\one\2006-6-08_14-26-15')
        local_session_path = Path(r'W:\Data\KDIBA\gor01\one\2006-6-13_14-42-6')
        ripple_df, out_all_ripple_results, out_all_ripple_results = main_compute_with_params_loaded_from_xml(local_session_path)


    """
    session_xml_filepath, session_stem, local_session_path = find_session_xml(local_session_path)
    out_xml_dict, d = LoadXml(session_xml_filepath)
    print(f"active_shank_channels_lists: {out_xml_dict['AnatGrps']}")

    ## Build the detector:
    test_detector = ExtendedRippleDetection(learning_rate=0.001, beta_1=0.9, beta_2=0.999, epsilon=1e-07, amsgrad=False)
    ripple_df, out_all_ripple_results = test_detector.compute(**({'active_session_folder': local_session_path,
         'numchannel': out_xml_dict['nChannels'], 'srLfp': out_xml_dict['lfpSampleRate'], 'active_shank_channels_lists': out_xml_dict['AnatGrps'],
         'overlapping': True, 'window_size': 0.0128, 'window_stride': 0.0064} | kwargs))

    # out_all_ripple_results
    ripple_df.to_pickle(local_session_path.joinpath('ripple_df.pkl'))
    print(f'done. Exiting.')
    return test_detector, ripple_df, out_all_ripple_results, out_all_ripple_results


if __name__ == '__main__':
    # model_path = r'C:\Users\pho\repos\cnn-ripple\model'
    # g_drive_session_path = Path('/content/drive/Shareddrives/Diba Lab Data/KDIBA/gor01/one/2006-6-08_14-26-15')

    local_session_parent_path = Path(r'W:\Data\KDIBA\gor01\one')
    local_session_names_list = ['2006-6-07_11-26-53', '2006-6-08_14-26-15', '2006-6-09_1-22-43', '2006-6-09_3-23-37', '2006-6-12_15-55-31', '2006-6-13_14-42-6']
    local_session_paths_list = [local_session_parent_path.joinpath(a_name).resolve() for a_name in local_session_names_list]

    active_local_session_path: Path = local_session_paths_list[0]
    test_detector, ripple_df, out_all_ripple_results, out_all_ripple_results = main_compute_with_params_loaded_from_xml(active_local_session_path)


    # # active_shank_channels_lists = [a_list[:8] for a_list in active_shank_channels_lists if len(a_list)>=8]
    