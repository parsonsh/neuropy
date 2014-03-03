"""Scatter plot various combinations of spatial sigma and temporal measures of spikes. Also
plot distributions and waveforms, as separated by shape thresholds. Run from within neuropy
using `run -i scripts/cell_type_temporal_spatial.py`"""

from __future__ import division

import scipy
from pylab import get_current_fig_manager as gcfm
from core import intround

plotwaves = False

# waveform timepoint to assume characteristic peak is roughly aligned to:
alignt = 400 # us
newtres = 1 # tres to interpolate to, in us
absslopethresh = 0.4 # uV/us
nabsslopethresh = 0.003 # for normalized waveforms, 1/us
durationthresh = 350 # duration separation threshold
nbins = 20
tracks = [ptc15.tr7c, ptc22.tr1, ptc22.tr2] # need to be loaded ahead of time

def calc_t(nt, tres, newtres):
    """Generate original and desired interpolated timebases t0 and t1, as well as initial
    guess for where the alignment point is in t1"""
    tend = nt*tres
    t0 = np.arange(0, tend, tres)
    t1 = np.arange(0, tend-tres, newtres)
    aligni = abs(t1 - alignt).argmin()
    return t0, t1, aligni

def argextrema(a):
    """Return indices of local extrema in 1D array a.
    Taken from http://stackoverflow.com/a/9667121/2020363"""
    return np.diff(np.sign(np.diff(a))).nonzero()[0] + 1

def arg0xextrema(a):
    """Return indices of biggest extrema between edges and 0 crossings in 1D array a"""
    zcis = np.where(np.diff(np.sign(a)) != 0)[0] # zero crossing indices
    edgeis = np.hstack([0, zcis, len(a)-1]) # add left and right edges
    extis = []
    for edgei0, edgei1 in zip(edgeis[:-1], edgeis[1:]):
        segment = a[edgei0:edgei1]
        segmentextis = argextrema(segment)
        if len(segmentextis) > 0: # start and end segments might not have any extrema
            maxsegmentextii = abs(segment[segmentextis]).argmax()
            extis.append(segmentextis[maxsegmentextii] + edgei0)
    return hstack(extis)

def argfwhm(a, exti, fraction=0.5):
    """Find timepoints of full width half max (or whatever fraction is) around extremum
    at index exti in 1D array a"""
    #a = abs(a)
    fm = a[exti] * fraction # fraction of max
    d = a - fm
    lis = np.diff(np.sign(d[:exti])).nonzero()[0]
    ris = np.diff(np.sign(d[exti:])).nonzero()[0] + exti + 1
    assert len(lis) > 0
    if not len(ris) > 0:
        # linearly extrapolate right edge of a until it falls below 0
        # find slope from last two points:
        m = a[-1] - a[-2]
        b = a[-1]
        assert b * m < 0 # heading towards 0? or we'll never find the end of this extremum
        n = ceil(abs(b / m)) # number of points to extrapolate to get to 0
        y = m * np.arange(n) + b # extrapolated points
        a = np.hstack([a, y]) # extrapolated points concatenated to end of a
        # now try again:
        d = a - fm
        lis = np.diff(np.sign(d[:exti])).nonzero()[0]
        ris = np.diff(np.sign(d[exti:])).nonzero()[0] + exti + 1
        assert len(lis) > 0
        assert len(ris) > 0
        #import pdb; pdb.set_trace()
    # return rightmost of left indices, and leftmost of right indices:
    return lis[-1], ris[0]

nt = 50
tres = 20
t0, t1, aligni = calc_t(nt, tres, newtres) # initial guess, for speed
sigmas = []
waves = []
nwaves = [] # peak-to-peak normalized waveforms
fwhm1s = [] # full-width half max values of primary peak
fwhm2s = [] # full-width half max values of secondary peak
ipis = [] # interpeak intervals
duration2s = [] # start of primary to end of secondary peak
# primary peak asymmetry index, secondary peak asymmetry index, amplitude asymmetry index
ai0s, ai1s, aais = [], [], []
#maxslopes = [] # maximum abs slopes of each waveform
#maxnslopes = [] # maximum abs slopes of each normalized waveform
#durations = [] # spike duration, measured by time between slope threshold crossings
#ndurations = [] # spike duration measured from normalized waveforms
#slopeiss = [] # start and end timepoint indices used for calculating durations
#nslopeiss = [] # start and end timepoint indices used for calculating ndurations
allnids = []
splitis = [] # indices which demarcate neurons from different tracks in allnids
nswaps = 0

