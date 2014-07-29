# WORKING COPY OF SPLAT CODE LIBRARY
# based on routines developed by:
#	Daniella Bardalez Gagliuffi
# 	Adam Burgasser
#	Caleb Choban
#	Aisha Iyer
# 	Yuhui Jin
#	Alex Mendez
#	Melisa Tallis

#
# CURRENT STATUS (5/6/2014)
# can now load up spectra and models from online sources
# source spectra can be selected by name, designation, young/subdwarf/red/blue/binary/spbin
# returned as array of spectra
#
# There is an odd error that is coming in when reading in multiple spectra:
#	/Users/adam/projects/splat/exercises/ex4/splat.py:746: RuntimeWarning: invalid value encountered in greater
#	w = numpy.where(flux > numpy.median(flux))
# only occurs on first go
#

# imports
import sys
import os
import numpy
import scipy
import astropy
from astropy.io import ascii, fits			# for reading in spreadsheet
from astropy.table import Table, join			# for reading in table files
import matplotlib.pyplot as plt
from scipy.integrate import trapz		# for numerical integration
from scipy.interpolate import interp1d
import re
import urllib2
from astropy import units as u			# standard units
from astropy.coordinates import ICRS, Galactic		# coordinate conversion


############ PARAMETERS - PLEASE SET THESE TO LOCAL FOLDERS ###############
SplatFolder = '~/splat/code/'
SPLAT_URL = 'http://pono.ucsd.edu/~adam/splat/'
###########################################################################


# some "universal" constants
Months = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

# helper functions from Alex
def lazyprop(fn):
	 attr_name = '_lazy_' + fn.__name__
	 @property
	 def _lazyprop(self):
		  if not hasattr(self, attr_name):
				setattr(self, attr_name, fn(self))
		  return getattr(self, attr_name)
	 return _lazyprop

def Show(fn):
	 def _show(self, *args, **kwargs):
		  noplot = kwargs.pop('noplot', False)
		  quiet = kwargs.pop('quiet', False)
		  tmp = fn(self, *args, **kwargs)
# 		if not quiet:
#				self.info()
#		  if not noplot:
#				self.plot(**kwargs)
		  return tmp
	 return _show

def Copy(fn):
	 def _copy(self, *args, **kwargs):
		  out = copy.copy(self)
		  return fn(out, *args, **kwargs)
	 return _copy


# define the Spectrum class which contains the relevant information
class Spectrum(object):
	 @Show
	 def __init__(self, filename, **kwargs):
		  '''Load the file'''
		  self.model = False
		  self.filename = filename
		  self.wlabel = 'Wavelength'
		  self.wunit = u.micron
		  self.flabel = 'F_lambda'
		  self.fscale = 'Arbitrary'
		  self.funit = u.erg/(u.cm**2 * u.s * u.micron)
		  self.simplefilename = os.path.basename(filename)
		  self.wave, self.flux, self.noise = readSpectrum(filename,**kwargs)
		  if not (kwargs.get('model',False)):
		  	x,y = filenameToNameDate(filename)
		  	self.name = kwargs.get('name',x)
		  	self.date = kwargs.get('date',y)
		  else:
		  	self.model = True
		  	self.teff = kwargs.get('teff',numpy.nan)
		  	self.logg = kwargs.get('logg',numpy.nan)
		  	self.z = kwargs.get('z',numpy.nan)
		  	self.cloud = kwargs.get('cloud',numpy.nan)
		  	self.modelset = kwargs.get('set','')
		  	self.name = self.modelset+' Teff='+str(self.teff)+' logg='+str(self.logg)
		  	self.fscale = 'Surface'
		  self.history = ['Loaded']
				
	 def __repr__(self):
		  '''A simple representation of an object is to just give it a name'''
		  return 'Spectra Object for {}'.format(self.name)

	 
	 @lazyprop
	 def _wrange(self):
		  ii = numpy.where(self.flux > 0)
		  xr = [numpy.nanmin(self.wave[ii]), numpy.nanmax(self.wave[ii])]
		  return xr
	 
	 @lazyprop
	 def _frange(self):
		  ii = numpy.where(numpy.logical_and(self.wave > 0.8,self.wave < 2.3))
		  yr = [0, numpy.nanmax(self.flux[ii])]
		  return yr

	 def normalize(self):
	 	'''Normalize spectrum'''
		self.scale(1./self._frange[1])
		self.fscale = 'Normalized'
		return

	 def scale(self,factor):
	 	'''Scale spectrum and noise by a constant factor'''
	 	self.flux = self.flux*factor
	 	self.noise = self.noise*factor
	 	self.fscale = 'Arbitrary'
	 	self._frange[1] = self._frange[1]*factor
	 	return
		
	 def flamTofnu(self):
	 	'''Convert flux density from F_lam to F_nu, the later in Jy'''
	 	self.flux.to(u.Jy,equivalencies=u.spectral_density(self.wave))
	 	self.noise.to(u.Jy,equivalencies=u.spectral_density(self.wave))
	 	self.flabel = 'F_nu'
	 	return

	 def fnuToflam(self):
	 	'''Convert flux density from F_nu to F_lam, the later in erg/s/cm2/Hz'''
	 	pass
	 	return

	 def snr(self):
	 	'''Compute a representative S/N value'''
	 	pass
	 	return

	 def absolute(self,band):
	 	'''Convert to absolute fluxes given absolute magnitude'''
	 	pass
	 	return

	 def apparent(self,band):
	 	'''Convert to apparent fluxes given absolute magnitude'''
	 	pass
	 	return

	 def surface(self,radius):
	 	'''Convert to surface fluxes given a radius, assuming at absolute fluxes'''
	 	pass
	 	return

		
	 def info(self):
		  '''Report some information about this spectrum'''
		  if (self.model):
		  	print '''{0:s} model with Teff = {1:i} and log g = {2:i}'''.format(self.modelset, self.teff, self.logg)
		  else:
		  	print '''Spectrum of {0:s} taken on {1:s}'''.format(self.name, self.date)
		  return

									 

