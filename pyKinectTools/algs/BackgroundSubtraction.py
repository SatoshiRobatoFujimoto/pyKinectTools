
import os, time, sys
import numpy as np
import scipy.ndimage as nd

# import cProfile
# from profilehooks import profile


def constrain(img, mini=-1, maxi=-1): #500, 4000
	if mini == -1:
		min_ = np.min(img[np.nonzero(img)])
	else:
		min_ = mini
	if maxi == -1:
		max_ = img.max()
	else:
		max_ = maxi

	img = np.clip(img, min_, max_)
	img -= min_
	if max_ == 0:
		max_ = 1
	img = np.array((img * (255.0 / (max_-min_))), dtype=np.uint8)

	img[img==img.max()] = 0

	return img

def extractPeople_old(img):
	from scipy.spatial import distance
	from sklearn.cluster import DBSCAN
	import cv2

	if len(img) == 1:
		img = img[0]
	img = img*nd.binary_opening(img>0, iterations=5)
	img = cv2.medianBlur(img, 5)
	# hist1 = np.histogram(img, 128)
	hist1 = np.histogram(img, 64)
	if (np.sum(hist1[0][1::]) > 100):
		samples = np.random.choice(np.array(hist1[1][1:-1], dtype=int), 1000, p=hist1[0][1::]*1.0/np.sum(hist1[0][1::]))
		samples = np.sort(samples)
	else:
		return np.zeros_like(img), []

	tmp = np.array([samples, np.zeros_like(samples)])
	D = distance.squareform(distance.pdist(tmp.T, 'cityblock'))
	# D = distance.squareform(distance.pdist(tmp.T, 'chebyshev'))
	S = 1 - (D / np.max(D))

	db = DBSCAN().fit(S, eps=0.95, min_samples=50)
	labels = db.labels_
	n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)

	clusterLimits = []
	# for i in range(-1, n_clusters_):
	max_ = 0
	for i in xrange(1, n_clusters_):		
		min_ = np.min(samples[np.nonzero((labels==i)*samples)])
		max_ = np.max(samples[np.nonzero((labels==i)*samples)])
		clusterLimits.append([min_,max_])
	if max_ != 255:
		clusterLimits.append([max_, 255])
	clusterLimits.append([0, min(clusterLimits)[0]])
	clusterLimits.sort()

	d = np.zeros_like(img)
	tmp = np.zeros_like(img)
	labels = []
	for i in xrange(0, n_clusters_):
		tmp = (img > clusterLimits[i][0])*(img < clusterLimits[i][1])
		d[np.nonzero((img > clusterLimits[i][0])*(img < clusterLimits[i][1]))] = (i+2)
		tmpLab = nd.label(tmp)
		if labels == []:
			labels = tmpLab
		else:
			labels = [labels[0]+((tmpLab[0]>0)*(tmpLab[0]+tmpLab[1])), labels[1]+tmpLab[1]]

	objs = nd.find_objects(labels[0])
	goodObjs = []
	for i in xrange(len(objs)):	
		if objs[i] != None:
			# px = nd.sum(d, labels[0], i)
			px = nd.sum(labels[0][objs[i]]>0)
			# print "Pix:", px
			if px > 7000:
				goodObjs.append([objs[i], i+1])

	d1A = np.zeros_like(img)
	for i in xrange(len(goodObjs)):
		## Plot all detected people
		# subplot(1, len(goodObjs)+1, i+1)
		# imshow(d[goodObjs[i][0]] == goodObjs[i][1])
		# imshow(d[goodObjs[i][0]] > 0)
		# imshow(labels[0] == goodObjs[i][1])

		d1A = np.maximum(d1A, (labels[0] == goodObjs[i][1])*(i+1))		
		# d1A[goodObjs[i][0]] = np.maximum(d1A[goodObjs[i][0]], (d[goodObjs[i][0]]>0)*8000)

	return d1A, goodObjs

# @Deprecated
def extractPeople_2(im):
	return extractPeople(im)

