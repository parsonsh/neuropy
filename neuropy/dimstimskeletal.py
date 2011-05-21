"""A skeletal copy of classes from dimstim required for interpreting
the textheader generated by dimstim.__version__ >= 0.16"""

import struct
from copy import copy

import numpy as np

from core import dictattr, TAB


def deg2pix(deg, I):
    """Convert from degrees of visual space to pixels"""
    # shouldn't I be using opp = 2.0 * distance * tan(deg/2), ie trig instead of solid angle of a circle ???!!
    # make it a one-liner, break it up into multiple lines in the docstring
    if deg == None:
        deg = 0 # convert to an int
    rad = deg * math.pi / 180 # float, angle in radians
    s = I.SCREENDISTANCECM * rad # arc length in cm
    return s * I.PIXPERCM # float, arc length in pixels


class InternalParams(dictattr):
    pass

class StaticParams(dictattr):
    pass

class DynamicParams(dictattr):
    pass

class Variable(object):
    """A dynamic experiment parameter that varies over sweeps"""
    def __init__(self, vals, dim=0, shuffle=False, random=False):
        """Bind the dynamic parameter values, its dim, and its shuffle and random flags to this experiment Variable"""
        self.vals = vals
        self.dim = dim
        self.shuffle = shuffle
        self.random = random
    def __iter__(self):
        return iter(self.vals)
    def __len__(self):
        return len(self.vals)

class Variables(dictattr):
    """A collection of Variable objects, attributed by their name.
    Exactly which attributes are stored here depends on the Variable objects themselves.
    Each of the Variable objects stored here can have different dims and shuffle and random flags,
    unlike those stored in a Dimension"""
    def __iter__(self):
        """Iterates over all Variable objects stored here"""
        return self.itervalues() # inconsistent with dict behaviour
    def __setattr__(self, varname, variable):
        try:
            variable.name
        except AttributeError:
            variable.name = varname # store the Variable's name in its own .name field
        dictattr.__setattr__(self, varname, variable)

class Runs(object):
    """Stores info about experiment runs"""
    def __init__(self, n=1, reshuffle=False):
        self.n = n # number of runs
        self.reshuffle = reshuffle # reshuffle/rerandomize on every run those variables with their shuffle/random flags set?

class BlankSweeps(object):
    """Stores info about blank sweeps in an experiment"""
    def __init__(self, T, sec, shuffle=False):
        self.T = T # period (blank sweep every T sweeps)
        self.sec = sec # duration (sec)
        self.shuffle = shuffle

class Dimension(object):
    """An experiment dimension, all of whose Variables co-vary"""
    def __init__(self, variables, dim, shuffle=False, random=False):
        self.variables = variables
        self.dim = dim
        self.shuffle = shuffle
        self.random = random
    def keys(self):
        return self.variables.keys()
    def values(self):
        return self.variables.values()
    def items(self):
        return self.variables.items()
    def __len__(self):
        """Number of conditions in this Dimension"""
        return len(self.variables.values()[0]) # assumes all vars in this dim have the same number of conditions


