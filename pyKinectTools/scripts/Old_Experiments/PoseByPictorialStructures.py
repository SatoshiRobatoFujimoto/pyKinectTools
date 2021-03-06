import numpy as np
sys.path.append('/Users/colin/libs/visionTools/slic-python/')
import slic
from pyKinectTools.algs.SkeletonBeliefPropagation import *
from pyKinectTools.algs.GraphAlgs import *



# dists2Tot[dists2Tot>1000] = 1000

# im8bit = (d[objects[ind]]*mask_erode)
# im8bit = im8bit / np.ceil(im8bit.max()/256.0)
im8bit = deepcopy(posMat)
for i in range(3):
	im8bit[:,:,i][im8bit[:,:,i]!=0] -= im8bit[:,:,i][im8bit[:,:,i]!=0].min()
	im8bit[:,:,i] /= im8bit[:,:,i].max()/256
im8bit = np.array(im8bit, dtype=uint8)
# im8bit = im8bit[:,:,2]
im4d = np.dstack([mask_erode, im8bit])
# im4d = np.dstack([mask_erode, im8bit, im8bit, im8bit])
# im4d = np.dstack([mask_erode, dists2Tot, dists2Tot, dists2Tot])
# im4d = np.dstack([mask_erode, im8bit, dists2Tot, mask_erode])
regions = slic.slic_n(np.array(im4d, dtype=uint8), 50,10)#2
# regions = slic.slic_s(np.array(im4d, dtype=uint8), 550,3)
regions *= mask_erode
imshow(regions)

avgColor = np.zeros([regions.shape[0],regions.shape[1],3])
# avgColor = np.zeros([regions.shape[0],regions.shape[1],4])

regionCount = regions.max()
regionLabels = [[0]]
goodRegions = 0
bodyMean = np.array([posMat[mask_erode,0].mean(),posMat[mask_erode,1].mean(),posMat[mask_erode,2].mean()])
for i in range(1, regionCount+2):
	if np.sum(np.equal(regions,i)) < 50:
		regions[regions==i] = 0
	else:
		if 1: #if using x/y/z
			meanPos = posMat[regions==i,:].mean(0)
		if 0: # If using distance map
			meanPos = np.array([posMat[regions==i,:].mean(0)[0],
								posMat[regions==i,:].mean(0)[1],
								# posMat[regions==i,:].mean(0)[2],
								(dists2Tot[regions==i].mean())])		
		if 0: # If using depth only
			meanPos = np.array([(np.nonzero(regions==i)[0].mean()),
						(np.nonzero(regions==i)[1].mean()),
						(im8bit[regions==i].mean())])
		avgColor[regions==i,:] = meanPos - bodyMean
		if not np.isnan(meanPos[0]) and meanPos[0] != 0.0:
			tmp = np.nonzero(regions==i)
			argPos = [int(tmp[0].mean()),int(tmp[1].mean())]
			regionLabels.append([i, meanPos-bodyMean, argPos])
			goodRegions += 1
			regions[regions==i] = goodRegions
			# print np.sum(np.equal(regions,i))
		else:
			regions[regions==i] = 0
regionCount = regions.max()

#Reindex
regionCount = len(regionLabels)
for lab, j in zip(regionLabels, range(regionCount)):
	lab.append(j)
	# mapRegionToIndex.append(lab[0])

# (Euclidan) Distance matrix
distMatrix = np.zeros([regionCount, regionCount])
for i_data,i_lab in zip(regionLabels, range(regionCount)):
	for j_data,j_lab in zip(regionLabels, range(regionCount)):
		if i_lab <= j_lab and i_lab!=0 and j_lab!=0:
			# distMatrix[i_lab,j_lab] = np.sqrt(((i_data[1][0]-j_data[1][0])**2)+((i_data[1][1]-j_data[1][1])**2)+.5*((i_data[1][2]-j_data[1][2])**2))
			distMatrix[i_lab,j_lab] = np.sqrt(np.sum((i_data[1]-j_data[1])**2))
distMatrix = np.maximum(distMatrix, distMatrix.T)
distMatrix += 1000*eye(regionCount)
# distMatrix[distMatrix > 400] = 1000
edges = distMatrix.argmin(0)