def extractPeople(im, mask, minPersonPixThresh=500, gradThresh=50, gradientFilter=True):


	if not gradientFilter:
		grad_bin = mask
	else:
		grad_g = np.diff(im.astype(np.int16), 1)#*(1.-mask[:,:mask.shape[1]-1])
		grad_g = np.abs(grad_g)
		grad_bin = (np.abs(grad_g) < gradThresh)
		# grad_bin = nd.binary_erosion(grad_bin, iterations=1)
		grad_bin = nd.binary_erosion(grad_bin, iterations=1)

	mask = nd.binary_erosion(mask, iterations=1)
	# import cv2
	# cv2.imshow("grad", mask.astype(np.uint8)*255)	
	mask[:,:-1] = mask[:,:-1]*grad_bin# np.logical_and(mask[:,:-1],grad_bin)# np.logical_not(grad_bin))
	# cv2.imshow("grad2", mask.astype(np.uint8)*255)	
	# ret = cv2.waitKey(10)
	# if ret > 0:
	# 	from matplotlib.pylab import *
	# 	from IPython import embed
	# 	embed()
	# cv2.imshow("grad", grad_g.astype(np.float)/gradThresh)	
	labelIm, maxLabel = nd.label(im*mask)
	connComps = nd.find_objects(labelIm, maxLabel)

	# Only extract if there are sufficient pixels
	minPersonPixThresh = 5000
	usrTmp = [(c,l) for c,l in zip(connComps,range(1, maxLabel+1)) if minPersonPixThresh < nd.sum(labelIm[c]==l)]
	if len(usrTmp) > 0:
		userBoundingBoxes, userLabels = zip(*usrTmp)
	else:
		userBoundingBoxes = []
		userLabels = []
	userCount = len(userLabels)

	#Relabel foregound mask with multiple labels
	mask = im.astype(np.uint8)*0
	for i,i_new in zip(userLabels, range(1, userCount+1)):
		mask[labelIm==i] = i_new

	return mask, userBoundingBoxes, userLabels



def getMeanImage(depthImgs):
	mean_ = np.mean(depthImgs, 2)
	mean_ = mean_*(~nd.binary_dilation(mean_==0, iterations=3))

	## Close holes in images
	inds = nd.distance_transform_edt(mean_<500, return_distances=False, return_indices=True)
	i2 = np.nonzero(mean_<500)
	i3 = inds[:, i2[0], i2[1]]
	mean_[i2] = mean_[i3[0], i3[1]] # For all errors, set to avg 

	return mean_

def fillImage(im, tol=500):
	## Close holes in images
	inds = nd.distance_transform_edt(im<tol, return_distances=False, return_indices=True)
	i2 = np.nonzero(im<50)
	i3 = inds[:, i2[0], i2[1]]
	im[i2] = im[i3[0], i3[1]] # For all errors, set to avg 	

	return im


def removeNoise(im, thresh=500):
	#Thresh is the envelope in the depth dimension within we remove noise
	zAvg = im[im[:,:,2]>0,2].mean()
	zThresh = thresh
	im[im[:,:,2]>zAvg+zThresh] = 0
	im[im[:,:,2]<zAvg-zThresh] = 0
	im[:,:,2] = nd.median_filter(im[:,:,2], 3)

	return im