# FUNCTIONS FOR SPLAT
def checkOnline():
	try:
		urllib2.urlopen(SPLAT_URL)
		return True
	except urllib2.URLError, ex:
		return False

def coordinateToDesignation(c):
	'''Convert RA, Dec into designation string'''
	if isinstance(value,ICRS):
		return 'J'+c.to_string(sep='',pad=True,precision=2,alwayssign=True)
	else:
		raise ValueError('\nMust provide an ICRS coordinate instance\n\n')



def designationToCoordinate(value, **kwargs):
	'''Convert a designation into a RA, Dec tuple or vice-versa'''
	icrsflag = kwargs.get('ICRS',False)
	if isinstance(value,str):
		if value[0].lower() != 'j':
#			raise ValueError('\nDesignation values must start with J\n\n')
			sys.stderr.write('\nDesignation values must start with J\n\n')
			return [0.,0.]
		a = re.sub('[j.:hms]','',value.lower())
		fact = 1.
		spl = a.split('+')
		if len(spl) == 1:
			spl = a.split('-')
			fact = -1.
		ra = 15.*float(spl[0][0:2])
		if (len(spl[0]) > 2):
			ra+=15.*float(spl[0][2:4])/60.
		if (len(spl[0]) > 4):
			ra+=15.*float(spl[0][4:6])/3600.
		if (len(spl[0]) > 6):
			ra+=15.*float(spl[0][6:8])/360000.
		dec = float(spl[1][0:2])
		if (len(spl[0]) > 2):
			dec+=float(spl[1][2:4])/60.
		if (len(spl[0]) > 4):
			dec+=float(spl[1][4:6])/3600.
		if (len(spl[1]) > 6): 
			dec+=float(spl[1][6:8])/360000.
		dec = dec*fact
		if icrsflag:
			return ICRS(ra=ra, dec=dec, unit=(u.degree, u.degree))
		else:
			return [ra,dec]
	elif isinstance(value,ICRS):
		return re.sub('[.]','','J{0}{1}'.format(value.ra.to_string(u.hour, sep='', precision=2, pad=True), \
			value.dec.to_string(sep='', precision=2, alwayssign=True, pad=True)))
	elif (len(value) == 2 and isinstance(value[0],float)):
		c = ICRS(ra=value[0], dec=value[1], unit=(u.degree, u.degree))
		return re.sub('[.]','','J{0}{1}'.format(c.ra.to_string(u.hour, sep='', precision=2, pad=True), \
			c.dec.to_string(sep='', precision=2, alwayssign=True, pad=True)))
	else:
		raise ValueError('\nMust provide a string value for designation\n\n')


def designationToShortName(value):
	'''Produce a shortened version of designation'''
	if isinstance(value,str):
		a = re.sub('[j.:hms]','',value.lower())
		mrk = '+'
		spl = a.split(mrk)
		if len(spl) == 1:
			mrk = '-'
			spl = a.split(mrk)
		if len(spl) == 2:
			return 'J'+spl[0][0:4]+mrk+spl[1][0:4]
		else:
			return value
	else:
		raise ValueError('\nMust provide a string value for designation\n\n')


def fetchDatabase(*args, **kwargs):	
	'''Get the SpeX Database from either online repository or local drive'''
	dataFile = kwargs.get('dataFile','db_spexprism.txt')
	folder = kwargs.get('folder',SplatFolder)
	url = kwargs.get('url',SPLAT_URL)
	local = kwargs.get('local',False)

# check if online
	local = local or (not checkOnline())
		
# first try online
	if not local:
		try:
			open(os.path.basename(dataFile), 'wb').write(urllib2.urlopen(url+dataFile).read())
			data = ascii.read(dataFile, delimiter='	',fill_values='-99.')
			os.remove(os.path.basename(dataFile))
