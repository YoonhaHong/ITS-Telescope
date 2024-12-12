import numpy as np
import pickle
import struct
from tqdm import tqdm
from mlr1daqboard.apts_decoder import decode_apts_event, decode_trigger_timestamp


def decode_scope_event(data,n_channels,n_frames,n_bytes_per_frame):
    ''' Decodes raw scope data to numpy array of shape (n_channels,nframes) '''
    assert n_bytes_per_frame in [1,2,4], "Scope data precision is 1, 2 or 4 bytes"
    if n_bytes_per_frame == 1:
        d = np.frombuffer(data, dtype=np.int8)
    elif n_bytes_per_frame == 2:
        d = np.frombuffer(data, dtype=np.int16)
    else:
        d = np.frombuffer(data, dtype=np.float32)
    frames = []
    for i in range(n_channels):
        frames.append(d[i*n_frames:(i+1)*n_frames])
    return np.swapaxes(np.array(frames).T,0,1)


class OPAMPDecoder:
    
    def __init__(self,fname,n_scope_channels,scope_memory_depth,scope_data_precision,header,progress_bar=True):
        with open(fname, 'rb') as f:
            raw_data_dict = pickle.load(f)
            self.adc_data = raw_data_dict["ADC"]
            self.scope_data = raw_data_dict["scope"]
            
        # ADC data
        self._len_adc_data = len(self.adc_data)
        self.i=0
        self.iev=0
        # scope data
        if header != None: #removing scope header, if present
            # The header argument is formed by:
            # [0] byte in header
            # [1] byte in footer
            # [2] num pulses
            # [3] num points scanned
            event_num = int(header[3])*int(n_scope_channels)*int(header[2])
            no_header = bytearray()
            for i in range(event_num+1):
                no_header.extend(self.scope_data[int(int(header[0]))+(scope_memory_depth+int(int(header[0]))+int(header[1]))*i:scope_memory_depth+int(int(header[0]))+(scope_memory_depth+int(int(header[0]))+int(header[1]))*i])
            self.scope_data = no_header
        
        self._len_scope_data = len(self.scope_data)
        self._measured_pixels = n_scope_channels
        self._n_points_waveform = scope_memory_depth
        self._n_bytes = scope_data_precision
        self.j=0
        self.jev=0        
        if progress_bar:
            self.adc_pbar = tqdm(total=self._len_adc_data,desc='ADC decoding')
            self.scope_pbar = tqdm(total=self._len_scope_data,desc='Scope decoding')
        else:
            self.adc_pbar = None
            self.scope_pbar = None

    def is_adc_done(self):
        done = self.i >= self._len_adc_data
        if self.adc_pbar and done:
            self.adc_pbar.close()
            self.adc_pbar = None
        return done

    def get_next_adc_event(self):
        if self.is_adc_done(): return None
        i=self.i
        assert i+8<=self._len_adc_data, f"Ev {self.iev}: Unexpected data length ({self._len_adc_data-i} < 8)"
        
        assert list(self.adc_data[i:i+4])==[0xAA]*4, f"Ev {self.iev}: expected header, got {self.adc_data[i:i+4].hex('-')}"
        length = struct.unpack('<I', self.adc_data[i+4:i+8])[0]
        i+=8
        assert i+length<=self._len_adc_data, f"Ev {self.iev}: Missing data ({i} {length} {self._len_adc_data})"
        
        waveforms = decode_apts_event(self.adc_data[i:i+length])
        i+=length
        if i+12<=self._len_adc_data and list(self.adc_data[i:i+4])==[0xBB]*4: # trigger timestamp
            trigger_timestamp = decode_trigger_timestamp(self.adc_data[i+4:i+16])
            i+=16
        else:
            trigger_timestamp = None
        if self.adc_pbar: self.adc_pbar.update(i-self.i)
        self.i = i
        self.iev += 1
        return waveforms,trigger_timestamp

    def is_scope_done(self):
        done = self.j >= self._len_scope_data
        if self.scope_pbar and done:
            self.scope_pbar.close()
            self.scope_pbar = None
        return done

    def get_next_scope_event(self):
        if self.is_scope_done(): return None
        j=self.j
        length = self._measured_pixels*self._n_points_waveform
        assert j+length<=self._len_scope_data, f"Ev {self.jev}: Unexpected data length ({self._len_scope_data-j} < {length})"

        waveforms = decode_scope_event(self.scope_data[j:j+length],self._measured_pixels,self._n_points_waveform,self._n_bytes)
        j+=length

        if self.scope_pbar: self.scope_pbar.update(j-self.j)
        self.j = j
        self.jev += 1
        return waveforms
