"""Plot orientation preference vs tuning strength and cell position of all oriented cells from
a number of orientated stimulus recordings. Run with 'run -i scripts/oripop.py' or copy and
paste into neuropy console

TODO: for each unique nid in each track, go through all driftbar and drift/flash grating
recordings and use the ori tuning from the earliest recording, or perhaps from the recording
that provides the strongest tuning. Need to do as much as possible to keep n as close to total
n in the track as possible

"""

from __future__ import division
from __future__ import print_function

from polar_demo import fractional_polar_axes

# drift bar, drift grating and flashed grating recordings:
trackrecs = {ptc15.tr7c: [ptc15.tr7c.r71, ptc15.tr7c.r73, ptc15.tr7c.r85],
             ptc22.tr1: [ptc22.tr1.r03, ptc22.tr1.r13, ptc22.tr1.r14, ptc22.tr1.r18],
             ptc22.tr2: [ptc22.tr2.r25, ptc22.tr2.r30, ptc22.tr2.r31]}
#trackrecs = {ptc15.tr7c: [ptc15.tr7c.r71, ptc15.tr7c.r73, ptc15.tr7c.r85]}
#trackrecs = {ptc15.tr7c: [ptc15.tr7c.r73]}

# ensure tracks are kept in a fixed order:
tracknames = sorted([ track.absname for track in trackrecs ])
tracks = [ eval(trackname) for trackname in tracknames ]

alpha = 0.01 # p value threshold for significance
ec = 'gray'
allnids, allthetas, allrs, alldepths = {}, {}, {}, {}
fs = fontsize() # save original font size
for track in tracks:
    thetas, rs, depths = {}, {}, {} # theta in deg, r in fraction of total spikes, depth in um
    for rec in trackrecs[track]:
        nids = np.array(sorted(rec.alln))
        for nid in nids:
            neuron = rec.alln[nid]
            tune = neuron.tune()
            theta, r, z, p = tune.pref(var='ori')
            if not p < alpha:
                continue # insignificant tuning, skip to next nid
            if nid in rs and r <= rs[nid]:
                continue # skip nid if it's less tuned than same nid from earlier rec
            thetas[nid] = theta # off by 90 deg for some reason
            rs[nid] = r
            depths[nid] = neuron.pos[1]
    nids = sorted(thetas.keys()) # just the significant ones that were kept
    thetas = np.asarray([ thetas[nid] for nid in nids ])
    rs = np.asarray([ rs[nid] for nid in nids ])
    depths = np.asarray([ depths[nid] for nid in nids ])
    cellmaxdepth = depths.max()
    chanmaxdepth = track.sort.chanpos[:, 1].max()
    maxdepth = max(cellmaxdepth, chanmaxdepth)
    depths /= maxdepth # normalize by cell or channel of greatest depth
    allnids[track.absname] = nids
    allthetas[track.absname] = thetas
    allrs[track.absname] = rs
    alldepths[track.absname] = depths

    # plot tuning strength vs theta, in half polar plot, colour by depth, with darker colours
    # indicating greater depth:
    f = figure()
    a = fractional_polar_axes(f, thlim=(0, 180), rlim=(0, 1.02),
                              thlabel=None, rlabel=None, ticklabels=False)
    a.scatter(thetas, rs, marker='o', edgecolors=ec, linewidth=1, s=175,
              cmap=cm.hot_r, c=depths, vmin=0, vmax=1, zorder=-0.1)
    # plot overlapping edges to help distinguish points:
    a.scatter(thetas, rs, marker='o', edgecolors=ec, facecolors='none', linewidth=1, s=175)
    #colorbar(sc)
    f.tight_layout(pad=0.3)
    f.canvas.manager.set_window_title(track.absname)
    f.show()

    # plot depth vs theta, and colour by r, with lighter colours indicating higher r:
    f = figure(figsize=(4.88, 3))
    fontsize(20)
    scatter(thetas, depths, marker='o', edgecolors=ec, linewidth=0.5, s=50,
            cmap=cm.hot, c=rs, vmin=0, vmax=1, zorder=-0.1)
    # plot overlapping edges to help distinguish points:
    scatter(thetas, depths, marker='o', edgecolors=ec, facecolors='none', linewidth=0.5, s=50)
    xlim(0, 180)
    xticks([0, 90, 180])
    ylim(1, 0)
    yticks([1, 0.5, 0])
    #xlabel('orientation preference ($^{\circ}$)')
    #ylabel('normalized depth')
    f.tight_layout(pad=0.3)
    f.canvas.manager.set_window_title(track.absname+'_depth')
    f.show()
    fontsize(fs) # restore
    print('%s: %d of %d neurons tuned' % (track.absname, len(nids), track.nallneurons))

# create flattened versions:
nids = np.hstack([ allnids[track.absname] for track in tracks ])
thetas = np.hstack([ allthetas[track.absname] for track in tracks ])
rs = np.hstack([ allrs[track.absname] for track in tracks ])
depths = np.hstack([ alldepths[track.absname] for track in tracks ])

af = figure()
aa = fractional_polar_axes(af, thlim=(0, 180), rlim=(0, 1.02),
                           thlabel='orientation preference', rlabel='tuning strength')
aa.scatter(thetas, rs, marker='o', edgecolors=ec, linewidth=0.5, s=25,
           cmap=cm.hot_r, c=depths, vmin=0, vmax=1, zorder=-0.1)
# plot overlapping edges to help distinguish points:
aa.scatter(thetas, rs, marker='o', edgecolors=ec, facecolors='none',
           linewidth=0.5, s=25)

#colorbar(sc)
af.tight_layout(pad=0.3)
af.canvas.manager.set_window_title('all tracks')
af.show()

## TODO: add scatter plots of ori prefs of cells from driftbar vs flashed grating, one per
## track, or overplot scatter of all three tracks, giving each a different colour. Also might
## scatter plot tuning strengths of same cells. Mention delta t in hours among each pair of
## recordings

## TODO: plot tuning pref over time, coloured by strength? Would need to decide whether to
## include those cells that lost or gained significance?
