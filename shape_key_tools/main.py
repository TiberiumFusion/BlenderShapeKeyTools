import sys, bpy

#
#====================================================================================================
#    Common
#====================================================================================================
#

### Creates a vertex filtering kernel function per the provided parameters
def CreateVertexFilterKernel(params):
	deltaDistanceMin = 0
	if ("DeltaDistanceMin" in params):
		deltaDistanceMin = params["DeltaDistanceMin"]
	
	deltaDistanceMax = sys.float_info.max
	if ("DeltaDistanceMax" in params):
		deltaDistanceMax = params["DeltaDistanceMax"]
	
	vertexGroupIndex = None
	if ("VertexGroupIndex" in params):
		vertexGroupIndex = int(params["VertexGroupIndex"], 10) # int() because blender requires a string identifier for EnumProperty value IDs (numbers cause silent errors)
	
	def filter(vertVGIndices, delta):
		return (
			(delta.length >= deltaDistanceMin and delta.length <= deltaDistanceMax)
			and
			(vertexGroupIndex == None or vertexGroupIndex in vertVGIndices)
		)
	
	return filter
	

	
#
#====================================================================================================
#    Pair Split/Merge
#====================================================================================================
#

### Given an existing shape key, determines the new names if this shape key was to be split into L and R halves
def FindShapeKeySplitNames(originalShapeKeyName):
	newLeftName = None
	newRightName = None
	usesPairNameConvention = False
	if ('+' in originalShapeKeyName):
		nameCuts = originalShapeKeyName.split("+")
		if (nameCuts[0].lower()[-1] == "l" and nameCuts[1].lower()[-1] == "r"):
			newLeftName = nameCuts[0]
			newRightName = nameCuts[1]
			usesPairNameConvention = True
		elif (nameCuts[1].lower()[-1] == "l" and nameCuts[0].lower()[-1] == "r"):
			newLeftName = nameCuts[1]
			newRightName = nameCuts[0]
			usesPairNameConvention = True
		else:
			raise Exception("Shape key \"" + originalShapeKeyName + "\" appears to use pair name convention (e.g. MyKeyL+MyKeyR), but it does not have both the 'L' and 'R' key characters in its name.")
	else:
		newLeftName = originalShapeKeyName + "L"
		newRightName = originalShapeKeyName + "R"
		usesPairNameConvention = False
	
	return [newLeftName, newRightName, usesPairNameConvention]