''' Adaptive Mixture of Gaussians '''
class AdaptiveMixtureOfGaussians:

	def __init__(self, im, maxGaussians=5, learningRate=0.05, decayRate=0.25, variance=100**2):

		xRez, yRez = im.shape
		self.MaxGaussians = maxGaussians
		self.LearningRate = learningRate
		self.DecayRate = decayRate
		self.VarianceInit = variance
		self.CurrentGaussianCount = 1		

		# self.Means = np.ones([xRez,yRez,self.CurrentGaussianCount])
		# self.Variances = np.ones([xRez,yRez,self.CurrentGaussianCount])*self.VarianceInit
		# self.Weights = np.ones([xRez,yRez,self.CurrentGaussianCount])*self.LearningRate
		# self.Deltas = np.zeros([xRez,yRez,self.CurrentGaussianCount])

		self.Means = np.zeros([xRez,yRez,self.MaxGaussians])
		self.Variances = np.empty([xRez,yRez,self.MaxGaussians])
		self.Weights = np.empty([xRez,yRez,self.MaxGaussians])
		self.Deltas = np.empty([xRez,yRez,self.MaxGaussians])
		self.NumGaussians = np.ones([xRez,yRez], dtype=np.uint8)

		self.Deltas = np.zeros([xRez,yRez,self.MaxGaussians]) + np.inf

		self.Means[:,:,0] = im
		self.Weights[:,:,0] = self.LearningRate
		self.Variances[:,:,0] = self.VarianceInit

		self.Deviations = ((self.Means - im[:,:,np.newaxis])**2 / self.Variances)
		self.backgroundModel = im
		self.currentIm = im

	# @profile
	def update(self, im):
		from matplotlib.pylab import *
		from IPython import embed
		# embed()

		import pdb
		# pdb.set_trace()
		self.currentIm = im

		''' Check deviations '''
		self.Deviations = ((self.Means - im[:,:,np.newaxis])**2 / self.Variances)
		# print "self.Deviations:", self.Deviations[150,20]

		for m in range(self.CurrentGaussianCount):
			# self.Deviations[:,:,m] = (m < self.NumGaussians)*self.Deviations[:,:,m] + (m >= self.NumGaussians)*9999999999
			self.Deviations[m > self.NumGaussians,m] = np.inf

		Ownership = np.argmin(self.Deviations, -1)
		deviationMin = np.min(self.Deviations, -1)
		# Ownership = np.nanargmin(self.Deviations, -1)
		# deviationMin = np.nanmin(self.Deviations, -1)
		# print "Dev max", deviationMin.max()

		createNewMixture = deviationMin > 3
		createNewMixture[np.isinf(deviationMin)] = False
		replaceLowestMixture = np.logical_and(createNewMixture, self.NumGaussians>=self.MaxGaussians)
		createNewMixture = np.logical_and(createNewMixture, self.NumGaussians<self.MaxGaussians)

		''' Create new mixture using existing indices'''
		if np.any(createNewMixture):
			activeset_x, activeset_y = np.nonzero(createNewMixture)
			activeset_z = self.NumGaussians[activeset_x, activeset_y].ravel()

			# print "-------New Mixture------", len(activeset_x)
			self.Means[activeset_x,activeset_y,activeset_z] = im[activeset_x,activeset_y]
			self.Weights[activeset_x,activeset_y,activeset_z] = self.LearningRate
			self.Variances[activeset_x,activeset_y,activeset_z] = self.VarianceInit
			self.NumGaussians[activeset_x,activeset_y] += 1
			Ownership[activeset_x,activeset_y] = activeset_z

		''' Replace lowest weighted mixture '''
		if np.any(replaceLowestMixture):
			activeset_x, activeset_y = np.nonzero(replaceLowestMixture)

			activeset_z = np.argmin(self.Weights[activeset_x, activeset_y,:], -1)

			print "-------Replace Mixture------", len(activeset_x)
			self.Means[activeset_x,activeset_y,activeset_z] = im[activeset_x,activeset_y]
			self.Weights[activeset_x,activeset_y,activeset_z] = self.LearningRate
			self.Variances[activeset_x,activeset_y,activeset_z] = self.VarianceInit
			Ownership[activeset_x,activeset_y] = activeset_z

		self.CurrentGaussianCount = self.NumGaussians.max()

		# if np.any(Ownership>0):
		# 	from skimage.viewer.viewers import CollectionViewer
		# 	nView = CollectionViewer([bgSubtraction.Weights[:,:,i]/np.nanmax(bgSubtraction.Weights[:,:,i]).astype(float) for i in range(bgSubtraction.MaxGaussians)])
		# 	# nView = CollectionViewer([self.NumGaussians[:,:,i]/np.nanmax(self.NumGaussians[:,:,i]).astype(float) for i in range(self.MaxGaussians)])
		# 	# nView.show()			
		# meanView = CollectionViewer([self.Means[:,:,i]/np.nanmax(self.Means[:,:,i]).astype(float) for i in range(self.MaxGaussians)])
		# meanView = CollectionViewer([bgSubtraction.Means[:,:,i]/np.nanmax(bgSubtraction.Means[:,:,i]).astype(float) for i in range(bgSubtraction.MaxGaussians)])
		# 	meanView.show()
		# 	varView = CollectionViewer([self.Variances[:,:,i]/np.nanmax(self.Variances[:,:,i]).astype(float) for i in range(self.MaxGaussians)])
		# 	varView.show()



		''' Update gaussians'''
		for m in range(self.CurrentGaussianCount):
			self.Deltas[:,:,m]		= im - self.Means[:,:,m]
			tmpOwn 					= Ownership==m
			# print "Own:",np.sum(tmpOwn)

			self.Weights[:,:,m]		= self.Weights[:,:,m] 	+ self.LearningRate*(tmpOwn - self.Weights[:,:,m]) - self.LearningRate*self.DecayRate			
			tmpWeight 				= tmpOwn*(self.LearningRate/self.Weights[:,:,m])			
			tmpMask = (self.Weights[:,:,m]<=0.01)
			tmpWeight[tmpMask] = 0

			self.Means[:,:,m] 		= self.Means[:,:,m] 	+ tmpWeight * self.Deltas[:,:,m]
			# self.Variances[:,:,m] 	= self.Variances[:,:,m] + tmpWeight * (self.Deltas[:,:,m]**2 - self.Variances[:,:,m])

			''' If the weight is zero, reset '''

			if np.any(tmpMask):
				self.Variances[tmpMask, m:self.CurrentGaussianCount-2] = self.Variances[tmpMask, m+1:self.CurrentGaussianCount-1]
				self.Means[tmpMask, m:self.CurrentGaussianCount-2] = self.Means[tmpMask, m+1:self.CurrentGaussianCount-1]
				self.Weights[tmpMask, m:self.CurrentGaussianCount-2] = self.Means[tmpMask, m+1:self.CurrentGaussianCount-1]
				self.Variances[tmpMask, m:self.CurrentGaussianCount-1] = 0
				self.Means[tmpMask, m:self.CurrentGaussianCount-1] = 0
				self.Weights[tmpMask, m:self.CurrentGaussianCount-1] = 0

			import cv2
			cv2.imshow(str(m), self.Means[:,:,m]/5000.)
			# cv2.imshow(str(m), self.Weights[:,:,m]/np.nanmax(self.Weights[:,:,m]))
		# cv2.imshow("ownership", Ownership/Ownership.max().astype(np.float))


		# embed()
		self.backgroundModel = np.max(self.Means, 2)
		# self.backgroundModel = np.nanmax(self.Means, 2)
		
		'''This'''
		# tmp = np.argmax(self.Weights,2).ravel()
		# self.backgroundModel = self.Means[:,:,tmp]

		# self.backgroundModel = self.Means[:,:,np.nanargmax(self.Weights, 2).ravel()]
		# self.backgroundModel = np.nanmax(self.Means*(self.Means<10000), 2)
		

		# print "Val:", im[150,20]
		# print "Owner:", Ownership[150,20]
		# print "Means:", self.Means[150,20]
		# print "Weight:", self.Weights[150,20]
		# print "Var:", self.Variances[150,20]
		# print 'Create new:', createNewMixture[150,20]
		# print 'numGauss:', self.NumGaussians[150,20]


	def getModel(self):
		return self.backgroundModel

	def getForeground(self, thresh=100):
		return (self.backgroundModel - self.currentIm) > thresh