# collect maxchan waveforms and calculate various measures of waveform duration:
for track in tracks:
    splitis.append(len(allnids))
    if tres != track.tres: # recalculate timepoints
        tres = track.tres
        t0, t1, aligni = calc_t(nt, tres, newtres)
    nids = sorted(track.alln)
    for nid in nids:
        n = track.alln[nid]
        if nt != n.nt: # recalculate timepoints
            nt = n.nt
            t0, t1, aligni = calc_t(nt, tres, newtres)
        sigmas.append(n.sigma)
        maxchani = n.chans.searchsorted(n.maxchan)
        wave = n.wavedata[maxchani]
        # interpolate waveforms from original t0 timebase to higher rez t1 timebase:
        wave = scipy.interpolate.spline(t0, wave, t1)
        waves.append(wave)
        nwave = wave / wave.ptp() # normalize peak-to-peak amplitudes
        nwaves.append(nwave)
        extis = arg0xextrema(wave) # indices of biggest peaks between 0 crossings and edges
        extii = abs(extis - aligni).argmin() # extremum closest to aligni
        exti0 = extis[extii] # index of extremum closest to aligni, assume main extremum

        # find index of extremum to the right of the one closest to aligni. If the one
        # closest to aligni is already the rightmost, make that one the secondary, and the one
        # to its left the primary:
        try:
            exti1 = extis[extii+1]
        except IndexError:
            exti1 = exti0 # make old primary the new secondary
            # set new primary to be the one to the left, hopefully without another IndexError:
            exti0 = extis[extii-1]
            nswaps += 1
        # 0.75 seems to give max fwhm2 bimodality, but 0.5 gives best overall clusterability
        # in fwhm2 vs aai space
        li0, ri0 = argfwhm(wave, exti0, fraction=0.5)
        li1, ri1 = argfwhm(wave, exti1, fraction=0.5)
        fwhm1 = (ri0 - li0) * newtres
        fwhm2 = (ri1 - li1) * newtres
        #t0i, t1i = wave.argmax(), wave.argmin() # previously used biggest peaks for ipi
        ipi = (exti1 - exti0) * newtres # interval between primary and secondary peaks
        duration2 = (ri1 - li0) * newtres # start of primary to end of secondary peak
        ai0 = (ri0 - exti0) / (exti0 - li0) # asymmetry index of primary peak
        ai1 = (ri1 - exti1) / (exti1 - li1) # asymmetry index of secondary peak
        V0, V1 = abs(wave[exti0]), abs(wave[exti1])
        aai = (V0 - V1)/(V0 + V1) # amplitude asymmetry index
        fwhm1s.append(fwhm1)
        fwhm2s.append(fwhm2)
        ipis.append(ipi)
        duration2s.append(duration2)
        ai0s.append(ai0)
        ai1s.append(ai1)
        aais.append(aai)
        if plotwaves:
            figure()
            plot(wave, 'k')
            # plot fwhm of primary and secondary peaks:
            nit = len(t1) # number of interpolated timepoints
            minri0 = min(ri0, nit)
            minri1 = min(ri1, nit)
            plot(np.arange(li0, minri0), wave[li0:minri0], 'r')
            plot(np.arange(li1, minri1), wave[li1:minri1], 'b')
            # plot points used for ipi:
            plot(exti0, wave[exti0], 'g', ms=10)
            plot(exti1, wave[exti1], 'g', ms=10)
            titlestr = 'wave %d (%s)' % (len(fwhm1s)-1, track.absname + '.n%d' % nid)
            gcfm().window.setWindowTitle(titlestr)
        '''
        absslope = abs(np.diff(wave)) / newtres # uV/us
        maxslopes.append(max(absslope))
        nabsslope = abs(np.diff(nwave)) / newtres # 1/us
        maxnslopes.append(max(nabsslope))        
        # another way to measure waveform duration is to see over what duration the abs(slope)
        # is greater than something close to 0. Starting from each end, at what timepoint does
        # the slope exceed this minimum threshold? Difference between timepoints is duration
        # of waveform
        slopeis = np.where(absslope > absslopethresh)[0]
        if len(slopeis) < 2:
            # exclude cells whose slope isn't above threshold for at least two timepoints:
            duration = 0
            slopeiss.append([0, 0])
        else:
            duration = (slopeis[-1] - slopeis[0]) * newtres
            slopeiss.append([slopeis[0], slopeis[-1]])
        durations.append(duration)
        # repeat for normalized waveforms:
        nslopeis = np.where(nabsslope > nabsslopethresh)[0]
        if len(nslopeis) < 2:
            # exclude cells whose slope isn't above threshold for at least two timepoints:
            nduration = 0
            nslopeiss.append([0, 0])
        else:
            nduration = (nslopeis[-1] - nslopeis[0]) * newtres
            nslopeiss.append([nslopeis[0], nslopeis[-1]])
        ndurations.append(nduration)
        '''
        allnids.append(nid)
        # - as an alternative to using absslopethresh, measure the fwhm of the last
        # extremum in each waveform. Looking at the overplotted waveforms, that, strangely,
        # is where I see the most dichotomy. Not so much in the first peak.
        # - try taking sum of slopes, or sum of 2nd derivatives, across entire waveform
        # - plot Vpp
        # - best of all might be to find the time between inflection points around the later of
        # the two biggest peaks. However, this really would require using longer waveforms
        # to ensure the inflection point after the second peak is found. Or, just estimate
        # it manually for the few templates that don't have one. Also, might require some
        # smoothing to get around the occasional noise in the slope

