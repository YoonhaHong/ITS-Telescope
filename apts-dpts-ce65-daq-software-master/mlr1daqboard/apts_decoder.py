import numpy as np
import struct
import tqdm
import mlr1daqboard

def decode_apts_event(data,decode_timestamps=False,mux=False):
    ''' Decodes raw APTS data to numpy array of shape (4,4,nframes) '''
    d = np.frombuffer(data,dtype=np.uint8)
    mapping = mlr1daqboard.APTS_MUX_PIXEL_ADC_MAPPING if mux else mlr1daqboard.APTS_PIXEL_ADC_MAPPING
    frames = []
    fts = [] # frame timestamps
    assert len(d)%40==0
    nframes = len(d)//40
    for i in range(nframes):
        ii=i*40
        frames.append(np.packbits(np.unpackbits(d[ii:ii+32],bitorder='little').reshape(16,16).T.flatten()).view('>u2')[np.argsort(mapping)].reshape(4,4))
        if decode_timestamps:
            fts.append(d[ii+33]<<40|d[ii+32]<<32|d[ii+35]<<24|d[ii+34]<<16|d[ii+37]<<8|d[ii+36]<<0)
        trailer=int(d[ii+39])<<8|int(d[ii+38])
        if i<nframes-1:
            assert trailer==0xFEFE, f"Unexpected frame trailer 0x{trailer:04X} for frame {i+1} out of {nframes}"
        else:
            assert trailer==0xAEAE, f"Unexpected event trailer 0x{trailer:04X} for frame {i+1} out of {nframes}"
    if decode_timestamps:
        return np.array(frames).T,np.array(fts)
    else:
        return np.array(frames).T


def decode_trigger_timestamp(data):
    # N.B. FW compiled before 13/01/22 contains an error and this decoding doesn't work
    ts1,ts2,trailer=struct.unpack('<III', data)
    assert trailer==0xAEAEAE00, f"Unexpected trigger timestamp trailer 0x{trailer:08X}"
    return (ts1<<32)|ts2

class APTSDecoder:
    def __init__(self,fname,progress_bar=True,mux=False):
        with open(fname,'rb') as f:
            self.data = f.read()
        self.i=0
        self._len_data = len(self.data)
        self.iev=0
        self._mux = mux
        if progress_bar:
            self.pbar = tqdm.tqdm(total=self._len_data,desc='Decoding')
        else:
            self.pbar = None

    def is_done(self):
        done = self.i >= self._len_data
        if self.pbar and done:
            self.pbar.close()
            self.pbar = None
        return done

    def get_next_event(self):
        if self.is_done(): return None
        i=self.i
        assert i+8<=self._len_data, f"Ev {self.iev}: Unexpected data length ({self._len_data-i} < 8)"
        
        assert list(self.data[i:i+4])==[0xAA]*4, f"Ev {self.iev}: expected header, got {self.data[i:i+4].hex('-')}"
        length = struct.unpack('<I', self.data[i+4:i+8])[0]
        i+=8
        assert i+length<=self._len_data, f"Ev {self.iev}: Missing data ({i} {length} {self._len_data})"
        
        waveforms = decode_apts_event(self.data[i:i+length], mux=self._mux)
        i+=length
        if i+12<=self._len_data and list(self.data[i:i+4])==[0xBB]*4: # trigger timestamp
            trigger_timestamp = decode_trigger_timestamp(self.data[i+4:i+16])
            i+=16
        else:
            trigger_timestamp = None
        if self.pbar: self.pbar.update(i-self.i)
        self.i = i
        self.iev += 1
        return waveforms,trigger_timestamp