### Splits the active shape key on the specified object into separate left and right halves
# Params:
# - obj: The object who has the active shape key we are going to split
# - optAxis: The world axis which determines which verts go into the "left" and "right" halves
# - newLeftName: Name for the newly split-off left side shape key
# - newRightName: Name for the newly split-off right side shape key
# - (optional) asyncProgressReporting: An object provided by __init__ for asynchronous operation (i.e. in a modal)
def SplitPairActiveShapeKey(obj, optAxis, newLeftName, newRightName, asyncProgressReporting=None):
	originalShapeKeyName = obj.active_shape_key.name
	originalShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(originalShapeKeyName)
	
	if (originalShapeKeyIndex == 0):
		raise Exception("You cannot split the basis shape key")
	
	# Create the two copies
	obj.shape_key_add(name=str(newLeftName), from_mix=True)
	newLeftShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	obj.shape_key_add(name=str(newRightName), from_mix=True)
	newRightShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	
	# Split axis factor
	axis = 0
	if (optAxis == "+X" or optAxis == "-X"):
		axis = 0
	elif (optAxis == "+Y" or optAxis == "-Y"):
		axis = 1
	elif (optAxis == "+Z" or optAxis == "-Z"):
		axis = 2
	axisFlip = 1
	if optAxis[0] == "-":
		axisFlip = -1
	
	# Async progress reporting
	reportAsyncProgress = False
	wm = None
	currentVert = 0
	totalVerts = 0
	if asyncProgressReporting:
		reportAsyncProgress = True
		wm = bpy.context.window_manager
		currentVert = asyncProgressReporting["currentVert"]
		totalVerts = asyncProgressReporting["totalVerts"]
	
	basisShapeKeyVerts = obj.data.shape_keys.key_blocks[0].data
	leftShapeKeyVerts = obj.data.shape_keys.key_blocks[newLeftShapeKeyIndex].data
	rightShapeKeyVerts = obj.data.shape_keys.key_blocks[newRightShapeKeyIndex].data
	
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if (currentVert % 100 == 0): # Only break for the UI thread every 100 verts. I'm not sure how much of a performance hit progress_update() incurs, but there's no need to call it faster than 60Hz.
				wm.progress_update(currentVert)
		
		# The coordinate of the vert on the basis shape key determines whether it is a left (+aXis) or right (-aXis) vert
		axisSplitCoord = 0
		if (axis == 0):
			axisSplitCoord = basisShapeKeyVerts[vert.index].co.x
		elif (axis == 1):
			axisSplitCoord = basisShapeKeyVerts[vert.index].co.y
		elif (axis == 2):
			axisSplitCoord = basisShapeKeyVerts[vert.index].co.z
		axisSplitCoord *= axisFlip
		
		# Neutralize the verts on the +aXis side (left side) for the right shape key
		if (axisSplitCoord < 0):
			leftShapeKeyVerts[vert.index].co = basisShapeKeyVerts[vert.index].co * 1
		# Neutralize the verts on the -aXis side (right side) for the left shape key
		if (axisSplitCoord >= 0):
			rightShapeKeyVerts[vert.index].co = basisShapeKeyVerts[vert.index].co * 1
			
	# Move the two copies in the shape key list to sit after the original shape key
	while (newLeftShapeKeyIndex > originalShapeKeyIndex + 1):
		# Move left copy
		obj.active_shape_key_index = newLeftShapeKeyIndex
		bpy.ops.object.shape_key_move(type="UP")
		# Move right copy (will always be on the tail of the left copy)
		obj.active_shape_key_index = newRightShapeKeyIndex
		bpy.ops.object.shape_key_move(type="UP")
		newLeftShapeKeyIndex -= 1
		newRightShapeKeyIndex -= 1
	
	# Delete original shape key
	obj.active_shape_key_index = originalShapeKeyIndex
	bpy.ops.object.shape_key_remove()
	
	# Update async progress reporting for delta verts processed
	if reportAsyncProgress:
		asyncProgressReporting["currentVert"] = currentVert


### Splits all shape key pairs (ONLY shape keys with names like "MyShapeKeyL+MyShapeKeyR") on the specified object into separate left and right halves
# This method can only run asynchronously with the help of a modal operator
# Params:
# - obj: The object whose shape keys we are going to split
# - axis: The world axis which determines which verts go into the "left" and "right" halves
def SplitAllShapeKeyPairsAsync(obj, axis):
	totalShapeKeys = 0
	toSplitCount = 0
	toSplitBatch = []
	
	# Check all shapekeys for the xyzL+xyzR naming convention and split only those
	# Examples:
	# - "HappyL+HappyR" becomes HappyL and HappyR
	# - "HappyL+UnhappyR" becomes HappyL and UnhappyR (works, but bad names, cannot recombine later)
	# - "Happyl+happyR" becomes "Happyl" and "happyR" (works, but bad names, cannot recombine later)
	for keyBlock in obj.data.shape_keys.key_blocks:
		totalShapeKeys += 1
		
		# Select the shape key
		obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(keyBlock.name)
		
		# Find the new names for the shape key halves
		newNameData = FindShapeKeySplitNames(keyBlock.name)
		newLeftName = newNameData[0]
		newRightName = newNameData[1]
		usesPairNameConvention = newNameData[2]
		
		if (newLeftName != None and newRightName != None and usesPairNameConvention == True):
			toSplitBatch.append([keyBlock.name, newLeftName, newRightName])
			toSplitCount += 1
	
	# Prepare the async work data for the modal operation's async handler
	if toSplitCount > 0:
		print("Preparing to split " + str(toSplitCount) + " of " + str(totalShapeKeys) + " total shape keys")
		
		def opMethod(asyncWorkData):
			splitOp = asyncWorkData["toSplitBatch"][asyncWorkData["currentOp"]]
			obj = asyncWorkData["obj"]
			axis = asyncWorkData["axis"]
			
			print("Splitting shape key \"" + splitOp[0] + "\" into left: \"" + splitOp[1] + "\" and right: \"" + splitOp[2] + "\" on axis: " + str(axis).upper())
			obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(splitOp[0])
			asyncProgressReporting = {
				"currentVert": asyncWorkData["currentVert"],
				"totalVerts": asyncWorkData["totalVerts"],
			}
			SplitPairActiveShapeKey(obj, axis, splitOp[1], splitOp[2], asyncProgressReporting)
			asyncWorkData["currentVert"] = asyncProgressReporting["currentVert"] # Update our tracker for the processed verts count
			
			asyncWorkData["currentOp"] += 1
			if (asyncWorkData["currentOp"] > asyncWorkData["totalOps"] - 1):
				asyncWorkData["_Finished"] = True
				bpy.context.window_manager.progress_end()
			
		asyncWorkData = {
				"_OpMethod": opMethod,
				"_Finished": False,
				
				"obj": obj,
				"axis": axis,
				"toSplitBatch": toSplitBatch,
				"currentOp": 0,
				"totalOps": len(toSplitBatch),
				"currentVert": 0,
				"totalVerts": len(obj.data.vertices) * len(toSplitBatch)
			}
		
		bpy.context.window_manager.progress_begin(0, asyncWorkData["totalVerts"])
		
		return asyncWorkData
	else:
		print("No shape keys matched the paired name convention (e.g. MyKeyL+MyKeyR). Nothing was split.")
		return None