#			return data
		except urllib2.URLError, ex:
			sys.stderr.write('\nReading local '+dataFile+'\n\n')
			local = True
	
# now try local drive - NOT WORKING
	file = dataFile
	if local:
		if (os.path.exists(file) == False):
			file = folder+os.path.basename(file)
		if (os.path.exists(file) == False):
			raise NameError('\nCould not find '+dataFile+' or '+file+' locally\n\n')
		else:
			data = ascii.read(file, delimiter='	')

# TEMPORARY ADD-ONS UNTIL DATABASE IS COMPLETED
# add in RA/Dec (TEMPORARY)
	ra = []
	dec = []
	for x in data['designation']:
		c = designationToCoordinate(x)
		ra.append(c[0])
		dec.append(c[1])
	data['ra'] = ra
	data['dec'] = dec

# add in young, subdwarf, binary, sbinary categories (TEMPORARY)
	data['young'] = ['young' in x for x in data['library']]
	data['subdwarf'] = ['subdwarf' in x for x in data['library']]
	data['binary'] = ['binary' in x for x in data['library']]
	data['spbin'] = ['spbin' in x for x in data['library']]
	data['blue'] = ['blue' in x for x in data['library']]
	data['red'] = ['red' in x for x in data['library']]

# add in shortnames (TEMPORARY)
	data['shortname'] = [designationToShortName(x) for x in data['designation']]

	return data


def filenameToNameDate(filename):
	months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']
	ind = filename.rfind('.')
	base = filename[:ind]
	spl = base.split('_')
	if (len(spl) < 2):
		return '', ''
	else:
		name = spl[-2]
		d = spl[-1]
		try:
			float(d)
			date = '20'+d[:2]+' '+months[int(d[3:4])-1]+' '+d[-2:]
		except ValueError:
			print filename+' does not contain a date'
			date = d
		
		return name, date


def getSourceKey(*args, **kwargs):
	'''Search the SpeX database to extract the key reference for that Source'''

	pass
	return


def getSpectrum(*args, **kwargs):
	'''Get a specific spectrum from online library'''

	result = []
	kwargs['output'] = 'data_file'
	files = getSpectrumRef(*args, **kwargs)
	if len(files) > 0:
		for x in files:
			result.append(loadSpectrum(x))
	else:
		sys.stderr.write('\nNo files match search criteria\n\n')
	return result
		

def getSpectrumRef(*args, **kwargs):
	'''Search the SpeX database to extract the key reference for that Spectrum
		Note that this is currently only and AND search - need to figure out
		how to a full SQL style search'''

# get database
	data = fetchDatabase(**kwargs)
	sql = Table()
	ref = kwargs.get('output','key')

# search parameters
	if kwargs.get('name',False) != False:
		nm = kwargs['name']
		if isinstance(nm,str):
			nm = [nm]
		sql['name'] = nm
	if kwargs.get('designation',False) != False:
		desig = kwargs['designation']
		if isinstance(desig,str):
			desig = [desig]
		sql['designation'] = desig
	if kwargs.get('shortname',False) != False:
		sname = kwargs['shortname']
		if isinstance(sname,str):
			sname = [sname]
		for i,sn in enumerate(sname):
			if sn[0].lower() != 'j':
				sname[i] = 'J'+sname[i]
		sql['shortname'] = sname
	if kwargs.get('date',False) != False:
		sql['observation_date'] = [kwargs['date']]
	if kwargs.get('young',False) != False:
		sql['young'] = [True]
	if kwargs.get('subdwarf',False) != False:
		sql['subdwarf'] = [True]
	if kwargs.get('binary',False) != False:
		sql['binary'] = [True]
	if kwargs.get('spbin',False) != False:
		sql['spbin'] = [True]
	if kwargs.get('red',False) != False:
		sql['red'] = [True]
	if kwargs.get('blue',False) != False:
		sql['blue'] = [True]

# NEED TO ADD IN SEARCH IN AREA, MAGNITUDE RANGE, OBS DATE RANGE, REFERENCES

	if len(sql) > 0:
		result = join(data,sql)
	else:
		result = data
		
	return result[ref]

	

# simple number checker
def isNumber(s):
	'''check if something is a number'''
	try:
		float(s)
		return True
	except ValueError:
		return False


def loadModel(*args, **kwargs):
	'''load up a model spectrum based on parameters'''
# keyword parameters
	set = kwargs.get('set','BTSettl')
	teff = kwargs.get('teff',1000)
	logg = kwargs.get('logg',5.0)
	z = kwargs.get('z',0.0)
	kzz = kwargs.get('kzz',2)
	folder = kwargs.get('folder','')
	url = kwargs.get('folder',SPLAT_URL+'/Models/')
	local = kwargs.get('local',False)
	kwargs['model'] = True

# check if online
	local = local or (not checkOnline())
		