class MedianModel:

	def __init__(self):
		self.prevDepthIms = fillImage(depthIm.copy())[:,:,np.newaxis]
		self.prevColorIms = colorIm_g[:,:,np.newaxis]		

	def update(self,depthIm, colorIm):

		# Add to set of images
		self.prevDepthIms = np.dstack([self.prevDepthIms, depthIm])
		self.prevColorIms = np.dstack([self.prevColorIms, colorIm])

		# Check if too many (or few) images
		imCount = self.prevDepthIms.shape[2]
		if imCount <= 1:
			return

		elif imCount > 50:
			self.prevDepthIms = self.prevDepthIms[:,:,-50:]
			self.prevColorIms = self.prevColorIms[:,:,-50:]	

		self.backgroundModel = np.median(self.prevDepthIms, -1)

	def getModel(self):
		return self.backgroundModel		




''' Likelihood based on optical flow'''

# backgroundProb[foregroundMask == 0] = 1.
# prevDepthIms[:,:,-1] = 5000.

# if backgroundProbabilities is None:
# 	backgroundProbabilities = backgroundProb[:,:,np.newaxis]
# else:
# 	backgroundProbabilities = np.dstack([backgroundProbabilities, backgroundProb])

# cv2.imshow("flow_color", flow[:,:,0]/float(flow[:,:,0].max()))
# cv2.imshow("Prob", backgroundProbabilities.mean(-1) / backgroundProbabilities.mean(-1).max())
# tmp = np.sum(backgroundProbabilities*prevDepthIms[:,:,1:],2) / np.sum(backgroundProbabilities,2)
# # print tmp.min(), tmp.max()
# cv2.imshow("BG_Prob", tmp/tmp.max())