class SweepTable(object):
    """A SweepTable holds all unique combinations of Experiment Variables, as well as indices
    into these combinations, based on shuffle/random flags for each Dimension, the number of runs,
    whether each run is reshuffled, with optional BlankSweeps inserted at the (potentially shuffled)
    intervals requested"""
    def __init__(self, experiment):
        self.experiment = experiment
        self.build()

    def build(self):
        """Build the sweep table.

        A Variable's dim value relative to the dim values of all the other
        Variables determines its order in the nested for loops that generate
        the combinations of values for each sweep: the Variable with the lowest
        dim value becomes the outermost for loop and changes least often;
        the Variable with the highest dim value becomes the innermost for loop
        and changes on every sweep. dim must be an integer. Variables with the
        same dim value are part of the same Dimension, are shuffled/randomized
        together, and must therefore be of the same length and have the same
        shuffle and random flags"""

        e = self.experiment # synonym

        # Build the dimensions
        self.builddimensions()

        # Build the dimension index table
        self.builddimitable()

        # Now use dimitable to build the sweep table
        self.data = dictattr() # holds the actual sweep table, a dict with attribute access
        for dim in self.dimensions:
            for var in dim.variables:
                dimi = self.dimitable[:, dim.dim] # get the entire column of indices into the values of this dimension
                vals = np.asarray(var.vals)[dimi] # convert to array so you can select multiple values with a sequence of indices
                self.data[var.name] = vals # store it as an array

        # Check to make sure that all the variables in self.data have the same number of vals
        try:
            nvals = len(self.data.values()[0])
        except IndexError: # there aren't any variables at all
            nvals = 0
        for varname in self.data:
            assert len(self.data[varname]) == nvals, '%s length in sweep table does not match expected length %d' % (varname, nvals)

        # For convenience in the main stimulus loop, add the non-varying dynamic params to self.data
        nvals = max(nvals, 1) # make sure the sweep table has at least one entry
        for paramname, paramval in e.dynamic.iteritems():
            if paramname not in self.data:
                self.data[paramname] = np.tile(paramval, nvals) # paramval was already checked to be a scalar in Experiment.check()

    def builddimensions(self):
        """Build the Dimension objects from the Experiment Variables"""
        e = self.experiment # synonym

        # find unique dimension values across variables. Dim values could be 0, 5, 5, 5, 2, 666, -74,...
        dims = list(np.unique([ var.dim for var in e.variables ])) # np.unique returns sorted values

        # renumber dimension values to be consecutive 0-based
        newdims = range(len(dims)) # 0-based consecutive dim values
        old2new = dict(zip(dims, newdims)) # maps from old dim values to new ones
        for var in e.variables:
            var.dim = old2new[var.dim] # overwrite each Variable's old dim value with the new one

        # use newdims to init a list of Dimensions, each with an empty Variables object
        self.dimensions = []
        for dim in newdims:
            d = Dimension(variables=Variables(), dim=dim)
            self.dimensions.append(d)

        # now assign each Variable object to the appropriate Dimension object
        for var in e.variables:
            d = self.dimensions[var.dim] # get the Dimension object
            d.variables[var.name] = var # assign the Variable to the Dimension's Variables
            d.shuffle = var.shuffle # set the Dimension's shuffle and random flags according to this Variable
            d.random = var.random

    def builddimitable(self):
        """Build the dimension index table"""
        # Can't figure out how to use a recursive generator/function to do this, see Apress Beginning Python p192
        # HACK!!: generate and exec the appropriate Python code to build the ordered (unshuffled/unrandomized) dimension index table
        dimi = [None]*len(self.dimensions) # stores the index we're currently on in each dimension
        self.dimitable = [] # ordered dimension index table, these are indices into the values in dimensions, dimensions are in columns, sweeps are in rows
        # generate code with the right number of nested for loops
        code = ''
        tabs = ''
        for dimension in self.dimensions: # generate ndim nested for loops...
            i = str(dimension.dim)
            code += tabs+'for dimi['+i+'] in range(len(self.dimensions['+i+'])):\n'
            tabs += TAB # add a tab to tabs in preparation for the next for loop, or the innermost part of the last one
        code += tabs+'self.dimitable.append(copy(dimi))\n' # innermost part of the nested for loops, copying dimi is important
        exec(code) # run the generated code, this builds the ordered dimitable with all the permutations
        '''
        # example of what the generated code looks like for 3 dimensions:
        for dimi[0] in range(len(self.dimensions[0])):
            for dimi[1] in range(len(self.dimensions[1])):
                for dimi[2] in range(len(self.dimensions[2])):
                    self.dimitable.append(copy(dimi))
        '''
        self.dimitable = np.asarray(self.dimitable)

    def pprint(self, i=None):
        """Print out the sweep table at sweep table indices i,
        formatted as an actual table instead of just a dict.
        Only Variables are included (non-varying dynamic params are left out).
        If i is left as None, prints the basic sorted sweep table"""
        print self._pprint(i)

    def _pprint(self, i=None):
        """Return a string representation of the sweep table at sweep table indices i,
        formatted as an actual table instead of just a dict.
        Only Variables are included (non-varying dynamic params are left out).
        If i is left as None, prints the basic sorted sweep table"""
        f = cStringIO.StringIO() # create a string file-like object, implemented in C, fast
        f.write('i\t') # sweep table index label
        for dim in self.dimensions:
            for var in dim.variables:
                f.write('%s\t' % var.name) # column label
        if i == None:
            # sweep table will always have at least one value per dynamic parameter, see self.build()
            i = range(len(self.data.values()[0])) # default to printing one Run's worth of the table in sorted order
        for ival in i:
            f.write('\n')
            f.write('%s\t' % ival) # sweep table index
            for dim in self.dimensions:
                for var in dim.variables:
                    if ival == None: # blank sweep
                        f.write('%s\t' % None)
                    else:
                        f.write('%s\t' % self.data[var.name][ival]) # variable value at sweep table index
        return f.getvalue()