# determine model set
	if (set.lower() == 'btsettl'):
		mFold = folder+'/BTSettl/'
		url = url+'/BTSettl/'
		mFile = 'lte'+'{:5.3f}'.format(teff/100000.)[2:]+'-'+str(logg)[0:3]+'-0.0.BT-Settl.7_r120.txt'
	else: 
		print 'Currently only have BTSettl models'

# a filename has been passed
	if (len(args) > 0):
		mFile = args[0]

# first try online
	if not local:
		try:
			open(os.path.basename(mFile), 'wb').write(urllib2.urlopen(url+mFile).read())
			sp = Spectrum(os.path.basename(mFile),**kwargs)
			os.remove(os.path.basename(mFile))
			return sp
		except urllib2.URLError, ex:
			sys.stderr.write('\nCould not find model file '+mFile+' on SPLAT website\n\n')
			local = True
	
# now try local drive
	file = mFile
	if (os.path.exists(file) == False):
		file = mFold+os.path.basename(file)
		if (os.path.exists(file) == False):
			raise NameError('\nCould not find '+file+' locally\n\n')
		else:
			return Spectrum(file,**kwargs)


# test code
def loadSpectrum(*args, **kwargs):
	'''load up a SpeX spectrum based name, shortname and/or date'''
# keyword parameters
#	name = kwargs.get('name','')
#	shname = kwargs.get('shname','')
#	date = kwargs.get('date','')
	local = kwargs.get('local',False)
	tempfilename = 'temp_model.txt'
	folder = kwargs.get('folder','')
	url = kwargs.get('folder',SPLAT_URL+'/Spectra/')
	local = kwargs.get('local',False)
	kwargs['model'] = False

# check if online
	local = local or (not checkOnline())
	
# CODE NEEDED HERE TO SET UP FILE NAME; FOR NOW JUST ERROR
	
# a filename has been passed
	if (len(args) > 0):
		dFile = args[0]
	else:
		raise NameError('\nNeed to pass in filename for spectral data')

# first try online
	if not local:
		try:
			open(os.path.basename(dFile), 'wb').write(urllib2.urlopen(url+dFile).read())
			sp = Spectrum(os.path.basename(dFile),**kwargs)
			os.remove(os.path.basename(dFile))
			return sp
		except urllib2.URLError, ex:
			sys.stderr.write('\nCould not find data file '+dFile+' at '+url+'\n\n')
			local = True
	
# now try local drive
	file = dFile
	if (os.path.exists(file) == False):
		file = folder+os.path.basename(file)
		if (os.path.exists(file) == False):
			raise NameError('\nCould not find '+file+' locally\n\n')
		else:
			return Spectrum(file,**kwargs)



# code to measure a defined index from a spectrum using Monte Carlo noise estimate
# measure method can be mean, median, integrate
# index method can be ratio = 1/2, valley = 1-2/3, OTHERS
# output is index value and uncertainty
def measureIndex(sp,*args,**kwargs):
	'''measure an index on a spectrum based on defined methodology'''

# keyword parameters
	method = kwargs.get('method','ratio')
	sample = kwargs.get('sample','integrate')
	nsamples = kwargs.get('nsamples',100)
			
# create interpolation functions
	w = numpy.where(sp.flux*sp.noise != numpy.nan)
	f = interp1d(sp.wave[w],sp.flux[w])
	s = interp1d(sp.wave[w],sp.noise[w])
				
# error checking on number of arguments provided
	if (len(args) < 2):
		print 'measureIndex needs at least two samples to function'
		return numpy.nan, numpy.nan
	elif (len(args) < 3 and (method == 'line' or method == 'allers')):
		print method+' requires at least 3 sample regions'
		return numpy.nan, numpy.nan

# define the sample vectors
	values = numpy.zeros((len(args),nsamples))

# loop over all sampling regions
	for i,waveRng in enumerate(args):
		xNum = (numpy.arange(0,nsamples+1.0)/nsamples)* \
			(numpy.nanmax(waveRng)-numpy.nanmin(waveRng))+numpy.nanmin(waveRng)
		yNum = f(xNum)
		yNum_e = s(xNum)

# now do MonteCarlo measurement of value and uncertainty
		for j in numpy.arange(0,nsamples):

# choose function for measuring indices
			if (sample == 'integrate'):
				values[i,j] = trapz(numpy.random.normal(yNum,yNum_e),xNum)
			elif (sample == 'average'):
				values[i,j] = numpy.nanmean(numpy.random.normal(yNum,yNum_e))
			elif (sample == 'median'):
				values[i,j] = numpy.median(numpy.random.normal(yNum,yNum_e))
			elif (sample == 'maximum'):
				values[i,j] = numpy.nanmax(numpy.random.normal(yNum,yNum_e))
			elif (sample == 'minimum'):
				values[i,j] = numpy.nanmin(numpy.random.normal(yNum,yNum_e))
			else:
				values[i,j] = numpy.nanmean(numpy.random.normal(yNum,yNum_e))