if 0:
	''' Draw edges based on closest node '''
	imLines = deepcopy(regions)
	for i in range(regionCount):
		pt1 = (regionLabels[i][2][1],regionLabels[i][2][0])
		cv2.circle(imLines, pt1, radius=0, color=125, thickness=3)

	for i in range(regionCount):
		pt1 = (regionLabels[i][2][1],regionLabels[i][2][0])
		pt2 = (regionLabels[edges[i]][2][1],regionLabels[edges[i]][2][0])
		cv2.line(imLines, pt1, pt2, 100)

mstEdges, edgeDict = MinimumSpanningTree(distMatrix)

# ''' Refine MST '''
# edgeDict, deletedInds = PruneEdges(edgeDict, maxLength=2)

# for i in deletedInds[-1::-1]:
# 	del regionLabels[i]

# #Reindex
# regionCount = len(regionLabels)
# for lab, j in zip(regionLabels, range(regionCount)):
# 	lab.append(j)
# 	# mapRegionToIndex.append(lab[0])

# # (Euclidan) Distance matrix
# distMatrix = np.zeros([regionCount, regionCount])
# for i_data,i_lab in zip(regionLabels, range(regionCount)):
# 	for j_data,j_lab in zip(regionLabels, range(regionCount)):
# 		if i_lab <= j_lab:
# 			# distMatrix[i_lab,j_lab] = np.sqrt(((i_data[1][0]-j_data[1][0])**2)+((i_data[1][1]-j_data[1][1])**2)+.5*((i_data[1][2]-j_data[1][2])**2))
# 			distMatrix[i_lab,j_lab] = np.sqrt(np.sum((i_data[1]-j_data[1])**2))
# distMatrix = np.maximum(distMatrix, distMatrix.T)
# distMatrix += 1000*eye(regionCount)
# edges = distMatrix.argmin(0)

# mstEdges, edgeDict = MinimumSpanningTree(distMatrix)



# figure(1); imshow(objTmp[:,:,2])

''' Draw edges based on minimum spanning tree '''
imLines = deepcopy(regions)
for i in range(1,regionCount):
	pt1 = (regionLabels[i][2][1],regionLabels[i][2][0])
	cv2.circle(imLines, pt1, radius=0, color=125, thickness=3)
# mstEdges = np.array(mstEdges) + 1
# Draw line for all edges
if 1:
	for i in range(len(mstEdges)):
		try:
			pt1 = (regionLabels[mstEdges[i][0]][2][1],regionLabels[mstEdges[i][0]][2][0])
			pt2 = (regionLabels[mstEdges[i][1]][2][1],regionLabels[mstEdges[i][1]][2][0])
			cv2.line(imLines, pt1, pt2, 100)
		except:
			pass
figure(2); imshow(imLines)

''' Draw line between all core nodes '''

# Draw circles
imLines = deepcopy(regions)
for i in range(1,regionCount):
	pt1 = (regionLabels[i][2][1],regionLabels[i][2][0])
	cv2.circle(imLines, pt1, radius=0, color=125, thickness=3)

leafPaths = GetLeafLengths(edgeDict)
leafLengths = [len(x) for x in leafPaths]
core = [x for x in edgeDict.keys() if len(edgeDict[x]) > 2]
branchesSet = set()
for i in leafPaths:
	for j in i:
		branchesSet.add(j)
core = np.sort(list(set(range(regionCount)).difference(branchesSet)))
# core = [x for x in edgeDict.keys() if len(edgeDict[x]) > 2]
for i in range(1, len(core)-1):
	pt1 = (regionLabels[core[i]][2][1], regionLabels[core[i]][2][0])
	pt2 = (regionLabels[core[i+1]][2][1],regionLabels[core[i+1]][2][0])
	cv2.line(imLines, pt1, pt2, 150)


# Draw line for all leafs
for i in range(len(leafPaths)):
	if len(leafPaths[i]) > 3:
		color = 125
	else:
		color = 100
	for j in range(len(leafPaths[i])-1):
		pt1 = (regionLabels[leafPaths[i][j]][2][1],regionLabels[leafPaths[i][j]][2][0])
		pt2 = (regionLabels[leafPaths[i][j+1]][2][1],regionLabels[leafPaths[i][j+1]][2][0])
		cv2.line(imLines, pt1, pt2, color)


#Draw head and hands
pt1 = (regionLabels[core[0]][2][1],regionLabels[core[0]][2][0])
cv2.circle(imLines, pt1, radius=10, color=150, thickness=1)

for i in xrange(len(leafLengths)):
	if leafLengths[i] >= 4:
		pt1 = (regionLabels[leafPaths[i][0]][2][1],regionLabels[leafPaths[i][0]][2][0])
		cv2.circle(imLines, pt1, radius=10, color=125, thickness=1)