waves = np.asarray(waves)
nwaves = np.asarray(nwaves)
sigmas = np.hstack(sigmas)
fwhm1s = np.hstack(fwhm1s)
fwhm2s = np.hstack(fwhm2s)
ipis = np.hstack(ipis)
duration2s = np.hstack(duration2s)
ai0s = np.hstack(ai0s)
ai1s = np.hstack(ai1s)
aais = np.hstack(aais)
#durations = np.hstack(durations)
#ndurations = np.hstack(ndurations)
#slopeiss = np.vstack(slopeiss)
#nslopeiss = np.vstack(nslopeiss)
allnids = np.hstack(allnids)
nn = len(allnids)
splitis.append(nn)
'''
# plot unclassified maxchan waveforms:
figure(figsize=(3, 3))
for wave in waves:
    plot(t1, wave, '-', lw=1) # overplot all waveforms
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('waveforms')
tight_layout(pad=0.3)
'''
'''
# scatter plot sigma vs ipi
figure(figsize=(3, 3))
plot(ipis, sigmas, 'k.')
#xticks([0, 100, 200, 300, 400])
yticks(np.arange(0, 100+20, 20))
xlabel('interpeak interval ($\mu$s)')
ylabel('$\sigma$ ($\mu$m)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma vs ipi')
tight_layout(pad=0.3)

# scatter plot sigma vs fwhm1
figure(figsize=(3, 3))
plot(fwhms, sigmas, 'k.')
xlabel('FWHM1 ($\mu$s)')
ylabel('$\sigma$ ($\mu$m)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma vs fwhm1')
tight_layout(pad=0.3)

# scatter plot sigma vs fwhm2
figure(figsize=(3, 3))
plot(fwhms, sigmas, 'k.')
xlabel('FWHM2 ($\mu$s)')
ylabel('$\sigma$ ($\mu$m)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma vs fwhm2')
tight_layout(pad=0.3)

# scatter plot sigma vs slope
figure(figsize=(3, 3))
plot(maxslopes, sigmas, 'k.')
xlabel('maximum slope ($\mu$V/$\mu$s)')
ylabel('$\sigma$ ($\mu$m)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma vs maxslope')
tight_layout(pad=0.3)

# scatter plot sigma vs duration2
figure(figsize=(3, 3))
plot(duration2s, sigmas, 'k.')
ylim(ymin=0)
#xticks([0, 200, 400, 600, 800])
xlabel('duration2 ($\mu$s)')
ylabel('$\sigma$ ($\mu$m)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma vs duration2')
tight_layout(pad=0.3)
'''
'''
# scatter plot fwhm1 vs ipi
figure(figsize=(3, 3))
plot(ipis, fwhm1s, 'k.')
xlabel('interpeak interval ($\mu$s)')
ylabel('FWHM1 ($\mu$s)')
gcfm().window.setWindowTitle('fwhm1 vs ipi')
tight_layout(pad=0.3)
'''
'''
# scatter plot fwhm2 vs ipi
figure(figsize=(3, 3))
plot(ipis, fwhm2s, 'k.')
xlabel('interpeak interval ($\mu$s)')
ylabel('FWHM2 ($\mu$s)')
gcfm().window.setWindowTitle('fwhm2 vs ipi')
tight_layout(pad=0.3)

# scatter plot fwhm2 vs fwhm1
figure(figsize=(3, 3))
plot(fwhm1s, fwhm2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
xlabel('FWHM1 ($\mu$s)')
ylabel('FWHM2 ($\mu$s)')
gcfm().window.setWindowTitle('fwhm2 vs fwhm1')
tight_layout(pad=0.3)
'''
'''
# scatter plot sumfwhm vs ipi
figure(figsize=(3, 3))
plot(ipis, fwhm1s+fwhm2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
xlabel('interpeak interval ($\mu$s)')
ylabel('sum(FWHM) ($\mu$s)')
gcfm().window.setWindowTitle('sum(fwhm) vs ipi')
tight_layout(pad=0.3)

# scatter plot slope vs ipi
figure(figsize=(3, 3))
plot(ipis, maxslopes, 'k.')
xlabel('interpeak interval ($\mu$s)')
ylabel('maximum slope ($\mu$V/$\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('maxslope vs ipi')
tight_layout(pad=0.3)
'''
'''
# scatter plot duration2 vs ipi
figure(figsize=(3, 3))
plot(ipis, duration2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
xlabel('interpeak interval ($\mu$s)')
ylabel('duration2 ($\mu$s)')
gcfm().window.setWindowTitle('duration2 vs ipi')
tight_layout(pad=0.3)
'''
'''
# scatter plot duration vs ipi
figure(figsize=(3, 3))
# equation for dividing line between the two clusters
x = array([0, 400])
y = 1.0*x + 140
durationthreshes = 1.0*ipis + 140
fastis = np.asarray(durations) <= durationthreshes
slowis = np.asarray(durations) > durationthreshes
plot(ipis[slowis], durations[slowis], 'b.')
plot(ipis[fastis], durations[fastis], 'r.')
plot(x, y, 'e--') # plot dividing line
xlim(0, 400)
xticks([0, 100, 200, 300, 400])
yticks([0, 200, 400, 600, 800])
xlabel('interpeak interval ($\mu$s)')
ylabel('slope-based duration ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('duration vs ipi')
tight_layout(pad=0.3)

# export spiketype:
spiketype = np.zeros(nn, dtype='|S4') # 4 character string array
spiketype[slowis] = 'slow'
spiketype[fastis] = 'fast'
assert not np.any(spiketype == '') # check for any empty entries
sts = {}
for tracki, track in enumerate(tracks):
    nii0, nii1 = splitis[tracki], splitis[tracki+1]
    nids = allnids[nii0:nii1]
    st = spiketype[nii0:nii1]
    d = dict(zip(nids, st))
    sts[track.absname] = d # can manually print these out and save to .spiketype file

# scatter plot nduration vs ipi
figure(figsize=(3, 3))
# equation for dividing line between the two clusters
x = array([0, 400])
y = 1.0*x + 140
ndurationthreshes = 1.0*ipis + 140
nfastis = np.asarray(ndurations) <= ndurationthreshes
nslowis = np.asarray(ndurations) > ndurationthreshes
plot(ipis[nslowis], ndurations[nslowis], 'b.')
plot(ipis[nfastis], ndurations[nfastis], 'r.')
plot(x, y, 'e--') # plot dividing line
xlim(xmin=0)
xticks([0, 100, 200, 300, 400])
yticks([0, 200, 400, 600, 800])
xlabel('interpeak interval ($\mu$s)')
ylabel('nduration ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('nduration vs ipi')
tight_layout(pad=0.3)
'''
'''
# scatter plot duration2 vs fwhm1
figure(figsize=(3, 3))
plot(fwhm1s, duration2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
xlabel('FWHM1 ($\mu$s)')
ylabel('duration2 ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('duration2 vs fwhm1')
tight_layout(pad=0.3)

# scatter plot duration2 vs fwhm2
figure(figsize=(3, 3))
plot(fwhm2s, duration2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
xlabel('FWHM2 ($\mu$s)')
ylabel('duration2 ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('duration2 vs fwhm2')
tight_layout(pad=0.3)

# scatter plot duration2 vs aai
figure(figsize=(3, 3))
plot(aais, duration2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
xlabel('aai')
ylabel('duration2 ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('duration2 vs aai')
tight_layout(pad=0.3)

# scatter plot sumfwhm vs aai
figure(figsize=(3, 3))
plot(aais, fwhm1s+fwhm2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
xlabel('aai')
ylabel('sum(FWHM) ($\mu$s)')
gcfm().window.setWindowTitle('sum(fwhm) vs aai')
tight_layout(pad=0.3)
'''
# scatter plot fwhm2 vs aai
figure(figsize=(3, 3))
def f0(x):
    """Dividing curve 0"""
    return -400*x + 330