### Given an existing shape key, determines the expected name of the complementary shape key (the L for the R, or the R for the L) and the name of the final shape key if they two were merged
def FindShapeKeyMergeNames(shapeKeyName):
	expectedCompShapeKeyName = None
	mergedShapeKeyName = None
	if shapeKeyName[-1] == "L":
		expectedCompShapeKeyName = shapeKeyName[:-1] + "R"
		mergedShapeKeyName = shapeKeyName + "+" + expectedCompShapeKeyName
	if shapeKeyName[-1] == "R":
		expectedCompShapeKeyName = shapeKeyName[:-1] + "L"
		mergedShapeKeyName = expectedCompShapeKeyName + "+" + shapeKeyName
		
	return [shapeKeyName, expectedCompShapeKeyName, mergedShapeKeyName]


### Merges the specified shape key pair (two shape keys with names like "MyShapeKeyL" and "MyShapeKeyR") on the specified object into a single shape key
# Params:
# - obj: The object who has the two specified shape keys to be merged
# - optAxis: The world axis which determines which verts belong to the "left" and "right" halves of the combined shape key
# - shapeKeyLeftName: Name of the "left" side shape key to be merged
# - shapeKeyRightName: Name of the "right" side shape key to be merged
# - mergedShapeKeyName: Name of the soon-to-be merged shape key
# - (optional) asyncProgressReporting: An object provided by __init__ for asynchronous operation (i.e. in a modal)
def MergeShapeKeyPair(obj, optAxis, shapeKeyLeftName, shapeKeyRightName, mergedShapeKeyName, asyncProgressReporting=None):
	# Find the indices of the left and right shape keys
	leftShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKeyLeftName)
	rightShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKeyRightName)
	
	# Create a new shape key from the basis
	obj.active_shape_key_index = 0
	obj.shape_key_add(name=str(mergedShapeKeyName), from_mix=False)
	newShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	
	# Cherry pick which verts to bring into the new shape key from the -/+ sides of the left and right shape keys pair
	axis = 0
	if (optAxis == "+X" or optAxis == "-X"):
		axis = 0
	elif (optAxis == "+Y" or optAxis == "-Y"):
		axis = 1
	elif (optAxis == "+Z" or optAxis == "-Z"):
		axis = 2
	axisFlip = 1
	if optAxis[0] == "-":
		axisFlip = -1
	
	# Async progress reporting
	reportAsyncProgress = False
	wm = None
	currentVert = 0
	totalVerts = 0
	if asyncProgressReporting:
		reportAsyncProgress = True
		wm = bpy.context.window_manager
		currentVert = asyncProgressReporting["currentVert"]
		totalVerts = asyncProgressReporting["totalVerts"]
	
	basisShapeKeyVerts = obj.data.shape_keys.key_blocks[0].data
	mergedShapeKeyVerts = obj.data.shape_keys.key_blocks[newShapeKeyIndex].data
	leftShapeKeyVerts = obj.data.shape_keys.key_blocks[leftShapeKeyIndex].data
	rightShapeKeyVerts = obj.data.shape_keys.key_blocks[rightShapeKeyIndex].data
	
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if (currentVert % 100 == 0):
				wm.progress_update(currentVert)
		
		axisSplitCoord = 0
		if (axis == 0):
			axisSplitCoord = basisShapeKeyVerts[vert.index].co.x
		elif (axis == 1):
			axisSplitCoord = basisShapeKeyVerts[vert.index].co.y
		elif (axis == 2):
			axisSplitCoord = basisShapeKeyVerts[vert.index].co.z
		axisSplitCoord *= axisFlip
		
		# If the original vert is -aXis (right side), then we pick the flexed vert from the Right shape key
		if (axisSplitCoord < 0):
			mergedShapeKeyVerts[vert.index].co = rightShapeKeyVerts[vert.index].co * 1
		# If the original vert is +aXis (left side), then we pick the flexed vert from the Left shape key
		if (axisSplitCoord >= 0):
			mergedShapeKeyVerts[vert.index].co = leftShapeKeyVerts[vert.index].co * 1
			
	# Move the new merged shape key in the shape key list to sit after the firstmost shape key of the pair in the shape key list
	originalShapeKeyIndex = min(leftShapeKeyIndex, rightShapeKeyIndex)
	while (newShapeKeyIndex > originalShapeKeyIndex + 1):
		# Move left copy
		obj.active_shape_key_index = newShapeKeyIndex
		bpy.ops.object.shape_key_move(type="UP")
		newShapeKeyIndex -= 1
	
	# Delete the left and right shape keys
	obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(shapeKeyLeftName)
	bpy.ops.object.shape_key_remove()
	obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(shapeKeyRightName)
	bpy.ops.object.shape_key_remove()
	
	# Reselect merged shape key
	obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(mergedShapeKeyName)
	
	# Update async progress reporting for delta verts processed
	if reportAsyncProgress:
		asyncProgressReporting["currentVert"] = currentVert