# compute index based on defined method
# default is a simple ratio
	if (method == 'ratio'):
		vals = values[0,:]/values[1,:]
	elif (method == 'line'):
		vals = (values[0,:]+values[1,:])/values[2,:]
	elif (method == 'change'):
		vals = 2.*(values[0,:]-values[1,:])/(values[0,:]+values[1,:])
	elif (method == 'allers'):
		vals = (((numpy.mean(args[0])-numpy.mean(args[1]))/(numpy.mean(args[2])-numpy.mean(args[1])))*values[2,:] \
			+ ((numpy.mean(args[2])-numpy.mean(args[0]))/(numpy.mean(args[2])-numpy.mean(args[1])))*values[1,:]) \
			/values[0,:]
	else:
		vals = values[0,:]/values[1,:]
			
# output mean, standard deviation
	return numpy.mean(vals), numpy.std(vals)


# wrapper function for measuring specific sets of indices

def measureIndexSet(sp,**kwargs):

# keyword parameters
	set = kwargs.get('set','burgasser')

# determine combine method
	if (set.lower() == 'burgasser'):
		reference = 'Indices from Burgasser et al. (2006)'
		names = ['H2O-J','CH4-J','H2O-H','CH4-H','H2O-K','CH4-K','K/J']
		inds = numpy.zeros(len(names))
		errs = numpy.zeros(len(names))
		inds[0],errs[0] = measureIndex(sp,[1.14,1.165],[1.26,1.285],method='ratio',sample='integrate',**kwargs)
		inds[1],errs[1] = measureIndex(sp,[1.315,1.335],[1.26,1.285],method='ratio',sample='integrate',**kwargs)
		inds[2],errs[2] = measureIndex(sp,[1.48,1.52],[1.56,1.60],method='ratio',sample='integrate',**kwargs)
		inds[3],errs[3] = measureIndex(sp,[1.635,1.675],[1.56,1.60],method='ratio',sample='integrate',**kwargs)
		inds[4],errs[4] = measureIndex(sp,[1.975,1.995],[2.08,2.12],method='ratio',sample='integrate',**kwargs)
		inds[5],errs[5] = measureIndex(sp,[2.215,2.255],[2.08,2.12],method='ratio',sample='integrate',**kwargs)
		inds[6],errs[6] = measureIndex(sp,[2.06,2.10],[1.25,1.29],method='ratio',sample='integrate',**kwargs)
	elif (set.lower() == 'tokunaga'):
		reference = 'Indices from Tokunaga & Kobayashi (1999)'
		names = ['K1','K2']
		inds = numpy.zeros(len(names))
		errs = numpy.zeros(len(names))
		inds[0],errs[0] = measureIndex(sp,[2.1,2.18],[1.96,2.04],method='change',sample='average',**kwargs)
		inds[1],errs[1] = measureIndex(sp,[2.2,2.28],[2.1,2.18],method='change',sample='average',**kwargs)
	elif (set.lower() == 'reid'):
		reference = 'Indices from Reid et al. (2001)'
		names = ['H2O-A','H2O-B']
		inds = numpy.zeros(len(names))
		errs = numpy.zeros(len(names))
		inds[0],errs[0] = measureIndex(sp,[1.33,1.35],[1.28,1.30],method='ratio',sample='average',**kwargs)
		inds[1],errs[1] = measureIndex(sp,[1.47,1.49],[1.59,1.61],method='ratio',sample='average',**kwargs)
	elif (set.lower() == 'geballe'):
		reference = 'Indices from Geballe et al. (2002)'
		names = ['H2O-1.2','H2O-1.5','CH4-2.2']
		inds = numpy.zeros(len(names))
		errs = numpy.zeros(len(names))
		inds[0],errs[0] = measureIndex(sp,[1.26,1.29],[1.13,1.16],method='ratio',sample='integrate',**kwargs)
		inds[1],errs[1] = measureIndex(sp,[1.57,1.59],[1.46,1.48],method='ratio',sample='integrate',**kwargs)
		inds[2],errs[2] = measureIndex(sp,[2.08,2.12],[2.215,2.255],method='ratio',sample='integrate',**kwargs)
	elif (set.lower() == 'allers'):
		reference = 'Indices from Allers et al. (2007) & Allers & Liu (2013)'
		names = ['H2O','FeH-z','VO-z','FeH-J','KI-J','H-cont']
		inds = numpy.zeros(len(names))
		errs = numpy.zeros(len(names))
		inds[0],errs[0] = measureIndex(sp,[1.55,1.56],[1.492,1.502],method='ratio',sample='average',**kwargs)
		inds[1],errs[1] = measureIndex(sp,[0.99135,1.00465],[0.97335,0.98665],[1.01535,1.02865],method='allers',sample='average',**kwargs)
		inds[2],errs[2] = measureIndex(sp,[1.05095,1.06505],[1.02795,1.04205],[1.07995,1.09405],method='allers',sample='average',**kwargs)
		inds[3],errs[3] = measureIndex(sp,[1.19880,1.20120],[1.19320,1.19080],[1.20920,1.20680],method='allers',sample='average',**kwargs)
		inds[4],errs[4] = measureIndex(sp,[1.23570,1.25230],[1.21170,1.22830],[1.26170,1.27830],method='allers',sample='average',**kwargs)
		inds[5],errs[5] = measureIndex(sp,[1.54960,1.57040],[1.45960,1.48040],[1.65960,1.68040],method='allers',sample='average',**kwargs)
	elif (set.lower() == 'slesnick'):
		reference = 'Indices from Slesnick et al. (2004)'
		names = ['H2O-1','H2O-2','FeH']
		inds = numpy.zeros(len(names))
		errs = numpy.zeros(len(names))
		inds[0],errs[0] = measureIndex(sp,[1.335,1.345],[1.295,1.304],method='ratio',sample='average',**kwargs)
		inds[1],errs[1] = measureIndex(sp,[2.035,2.045],[2.145,2.155],method='ratio',sample='average',**kwargs)
		inds[2],errs[2] = measureIndex(sp,[1.1935,1.2065],[1.2235,1.2365],method='ratio',sample='average',**kwargs)