#def f1(x):
    #"""Dividing curve 1"""
    #return -2300*(x-0.44)**2 + 260
def f1(x):
    """Dividing curve 1"""
    return 3000*x - 575
def f2(x):
    """Dividing curve 1"""
    return 150*x + 185
def f3(x):
    """Dividing curve 3"""
    return -5000*x + 3000
x0 = array([-0.2, 0.266])
y0 = f0(x0)
#x1 = np.arange(0.2, 0.6, 0.01)
x1 = array([0.2, 0.266])
y1 = f1(x1)
x2 = array([0.266, 0.8])
y2 = f2(x2)
x3 = array([0.46, 0.546])
y3 = f3(x3)
f0aais = f0(aais) # calculate these once
f1aais = f1(aais)
f2aais = f2(aais)
f3aais = f3(aais)
fastis = (fwhm2s < f0aais) * (fwhm2s > f1aais)
slowis = (fwhm2s > f0aais) * (fwhm2s > f2aais) * (fwhm2s < f3aais)
fastasymis = (fwhm2s < f1aais) * (fwhm2s < f2aais)
slowasymis = (fwhm2s > f2aais) * (fwhm2s > f3aais)

plot(aais[fastis], fwhm2s[fastis], 'r.')
plot(aais[slowis], fwhm2s[slowis], 'b.')
plot(aais[fastasymis], fwhm2s[fastasymis], 'g.')
plot(aais[slowasymis], fwhm2s[slowasymis], 'e.')
plot(x0, y0, 'e--') # plot dividing curve 0
plot(x1, y1, 'e--') # plot dividing curve 1
plot(x2, y2, 'e--') # plot dividing curve 1
plot(x3, y3, 'e--') # plot dividing curve 1
ylim(ymax=700) # cuts a couple points off top, but makes the rest more visible
xticks([-0.4, 0, 0.4, 0.8])
yticks([0, 200, 400, 600])
xlabel('amplitude asymmetry')
ylabel('FWHM2 ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('fwhm2 vs aai')
tight_layout(pad=0.3)

# export spiketype:
spiketype = np.zeros(nn, dtype='|S8') # 8 character string array
spiketype[fastis] = 'fast'
spiketype[slowis] = 'slow'
spiketype[fastasymis] = 'fastasym'
spiketype[slowasymis] = 'slowasym'
assert not np.any(spiketype == '') # check for any empty entries
sts = {}
for tracki, track in enumerate(tracks):
    nii0, nii1 = splitis[tracki], splitis[tracki+1]
    nids = allnids[nii0:nii1]
    st = spiketype[nii0:nii1]
    d = dict(zip(nids, st))
    sts[track.absname] = d # can manually print these out and save to .spiketype file


'''
# scatter plot fwhm2 vs ai1
figure(figsize=(3, 3))
plot(ai1s, fwhm2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
xlabel('ai1')
ylabel('FWHM2 ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('fwhm2 vs ai1')
tight_layout(pad=0.3)

# scatter plot fwhm2 vs ai1 vs aai
f = figure(figsize=(3, 3))
a = f.add_subplot(111, projection='3d')
a.plot(aais, ai1s, fwhm2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
a.set_xlabel('aai')
a.set_ylabel('ai1')
a.set_zlabel('fwhm2')
gcfm().window.setWindowTitle('fwhm2 vs ai1 vs aai')
tight_layout(pad=0.3)

# scatter plot fwhm2 vs fwhm1 vs aai
f = figure(figsize=(3, 3))
a = f.add_subplot(111, projection='3d')
a.plot(aais, fwhm1s, fwhm2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
a.set_xlabel('aai')
a.set_ylabel('fwhm1')
a.set_zlabel('fwhm2')
gcfm().window.setWindowTitle('fwhm2 vs fwhm1 vs aai')
tight_layout(pad=0.3)

# scatter plot fwhm2 vs duration2 vs aai
f = figure(figsize=(3, 3))
a = f.add_subplot(111, projection='3d')
a.plot(aais, duration2s, fwhm2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
a.set_xlabel('aai')
a.set_ylabel('duration2')
a.set_zlabel('fwhm2')
gcfm().window.setWindowTitle('fwhm2 vs duration2 vs aai')
tight_layout(pad=0.3)

# scatter plot fwhm2 vs ipi vs aai
f = figure(figsize=(3, 3))
a = f.add_subplot(111, projection='3d')
a.plot(aais, ipis, fwhm2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
a.set_xlabel('aai')
a.set_ylabel('ipi')
a.set_zlabel('fwhm2')
gcfm().window.setWindowTitle('fwhm2 vs ipi vs aai')
tight_layout(pad=0.3)

# scatter plot fwhm2 vs sigma vs aai
f = figure(figsize=(3, 3))
a = f.add_subplot(111, projection='3d')
a.plot(aais, sigmas, fwhm2s, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
a.set_xlabel('aai')
a.set_ylabel('sigma')
a.set_zlabel('fwhm2')
gcfm().window.setWindowTitle('fwhm2 vs sigma vs aai')
tight_layout(pad=0.3)
'''
'''
# scatter plot ipi vs aai
figure(figsize=(3, 3))
plot(aais, ipis, 'k.')
#xticks([0, 50, 100, 150, 200])
#yticks([0, 200, 400, 600, 800])
xlabel('aai')
ylabel('ipi ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('ipi vs aai')
tight_layout(pad=0.3)
'''

'''
# scatter plot duration vs slope
figure(figsize=(3, 3))
plot(maxslopes, durations, 'k.')
xlabel('maximum slope ($\mu$V/$\mu$s)')
ylabel('duration ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('duration vs maxslope')
tight_layout(pad=0.3)

# scatter plot slope vs fwhm
figure(figsize=(3, 3))
plot(fwhms, maxslopes, 'k.')
xlabel('FWHM ($\mu$s)')
ylabel('maximum slope ($\mu$V/$\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('maxslope vs fwhm')
tight_layout(pad=0.3)

# plot sigma distribution
figure(figsize=(3, 3))
hist(sigmas, bins=nbins, fc='k')
xlim(xmin=0)
xticks([0, 25, 50, 75, 100])
xlabel('$\sigma$ ($\mu$m)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma distrib')
tight_layout(pad=0.3)

# plot duration distribution
figure(figsize=(3, 3))
hist(durations, bins=nbins, fc='k')
xticks([0, 200, 400, 600, 800])
xlabel('slope-based duration ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('duration distrib')
tight_layout(pad=0.3)

# plot duration2 distribution
figure(figsize=(3, 3))
hist(duration2s, bins=nbins, fc='k')
#xticks([0, 200, 400, 600, 800])
xlabel('duration2 ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('duration2 distrib')
tight_layout(pad=0.3)

# plot ipi distribution, exclude the few outliers > 400 us
figure(figsize=(3, 3))
hist(ipis[ipis<=400], bins=nbins, fc='k')
xlim(xmin=0)
xticks([0, 100, 200, 300, 400])
xlabel('interpeak interval ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('ipi distrib')
tight_layout(pad=0.3)
'''
# plot fwhm1 distribution
figure(figsize=(3, 3))
hist(fwhm1s, bins=nbins, fc='k')
xticks([0, 50, 100, 150, 200])
xlabel('FWHM1 ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('fwhm1 distrib')
tight_layout(pad=0.3)

# plot fwhm2 distribution, cut off values above 700 for display
figure(figsize=(3, 3))
hist(fwhm2s[fwhm2s < 700], bins=nbins, fc='k')
xticks([0, 200, 400, 600])
xlabel('FWHM2 ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('fwhm2 distrib')
tight_layout(pad=0.3)
'''
# plot ai0 distribution
figure(figsize=(3, 3))
hist(ai0s, bins=nbins, fc='k')
#xticks([0, 50, 100, 150, 200])
xlabel('ai0')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('ai0 distrib')
tight_layout(pad=0.3)
'''
'''
# plot ai1 distribution
figure(figsize=(3, 3))
hist(ai1s, bins=nbins, fc='k')
#xticks([0, 50, 100, 150, 200])
xlabel('ai1')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('ai1 distrib')
tight_layout(pad=0.3)
'''
# plot aai distribution
figure(figsize=(3, 3))
hist(aais, bins=nbins, fc='k')
xticks([-0.4, 0, 0.4, 0.8])
xlabel('amplitude asymmetry')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('aai distrib')
tight_layout(pad=0.3)
'''
# plot ffwhm distribution
figure(figsize=(3, 3))
hist(fwhm2s/fwhm1s, bins=nbins, fc='k')
#xticks([0, 50, 100, 150, 200])
xlabel('fFWHM ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('ffwhm distrib')
tight_layout(pad=0.3)

# plot dfwhm distribution
figure(figsize=(3, 3))
hist(fwhm2s-fwhm1s, bins=nbins, fc='k')
#xticks([0, 50, 100, 150, 200])
xlabel('dFWHM ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('dfwhm distrib')
tight_layout(pad=0.3)

# plot aifwhm distribution
figure(figsize=(3, 3))
hist((fwhm2s-fwhm1s)/(fwhm1s+fwhm2s), bins=nbins, fc='k')
#xticks([0, 50, 100, 150, 200])
xlabel('aiFWHM ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('aifwhm distrib')
tight_layout(pad=0.3)

# plot maxslope distribution
figure(figsize=(3, 3))
hist(maxslopes, bins=nbins, fc='k')
xlabel('maximum slope ($\mu$V/$\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('maxslope distrib')
tight_layout(pad=0.3)

# plot maxnslope distribution
figure(figsize=(3, 3))
hist(maxnslopes, bins=nbins, fc='k')
xticks([0, 0.01, 0.02])
xlabel('maximum normalized slope (1/$\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('maxnslope distrib')
tight_layout(pad=0.3)
'''
# plot fast waveforms:
figure(figsize=(3, 3))
for wave in waves[fastis]:
    plot(t1, wave, 'r-', lw=1)
ylim(ymax=250)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('fast waveforms')
tight_layout(pad=0.3)

# plot slow waveforms:
figure(figsize=(3, 3))
for wave in waves[slowis]:
    plot(t1, wave, 'b-', lw=1)
ylim(ymax=250)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('slow waveforms')
tight_layout(pad=0.3)

# plot fast asymmetric waveforms:
figure(figsize=(3, 3))
for wave in waves[fastasymis]:
    plot(t1, wave, 'g-', lw=1)
ylim(ymax=250)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('fast asymmetric waveforms')
tight_layout(pad=0.3)

# plot slow asymmetric waveforms:
figure(figsize=(3, 3))
for wave in waves[slowasymis]:
    plot(t1, wave, 'e-', lw=1)
ylim(ymax=250)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('slow asymmetric waveforms')
tight_layout(pad=0.3)

# plot fast, slow, fastasym and slowasym waveforms:
figure(figsize=(3, 3))
for wave in waves[fastis]:
    plot(t1, wave, 'r-', lw=1)
for wave in waves[slowis]:
    plot(t1, wave, 'b-', lw=1)
for wave in waves[fastasymis]:
    plot(t1, wave, 'g-', lw=1)
for wave in waves[slowasymis]:
    plot(t1, wave, 'e-', lw=1)
ylim(ymax=250)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('all waveforms')
tight_layout(pad=0.3)
'''
# plot slow waveforms classified by nduration vs ipi plot:
figure(figsize=(3, 3))
for wave in waves[nslowis]:
    plot(t1, wave, 'b-', lw=1)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, nabsslopethresh=%.3f' % (tracknames, nabsslopethresh))
gcfm().window.setWindowTitle('slow nduration waveforms')
tight_layout(pad=0.3)

# plot fast normalized waveforms separately:
figure(figsize=(3, 3))
for nwave in nwaves[nfastis]:
    plot(t1, nwave, 'r-', lw=1)
xticks([0, 200, 400, 600, 800])
yticks([-1, -0.5, 0, 0.5, 1])
xlabel('time ($\mu$s)')
ylabel('normalized voltage')
#title('tracks: %r, nabsslopethresh=%.3f' % (tracknames, nabsslopethresh))
gcfm().window.setWindowTitle('fast normalized waveforms')
tight_layout(pad=0.3)

# plot unnormalized waveforms classified by dividing line in nduration vs ipi plot:
figure(figsize=(3, 3))
for wave in waves[nslowis]:
    plot(t1, wave, 'b-', lw=1)
for wave in waves[nfastis]:
    plot(t1, wave, 'r-', lw=1)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, nabsslopethresh=%.3f' % (tracknames, nabsslopethresh))
gcfm().window.setWindowTitle('waveformsep nduration vs ipi')
tight_layout(pad=0.3)

# plot waveforms classified only by durationthresh (in us):
fastis = durations <= durationthresh
slowis = durations > durationthresh
waves = np.asarray(waves)
figure(figsize=(3, 3))
for wave in waves[slowis]:
    plot(t1, wave, 'b-', lw=1)
for wave in waves[fastis]:
    plot(t1, wave, 'r-', lw=1)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('waveformsep durationthresh=%s' % durationthresh)
tight_layout(pad=0.3)
'''
'''
# this code reveals which timepoints are considered part of the duration of the spike,
# as defined by first and last slope threshold crossings. For better visibility, overplot
# just the first few waveforms of the 245 in total:
figure()
n = 5
for i in range(n):
    plot(waves[i], 'b')
    x = np.arange(slopeiss[i,0], slopeiss[i,1], 1)
    y = waves[i, slopeiss[i,0]:slopeiss[i,1]]
    plot(x, y, 'r')
gcfm().window.setWindowTitle("artifactual duration bimodality")

# The problem with duration is that it induces an artifactual bimodality: it either includes
# only the first phase of a spike, or both phases. This leads to bimodailty in the measured
# duration, even if the underlying waveforms don't have that bimodality. It's simply noise
# in the slope that the threshold is using to somewhat randomly assign cells to the slow
# and fast group. Using a threshold in retrospect was dangerous, because that imposes
# a nonlinearity, which would be best avoided prior to clustering.
'''
show()
