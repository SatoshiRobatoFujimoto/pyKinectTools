
import os, time, sys
import numpy as np
import scipy.ndimage as nd


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

def extractPeople(im, minPersonPixThresh=7000, gradientFilter=True):
	# im *= im < im.max()
	# shape_ = im.shape
	# im_ = im[1:shape_[0], 1:shape_[1]]
	# im = np.array(im, dtype=np.int16)

	if not gradientFilter:
		grad_bin = im > 0
	else:
		# grad = np.gradient(im)
		# grad_g = np.sqrt(grad[0]**2+grad[1]**2)
		# grad_bin = (grad_g < 50)*(im > 0)
		grad_g = np.diff(np.asarray(im, dtype=np.int16), 3)		
		grad_bin = (np.abs(grad_g) < 20) * (im[:,1:-2]>0)

		# grad_bin = nd.binary_erosion(grad_bin, iterations=1)

	# structure = np.array([[1,1,1],[1,1,1],[1,1,1]])
	# labels = nd.label(grad_bin, structure)
	labels = nd.label(grad_bin)
	objs = nd.find_objects(labels[0])#, labels[1])

	# Only extract if there are sufficient pixels
	objs2 = [x for x in zip(objs,range(1, len(objs)+1)) if minPersonPixThresh < nd.sum(labels[0][x[0]]==x[1]) < .9*im.shape[0]*im.shape[1] ]
	# [x[0]]
	if len(objs2) > 0:
		objs, goodLabels = zip(*objs2) # unzip objects
	else:
		objs = []
		goodLabels = []

	return labels[0], objs, goodLabels


def getMeanImage(depthImgs):
	mean_ = np.mean(depthImgs, 2)
	mean_ = mean_*(~nd.binary_dilation(mean_==0, iterations=3))

	## Close holes in images
	inds = nd.distance_transform_edt(mean_<500, return_distances=False, return_indices=True)
	i2 = np.nonzero(mean_<500)
	i3 = inds[:, i2[0], i2[1]]
	mean_[i2] = mean_[i3[0], i3[1]] # For all errors, set to avg 

	return mean_


def removeNoise(im, thresh=500):
	#Thresh is the envelope in the depth dimension within we remove noise
	zAvg = im[im[:,:,2]>0,2].mean()
	zThresh = thresh
	im[im[:,:,2]>zAvg+zThresh] = 0
	im[im[:,:,2]<zAvg-zThresh] = 0
	im[:,:,2] = nd.median_filter(im[:,:,2], 3)

	return im