# output dictionary of indices
	result = {names[i]: (inds[i],errs[i]) for i in numpy.arange(len(names))}
#	result['reference'] = reference
#	return inds,errs,names

	return result


def measureIndexSpT(sp, *args, **kwargs):

	str_flag = kwargs.get('string', False)
	rnd_flag = kwargs.get('round', False)
	rem_flag = kwargs.get('remeasure', True)
	nsamples = kwargs.get('nsamples', 100)
	nloop = kwargs.get('nloop', 5)
	set = kwargs.get('set','burgasser')
	allowed_sets = ['burgasser','reid','testi','allers']

# measure indices if necessary
	if (rem_flag or len(args) == 0):
		indices = measureIndexSet(sp, **kwargs)
	else:
		indices = args[0]

# Burgasser (2007, ApJ, 659, 655) calibration
	if (set.lower() == 'burgasser'):
		sptoffset = 20.
		sptfact = 1.
		coeffs = { \
			'H2O-J': {'fitunc': 0.8, 'range': [20,38], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [1.038e2, -2.156e2,  1.312e2, -3.919e1, 1.949e1]}, \
			'H2O-H': {'fitunc': 1.0, 'range': [20,38], 'spt': 0., 'sptunc': 99., 'mask': 1.,  \
			'coeff': [9.087e-1, -3.221e1, 2.527e1, -1.978e1, 2.098e1]}, \
			'CH4-J': {'fitunc': 0.7, 'range': [30,38], 'spt': 0., 'sptunc': 99., 'mask': 1.,  \
			'coeff': [1.491e2, -3.381e2, 2.424e2, -8.450e1, 2.708e1]}, \
			'CH4-H': {'fitunc': 0.3, 'range': [31,38], 'spt': 0., 'sptunc': 99., 'mask': 1.,  \
			'coeff': [2.084e1, -5.068e1, 4.361e1, -2.291e1, 2.013e1]}, \
			'CH4-K': {'fitunc': 1.1, 'range': [20,37], 'spt': 0., 'sptunc': 99., 'mask': 1.,  \
			'coeff': [-1.259e1, -4.734e0, 2.534e1, -2.246e1, 1.885e1]}}

# Reid et al. (2001, AJ, 121, 1710)
	elif (set.lower() == 'reid'):
		sptoffset = 20.
		sptfact = 1.
		coeffs = { \
			'H2O-A': {'fitunc': 1.18, 'range': [18,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [-32.1, 23.4]}, \
			'H2O-B': {'fitunc': 1.02, 'range': [18,28], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [-24.9, 20.7]}}

# Testi et al. (2001, ApJ, 522, L147)
	elif (set.lower() == 'testi'):
		sptoffset = 20.
		sptfact = 10.
		coeffs = { \
			'sHJ': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [-1.87, 1.67]}, \
			'sKJ': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [-1.20, 2.01]}, \
			'sH2O_J': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [1.54, 0.98]}, \
			'sH2O_H1': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [1.27, 0.76]}, \
			'sH2O_H2': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [2.11, 0.29]}, \
			'sH2O_K': {'fitunc': 0.5, 'range': [20,26], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [2.36, 0.60]}}

