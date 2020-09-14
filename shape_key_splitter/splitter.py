import bpy

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
			raise Exception("Shape key \"" + originalShapeKeyName + "\"appears to use pair name convention (e.g. MyKeyL+MyKeyR), but it does not both the L and R terminators in the name.")
	else:
		newLeftName = originalShapeKeyName + "L"
		newRightName = originalShapeKeyName + "R"
		usesPairNameConvention = False
	
	return [newLeftName, newRightName, usesPairNameConvention]

def SplitSelectedShapeKey(obj, optAxis, newLeftName, newRightName, asyncProgressReporting=None):
	originalShapeKeyName = obj.active_shape_key.name
	originalShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(originalShapeKeyName)
	
	if (originalShapeKeyIndex == 0):
		raise Exception("You cannot split the basis shape key")
	
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
	
	# Set the shape key envelope to 100%
	obj.active_shape_key.value = obj.active_shape_key.slider_max
	
	# Create the two copies
	obj.shape_key_add(name=str(newLeftName), from_mix=True)
	newLeftShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	obj.shape_key_add(name=str(newRightName), from_mix=True)
	newRightShapeKeyIndex = len(obj.data.shape_keys.key_blocks) - 1
	
	# Modify shape key copies
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
	
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if currentVert % 100: # Only update every 100 verts. I'm not sure how much of a performance hit progress_update() incurs, but there's no need to call it faster than 60Hz.
				wm.progress_update(currentVert)
	
		basisShapeKeyVerts = obj.data.shape_keys.key_blocks[0].data
		leftShapeKeyVerts = obj.data.shape_keys.key_blocks[newLeftShapeKeyIndex].data
		rightShapeKeyVerts = obj.data.shape_keys.key_blocks[newRightShapeKeyIndex].data
		
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
			leftShapeKeyVerts[vert.index].co.x = basisShapeKeyVerts[vert.index].co.x
			leftShapeKeyVerts[vert.index].co.y = basisShapeKeyVerts[vert.index].co.y
			leftShapeKeyVerts[vert.index].co.z = basisShapeKeyVerts[vert.index].co.z
		# Neutralize the verts on the -aXis side (right side) for the left shape key
		if (axisSplitCoord >= 0):
			rightShapeKeyVerts[vert.index].co.x = basisShapeKeyVerts[vert.index].co.x
			rightShapeKeyVerts[vert.index].co.y = basisShapeKeyVerts[vert.index].co.y
			rightShapeKeyVerts[vert.index].co.z = basisShapeKeyVerts[vert.index].co.z
			
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

def SplitAllShapeKeyPairsAsync(obj, axis):
	totalShapeKeys = 0
	toSplitCount = 0
	toSplitBatch = []
	
	# Check all shapekeys for the xyzL+xyzR naming convention and split only those
	#     Examples:
	#     "HappyL+HappyR" becomes HappyL and HappyR
	#     "HappyL+UnhappyR" becomes HappyL and UnhappyR (works, but bad names, cannot recombine later)
	#     "Happyl+happyR" becomes "Happyl" and "happyR" (works, but bad names, cannot recombine later)
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
			SplitSelectedShapeKey(obj, axis, splitOp[1], splitOp[2], asyncProgressReporting)
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


def MergeShapeKeys(obj, optAxis, shapeKeyLeftName, shapeKeyRightName, mergedShapeKeyName, asyncProgressReporting=None):
	# Find the indices of the left and right shape keys
	leftShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKeyLeftName)
	rightShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(shapeKeyRightName)
	
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
	
	# Set the shape key envelope to 100%
	obj.active_shape_key.value = obj.active_shape_key.slider_max
	
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
	
	for vert in obj.data.vertices:
		if reportAsyncProgress:
			currentVert += 1
			if currentVert % 100:
				wm.progress_update(currentVert)
	
		basisShapeKeyVerts = obj.data.shape_keys.key_blocks[0].data
		mergedShapeKeyVerts = obj.data.shape_keys.key_blocks[newShapeKeyIndex].data
		leftShapeKeyVerts = obj.data.shape_keys.key_blocks[leftShapeKeyIndex].data
		rightShapeKeyVerts = obj.data.shape_keys.key_blocks[rightShapeKeyIndex].data
		
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
			mergedShapeKeyVerts[vert.index].co.x = rightShapeKeyVerts[vert.index].co.x
			mergedShapeKeyVerts[vert.index].co.y = rightShapeKeyVerts[vert.index].co.y
			mergedShapeKeyVerts[vert.index].co.z = rightShapeKeyVerts[vert.index].co.z
		# If the original vert is +aXis (left side), then we pick the flexed vert from the Left shape key
		if (axisSplitCoord >= 0):
			mergedShapeKeyVerts[vert.index].co.x = leftShapeKeyVerts[vert.index].co.x
			mergedShapeKeyVerts[vert.index].co.y = leftShapeKeyVerts[vert.index].co.y
			mergedShapeKeyVerts[vert.index].co.z = leftShapeKeyVerts[vert.index].co.z
			
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

def MergeSelectedShapeKey(obj, optAxis, asyncProgressReporting=None):
	selectedShapeKeyName = obj.active_shape_key.name
	originalShapeKeyIndex = obj.data.shape_keys.key_blocks.keys().index(selectedShapeKeyName)
	
	if (originalShapeKeyIndex == 0):
		raise Exception("You cannot merge the basis shape key")
	
	mergeNames = FindShapeKeyMergeNames(selectedShapeKeyName)
	if mergeNames == None:
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
		raise Exception("No complementary shape key \"" + expectedCompShapeKeyName + "\" was found for the selected shape key \"" + selectedShapeKeyName + "\". No merge can occur.")
	
	# Delegate to main merge op
	if (selectedShapeKeyName[-1] == "L"):
		MergeShapeKeys(obj, optAxis, selectedShapeKeyName, expectedCompShapeKeyName, mergedShapeKeyName, asyncProgressReporting)
	else:
		MergeShapeKeys(obj, optAxis, expectedCompShapeKeyName, selectedShapeKeyName, mergedShapeKeyName, asyncProgressReporting)
	
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
		if mergeNames == None:
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
			MergeShapeKeys(obj, axis, mergeOp[0], mergeOp[1], mergeOp[2], asyncProgressReporting)
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
