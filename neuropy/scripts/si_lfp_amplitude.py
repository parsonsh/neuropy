"""Scatter plot synchrony index SI as a function of LFP peak-to-peak voltage and stdev. Run
from within neuropy using `run -i scripts/si_lfp_amplitude.py`"""

from __future__ import division, print_function

import numpy as np
import matplotlib as mpl
import pylab as pl
from pylab import get_current_fig_manager as gcfm

from core import intround, scatterbin
import filter


#tracks = [ptc21.tr6b]
#tracks = [ptc15.tr7c, ptc17.tr1, ptc17.tr2b, ptc18.tr1, ptc18.tr2c, ptc20.tr1, ptc20.tr2,
#          ptc20.tr3, ptc21.tr2, ptc21.tr5c, ptc21.tr6b, ptc22.tr1, ptc22.tr2, ptc22.tr4b,
#          ptc22.tr5b]
# ptc21 has is an outlier in these plots
# all cats except ptc21:
tracks = [ptc15.tr7c, ptc17.tr1, ptc17.tr2b, ptc18.tr1, ptc18.tr2c, ptc20.tr1, ptc20.tr2,
          ptc20.tr3, ptc22.tr1, ptc22.tr2, ptc22.tr4b, ptc22.tr5b]


lfpwidth, lfptres = 30, 5 # sec
chani = -1
kind = 'L/(L+H)'
figsize = (3.5, 3.5)
VPPMAX = 2 # mV
STDMAX = 250 # uV

if lfpwidth == None: # LFP window width
    lfpwidth = LFPSIWIDTH # sec
if lfptres == None: # LFP window tres
    lfptres = LFPSITRES # sec
assert lfptres <= lfpwidth

# collect SI and LFP Vpp from all recordings in all tracks:
sis, Vpps, stds = [], [], []
for track in tracks:
    print(track.absname)
    for rid in sorted(track.r):
        rec = track.r[rid]
        rname = rec.name.lower()
        if rname.count('freqsweep') > 0 or rname.count('csd') > 0:
            # it's a freqsweep or CSD recording:
            print('skip %s.' % rec.name, end='')
            continue # skip it, freqsweep especially induces wild high freqs in the LFP
        si, t = rec.lfp.si(kind=kind, lfpwidth=lfpwidth, lfptres=lfptres, plot=False)
        sis.append(si)
        data = rec.lfp.data[chani]
        ts = rec.lfp.get_tssec() # full set of timestamps, in sec
        tranges = core.split_tranges([(t[0]-lfpwidth/2, t[-1]+lfpwidth/2)], lfpwidth, lfptres)
        tiranges = ts.searchsorted(tranges)
        Vpp = [ data[tirange[0]:tirange[1]].ptp() for tirange in tiranges ]
        std = [ data[tirange[0]:tirange[1]].std() for tirange in tiranges ]
        Vpps.append(Vpp)
        stds.append(std)
        # keeping all 10 chans for each LFP for all tracks gives MemoryError:
        del data
        del rec.lfp.data
        print('.', end='')
    print()
sis = np.hstack(sis)
Vpps = np.hstack(Vpps) / 1e3 # convert from uV to mV
stds = np.hstack(stds)

figure(figsize=figsize)
plot(Vpps, sis, 'k.', ms=4, alpha=0.02)
Vppedges = np.arange(0.2, VPPMAX+0.15, 0.15) # mV
Vppmeans, sismeans, sisstds = scatterbin(Vpps, sis, Vppedges, average=np.median)
errorbar(Vppmeans, sismeans, yerr=sisstds, fmt='r.-', ms=5, lw=1, zorder=9999)
xlim(xmin=0, xmax=VPPMAX)
ylim(0, 1)
xlabel('LFP $V_{pp}$ (mV)')
ylabel('SI (L/(L+H))')
gcfm().window.setWindowTitle('SI vs Vpp lfpwidth=%g lfptres=%g' % (lfpwidth, lfptres))
tight_layout(pad=0.3)

figure(figsize=figsize)
plot(stds, sis, 'k.', ms=4, alpha=0.02)
stdedges = np.arange(20, STDMAX+20, 20) # mV
stdmeans, sismeans, sisstds = scatterbin(stds, sis, stdedges, average=np.median)
errorbar(stdmeans, sismeans, yerr=sisstds, fmt='r.-', ms=5, lw=1, zorder=9999)
xlim(xmin=0, xmax=STDMAX)
ylim(0, 1)
xlabel('LFP $\sigma$ ($\mu$V)')
ylabel('SI (L/(L+H))')
gcfm().window.setWindowTitle('SI vs sigma lfpwidth=%g lfptres=%g' % (lfpwidth, lfptres))
tight_layout(pad=0.3)

pl.show()