# Allers et al. (2007, ApJ, 657, 511)
	elif (set.lower() == 'allers'):
		sptoffset = 10.
		sptfact = 1.
		coeffs = { \
			'H2O': {'fitunc': 0.7, 'range': [15,25], 'spt': 0., 'sptunc': 99., 'mask': 1., \
			'coeff': [25,-19.25]}}
	else:
		sys.stderr.write('\nWarning: '+set.lower()+' SpT-index relation not in measureSpT code\n\n')
		return numpy.nan, numpy.nan


	for index in coeffs.keys():
		vals = numpy.polyval(coeffs[index]['coeff'],numpy.random.normal(indices[index][0],indices[index][1],nsamples))*sptfact
		coeffs[index]['spt'] = numpy.nanmean(vals)+sptoffset
		coeffs[index]['sptunc'] = (numpy.nanstd(vals)**2+coeffs[index]['fitunc']**2)**0.5
		
	print indices[index][0], numpy.polyval(coeffs[index]['coeff'],indices[index][0]), coeffs[index]
	mask = numpy.ones(len(coeffs.keys()))
	result = numpy.zeros(2)
	for i in numpy.arange(nloop):
		wts = [coeffs[index]['mask']/coeffs[index]['sptunc']**2 for index in coeffs.keys()]
		if (numpy.nansum(wts) == 0.):
			sys.stderr.write('\nIndices do not fit within allowed ranges\n\n')
			return numpy.nan, numpy.nan			
		vals = [coeffs[index]['mask']*coeffs[index]['spt']/coeffs[index]['sptunc']**2 \
			for index in coeffs.keys()]
		sptn = numpy.nansum(vals)/numpy.nansum(wts)
		sptn_e = 1./numpy.nansum(wts)**0.5
		for index in coeffs.keys():
			coeffs[index]['mask'] = numpy.where( \
				coeffs[index]['range'][0] <= sptn <= coeffs[index]['range'][1],1,0)

# round off to nearest 0.5 subtypes if desired
	if (rnd_flag):
		sptn = 0.5*numpy.around(sptn*2.)

# change to string if desired
	if (str_flag):
		spt = typeToNum(sptn,uncertainty=sptn_e)
	else:
		spt = sptn

	return spt, sptn_e



# To do:
# 	masking telluric regions
#	labeling features

def plotSpectrum(*args, **kwargs):

# error check - make sure you're plotting something
	if (len(args) < 1):
		print 'plotSpectrum needs at least on Spectrum object to plot'
		return

# keyword parameters
	title = kwargs.get('title','')
	xlabel = kwargs.get('xlabel','{} ({})'.format(args[0].wlabel,args[0].wunit))
	ylabel = kwargs.get('ylabel','{} {} ({})'.format(args[0].fscale,args[0].flabel,args[0].funit))
	xrange = kwargs.get('xrange',args[0]._wrange)
	yrange = kwargs.get('yrange',args[0]._frange)
	bound = xrange
	bound.extend(yrange)
	grid = kwargs.get('grid',False)
	colors = kwargs.get('colors',['k' for x in range(len(args))])
	if (len(colors) < len(args)):
		colors.extend(['k' for x in range(len(args)-len(colors))])
	colorsUnc = kwargs.get('colors',['k' for x in range(len(args))])
	if (len(colorsUnc) < len(args)):
		colorsUnc.extend(['k' for x in range(len(args)-len(colorsUnc))])
	linestyle = kwargs.get('linestyle',['steps' for x in range(len(args))])
	if (len(linestyle) < len(args)):
		linestyle.extend(['steps' for x in range(len(args)-len(linestyle))])
	file = kwargs.get('file','')
	format = kwargs.get('format',file.split('.')[-1])
	zeropoint = kwargs.get('zeropoint',[0. for x in range(len(args))])
	showNoise = kwargs.get('showNoise',[False for x in range(len(args))])
	if not isinstance(showNoise, tuple):
		showNoise = [showNoise]
	if (len(showNoise) < len(args)):
		showNoise.extend(['k' for x in range(len(args)-len(showNoise))])
	showZero = kwargs.get('showZero',[False for x in range(len(args))])
	if not isinstance(showZero, tuple):
		showZero = [showZero]
	if (len(showZero) < len(args)):
		showZero.extend(['k' for x in range(len(args)-len(showZero))])
	mask = kwargs.get('mask',False)				# not yet implemented
	labels = kwargs.get('labels','')			# not yet implemented
	features = kwargs.get('features','')		# not yet implemented

#	plt.clf()
# loop through sources
	plt.subplots(1)
	for ii,sp in enumerate(args):
		plt.plot(sp.wave,sp.flux,color=colors[ii],linestyle=linestyle[ii])
# show noise
		if (showNoise[ii]):
			plt.plot(sp.wave,sp.noise,color=colorsUnc[ii],linestyle=linestyle[ii],alpha=0.3)
# zeropoint
		if (showZero[ii]):
			plt.plot(args[0].wave,args[0].flux*0.+zeropoint[ii],color='k',linestyle='-')
# grid
	if (grid):
		plt.grid()
# labels
	plt.xlabel(xlabel)
	plt.ylabel(ylabel)
	plt.axis(bound)
	plt.title(title)
	
# save to file or display
	if (len(file) > 0): 
		plt.savefig(file, format=format)
	
	else:
		plt.show()
		plt.ion()		# make window interactive by default
	
	return