figure(3); imshow(imLines)






if 1:
	imLines = deepcopy(regions)
	imLines[imLines>0] = 20
	for i in range(len(mstEdges)):
		pt1 = (regionLabels[mstEdges[i][0]][2][1],regionLabels[mstEdges[i][0]][2][0])
		pt2 = (regionLabels[mstEdges[i][1]][2][1],regionLabels[mstEdges[i][1]][2][0])
		cv2.line(imLines, pt1, pt2, 3)


	# head, body, arm, legs
	# potentialPoses = [np.array([[500, 30, 0], [50, 44, -27], [-18, -150, 25]]),
	# 				  np.array([[500, 30, 0], [107, 44, 0], [-18, 150, 25]]),
	# 				  np.array([[0, 30, 0], [107, 44, 0], [-18, -150, 25]]),
	# 				  np.array([[200, 30, 0], [107, 144, 0], [-18, -150, 25]])]
	# 				  np.array([[500, 0, -25], [-107, 144, 100], [-18, -150, 25]])]

	potentialPoses = [np.array([regionLabels[3][1], regionLabels[27][1], regionLabels[24][1],regionLabels[55][1]]),
					  np.array([regionLabels[7][1], regionLabels[30][1], regionLabels[22][1],regionLabels[53][1]]),
					  np.array([regionLabels[5][1], regionLabels[22][1], regionLabels[29][1],regionLabels[54][1]]),
					  np.array([regionLabels[0][1], regionLabels[23][1], regionLabels[24][1],regionLabels[55][1]])]
	potentialLabels = [np.array([regionLabels[3][2], regionLabels[27][2], regionLabels[24][2],regionLabels[55][2]]),
					  np.array([regionLabels[7][2], regionLabels[30][2], regionLabels[22][2],regionLabels[53][2]]),
					  np.array([regionLabels[5][2], regionLabels[22][2], regionLabels[29][2],regionLabels[54][2]]),
					  np.array([regionLabels[0][2], regionLabels[23][2], regionLabels[24][2],regionLabels[55][2]])]  

	# transitionMatrix = np.matrix([[.1,.45, .45],[.45,.1, .45],[.45,.45,.1]])
	# transitionMatrix = np.matrix([[.5,.25, .25],[.25,.5, .25],[.25,.25,.5]])
	# transitionMatrix = np.matrix([[.9,.05, .05],[.05,.9, .05],[.05,.05,.9]])

	transitionMatrix = np.matrix([[.55,.15, .15, .15],[.15,.55, .15, .15],[.15,.15,.55, .15],[.15,.15,.15,.55]])
	# transitionMatrix = np.matrix([[.7,.1, .1, .1],[.1,.7, .1, .1],[.1,.1,.7, .1],[.1,.1,.1,.7]])	
	# transitionMatrix = np.matrix([[1,.0, .0, .0],[.0,1, .0, .0],[.0,.0,1, .0],[.0,.0,.0,1]])	
	# transitionMatrix = np.matrix([[0,1.0,1.0,1.0],[1.0,.0,1.0,1.0],[1.0,1.0,.0,1.0],[1.0,1.0,1.0,.0]])	
	# transitionMatrix = np.matrix([[.0,.0, .0, .0],[.0,0, .0, .0],[.0,.0,0, .0],[.0,.0,.0,0]])	


	rootNodeInd = core[int(len(core)/2)]
	rootNode = Node(index_=rootNodeInd, children_=edgeDict[rootNodeInd], pos_=regionLabels[rootNodeInd][1])

	beliefs = []
	ims = []
	for guessPose,i in zip(potentialPoses, range(len(potentialPoses))):
		print "-----"
		# print guessPose
		t1 = time.time()
		rootNode.calcAll(guessPose)
		print "Time:", time.time() - t1

		beliefs.append(rootNode.calcTotalBelief())
		print beliefs[-1]
		rootNode.drawAll()

		ims.append(deepcopy(imLines))
		pts = potentialLabels[i]
		for j,j_i in zip(pts, range(len(pts))):
			print j
			cv2.circle(ims[-1], (j[1], j[0]), radius=15, color=20*j_i+10, thickness=2)
		subplot(1,4,i+1)
		imshow(ims[-1])



	print "Best pose:", np.argmax(beliefs)
	subplot(1,4,np.argmax(beliefs)+1)
	xlabel("**Best**")


	# imshow(imLines)

