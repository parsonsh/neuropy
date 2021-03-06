"""Global variables that can be modified by the user at the IPython command line.
Access programatically using:

get_ipython().user_ns['VARNAME']
"""
import os
from core import mergeuniquedictvals, dictattr
import colour as clr

DATAPATH = os.path.expanduser('~/data')
#BLABPATH = os.path.join(DATAPATH, 'blab') # Busse Lab
BLABPATH = os.path.join(DATAPATH, 'blab', 'natstate') # Busse Lab
SLABPATH = os.path.join(DATAPATH, 'slab') # Swindale Lab
MOVIEPATH = os.path.join(SLABPATH, 'mov')
MOVIES = dictattr()

# for each recording, load all Sorts, or just the most recent one?
LOADALLSORTS = False

"""Mean spike rate that delineates normal vs "quiet" neurons. 0.1 Hz seems reasonable if you
plot mean spike rate distributions for all the neurons in a given track. But, if you want a
reasonable looking DJS histogram without a lot of missing netstates, you need to exclude
more low firing rate cells, 0.5 works better"""
MINRATE = 0.05 # Hz
"""Calculate a TrackNeuron's meanrate according to its trange (period between its first and
last spike), or according to its track's entire duration. Need to reload the track or call
Track.calc_meanrates() after changing this on the fly"""
TRACKNEURONPERIOD = 'track' # 'trange' or 'track'
# ditto for recordings:
RECNEURONPERIOD = 'recording' # 'trange' or 'recording'

"""NeuronCode (Ising matrix) and network state parameters"""
CODEKIND = 'binary'
# values to use for CODEKIND codes, doesn't seem to make any difference to correlation
# calcs, unless set to really extreme values like [-100s, 100s], which is probably due to
# int8 overflow
CODEVALS = [0, 1]
CODETRES = 20000 # us
CODEPHASE = 0 # deg
CODEWORDLEN = 10 # in bits

"""Spike correlation time range windows"""
SCWIDTH = 10 # sec
SCTRES = 1 # sec
SCLIMITS = -0.01, 0.13

"""Multiunit activity time range windows"""
MUAWIDTH = 0.25 # sec
MUATRES = 0.1 # sec
TMUAWIDTH = 0.02 # sec
TMUATRES = 0.005 # sec

"""MUA synchrony index time range windows"""
MUASIWIDTH = 10 # sec
MUASITRES = 1 # sec
MUASIKIND = 'nstdmed'

"""LFP spectrogram time range windows"""
LFPSPECGRAMWIDTH = 2 # sec
LFPSPECGRAMTRES = 0.5 # sec

"""LFP power ratio time range windows, used by default LFPSIKIND"""
LFPPRWIDTH = 30 # sec
LFPPRTRES = 1 # sec
LFPPRLOBAND = 0.5, 5 # Hz
LFPPRHIBAND = 15, 150 # Hz
LFPPRBINLEDGES = [0, 0.5, 0.7, 0.85] # power ratio left bin edges, designate states
LFPPRBINCOLOURS = clr.MIDBLUE, clr.DARKGREEN, clr.ORANGE, clr.RED
NAUTOSTATES = len(LFPPRBINLEDGES)
assert NAUTOSTATES == len(LFPPRBINCOLOURS)
AUTOSTATES = list(range(NAUTOSTATES))

"""LFP synchrony index time range windows"""
LFPSIKIND = 'L/(L+H)' #'n3stdmed'
LFPSIWIDTH = 10 # sec, used only for non-power ratio LFPSIKIND
LFPSITRES = 2 # sec, used only for non-power ratio LFPSIKIND

"""List of sorted track IDs"""
TRACKS = ['ptc15.tr7c', 'ptc22.tr1', 'ptc22.tr2']

"""Track-specific superficial, middle and deep layer ranges (um), inferred from
track.pospdf and sc.pos"""
LAYERS = {'ptc15.tr7c': [(0, 900), (900, 1100), (1100, 2000)],
          'ptc22.tr1':  [(0, 500), (500,  700), ( 700, 2000)],
          'ptc22.tr2':  [(0, 550), (550,  700), ( 700, 2000)]}

"""Polytrode type to shank width (um) mapping, from NeuroNexus 2008 catalog"""
PTSHANKWIDTHS = {'uMap54_1a':207, 'uMap54_1b':210, 'uMap54_1c':208,
                 'uMap54_2a':200, 'uMap54_2b':207}

"""Polytrode type to shank tip length (um) mapping, from NeuroNexus 2008 catalog"""
PTTIPLENGTHS = {'uMap54_1a':325, 'uMap54_1b':324, 'uMap54_1c':324,
                'uMap54_2a':324, 'uMap54_2b':324}

"""IDs of blankscreen recordings"""
BSRIDS = {'ptc15.tr7c': ['87'],
          'ptc22.tr1':  ['07', '09', '11', '21'],
          'ptc22.tr2':  ['27', '32', '36']}