### Merges the active shape key with its complementary opposite side shape key (L with R, R with L) if such complementary key exists
# Params:
# - obj: The object who has the active shape key we are going to merge
# - optAxis: The world axis which determines which verts belong to the "left" and "right" halves of the combined shape key
# - (optional) asyncProgressReporting: An object provided by __init__ for asynchronous operation (i.e. in a modal)
def MergePairActiveShapeKey(obj, optAxis, asyncProgressReporting=None):
	selectedShapeKeyName = obj.active_shape_key.name
	originalShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(selectedShapeKeyName)
	
	if (originalShapeKeyIndex == 0):
		raise Exception("You cannot merge the basis shape key")
	
	mergeNames = FindShapeKeyMergeNames(selectedShapeKeyName)
	if (mergeNames[1] == None):
		raise Exception("The selected shape key does not follow the L/R naming convention. This operation only works on shape keys that end in L or R.")
	expectedCompShapeKeyName = mergeNames[1]
	mergedShapeKeyName = mergeNames[2]
	
	# Find a complementary shape key by name
	matchedShapeKeyName = None
	for keyBlock in obj.data.shape_keys.key_blocks:
		if keyBlock.name == expectedCompShapeKeyName:
			matchedShapeKeyName = keyBlock.name
			break
	
	if matchedShapeKeyName == None:
		raise Exception("No complementary shape key \"" + str(expectedCompShapeKeyName) + "\" was found for the selected shape key \"" + str(selectedShapeKeyName) + "\". No merge can occur.")
	
	# Delegate to main merge op
	if (selectedShapeKeyName[-1] == "L"):
		MergeShapeKeyPair(obj, optAxis, selectedShapeKeyName, expectedCompShapeKeyName, mergedShapeKeyName, asyncProgressReporting)
	else:
		MergeShapeKeyPair(obj, optAxis, expectedCompShapeKeyName, selectedShapeKeyName, mergedShapeKeyName, asyncProgressReporting)