# backgroundProbabilities -= .01
# backgroundProbabilities = np.maximum(backgroundProbabilities, 0)

# prob = .5
# # backgroundModel = tmp#(tmp > prob)*tmp + (tmp < prob)*5000
# backgroundModel = np.median(prevDepthIms, 2)
# cv2.imshow("BG model", backgroundModel/5000.)




# backgroundProb = np.exp(-flowMag)











# else:
# 	mask = np.abs(backgroundModel.astype(np.int16) - depthIm) < 50
# 	mask[depthIm < 500] = 0

# 	depthBG = depthIm.copy()
# 	depthBG[~mask] = 0
# 	if backgroundTemplates.shape[2] < backgroundCount or np.random.rand() < bgPercentage:
# 		# mask = np.abs(backgroundTemplates[0].astype(np.int16) - depthIm) < 20
# 		backgroundTemplates = np.dstack([backgroundTemplates, depthBG])
# 		backgroundModel = backgroundTemplates.sum(-1) / np.maximum((backgroundTemplates>0).sum(-1), 1)
# 		backgroundModel = nd.maximum_filter(backgroundModel, np.ones(2))
# 	if backgroundTemplates.shape[2] > backgroundCount:
# 		# backgroundTemplates.pop(0)
# 		backgroundTemplates = backgroundTemplates[:,:,1:]

# 	depthIm[mask] = 0


''' Background model #2 '''
# mask = None
# if backgroundModel is None:
# 	backgroundModel = depthIm.copy()
# 	backgroundTemplates = depthIm[:,:,np.newaxis].copy()
# else:
# 	mask = np.abs(backgroundModel.astype(np.int16) - depthIm)
# 	mask[depthIm < 500] = 0

# 	depthBG = depthIm.copy()
# 	# depthBG[~mask] = 0
# 	if backgroundTemplates.shape[2] < backgroundCount or np.random.rand() < bgPercentage:
# 		# mask = np.abs(backgroundTemplates[:,:,0].astype(np.int16) - depthIm)# < 20
# 		backgroundTemplates = np.dstack([backgroundTemplates, depthBG])
# 		backgroundModel = backgroundTemplates.sum(-1) / np.maximum((backgroundTemplates>0).sum(-1), 1)
# 		# backgroundModel = nd.maximum_filter(backgroundModel, np.ones(2))
# 	if backgroundTemplates.shape[2] > backgroundCount:
# 		backgroundTemplates = backgroundTemplates[:,:,1:]

	# depthIm[mask] = 0
