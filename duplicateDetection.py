# -*- coding: utf-8 -*-
"""
Determining Duplicate images

http://blog.iconfinder.com/detecting-duplicate-images-using-python/
"""

import os
from PIL import Image

def phash(image, hash_size=8, highfreq_factor=4):
    """
    from: import imagehash
    Perceptual Hash computation.
    Implementation follows http://www.hackerfactor.com/blog/index.php?/archives/432-Looks-Like-It.html
    @image must be a PIL instance.
	 """
    import numpy
    if hash_size < 0:
        raise ValueError("Hash size must be positive")
    import scipy.fftpack
    img_size = hash_size * highfreq_factor
    image = image.convert("L").resize((img_size, img_size), Image.ANTIALIAS)
    pixels = numpy.array(image.getdata(), dtype=numpy.float).reshape((img_size, img_size))
    dct = scipy.fftpack.dct(scipy.fftpack.dct(pixels, axis=0), axis=1)
    dctlowfreq = dct[:hash_size, :hash_size]
    med = numpy.median(dctlowfreq)
    diff = dctlowfreq > med
    return diff


def getImageHashesPrevious():
    # Get Images
    filesInDirectory  = os.listdir()
    imagesInDirectory = [filename for filename in filesInDirectory if filename[-4:] == '.jpg']

    # Declare Bookkeeping Structure
    imageHashDic  = {}
    imageHashList = []

    # First Image
    imageName = imagesInDirectory[0]
    imageFile = Image.open(imagesInDirectory[0])
    hashArray = phash(imageFile,hash_size=16, highfreq_factor=8)
    imageHashList.append(hashArray)
    imageHashDic[imageName] = hashArray

    # Cycle through every image
    for imageName in imagesInDirectory[1:]:
        print(imageName)
        imageFile = Image.open(imageName)
        hashArray = phash(imageFile,hash_size=16, highfreq_factor=8)
        duplicate = False
        while not duplicate:
            for otherFile in imageHashDic.keys():
                otherHash = imageHashDic[otherFile]
                diff = (otherHash ^ hashArray).sum()
                # Possible Duplicate
                if diff < 30:
                    print(imageName, otherFile, diff)
                    duplicate = True
        # Actual duplicate
        if duplicate:
            os.remove(imageName)
        # Not duplicate
        if not duplicate:
            imageHashDic[imageName] = hashArray
            imageHashList.append(hashArray)

def checkDuplicate(hashArray, imageHashDic, sensitivity = 30):
    '''  '''
    duplicate = False
    while not duplicate:
        for otherFile in imageHashDic.keys():
            otherHash = imageHashDic[otherFile]
            diff = (otherHash ^ hashArray).sum()
            # Possible Duplicate
            if diff < sensitivity:
                duplicate = True
    return duplicate

def getSelfImageHashes(instagram):
    ''' returns dictionary of pk:hash of all posts '''
    import requests
    from io import BytesIO
    selfImageHashDic = {}  # Timestamp:HashArray
    selfFeedJson = instagram.getTotalSelfUserFeed()
    for post in selfFeedJson:
        postImageURL   = post['image_versions2']['candidates'][-1]['url']
        imageResponse  = requests.get(postImageURL)
        imageFile      = Image.open(BytesIO(imageResponse.content))
        imageHashArray = phash(imageFile, hash_size=16, highfreq_factor=8)
        selfImageHashDic[post['pk']] = imageHashArray
    return selfImageHashDic

def checkPrevPosted(selfImageHashDic, post, sensitivity=30):
    ''' returns pk of duplicate post '''
    from PIL import Image
    import requests
    from io import BytesIO
    postImageURL   = post['image_versions2']['candidates'][-1]['url']
    imageResponse  = requests.get(postImageURL)
    imageFile      = Image.open(BytesIO(imageResponse.content))
    imageHashArray = phash(imageFile, hash_size=16, highfreq_factor=8)
    checkedImages = 0
    duplicate = False
    for otherFile in selfImageHashDic.keys():
        otherHashArray = selfImageHashDic[otherFile]
        diff = (otherHashArray ^ imageHashArray).sum()
        # Possible Duplicate
        if diff < sensitivity:
            duplicate = otherFile
        checkedImages = checkedImages + 1
    print("checkedImages: ", checkedImages)
    return duplicate