class Experiment(object):
    """Base Experiment class, all dimstim experiments inherit from this"""
    def __init__(self, script=None, static=None, dynamic=None, variables=None, runs=None, blanksweeps=None):
        self.script = script # Experiment script file name
        self.static = static # StaticParams object
        self.dynamic = dynamic # DynamicParams object
        self.variables = variables # Variables object
        self.runs = runs # Runs object
        self.blanksweeps = blanksweeps # BlankSweeps object

class Bar(Experiment):
    pass

class Grating(Experiment):
    pass

class SparseNoise(Experiment):
    pass

class BlankScreen(Experiment):
    pass


class Movie(Experiment):
    def load(self, asarray=False, flip=True):
        """Load movie frames"""
        self.f = file(self.static.fname, 'rb') # open the movie file for reading in binary format
        headerstring = self.f.read(5)
        if headerstring == 'movie': # a header has been added to the start of the file
            self.ncellswide, = struct.unpack('H', self.f.read(2)) # 'H'== unsigned short int
            self.ncellshigh, = struct.unpack('H', self.f.read(2))
            self.nframes, = struct.unpack('H', self.f.read(2))
            if self.nframes == 0: # this was used in Cat 15 mseq movies to indicate 2**16 frames, shouldn't really worry about this, cuz we're using slightly modified mseq movies now that don't have the extra frame at the end that the Cat 15 movies had (see comment in Experiment module), and therefore never have a need to indicate 2**16 frames
                self.nframes = 2**16
            self.offset = self.f.tell() # header is 11 bytes long
        else: # there's no header at the start of the file, set the file pointer back to the beginning and use these hard coded values:
            self.f.seek(0)
            self.ncellswide = self.ncellshigh = 64
            self.nframes = 6000
            self.offset = self.f.tell() # header is 0 bytes long
        self.framesize = self.ncellshigh*self.ncellswide

        # read in all of the frames
        # maybe check first to see if file is > 1GB, if so, _loadaslist() to prevent trying to allocate one huge piece of contiguous memory and raising a MemoryError, or worse, segfaulting
        if asarray:
            self._loadasarray(flip=flip)
        else:
            self._loadaslist(flip=flip)
        leftover = self.f.read() # check if there are any leftover bytes in the file
        if leftover != '':
            pprint(leftover)
            print self.ncellswide, self.ncellshigh, self.nframes
            raise RuntimeError('There are unread bytes in movie file %r. Width, height, or nframes is incorrect in the movie file header.' % self.static.fname)
        self.f.close() # close the movie file

    def _loadasarray(self, flip=True):
        self.frames = np.fromfile(self.f, dtype=np.uint8, count=self.nframes*self.framesize)
        self.frames.shape = (self.nframes, self.ncellshigh, self.ncellswide)
        if flip:
            self.frames = self.frames[::, ::-1, ::] # flip all frames vertically for OpenGL's bottom left origin

    def _loadaslist(self, flip=True):
        self.frames = []
        for framei in xrange(self.nframes): # one frame at a time...
            frame = np.fromfile(self.f, dtype=np.uint8, count=self.framesize) # load the next frame
            frame.shape = (self.ncellshigh, self.ncellswide)
            if flip:
                frame = frame[::-1, ::] # flip all frames vertically for OpenGL's bottom left origin
            self.frames.append(frame)