"""IDs of msequence recordings"""
MSRIDS = {'ptc15.tr7c': ['70', '81', '91', '92', '94'],
          'ptc22.tr1':  ['04', '17'],
          'ptc22.tr2':  ['26', '34']}

"""IDs of natural scene movie recordings"""
NSRIDS = {'ptc15.tr7c': ['76', '96'],
          'ptc22.tr1':  ['05', '06', '08', '10', '19', '20'],
          'ptc22.tr2':  ['28', '33']}

"""IDs of drift bar recordings"""
DBRIDS = {'ptc15.tr7c': ['71', '82'],
          'ptc22.tr1':  ['03', '18'],
          'ptc22.tr2':  ['25', '31']}

"""IDs of drift grating recordings"""
DGRIDS = {'ptc15.tr7c': ['85'],
          'ptc22.tr1':  ['14']}

"""IDs of flash grating recordings"""
FGRIDS = {'ptc15.tr7c': ['73'],
          'ptc22.tr1':  ['13'],
          'ptc22.tr2':  ['30']}

"""IDs of full field flash recordings"""
FFRIDS = {'ptc15.tr7c': ['69', '78', '79', '88', '93'],
          'ptc22.tr1':  ['01', '02', '12', '16', '22'],
          'ptc22.tr2':  ['23', '24', '35']}

"""Per-track list of blankscreen, mseq, natscene, and driftbar recordings"""
BSMSNSDBRIDS = mergeuniquedictvals([BSRIDS, MSRIDS, NSRIDS, DBRIDS])
"""Per-track list of mseq, driftbar, driftgrating, and flashed grating recordings"""
MSDBDGFGRIDS = mergeuniquedictvals([MSRIDS, DBRIDS, DGRIDS, FGRIDS])
"""Per-track list of blankscreen, natscene, mseq, driftbar, driftgrating, and flashed grating
recordings"""
BSNSMSDBDGFGRIDS = mergeuniquedictvals([BSRIDS, NSRIDS, MSRIDS, DBRIDS, DGRIDS, FGRIDS])


NULLDIN = 65535 # integer value in stimulus .din files used as NULL (stimulus off)
ALPHA = 0.05 # threshold p value for rejecting null hypothesis

# mapping of recording absname to list of desynched and synched tranges, in that order.
# tranges are in us relative to start of ADC clock:
REC2STATETRANGES = {'ptc17.tr2b.r58': [(5.7e6, 700e6), # desynched trange, 66 Hz refresh rate
                                       (800e6, 1117.1e6)], # synched trange, 66 Hz refresh rate
                    'ptc18.tr1.r38':  [(43.8e6, 425e6), # desynched trange, ends ~ trial 76
                                       (550e6, 2243.8e6)], # synched trange, starts ~ trial 98
                    'ptc18.tr2c.r58': [(49e6, 750e6), # desynched trange
                                       (1000e6, 2248.9e6)], # synched trange
                    'ptc22.tr1.r08':  [(11e6, 1500e6), # desynched trange
                                       (1550e6, 2329.9e6)], # synched trange
                    'ptc22.tr1.r10':  [(1480e6, 2330.9e6), # desynched trange
                                       (12.1e6, 1400e6)], # synched trange
                    'ptc22.tr4b.r49': [(12.7e6, 1475e6), # desynched trange
                                       (1500e6, 2331.6e6)], # synched trange
                   }


MANUALSTATES = ['d', 's']
MANUALSTATECOLOURS = {'d':clr.MIDBLUE, 's':clr.RED}
# mapping of recording absname to dict of manually defined lists of
# desynched ('d') and synched ('s') tranges.
# tranges are in sec relative to start of ADC clock:
REC2STATE2TRANGES = {
                     'ptc17.tr2b.r58': {'d':[(5.7, 700)], # 66 Hz refresh rate
                                        's':[(800, 1117.1)]}, # 66 Hz refresh rate
                     'ptc18.tr1.r38':  {'d':[(43.8, 425)],
                                        's':[(550, 2243.8)]},
                     'ptc18.tr2c.r58': {'d':[(49, 750)],
                                        's':[(1000, 2248.9)]},
                     'ptc22.tr1.r08':  {'d':[(11, 1500)],
                                        's':[(1550, 2329.9)]},
                     'ptc22.tr1.r10':  {'d':[(1480, 2330.9)],
                                        's':[(12.1, 1400)]},
                     'ptc22.tr4b.r49': {'d':[(12.7, 1475)],
                                        's':[(1500, 2331.6)]},
                     'nts174.tr2.r05': {'d':[(1260, 3605)],
                                        's':[(0, 1250)]},
                     'pvc107.tr1.r09': {'d':[(550, 1205)],
                                        's':[(0, 500)]},
                     'pvc113.tr1.r11': {'d':[(0, 340), (1050, 1205)],
                                        's':[(370, 1040)]},
                    }