### Merges all the valid paired shape keys (pairs like "MyShapeKeyL" and "MyShapeKeyR") on the specified object into combined shape keys
# This method can only run asynchronously with the help of a modal operator
# Params:
# - obj: The object who has the active shape key we are going to merge
# - axis: The world axis which determines which verts belong to the "left" and "right" halves of the combined shape key
def MergeAllShapeKeyPairsAsync(obj, axis):
	totalShapeKeys = 0
	toMergeCount = 0
	toMergeBatch = []
	
	# Process all shape keys that have an xyzL/xyzR naming convention AND have a complementary shape key to merge with
	# Example: "HappyL" and "HappyR" becomes "HappyL+HappyR"
	exclude = {}
	for keyBlock in obj.data.shape_keys.key_blocks:
		totalShapeKeys += 1		
		
		# Skip already matched shape keys
		if keyBlock.name in exclude:
			continue
		
		# Check if there's a complementary shape key for this one
		mergeNames = FindShapeKeyMergeNames(keyBlock.name)
		if (mergeNames[1] == None):
			continue
		expectedCompShapeKeyName = mergeNames[1]
		mergedShapeKeyName = mergeNames[2]
		
		matched = False
		for checkKeyBlock in obj.data.shape_keys.key_blocks:
			if checkKeyBlock.name in exclude: # Skip already matched shape keys
				continue
			if (checkKeyBlock != keyBlock and checkKeyBlock.name == expectedCompShapeKeyName):
				matched = True
				break
		
		# Mark an op for the matched pair
		if matched:
			exclude[keyBlock.name] = True
			exclude[expectedCompShapeKeyName] = True
			toMergeCount += 2 # This counts individual shape keys, not pairs
			if (keyBlock.name[-1] == "L"):
				toMergeBatch.append([keyBlock.name, expectedCompShapeKeyName, mergedShapeKeyName])
			else:
				toMergeBatch.append([expectedCompShapeKeyName, keyBlock.name, mergedShapeKeyName])
	
	# Prepare the async work data for the modal operation's async handler
	if toMergeCount > 0:
		print("Preparing to merge " + str(toMergeCount) + " shape keys (" + str(toMergeCount / 2) + " pairs) of " + str(totalShapeKeys) + " total shape keys")
		
		def opMethod(asyncWorkData):
			mergeOp = asyncWorkData["toMergeBatch"][asyncWorkData["currentOp"]]
			obj = asyncWorkData["obj"]
			axis = asyncWorkData["axis"]
			
			print("Merging left shape key: \"" + mergeOp[0] + "\" and right shape key: \"" + mergeOp[1] + "\" into merged: \"" + mergeOp[2] + "\" on axis: " + str(axis).upper())
			asyncProgressReporting = {
				"currentVert": asyncWorkData["currentVert"],
				"totalVerts": asyncWorkData["totalVerts"],
			}
			MergeShapeKeyPair(obj, axis, mergeOp[0], mergeOp[1], mergeOp[2], asyncProgressReporting)
			asyncWorkData["currentVert"] = asyncProgressReporting["currentVert"] # Update our tracker for the processed verts count
			
			asyncWorkData["currentOp"] += 1
			if (asyncWorkData["currentOp"] > asyncWorkData["totalOps"] - 1):
				asyncWorkData["_Finished"] = True
				bpy.context.window_manager.progress_end()
			
		asyncWorkData = {
				"_OpMethod": opMethod,
				"_Finished": False,
				
				"obj": obj,
				"axis": axis,
				"toMergeBatch": toMergeBatch,
				"currentOp": 0,
				"totalOps": len(toMergeBatch),
				"currentVert": 0,
				"totalVerts": len(obj.data.vertices) * len(toMergeBatch)
			}
		
		bpy.context.window_manager.progress_begin(0, asyncWorkData["totalVerts"])
		
		return asyncWorkData
	else:
		print("No shape key pairs matched the L/R name convention (e.g. MyKeyL and MyKeyR). Nothing was merged.")
		return None


#
#====================================================================================================
#    Arbitrary Split/Merge
#====================================================================================================
#