def readSpectrum(filename, **kwargs):

# TO BE DONE:
# FIX IF THERE IS NO NOISE CHANNEL
# PRODUCE AND RETURN HEADER => CHANGE OUTPUT TO DICTIONARY?
	
# keyword parameters
	folder = kwargs.get('folder','./')
	catchSN = kwargs.get('catchSN',True)
	model = kwargs.get('model',False)
	uncertainty = kwargs.get('uncertainty',not model)
	file = filename
	if (os.path.exists(file) == False):
		file = folder+os.path.basename(filename)
	if (os.path.exists(file) == False):
		raise NameError('\nCould not find ' + filename+'\n\n')

# determine which type of file
	ftype = file.split('.')[-1]

# fits file	
	if (ftype == 'fit' or ftype == 'fits'):
		data = fits.open(file)
		wave = data[0].data[0,:]
		flux = data[0].data[1,:]
		if (len(data[0].data[:,0]) > 2):
			noise = data[0].data[2,:]
		data.close()

# ascii file	
	else:
		if (uncertainty == True):
			try:
				wave,flux,noise = numpy.genfromtxt(file, comments='#', unpack=True, \
					missing_values = ('NaN','nan'), filling_values = (numpy.nan))
			except ValueError:
				wave,flux,noise = numpy.genfromtxt(file, comments=';', unpack=True, \
	 				missing_values = ('NaN','nan'), filling_values = (numpy.nan))
	 	if (uncertainty == False):
	 		try:
	 			wave,flux = numpy.genfromtxt(file, comments='#', unpack=True,missing_values = ('NaN','nan'), filling_values = (numpy.nan))
	 		except ValueError:
	 			wave,flux = numpy.genfromtxt(file, comments=';', unpack=True, missing_values = ('NaN','nan'), filling_values = (numpy.nan))

# add in fake uncertainty vector if needed
	if (not uncertainty):
		noise = numpy.zeros(len(flux))
		noise[:] = numpy.nan
  			

# fix places where noise is claimed to be 0
	w = numpy.where(noise == 0.)
	noise[w] = numpy.nan

# fix to catch badly formatted files where noise column is S/N	 			
#	print flux, numpy.median(flux)
	if (catchSN):
  		w = numpy.where(flux > numpy.median(flux))
  		if (numpy.median(flux[w]/noise[w]) < 1.):
  			noise = flux/noise
  			w = numpy.where(numpy.isnan(noise))
  			noise[w] = numpy.median(noise)

	return wave, flux, noise


def typeToNum(input, **kwargs):
	'''convert between string and numeric spectral types'''
# keywords	 
	error = kwargs.get('error','')
	unc = kwargs.get('uncertainty',0.)
	subclass = kwargs.get('subclass','')
	lumclass = kwargs.get('lumclass','')
	ageclass = kwargs.get('ageclass','')
	colorclass = kwargs.get('colorclass','')
	peculiar = kwargs.get('peculiar',False)
	spletter = 'KMLTY'

# number -> spectral type
	if (isNumber(input)):
		spind = int(abs(input/10))
		spdec = numpy.around(input,1)-spind*10.
		pstr = ''
		if (unc > 1.):
			error = ':'
		if (unc > 2.):
			error = '::'
		if (peculiar):
			pstr = 'p'
		if (0 <= spind < len(spletter)):
			output = colorclass+subclass+spletter[spind]+'{:3.1f}'.format(spdec)+ageclass+lumclass+pstr+error
		else:
			print 'Spectral type number must be between 0 ({}0) and {} ({}9)'.format(spletter[0],len(spletter)*10.-1.,spletter[-1])
			output = numpy.nan

# spectral type -> number
	else:
		sptype = re.findall('[{}]'.format(spletter),input)
		if (len(sptype) == 1):
			output = spletter.find(sptype[0])*10.
			spind = input.find(sptype[0])+1
			if (input.find('.') < 0):
				output = output+float(input[spind])
			else:
				output = output+float(input[spind:spind+3])
				spind = spind+3
	 		ytype = re.findall('[abcd]',input.split('p')[-1])
	 		if (len(ytype) == 1):
				ageclass = ytype[0]
	 		if (input.find('p') != -1):
	 			peculiar = True
	 		if (input.find('sd') != -1):
	 			subclass = 'sd'
	 		if (input.find('esd') != -1):
	 			subclass = 'esd'
	 		if (input.find('usd') != -1):
	 			subclass = 'usd'
	 		if (input.count('I') > 0):
	 			lumclass = ''.join(re.findall('I',input))
	 		if (input.count(':') > 0):
	 			error = ''.join(re.findall(':',input))
	 		if (input[0] == 'b' or input[0] == 'r'):
	 			colorclass = input[0]
		if (len(sptype) != 1):
			print 'Only spectral classes {} are handled with this routine'.format(spletter)
			output = numpy.nan
	return output


	 