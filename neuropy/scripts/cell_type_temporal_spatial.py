"""Scatter plot various combinations of spatial sigma and temporal measures of spikes. Also
plot distributions and waveforms, as separated by shape thresholds. Run from within neuropy
using `run -i scripts/cell_type_temporal_spatial.py`"""

import scipy
from pylab import get_current_fig_manager as gcfm
from core import intround

# fractional position along waveform to assume characteristic peak is roughly aligned to:
alignf = 0.4
newtres = 1 # tres to interpolate to, in us
absslopethresh = 0.3 # uV/us
nabsslopethresh = 0.003 # for normalized waveforms, 1/us
durationthresh = 350 # duration separation threshold
nbins = 20
tracks = [ptc15.tr7c, ptc22.tr1, ptc22.tr2] # need to be loaded ahead of time
#tracknames = [ track.absname for track in tracks ]

def calc_t(nt, tres):
    """Generate original and desired interpolated timebases t0 and t1, as well as initial
    guess for where the alignment point is in t1"""
    tend = nt*tres
    t0 = np.arange(0, tend, tres)
    t1 = np.arange(0, tend-tres, newtres)
    aligni = intround(alignf * len(t1))
    return t0, t1, aligni

def argextrema(a):
    """Return indices of local extrema in 1D array a.
    Taken from http://stackoverflow.com/a/9667121/2020363"""
    return np.diff(np.sign(np.diff(a))).nonzero()[0] + 1

def argfwhm(a, exti, fraction=0.5):
    """Find timepoints of full width half max (or whatever fraction is) around extremum exti
    in 1D array a"""
    a = abs(a)
    fm = a[exti] * fraction # fraction of max
    d = a - fm
    lis = np.diff(np.sign(d[:exti])).nonzero()[0]
    ris = np.diff(np.sign(d[exti:])).nonzero()[0] + exti + 1
    assert len(lis) > 0
    assert len(ris) > 0
    # return rightmost of left indices, and leftmost of right indices:
    return lis[-1], ris[0]

nt = 50
tres = 20
t0, t1, aligni = calc_t(nt, tres) # initial guess, for speed
sigmas = []
waves = []
nwaves = [] # peak-to-peak normalized waveforms
ipis = [] # interpeak intervals
fwhms = [] # full-width half max values
maxslopes = [] # maximum abs slopes of each waveform
maxnslopes = [] # maximum abs slopes of each normalized waveform
durations = [] # spike duration, measured by time between slope threshold crossings
ndurations = [] # spike duration measured from normalized waveforms
slopeiss = [] # start and end timepoint indices used for calculating durations
nslopeiss = [] # start and end timepoint indices used for calculating ndurations
allnids = []
splitis = [] # indices which demarcate neurons from different tracks in allnids

# collect maxchan waveforms and calculate various measures of waveform duration:
for track in tracks:
    splitis.append(len(allnids))
    if tres != track.tres: # recalculate timepoints
        tres = track.tres
        t0, t1, aligni = calc_t(nt, tres)
    nids = sorted(track.alln)
    for nid in nids:
        n = track.alln[nid]
        if nt != n.nt: # recalculate timepoints
            nt = n.nt
            t0, t1, aligni = calc_t(nt, tres)
        sigmas.append(n.sigma)
        maxchani = n.chans.searchsorted(n.maxchan)
        wave = n.wavedata[maxchani]
        # interpolate waveforms from original t0 timebase to higher rez t1 timebase:
        wave = scipy.interpolate.spline(t0, wave, t1)
        waves.append(wave)
        nwave = wave / wave.ptp() # normalize peak-to-peak amplitudes
        nwaves.append(nwave)
        t0i, t1i = wave.argmax(), wave.argmin()
        ipi = abs(t0i - t1i) * newtres
        ipis.append(ipi) # interval between biggest max and min peaks
        extis = argextrema(wave) # indices of all local extrema
        exti = extis[abs(extis - aligni).argmin()] # extremum closest to aligni
        li, ri = argfwhm(wave, exti, fraction=0.5)
        fwhm = abs(li - ri) * newtres
        fwhms.append(fwhm)
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
        allnids.append(nid)
        # or as an alternative to using absslopethresh, measure the fwhm of the last
        # extremum in each waveform. Looking at the overplotted waveforms, that, strangely,
        # is where I see the most dichotomy. Not so much in the first peak.

waves = np.asarray(waves)
nwaves = np.asarray(nwaves)
sigmas = np.hstack(sigmas)
ipis = np.hstack(ipis)
durations = np.hstack(durations)
ndurations = np.hstack(ndurations)
slopeiss = np.vstack(slopeiss)
nslopeiss = np.vstack(nslopeiss)
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