### Merges the two specified shape keys on the specified object into a single shape key, using various blend modes
# Params:
# - obj: The object who has the two specified shape keys to be merged
# - shapeKey1Name: Name of the shape key to use as the lower layer in blending
# - shapeKey2Name: Name of the shape key to use as the upper layer in blending
# - destination: Either 1 (output to shape key 1), 2 (output to shape key 2), or a string (name of a new shape key to create)
# - blendMode: Name of the blend mode
# - (optional) blendModeParams: Dictionary of parameters specific to the chosen blend mode
# - (optional) vertexFilterParams: Dictionary of parameters for vertex filtering. If None, vertex filtering is disabled.
# - (optional) delete1OnFinish: If true, shape key 1 will be deleted after the merge is complete
# - (optional) delete2OnFinish: If true, shape key 2 will be deleted after the merge is complete
# - (optional) asyncProgressReporting: An object provided by __init__ for asynchronous operation (i.e. in a modal)
def MergeAndBlendShapeKeys(obj, shapeKey1Name, shapeKey2Name, destination, blendMode, blendModeParams=None, vertexFilterParams=None, delete1OnFinish=False, delete2OnFinish=False, asyncProgressReporting=None):
	# New shape key from the basis (if we are outputting to a new shape key)
	newShapeKeyIndex = None
	if (isinstance(destination, str)):
		obj.active_shape_key_index = 0
		obj.shape_key_add(name=str(destination), from_mix=False)
		newShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	
	# Find the indices of the source shape keys
	lowerShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKey1Name)
	upperShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKey2Name)
	
	basisShapeKeyVerts = obj.data.shape_keys.key_blocks[0].data
	lowerShapeKeyVerts = obj.data.shape_keys.key_blocks[lowerShapeKeyIndex].data
	upperShapeKeyVerts = obj.data.shape_keys.key_blocks[upperShapeKeyIndex].data
	newShapeKeyVerts = None
	if (newShapeKeyIndex != None):
		newShapeKeyVerts = obj.data.shape_keys.key_blocks[newShapeKeyIndex].data
	
	destinationShapeKeyName = None
	destinationShapeKeyVerts = None
	if (destination == 1):
		destinationShapeKeyName = shapeKey1Name
		destinationShapeKeyVerts = lowerShapeKeyVerts
	elif (destination == 2):
		destinationShapeKeyName = shapeKey2Name
		destinationShapeKeyVerts = upperShapeKeyVerts
	else:
		destinationShapeKeyName = destination
		destinationShapeKeyVerts = newShapeKeyVerts
	
	
	### Blend-mode-specific params
	blendModeLerp_Factor = None
	if (blendMode == "lerp"):
		blendModeLerp_Factor = min(max(0, blendModeParams["Factor"]), 1)
	
	
	### Vertex filter kernel
	vertexFilterKernel = None
	doVertexFiltering = False
	if (vertexFilterParams != None):
		doVertexFiltering = True
		vertexFilterKernel = CreateVertexFilterKernel(vertexFilterParams)
		
	
	# Async progress reporting
	reportAsyncProgress = False
	wm = None
	currentVert = 0
	totalVerts = 0
	if asyncProgressReporting:
		reportAsyncProgress = True
		wm = bpy.context.window_manager
		currentVert = asyncProgressReporting["currentVert"]
		totalVerts = asyncProgressReporting["totalVerts"]
	
	### Iterate all the verts and combine the deltas as per the blend mode
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if (currentVert % 100 == 0):
				wm.progress_update(currentVert)
		
		# Unfortunately, bpy does not expose relative position of each vert, so we have to calculate the deltas ourself
		basePos = basisShapeKeyVerts[vert.index].co
		lowerDelta = lowerShapeKeyVerts[vert.index].co - basePos
		upperDelta = upperShapeKeyVerts[vert.index].co - basePos
		
		# Filter the upper vert if vertex filtering is enabled
		vertPassesFilter = True # RED verts are True, BLACK verts are False.
		if (doVertexFiltering):
			vgIndices = [vg.group for vg in vert.groups]
			vertPassesFilter = vertexFilterKernel(vgIndices, upperDelta)
		
		### Blend the upper shape key's delta with the lower shape key's delta
		if (vertPassesFilter): # We only incorporate RED verts into combined shape key
			newDelta = None
			
			# Additive
			if (blendMode == "add"):
				newDelta = lowerDelta + upperDelta
			
			# Subtractive
			elif (blendMode == "subtract"):
				newDelta = lowerDelta - upperDelta
			
			# Multiply
			elif (blendMode == "multiply"):
				newDelta = lowerDelta * upperDelta
			
			# Divide
			elif (blendMode == "divide"):
				newDelta = lowerDelta * upperDelta
				
			# Overwrite
			elif (blendMode == "over"):
				newDelta = upperDelta
				
			# Lerp
			elif (blendMode == "lerp"):
				newDelta = lowerDelta.lerp(upperDelta, blendModeLerp_Factor)
			
			# Update the destination shape key
			destinationShapeKeyVerts[vert.index].co = basePos + newDelta
		
	# If outputting to a new shape key, move the new merged shape key in the shape key list to sit after the upper shape key
	if (newShapeKeyIndex != None):
		while (newShapeKeyIndex > upperShapeKeyIndex + 1):
			obj.active_shape_key_index = newShapeKeyIndex
			bpy.ops.object.shape_key_move(type="UP")
			newShapeKeyIndex -= 1
	
	# Delete the source shape keys if desired
	if (delete1OnFinish):
		obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(shapeKey1Name)
		bpy.ops.object.shape_key_remove()
	if (delete2OnFinish):
		obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(shapeKey2Name)
		bpy.ops.object.shape_key_remove()
	
	# Make the destination shape key active
	obj.active_shape_key_index = obj.data.shape_keys.key_blocks.keys().index(destinationShapeKeyName)
	
	# Update async progress reporting for delta verts processed
	if reportAsyncProgress:
		asyncProgressReporting["currentVert"] = currentVert


