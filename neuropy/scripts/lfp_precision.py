"""Examine trial-averaged LFP during synched and desynched state of the specified natural
scene movies. Run from within neuropy using `run -i scripts/lfp_precision.py`"""

from __future__ import division, print_function

import matplotlib.pyplot as plt
from matplotlib import gridspec

from core import sparseness, ceilsigfig

# copied from psth_precision.py:
rec2tranges = {ptc17.tr2b.r58: [(0, 700e6), # desynched trange, 66 Hz refresh rate
                                (800e6, 1117e6)], # synched trange, 66 Hz refresh rate
               ptc18.tr1.r38:  [(0, 425e6), # desynched trange, ends ~ trial 76
                                (550e6, 2243e6)], # synched trange, starts ~ trial 98
               ptc18.tr2c.r58: [(0, 750e6), # desynched trange
                                (1000e6, 2248e6)], # synched trange
               ptc22.tr1.r08:  [(0, 1500e6), # desynched trange
                                (1550e6, 2329e6)], # synched trange
               ptc22.tr1.r10:  [(1480e6, 2331e6), # desynched trange
                                (0, 1400e6)], # synched trange
               ptc22.tr4b.r49: [(0, 1475e6), # desynched trange
                                (1500e6, 2331e6)], # synched trange
              }

FIGSIZE = (10, 5)
YLABELX = -0.05

reccmp = lambda reca, recb: cmp(reca.absname, recb.absname)
urecs = sorted(rec2tranges, cmp=reccmp) # unique recordings, no repetition, sorted
#urecnames = ' '.join([rec.absname for rec in urecs])
fmts = ('b-', 'r-') # desynched and synched
SNRs = [[], []] # desynched and synched

for rec in urecs:
    print(rec.absname)
    # subplotting trickery from
    # http://stackoverflow.com/questions/22511550/gridspec-with-shared-axes-in-python
    f = plt.figure(figsize=FIGSIZE)
    gs = gridspec.GridSpec(3, 1, height_ratios=[0.3, 0.3, 0.4])
    LFPa1 = f.add_subplot(gs[0])
    LFPa2 = f.add_subplot(gs[1], sharex=LFPa1)
    LFPas = [LFPa1, LFPa2]
    SNRa = f.add_subplot(gs[2], sharex=LFPa1)
    plt.setp(LFPa1.get_xticklabels(), visible=False)
    plt.setp(LFPa2.get_xticklabels(), visible=False)
    stranges = rec2tranges[rec]
    for statei, (strange, fmt, LFPa) in enumerate(zip(stranges, fmts, LFPas)): # desynched, then synched
        t, lfptrials = rec.tlfp(trange=strange, plot=False)
        lfpmean, lfpstd = lfptrials.mean(axis=0), lfptrials.std(axis=0)
        ntrials = len(lfptrials)
        # to make saturation represent LFP reliability, scale transparency inversely
        # with ntrials:
        alpha = 10 / ntrials
        # plot all trials for this rec, in mV
        LFPa.plot(t, lfptrials.T/1e3, fmt, alpha=alpha)
        LFPa.plot(t, lfpmean/1e3, 'w-', alpha=1)
        LFPa.plot(t, (lfpmean+lfpstd)/1e3, 'k-', alpha=1)
        LFPa.plot(t, (lfpmean-lfpstd)/1e3, 'k-', alpha=1)
        LFPa.set_xlim(xmax=5.5)
        LFPa.set_ylim(-0.5, 0.5) # mV
        LFPa.set_yticks([-0.5, 0, 0.5])
        LFPa.set_ylabel("LFP (mV)")
        LFPa.yaxis.set_label_coords(YLABELX, 0.5)
        # Fano-factor and CV don't work very well when mean approaches zero
        SNR = np.abs(lfpmean) / lfpstd # something like S/N ratio
        SNRs[statei].append(SNR)
        #SNR = lfpmean**2 / lfpstd**2 # something like (S/N)**2 ratio
        SNRa.plot(t, SNR, fmt)
        SNRa.set_xlim(xmax=5.5)
        SNRa.set_ylim(0, 3)
        SNRa.set_yticks([0, 1, 2, 3])
        SNRa.set_xlabel("time (s)")
        SNRa.set_ylabel(r"LFP S/N ($|\mu|/\sigma)$")
        SNRa.yaxis.set_label_coords(YLABELX+0.0012, 0.5) # has a descender
        f.canvas.manager.set_window_title("LFP reliability %s" % rec.absname)
        print('sparseness:', sparseness(np.abs(lfpmean)))
        print('mean tLFP S/N:', SNR.mean())
        f.tight_layout(pad=0.3) # crop figure to contents

#  collapse SNRs across recs:
for statei in range(2):
    SNRs[statei] = np.hstack(SNRs[statei])


SNRBINW = 0.1
snrbins = np.arange(0, 3+SNRBINW, SNRBINW) # left edges + rightmost edge
# calculate significance
u, p = mannwhitneyu(SNRs[0], SNRs[1]) # 1-sided
if p < np.finfo(np.float64).eps: # prevent 0 p-value due to underflow
    p = np.finfo(np.float64).eps
print('%.1g' % p)
# calculate PDFs:
nd = np.histogram(SNRs[0], bins=snrbins, density=True)[0]
ns = np.histogram(SNRs[1], bins=snrbins, density=True)[0]
#nmax = max(np.hstack([nd, ns]))
# normalize density to arbitrary units:
#nd = nd / nmax
#ns = ns / nmax
nd = np.hstack([nd, nd[-1]]) # repeat last point for right edge
ns = np.hstack([ns, ns[-1]])
figure(figsize=(3, 3))
plot(snrbins, nd, 'b-', lw=2)
plot(snrbins, ns, 'r-', lw=2)
# draw arrows at means:
ah = 0.4 # arrow height
dmean, smean = SNRs[0].mean(), SNRs[1].mean()
arrow(dmean, 3.5, 0, -ah, head_width=0.1, head_length=ah/2,
      length_includes_head=True, color='b')
arrow(smean, 3.5, 0, -ah, head_width=0.1, head_length=ah/2,
      length_includes_head=True, color='r')
xlabel(r"LFP S/N ($|\mu|/\sigma)$")
ylabel('probability density')
xticks([0, 1, 2, 3])
yticks([0, 1, 2, 3])
# display means and p value:
text(0.98, 0.98, '$\mu$ = %.1f' % smean, # synched
                 horizontalalignment='right', verticalalignment='top',
                 transform=gca().transAxes, color='r')
text(0.98, 0.90, '$\mu$ = %.1f' % dmean, # desynched
                 horizontalalignment='right', verticalalignment='top',
                 transform=gca().transAxes, color='b')
text(0.98, 0.82, 'p < %.1g' % ceilsigfig(p, 1),
                 horizontalalignment='right', verticalalignment='top',
                 transform=gca().transAxes, color='k')
gcfm().window.setWindowTitle('SNR_hist')
tight_layout(pad=0.3)
'''
# use hist() instead of histogram() and plot():
figure(figsize=(3, 3))
nd = hist(SNRs[0], bins=snrbins, histtype='step', color='b', normed=True)[0] # desynched
ns = hist(SNRs[1], bins=snrbins, histtype='step', color='r', normed=True)[0] # synched
xlabel(r"LFP S/N ($|\mu|/\sigma)$")
ylabel('probability density')
gcfm().window.setWindowTitle('SNR_hist')
tight_layout(pad=0.3)
'''
pl.show()