# scatter plot sigma vs ipi
figure(figsize=(3, 3))
plot(ipis, sigmas, 'k.')
xticks([0, 100, 200, 300, 400])
yticks(np.arange(0, 100+20, 20))
xlabel('interpeak interval ($\mu$s)')
ylabel('$\sigma$ ($\mu$m)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma vs ipi')
tight_layout(pad=0.3)

# scatter plot sigma vs fwhm
figure(figsize=(3, 3))
plot(fwhms, sigmas, 'k.')
xlabel('FWHM ($\mu$s)')
ylabel('$\sigma$ ($\mu$m)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma vs fwhm')
tight_layout(pad=0.3)

# scatter plot sigma vs slope
figure(figsize=(3, 3))
plot(maxslopes, sigmas, 'k.')
xlabel('maximum slope ($\mu$V/$\mu$s)')
ylabel('$\sigma$ ($\mu$m)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma vs maxslope')
tight_layout(pad=0.3)

# scatter plot sigma vs duration
figure(figsize=(3, 3))
plot(durations, sigmas, 'k.')
ylim(ymin=0)
xticks([0, 200, 400, 600, 800])
xlabel('duration ($\mu$s)')
ylabel('$\sigma$ ($\mu$m)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('sigma vs duration')
tight_layout(pad=0.3)

# scatter plot fwhm vs ipi
figure(figsize=(3, 3))
plot(ipis, fwhms, 'k.')
xlabel('interpeak interval ($\mu$s)')
ylabel('FWHM ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('fwhm vs ipi')
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
xlim(xmin=0)
xticks([0, 100, 200, 300, 400])
yticks([0, 200, 400, 600, 800])
xlabel('interpeak interval ($\mu$s)')
ylabel('duration ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('duration vs ipi')
tight_layout(pad=0.3)
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
# scatter plot duration vs fwhm
figure(figsize=(3, 3))
plot(fwhms, durations, 'k.')
xticks([0, 50, 100, 150, 200])
yticks([0, 200, 400, 600, 800])
xlabel('FWHM ($\mu$s)')
ylabel('duration ($\mu$s)')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('duration vs fwhm')
tight_layout(pad=0.3)

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
xlabel('duration ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('duration distrib')
tight_layout(pad=0.3)

# plot ipi distribution
figure(figsize=(3, 3))
hist(ipis, bins=nbins, fc='k')
xlim(xmin=0)
xticks([0, 100, 200, 300, 400])
xlabel('interpeak interval ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('ipi distrib')
tight_layout(pad=0.3)

# plot fwhm distribution
figure(figsize=(3, 3))
hist(fwhms, bins=nbins, fc='k')
xticks([0, 50, 100, 150, 200])
xlabel('FWHM ($\mu$s)')
ylabel('neuron count')
#title('tracks: %r' % tracknames)
gcfm().window.setWindowTitle('fwhm distrib')
tight_layout(pad=0.3)
'''
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

# plot slow waveforms separately:
figure(figsize=(3, 3))
for wave in waves[slowis]:
    plot(t1, wave, 'b-', lw=1)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
slow_ymax = ylim()[1]
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('slow waveforms')
tight_layout(pad=0.3)
'''
# plot fast waveforms separately:
figure(figsize=(3, 3))
for wave in waves[fastis]:
    plot(t1, wave, 'r-', lw=1)
ylim(ymax=slow_ymax)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, absslopethresh=%.1f' % (tracknames, absslopethresh))
gcfm().window.setWindowTitle('fast waveforms')
tight_layout(pad=0.3)
'''
# plot waveforms classified by dividing line in duration vs ipi plot:
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
gcfm().window.setWindowTitle('waveformsep duration vs ipi')
tight_layout(pad=0.3)

# plot slow waveforms classified by nduration vs ipi plot:
figure(figsize=(3, 3))
for wave in waves[nslowis]:
    plot(t1, wave, 'b-', lw=1)
xticks([0, 200, 400, 600, 800])
yticks(np.arange(-200, 200+100, 100))
slow_ymax = ylim()[1]
xlabel('time ($\mu$s)')
ylabel('voltage ($\mu$V)')
#title('tracks: %r, nabsslopethresh=%.3f' % (tracknames, nabsslopethresh))
gcfm().window.setWindowTitle('slow nduration waveforms')
tight_layout(pad=0.3)
'''
# plot fast normalized waveforms separately:
figure(figsize=(3, 3))
for nwave in nwaves[nfastis]:
    plot(t1, nwave, 'r-', lw=1)
ylim(ymax=slow_ymax)
xticks([0, 200, 400, 600, 800])
yticks([-1, -0.5, 0, 0.5, 1])
xlabel('time ($\mu$s)')
ylabel('normalized voltage')
#title('tracks: %r, nabsslopethresh=%.3f' % (tracknames, nabsslopethresh))
gcfm().window.setWindowTitle('fast normalized waveforms')
tight_layout(pad=0.3)
'''
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

'''
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

show()