### Splits off a new shape key from the active shape key, using the Vertex Filter to determine which deltas go to which shape key
# Params:
# - obj: The object who has the two specified shape keys to be merged
# - newShapeKeyName: Name of to-be-created new shape key
# - mode: Name of the split mode to use
# - vertexFilterParams: Dictionary of parameters for vertex filtering
# - (optional) asyncProgressReporting: An object provided by __init__ for asynchronous operation (i.e. in a modal)
def SplitFilterActiveShapeKey(obj, newShapeKeyName, mode, vertexFilterParams, asyncProgressReporting=None):
	if (vertexFilterParams == None):
		raise Exception("Vertex filter parameters must be specified.")
		
	sourceShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(obj.active_shape_key.name)
	
	# New shape key from the basis
	obj.active_shape_key_index = 0
	obj.shape_key_add(name=str(newShapeKeyName), from_mix=False)
	newShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	
	basisShapeKeyVerts = obj.data.shape_keys.key_blocks[0].data
	sourceShapeKeyVerts = obj.data.shape_keys.key_blocks[sourceShapeKeyIndex].data
	newShapeKeyVerts = obj.data.shape_keys.key_blocks[newShapeKeyIndex].data
	
	# Vertex filter kernel
	vertexFilterKernel = CreateVertexFilterKernel(vertexFilterParams)
	
	# Async progress reporting
	reportAsyncProgress = False
	wm = None
	currentVert = 0
	totalVerts = 0
	if asyncProgressReporting:
		reportAsyncProgress = True
		wm = bpy.context.window_manager
		currentVert = asyncProgressReporting["currentVert"]
		totalVerts = asyncProgressReporting["totalVerts"]
	
	### Update the verts of all the involved shape keys
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if (currentVert % 100 == 0):
				wm.progress_update(currentVert)
		
		# Unfortunately, bpy does not expose relative position of each vert, so we have to calculate the deltas ourself
		basePos = basisShapeKeyVerts[vert.index].co
		sourcePos = sourceShapeKeyVerts[vert.index].co
		sourceDelta = sourcePos - basePos
		
		# Filter the vertex
		vgIndices = [vg.group for vg in vert.groups]
		vertPassesFilter = vertexFilterKernel(vgIndices, sourceDelta) # RED verts are True, BLACK verts are False.
		
		### Change shape key verts depending on the operation mode
		# RED deltas make it into the new shape key. BLACK deltas do not (those verts revert to their basis pos defined in the basis shape key).
		if (vertPassesFilter):
			if (mode == "copy"):
				# Copy delta to new shape key and leave the original shape key unchanged
				newShapeKeyVerts[vert.index].co = sourcePos * 1
			
			elif (mode == "move"):
				# Copy delta to new shape key and neutralize the delta in the original shape key
				newShapeKeyVerts[vert.index].co = sourcePos * 1
				sourceShapeKeyVerts[vert.index].co = basePos * 1
	
	# Make the newly created shape key active
	obj.active_shape_key_index = newShapeKeyIndex
	# And move it to sit after original shape key
	while (newShapeKeyIndex > sourceShapeKeyIndex + 1):
		# Move left copy
		obj.active_shape_key_index = newShapeKeyIndex
		bpy.ops.object.shape_key_move(type="UP")
		newShapeKeyIndex -= 1
	
	# Update async progress reporting for delta verts processed
	if reportAsyncProgress:
		asyncProgressReporting["currentVert"] = currentVert

