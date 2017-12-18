# -*- coding: utf-8 -*-
"""
Instagram Competition Automation
@author: RCCG

pip install git+https://github.com/LevPasha/Instagram-API-python

TODOs:
    [ ]  create log, make timing dependent on log since last action was taken, log account name to allow expansion for multiple accounts later on.
    [ ]  split on "bonus" "optional" "double/extra chance" etc to find repost required versus bonus
    [ ]  recognize: pick a number between

    [ ]  implement wait list for posts to be confirmed to allow continuous running
    [ ]  implement recognizing deadlines
    [ ]  implement cross check for "today" and time < 24 hours
    [ ]  implement get people tags from previous comments
    [ ]  count 404 429 errors
    [ ]  implement check if commented before
    [ ]  implement in indivudual comments
    [ ]  implement check own feed instead
    [ ]  implement new/viewed parameter
    [ ]  implement unfollow after no contest in X months
    [ ]  implement after reaching old time
    [ ]  delete old reposts
    [ ]  implement post real content: if not posted in a while, post content from a folder, move image to archive
    [ ]  implement check for repost / tag to count towards contest count
    [ ]  implement blocked account List
    [ ]  outlay positive / negative dictionaries
    [ ]  implement google translate of foreign languages
    [ ]  differentiate between additional/extra repost vs required
    [ ]  implement check after 7 days for counting people entered
    [ ]  implement keeping track of other tags in contests entered/won/etc.
    [ ]  implement keeping track of failed follow finding
    [ ]  recogniyze: 'shoe size'
    [ ]  reduce checks for to 1: for Followers (usernames), Followings (ID)
    [ ]  maximum number of tags

Features:
    [x]  Uses Follow List as
    [x]  Given Names, searches for relevant users and follows them
    [x]  Given Tags, adds the Tag feeds to search for contests
    [x]  Detects contests based on key word values
    [x]  Detects if contest requires: Like, Comment, Tags, Repost
    [x]  Allows for Liking, Commenting, Tagging, Reposting
    [x]  Checks if already entered by checking for like
    [x]  Prevents double posts via phash check of previously posted

    [x]  implement follow users tagged in post
    [x]  implement get users to follow
    [x]  breaks loop on liked item (Warning, can create gaps)
    [x]  implement minimum followers for entering contest
    [x]  implement own followers retrieval for > 200
    [x]  implement check if already reposted using picture hash comparison
    [x]  implement only items newer than X retrieved
    [x]  implement retrieve more items
    [x]  implement help function

    [x]  After following checks users again to allow for loops


Maybe Future:
    searching of bios
    searching of facebook pages
"""


import InstagramAPI_local as insta
#from InstagramAPI import InstagramAPI as insta
import pandas as pd
import random
import datetime
import time
import urllib.request
import itertools
from duplicateDetection import checkPrevPosted, getSelfImageHashes
print("Successfully loaded all modules")


# Account Details
accName = ""
accPw   = ""
primaryAccount = ""
# Settings
validLanguageList = ["en", "de"]

# Book keeping Parameters
filenames      = ['contests.csv', 'stats.csv']
testing        =     2  # 2=check, 1=no-repost, 0=automated.
slowdownFactor =     5  # time between cycles: 5 min * slowdown Factor
# Run parameters
maxLength      =  1000  # Maximum # of  characters for display
minScore       =     3  # Minimum # of  points     to enter  (contest score)
maxDays        =     7  # Maximum # of  days old   to check for contest
# Prevent Fake Accounts
minFollowers   =   400  # Minimum # of  followers  for search
minFollowing   =    10  # Minimum # of  followed   for search
minPosts       =     5  # Minimum # of  posts of an account to enter to prevent spam
# Prevent Banning
#maxToLike     =   500
# Commenting Parameters
baseComment1   = ['yes', 'perfect', 'awesome', 'fantastic', 'done', 'love it', 'amazing'] #'wish me luck', '#win hopefully', 'youre the best'
baseComment2   = ['!', ' ❤️', ' ', ' !', ' <3']
baseComments   = [word+ending for word,ending in itertools.product(baseComment1, baseComment2)]
minComments    =     3  # Minimum # of  comments   before taking most commented answer
maxTagsCopy    =     5  # Maximum # of  tags       to copy from post
minLength      =    80  # Minimum # of  characters in alphanumeric words to check
minTimePassed  = 72*60  # Minimum # of  minutes    before checking followers again
#inactiveMonths =  6  # unfollow if not posted in X months

# New to add
searchUserList = []  # 'Thomas Pink'
searchTagList  = ['#verlosung','#giveaway']#, '#freebies', '#nopurchasenecessary', '#chancetowin'] # , 'freegift'
#################################################################
print("Successfully loaded all parameters")

# Functions
contestCols = [ # Contest History
                'username',         # User Name (str)
                'userPk',           # User ID   (num)
                'timestamp',        # Post Time (num)
                'postId',           # Post ID   (str)
                'postPk',           # Post ???  (num)
                'caption',          # Post Description (str)
                # Action Taken
                'commented',        # WHAT      (str)
                #'tagCount',         # How Many  (int)
                #'contestScore',     # Con. Sore (int)
                'commentNumber',    # WHEN      (int)
                'commentTimestamp', # Timestamp (int)
                'liked',            # Liked?    (bool)
                'shared',           # Reposted? (bool)
                'shareCaption'      # Caption   (str)
                # Review / Analysis Columns
                #'hitScore'          # 0=Perfect, 1=Mistake, 2=False Positive, 3=Positive False
                #'hitNote'           # What went wrong? (str)
                #'trueTagCount'      # How many (int)
                #'trueLiked'         # Should have Liked? (bool)
                #'trueShared'        # Should have Shared? (bool)
                #'trueCommented'     # Should have commented? (str)
                #'trueWon'           # Did I win? (bool)
                #'totalEntered'      # How many entered contest? (int)
              ]
statCols    = [ # Bot Statistics
                'timestamp',        # Timestamp (num)
                'entered',          # Contests Entered (num)
                'searched',         # Posts Searched (num)
                'newFollows',       # Username List (list)
                'searchUserIdList',  # Userid   List (list)
                'searchHashTagList'  # Tags List (list)
              ]



def loadSettings(filename, headers):
    try:
        ret = pd.DataFrame.from_csv(filename, encoding = 'utf-16')
        # New Columns Added: Append new, Insert NaN, Sort cols
        if len(ret.keys()) < len(headers) and set(headers) != set(ret.keys()):
            newCols = list(set(headers)-set(ret.keys()))
            import numpy as np
            for column in newCols:
                ret[column] = np.nan  # Append & Insert dummmy value
            ret = ret[headers]  # Sort again
        # Unmatched Columns: Create new, Rename old
        elif set(headers) != set(ret.keys()):
            ret = pd.DataFrame(columns=headers)
            import os;  os.rename(filename, filename[:-4]+"_"+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+".csv")
            print("Weird columns. Created new. Renamed Old.")
        # All clear.
        else: print("Successfully loaded %s" %filename)
    # Something went very wrong
    except:
        ret = pd.DataFrame(columns=headers)
        print("Failed loading %s. Created new. Renamed Old." %filename)
        import os;  os.rename(filename, filename[:-4]+"_"+datetime.datetime.now().strftime('%Y%m%d_%H%M%S')+".csv")
    return ret

def saveSettings(filename, dataframe):
    dataframe.to_csv(filename, encoding='utf-16')

def getBaseComment(baseComments):
    return baseComments[random.randint(0,len(baseComments)-1)]
#################################################################

# Analyzing Post
def getPostTags(post):
    ''' returns primary, and all tags in post '''
    import re
    item = post['caption']
    primaryTag  = re.findall('(?<=Tag ).\S*',   item['text'], flags=re.IGNORECASE)
    allTags     = re.findall('([#@][\w_+#@]*)', item['text'])
    print(primaryTag, allTags)
    return primaryTag, allTags

def removeTags(text):
    ''' removes all hash- and people tags '''
    import re
    return re.sub(r'\s[#@][\w#.]*','',text)

def getPlainText(text):
    ''' Only alphanumeric words '''
    return " ".join([word for word in text.split(" ") if word.isalnum()==True])

def checkMinLength(caption):
    wordCaption = getPlainText(caption)
    if len(wordCaption) < minLength:
        print("  Caption Length: ", len(wordCaption))
        return False
    else: return True

def verifyUser(instagram, userPk, minPosts, minFollower, minFollowing):
    ''' verify user meets minimum required: posts, followers, followings '''
    attempt = 1  # Retry to succeed
    while not instagram.getUsernameInfo(userPk): time.sleep(60*attempt); attempt+=1
    userInfoDic = instagram.LastJson['user']
    postCountOK       = (userInfoDic['media_count']     > minPosts)
    followerCountOK   = (userInfoDic['follower_count']  > minFollower)
    followingCountOK  = (userInfoDic['following_count'] > minFollowing)
    if postCountOK and followerCountOK and followingCountOK: return True
    else: return False

def checkPhoneNumber(item):
    ''' search for all major phone number types, prints phone number '''
    import re
    if re.search(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})', item) is not None:
        print("phone number recognized", re.search(r'(\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}|\(\d{3}\)\s*\d{3}[-\.\s]??\d{4}|\d{3}[-\.\s]??\d{4})', item).group(1))
        return True
    else: return False

def checkLanguage(text):
    ''' check if item is in the english language, prints if foreign '''
    global validLanguageList
    from langdetect import detect
    wordCaption = getPlainText(text)  # Only alpha numerical words should count
    if detect(wordCaption) not in validLanguageList:
        print("  foreign:  ", detect(wordCaption));
        return False
    else: return True

def translateToEnglish(text):
    ''' uses google translate to translate post to english '''
    from langdetect import detect
    wordCaption = getPlainText(text)  # Only alpha numerical words should count
    if detect(wordCaption) != "en":
        from googletrans import Translator  # pip install googletrans
        translator = Translator()
        translation = None
        while not translation: 
            try:    translation = translator.translate(wordCaption, dest='en').text
            except: randomSleepTimer(1,3)
        return translation
    else:
        return text

def checkForContest(post, minScore):
    ''' checks post for contest by keywords below rules below rules on keywords '''
    item = post['caption']['text'].lower()
    contestScore = 0
    allTags = []
    # Keywords
    positives  = {'giveaway':2, 'give away':3, 'giving away':3, 'free':2, 'no purchase':4, #'nopurchase':2,
                  'contest':1, 'win':1, 'comment':1, 'chance':2, 'like':1, 'tag':1, 'friend':1, 'gift package':2}
    negatives  = {
                  'open house':1, 'raffle':3,
                  'snap':1, 'best':1, 'class':1, 'go to':1,   #'lucky customer':1, 'your address':1, 'results':1,
                  'casino':1, 'stay tuned':3,
                  # Avoid good causes to spam
                  'fundraiser':6, 'fundraising':6, 'donate':1, 'donations':4,
                  'raredisease':6,
                  # useless stuff
                  '#slime':8, ' slime':8, 'dragon ball':6, 'csgo':6, 'stickers':4, 'pokemon':6,
                  'weed':8, # gets you banned
                  'photoshoot':4, 'ebook':8, 'e-book':8, 'mommy':6, 'mother':6,
                  'service desired':9,
                  # require to comment
                  'tell us':2, 'post a photo':6, 'post a pic':5, 'best photo':6, 'answer this question':6,
                  'tell us why':7, 'tell me why':7,
                  'screenshot':2, 'your order':3, 'every order':3,
                  # location based
                  "we're at":4, '#roadshow':8, 'find us':6, 'come down to':8, 'stop in':1, 'get down here':7, 'come out to':9,
                  # signups....
                  'sign up':2, 'check it out':2, 'message me':2, 'register':2, 'free event':2, #'winner announced':2,
                  'must be new to':12, 'fill out':6,
                  # Live shows
                  'watch us live':10, 'tune in live':10, ' live at ':9,
                  # Facebook and Websites
                  'www.':1, '.com':1, 'http://':3, 'https://':3, '.net':3,
                  'facebook':3,  'facebook page':3, 'fb page':3, 'facebook.com':3, 'page on facebook':3, 'like us on fb':6,
                  'iphone':6, 'dm or ws':8,
                  'twitter':4,
                  'email':2, 'e-mail':2,
                  'youtube channel':3,
                  'bitly':8, 'goo.gl':5,
                  'whatsapp':4,
                  'twitch':8,
                  'instastory':5,
                  # Link to something
                  'link in':5, 'link on my':5, 'click link':4, '#linkinbio':5, 'dm me':2,
                  # Purchase indicators
                  'on orders':2, 'call today':7, 'call now':6, 'with every order':6,
                  'coupon':6, 'sale':1, 'purchase':1, 'purchasing':1,
                  'place an order':6, 'with the purchase':8, 'with every purchase':6,
                  'buy':4, 'forsale':4, 'invoice':4, 'sales event':10,
                  '% off':5, 'with any purchase':6, 'with every purchase':6,
                  'book now':4, 'when you order':6,
                  # Finished
                  'for participating':2, 'thank you for participating':4, 'the winner of':6,
                  'better luck':4, 'closed':2, 'now closed':4, 'is our giveaway winner':6, 'have our first winner':8,
                  'won this':3,
                  # Repost Indicators
                  '#repost':8, '#reposting':8, 'repost @':8, ' via ':8, 'wish me luck':10,
                  'pickme':6, 'reposted using':10,
                  'visit her ':6
                  }
    dealbreakers = {'spend $':6, 'sales over $':6, 'purchase over':12, 'order over':12, #'$300 required' through regex
                    'buy 1 get 1 free':6, 'order now':9, 'order something':9,
                  # Spam
                  'free followers':9, 'famenow':9,
                  # Ad for giveaway?
                  'head over':8, 'head back':7, 'over at @':7, 'over on my blog':5,
                  'pop over':10,
                  'check out @':4, 'check out the @':4,
                  'jump over':10, 'earlier post':4,
                  # Reminder post?
                  'previous post':10, 'last post':10, 'posts back':5,  'post back':5, 'original post':10,
                  'see their acc':8, 'already posted':8, 'past post':3, 'swing over':4, 'back few posts':5, 'back a few posts':5, 'few posts':5,
                  'original photo':4, 'check out our  post':11, 'out latest post':5, 'see my previous':5,
                  # thank you for received?
                  'i received':4, 'thanks to @':4, 'thank you to @':4,
                  # Repost ?
                  '@instatoolsapp':6, '@regram.app':6, 'repostapp':6, 'regrann':6, 'regram':6, '@get_repost':6, '@renstapp':6,
                  'repost any':6,
                  'respost from @':6, 'repost  from @':6, 'repost from @':8,
                  'repostby @':6, 'Posted @withrepost':6,  '@ziapplications':8,
                  # Closed
                  'congratulation':6, 'congrats ':6, 'congrats to':6,
                  'winner is @':6, 'winner is... @':6, 'winners are @':6, 'winner was @':6, 'winner @':6,
                  '1st winner':6, 'won my giveaway':6, 'we have a winner':6,
                  'giveaway closed':6
                   }
    # Check for minimum length -> end
    if not checkMinLength(item):  return contestScore, allTags
    # Check if foreign / not in English -> end
    if not checkLanguage(item):    return contestScore, allTags
    # Translate if Foreign
    item = translateToEnglish(item)
    # Check for phone number -> end
    if checkPhoneNumber(item):    return contestScore, allTags
    # If first letter is a @, its a repost
    if item[0] == "@":            return contestScore, allTags
    # Check user stats (Leads to spam disconnect of server after a few)
#    if not verifyUser(instagram, post['user']['pk'], minPosts, minFollowers, minFollowing):
#        return contestScore, allTags
    # Passed All Tests
    try:  # Scoring
        positiveList = [phrase for phrase in positives.keys() if phrase in item]
        contestScore += sum(positives[phrase] for phrase in positives.keys() if phrase in item)
        #contest_count -= sum(negatives[phrase] for phrase in negatives.keys() if phrase in item)
        if contestScore >= minScore:
            negativeList = [phrase for phrase in negatives.keys() if phrase in item]
            contestScore -= sum(negatives[phrase] for phrase in negatives.keys() if phrase in item)
            contestScore -= sum(10             for phrase in dealbreakers.keys() if phrase in item)
            if len(negativeList) > 0: print("  Negatives:", " ", negativeList)
    except: print("failed to determine score!")
    try:
        if contestScore >= minScore:
            print("  Contest Score: %i (%s)" %(contestScore, ", ".join(print(positiveList))));
            # Find Tagsent
            if (item.find('tag')      != -1):   # or '#'
                primaryTag, allTags = getPostTags(post)
    except:  print("  Failed: Determining any Tags!")
    return contestScore, allTags

def mostCommonComment(instagram, post, minComments=10, minCount=3):
    ''' Comment on Contest to enter: 1) most common answer 2) just yes '''
    commented = baseComment
    if 'comments_disabled' in post.keys() and post['comments_disabled'] == True:  return commented
    if post['comment_count'] > minComments: # Comment the same as most commented
        instagram.getMediaComments(post['id'])
        commentDf = pd.DataFrame(instagram.LastJson['comments'])
        commentDf['text'] = commentDf['text'].str.replace('([@][\w_.@]*)','') # Remove: People Tags
        commentDf = commentDf[commentDf['text'].apply(set).apply(len) > 2]    # Remove: Whitespace Only Entries
        commentDf['text'] = commentDf['text'].str.replace('  ',' ') # Remove: People Tags
        decOrder = commentDf['text'].str.lower().value_counts()
        print(decOrder)
        if len(decOrder) > 0 and decOrder[0] > minCount:
            print("  commented: ", decOrder[0], decOrder.index[0])
            mostCommented = decOrder.index[0]
            commented = mostCommented
        else:  commented = baseComment
    # TODO: Check if commmented before - using liking as checkmark
    return commented

def searchPost4PeopleTag(post):
    ''' returns number of people needed to tag '''
    from re import findall, IGNORECASE
    item = post['caption']['text'].lower()
    #item = " ".join([word for word in item.split(" ") if word.isalnum()==True])
    # Phrase List
    import itertools
    tagList = ["tag", "tagging"]
    attList = ["at least", "a minimum of", "a minimal", "me and"]
    phraseList = tagList + [tag+" "+att for tag,att in itertools.product(tagList,attList)]
    # Works if:  Integer
    for phrase in phraseList:
        hitList = findall('(?<='+phrase+' ).[0-9]*', item, flags=IGNORECASE)
        hitList = [int(k) for k in hitList if k.isdigit()]
        if   len(hitList) == 1:  return hitList[0]
        elif len(hitList)  > 1:  # This should never happen
            print(hitList);
            randomSleepTimer(9,10)
            return hitList[0]
    # Works if:  Non-Integer
    # comment <-> tag
    if   'tag a friend'             in item: return 1
    elif 'mention a friend'         in item: return 1
    elif 'tag a mate'               in item: return 1
    elif 'tag the friend'           in item: return 1
    elif 'tag one friend'           in item: return 1
    elif 'tag your bff'             in item: return 1
    elif 'tag your friend'          in item: return 1
    elif 'tag someone'              in item: return 1
    elif 'comment who'              in item: return 1
    elif 'tag as many'              in item: return 1
    elif 'tag at least one'         in item: return 1
    elif 'tag your friends'         in item: return 2
    elif 'tag two friends'          in item: return 2
    elif 'tag two people'           in item: return 2
    elif 'tag two '                 in item: return 2
    elif 'tag two of your friends'  in item: return 2
    elif 'tag two or'               in item: return 2
    elif 'tag some'                 in item: return 2
    elif 'tag lots'                 in item: return 2
    elif 'tag firend'               in item: return 2
    elif 'tag three friends'        in item: return 3
    elif 'tag four friends'         in item: return 4
    elif 'tag five friends'         in item: return 5
    elif 'get tagging'              in item: return 2
    else:  print("  [ ] No people tags necessary"); return 0

def addPeopleTags(post, numPeopleToTag, instagram):
    ''' returns string of tagged usernames in amount needed '''
    usernameList   = usernamesToTagList(numPeopleToTag, instagram)
    if numPeopleToTag > 0: print("  [ ] Tagging %s people required" %numPeopleToTag); return "@"+" @".join(usernameList)
    else: return ""

def repost(post, captionText, instagram):
    ''' repost picture in post with previous caption attached '''
    global sleepCounter
    # check if posted before: Add Name
    selfImageHashDic = getSelfImageHashes(instagram)
    # TODO: make selfImageHashDic global once at the beginning of the script and add values rather than recalculating
    duplicatePk = checkPrevPosted(selfImageHashDic, post, sensitivity=30)
    if duplicatePk:
        print("  Duplicate - not reposting")
        while not instagram.mediaInfo(duplicatePk): sleepCounter += randomSleepTimer(20,60)
        if instagram.LastJson['items'][0]['caption'] is None:
            checkCaptions(contests)
            while not instagram.mediaInfo(duplicatePk): sleepCounter += randomSleepTimer(20,60)
        oldCaption = instagram.LastJson['items'][0]['caption']['text']
        if post['user']['username'] not in oldCaption:
            newCaption = oldCaption[:oldCaption.find('@')] + '@' + post['user']['username'] + ' ' + oldCaption[oldCaption.find('@'):]
            instagram.editMedia(duplicatePk, newCaption)
            print("  Added tag @%s" % post['user']['username'])
        print("  Already tagged @%s" % post['user']['username'])
        return True
    else:
        # else
        url = post['image_versions2']['candidates'][0]['url']  # link of largest
        photoName = post['user']['username'] + ".jpg"
        try:
            urllib.request.urlretrieve(url, photoName)
            instagram.uploadPhoto(photoName, caption = captionText, upload_id = None)
            print("  [x] Reposted")
            # TODO !!!
            # Caption seems to be broken.
            # Check for caption
            # instagram.mediaInfro(mediaId)
            # instagram.editMedia(self, mediaId, captionText = '')
            return True
        except:
            print("  Failed:  repost")
            return False

def check4Repost(post):
    ''' Check if repost of picture required '''
    import itertools
    caption = post['caption']['text'].lower()
    verbIndicators = ["post", "posts", "repost", "reposts", "share", "shares", "pot", "repot",
                      "like/share", "like&share", "like &share", "like & share"]
    adjIndicators  = ["the", "this photo", "this picture", "this pic", "this post", "this image", "this and", "and", "a screenshot", "picture", "image", "&"]
    specIndicators = ["shoutout this account", "shout out this account"]
    repostIndicators = [verb+" "+adj for verb,adj in itertools.product(verbIndicators, adjIndicators)] + specIndicators
    repostIndicators.remove("post and")
    repostIndicators.remove("posts and")
    repostIndicators.remove("share the")
    repostIndicators.remove("post &")
    repostIndicators.remove("posts &")
    repostIndicators.append("repost n tag")
    repostIndicators.append("repost with") # followed by tag often
    repostIndicators.append("& share")
    for indicator in repostIndicators:
        if caption.find(indicator) != -1:
            print("  [ ] Repost required")
            return True
    return False

def getPeopleTagged(post):
    ''' Get all people tags in the post '''
    #TODO: Does not include some characters, e.g. had hit for @by
    from re import findall
    text = post['caption']['text'].lower()
    allFollows = []
    if text.find("follow") != -1:
        allFollows = findall('([@][\w@_.]*)', text)
        print("  [ ] Follow requried: (%s)" % ", ".join(set(allFollows)))
    return allFollows

def enterContest(instagram, sleepCounter, contests, post, commented, usernameList, caption=""):
    ''' Likes, follows, comments, and reposts if required '''
    global searchList
    # Follow all tagged users
    userIdList = tagsToUserIds(usernameList)
    sleepCounter += followUsers(userIdList + [post['user']['pk']])
    if len(userIdList) > 0: searchList = searchList + [str(userId) for userId in userIdList]  # Add new follows to current search for loops
    # Comment Post
    instagram.comment(post['pk'], commented)      # Comment
    print("  [x] Commented")
    # Repost Post
    reposted = False
    if len(caption) > 1: repost(post, caption, instagram); reposted = True # Repost
    # Add to History
    newRow = {
        # Post Details
        'username':      post['user']['username'],
        'userPk':        post['user']['pk'],
        'timestamp':     post['taken_at'],
        'postPk':        post['pk'],
        'postId':        post['id'],
        'caption':       post['caption']['text'].strip().replace('\n',' ').replace('\n','    '),
        # Action Taken
        'commented':     commented,
        'commentNumber': post['comment_count'],
        'commentTimestamp': round(time.time()),
        'liked':         True,
        'shared':        reposted,
        'shareCaption':  caption
    }
    # Like Post
    instagram.like(post['pk'])  # Like
    print("  [x] Liked")
    print("  Successfully entered contest!")
    sleepCounter += randomSleepTimer(0,3)
    return contests.append(newRow, ignore_index=True)      # Add Stats
###################################################################

# User Searches
def cleanUserSearch(userSearchJson, minFollowers):
    ''' Cleans Json of User search, Returns Dataframe '''
    userSearchData = pd.DataFrame(userSearchJson['users'])  # To Dataframe
    # Remove useless
    del userSearchData['byline']
    userSearchData = userSearchData[userSearchData['is_private'] == False]  # Remove Private
    userSearchData = userSearchData[userSearchData['follower_count'] > minFollowers]  # Cutoff follower
    # Organize
    userSearchData = userSearchData.set_index('username')   # Username = Index
    return userSearchData

def findUser(searchUser, minFollowers, returnType='list'):
    ''' given name, search, clean, return restults '''
    instagram.searchUsers(searchUser)       # Search: for User
    userSearchJson = instagram.LastJson     # Save:   Return Data
    if userSearchJson['status'] == 'fail':  # Catch:  Fail
        print("fail ", datetime.datetime.now())
        return
    else:
        userSearchData = cleanUserSearch(userSearchJson, minFollowers)  # Clean Search Data
        print("Users found: ", len(userSearchData))
        if    returnType=='list': return userSearchData['pk'].tolist()
        elif  returnType=='dict': return userSearchData['pk'].to_dict()
        else: print('return type not recognized, returning List'); return userSearchData['pk'].tolist()

def getFollowIdList(instagram):
    ''' returns list of IDs from people I follow '''
    followingList = instagram.getTotalSelfFollowings()
    followingDf = pd.DataFrame(followingList)
    try:    return followingDf['pk'].tolist()
    except: return []

def usernamesToTagList(peopleNeeded, instagram):
    ''' returns List of n usernames from own followers '''
    instagram.getSelfUserFollowers()
    followers     = pd.DataFrame(instagram.LastJson['users'])
    # Case 1:  Not enough followers
    if len(followers) < peopleNeeded:
        print("not enough followers to tag")
        followerNames=["braidsbybreann", "brownhairedbliss", "emmaa.w", "daisy_cullenn", "tara_sagexo", "madisinw", "jenny_filt", "garymannwx", "cam_raee", "tori_auricht", "braids_by_lisa", "mybraidings", "ellaboag", "Jada_autumn", "mimi_floreani", "saramccoy11", "jovanoviclj", "dulce_lo_", "saraawegz", "brunosaltor", "nailp0lish_", "natalieszenas", "mia__chan", "indieconnolly", "zoerelf", "tay.k.18", "fatom_3sk", "dyna_kd", "meryemlaaraich", "maryam_tariq", "lujain_alesawy", "______555suzi__", "xx_anoode", "omneat", "saragrammm", "joslexispam"]
    # Case 2:  No one Needed
    elif peopleNeeded == 0:  followerNames = ['']
    # Case 3:  Enougn followers
    else:
        followerNames = followers['username'].tolist()
    #TODO: Remove spam accounts
    try:    followerNames.remove(primaryAccount)
    except ValueError: pass
    followerNames = [name for name in followerNames if not any(["follow" in name,
                    "golf" in name, "shop" in name, "app" in name, "furniture" in name,
                    "free" in name, "hack" in name, "store" in name])]
    # Attempt to randomize picking
    try:    firstTagIx = random.randrange(0,len(followerNames)-1-peopleNeeded)
    except: firstTagIx = 0
    # Tag self first always
    followerNames = [primaryAccount] + followerNames[firstTagIx:firstTagIx+peopleNeeded-1]
    return followerNames

def search4NewUsers(searchUserList, sleepCounter):
    ''' search for new Users given list '''
    totalFollowingIdList = getFollowIdList(instagram)  # User Already Followed
    for searchUser in searchUserList:
        print("Searching for: ", searchUser)
        newUserIds = findUser(searchUser, minFollowers)
        for userId in newUserIds:
            if userId not in totalFollowingIdList: # check if already followed
                instagram.follow(userId)   # Follow New Users
                sleepCounter += randomSleepTimer(0,2)
    print("Successfully finished search")
    return sleepCounter

def tagsToUserIds(tagList):
    ''' given a list of userids, gets user tag by search and match '''
    ids = []
    for tag in tagList:
        if len(tag)>1:
            added = False
            instagram.searchUsers(tag)
            userList = instagram.LastJson['users']
            for user in userList:
                if user['username'].lower() == tag.lower():
                    ids.append(user['pk'])
                    added = True
                elif user['username'].lower() == tag[1:].lower():   # if @ doesnt work
                    ids.append(user['pk'])
                    added = True
                elif user['username'].lower() == ('@'+tag).lower(): # if @ doesnt work
                    ids.append(user['pk'])
                    added = True
            if added == False:  # Not found
                try:
                    ids.append(userList[0]['pk'])  # Follow first
                    print("  Failed: finding %s. Following: %s" % (tag, instagram.LastJson['users'][0]['username']))
                except:
                    print("  Failed: Cannot recognize ID !!!")
                    print(ids)
    return ids

def followUsers(userIdList):
    ''' follow a list of new users if not already followed '''
    # check if already followed
    totalFollowingIdList = getFollowIdList(instagram)
    toFollow     = set([str(userId) for userId in userIdList if userId not in totalFollowingIdList])
    sleepCounter = 0
    for userId in toFollow:
        instagram.follow(userId)   # Follow
        newFollows.append(userId)  # Keeps track of new accounts followed
        sleepCounter += randomSleepTimer(1,2) # Sleep
    # TODO:  Already followed not working
    print("  [x] Followed: " + ", ".join(toFollow), "- already followed: ", ", ".join([str(item) for item in list(set(userIdList)-set(toFollow))]))
    return sleepCounter

def checkCaptions(contests):
    ''' Check and update captions of posts '''
    changed  = 0  # Keep track of changes made
    selfFeed = instagram.getTotalSelfUserFeed()
    postsToCheck = contests[contests['shared'] == True][::-1]
    for i in range(min(len(selfFeed), len(postsToCheck))):
        # TODO: Implement Image Hash Check
        # Case 1:  Neither has values -> pass
        if   selfFeed[i]['caption'] == None and postsToCheck.iloc[i]['shareCaption'] == 'nan': continue
        # Case 2:  Posted has none -> edit
        elif selfFeed[i]['caption'] == None and postsToCheck.iloc[i]['shareCaption'] != 'nan':
            print("Changing caption")
            # try. except: delete
            print(selfFeed[i]['pk'])
            try:
                print(postsToCheck.iloc[i]['shareCaption'])
                if instagram.editMedia(mediaId = selfFeed[i]['pk'], captionText = postsToCheck.iloc[i]['shareCaption']):
                    changed = changed + 1
                else:
                    print("Could not edit image")
            except:
                print("Unable to change. Deleting.")
                instagram.deleteMedia(selfFeed[i]['pk'])
        # Case 3:  Has a caption -> pass
        else: continue
    print("Changed items: ", changed)
#################################################################

# Other Functions
def randomSleepTimer(start, stop):
    ''' prevent spam / overflow / suspension '''
    count = random.randrange(start, stop)*slowdownFactor
    print("sleeping ", "."*count)
    time.sleep(count) # Count sheeps
    return count      # Return 'Count' to track time slept

def searchWebsite4Account(website, account='instagram.com'):
    ''' finds instagram (or other) account linked on website '''
    ''' e.g. print(searchWebsite4Account('https://www.thomaspink.com/', account='instagram.com')) '''
    import re, urllib
    checkWebsite = account.encode('ascii')
    req = urllib.request.Request(website)          # Define Request for website
    with urllib.request.urlopen(req) as response:  # Open Connection to Website
       pageHTML = response.read()                  # Read website content and save as pageHTML
    pattern = b'([^"$"]*'+checkWebsite+b'*[a-zA-Z0-9_+/]*)' # Start ", end ", website, allowed characters following
    results = re.findall(pattern, pageHTML)
    return results
#################################################################
def crashSave(contests, stats, prevContests, totalPostCount, newFollows, totalFollowingIdList, searchTagList):
    print("initiating exit")
    newContests = pd.concat([contests, prevContests]).drop_duplicates(keep=False)
    # Save Files
    newRow = {'timestamp':cycleStartTime, 'entered':len(newContests), 'searched':totalPostCount, 'newFollows':newFollows, 'searchUserIdList':totalFollowingIdList, 'searchHashTagList':searchTagList}
    stats  = stats.append(newRow, ignore_index = True)
    saveSettings(filenames[0], contests)
    saveSettings(filenames[1], stats)
    # Restart
    with open("instagramBot.py", encoding='utf8') as f:
        code = compile(f.read(), "instagramBot.py", 'exec')
        exec(code)

import atexit
#################################################################
print("Successfully loaded all functions!")


try:
    # Save Files
    newRow = {'timestamp':cycleStartTime, 'entered':len(newContests), 'newFollows':newFollows, 'searchUserIdList':totalFollowingIdList, 'searchHashTagList':searchTagList, 'searched':totalPostCount}
    stats  = stats.append(newRow, ignore_index = True)
    saveSettings(filenames[0], contests)
    saveSettings(filenames[1], stats)
    print("successfully saved new stats!")
except:
    pass

# Initilializing
contests = loadSettings(filenames[0], contestCols)
contests['shareCaption'] = contests['shareCaption'].apply(str)
stats    = loadSettings(filenames[1], statCols)
#selfImageHashDic = load
prevContests = contests
newFollows = []
# Test Parameters
#if len(stats) == 0:
#    newRow = {'timestamp':round(time.time())-(60*60*24*maxDays), 'entered':0, 'newFollows':[], 'searchUserIdList':[], 'searchHashTagList':[]}
#    stats  = stats.append(newRow, ignore_index = True)
#################################################################
print("Successfully loaded all test parameters")
print("Last check:  %s" % (datetime.datetime.strftime(datetime.datetime.fromtimestamp(stats['timestamp'].max()), '%c')))


# Start up
try:
    instagram
    print("already logged in")
except:
    instagram = insta.InstagramAPI(accName, accPw)
    instagram.login()
    print ("Successfully logged in")
sleepCounter = 0


# Get global parameters
totalSelfFollowers = pd.DataFrame(instagram.getTotalSelfFollowers())
#totalFollowerIdList = totalSelfFollowers['pk'].tolist()
#totalFollowerUsenameList = totalSelfFollowers['username'].tolist()


# If new Usernames given, add them
if len(searchUserList)!=0: sleepCounter += search4NewUsers(searchUserList, sleepCounter)

# Get things running
cycleStartTime = time.time()
totalPostCount = 0
# Look through Feed
# TODO: Check Own Feed instead
#instagram.getSelfUserFeed(maxid = '', minTimestamp = None)  # Doesnt get feed, gets own posts
totalFollowingIdList = []
searchDict = {}  # Keeps track of how many post searched for each
searchList = searchTagList
# Only check users if it has been enough time
if time.time() > stats[stats['searchUserIdList'].apply(lambda c: c!=[])]['timestamp'].max() + (minTimePassed*60): # Check only if enough time has passed
    totalFollowingIdList = getFollowIdList(instagram)  # Follow = Check User
    searchList   = searchTagList + totalFollowingIdList
    print(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'), datetime.datetime.fromtimestamp(stats['timestamp'].max() + (minTimePassed*60)).strftime('%Y-%m-%d %H:%M:%S'), )
else: print("Too soon to check followed. Next time at:", datetime.datetime.fromtimestamp(stats['timestamp'].max()).strftime('%Y-%m-%d %H:%M:%S'))

# Start Search
for searchTerm in searchList:               # Over User ID's / Personal Key ?
    userPostCount = 0
    # TODO: only get items newer than X / use the new/unseen feature?
    if type(searchTerm) is int:  # User ID
        instagram.getUserFeed(searchTerm)   # searchTerm = userPk  feed(userID) # getTotalUserFeed(userPk)
        itemFeed = instagram.LastJson['items']
        totPosts = len(itemFeed)
        if totPosts != 0:  print(itemFeed[0]['user']['username'])
        else: print("%s has no posts!" % str(searchTerm)); continue
    else:  # Hashtag
        print(searchTerm)
        searchTerm = searchTerm[1:]
        lastTimestamp = int(stats['timestamp'].max())
        if instagram.getHashTagFeedSince(searchTerm, lastTimestamp):
        #getHashtagFeed(searchTerm):    # feed(userID) # getTotalUserFeed(userPk)
            itemFeed = instagram.LastJson['items']
            totPosts = len(itemFeed)
        else:
            print("failed to getHastagFeed")
            if instagram.tagFeed(searchTerm):
                itemFeed = instagram.LastJson['items']
                totPosts = len(itemFeed)
            else:
                print("failed to tagFeed")
                instagram.searchTags(searchTerm)
                itemFeed = instagram.LastJson
                if len(itemFeed) < 10:
                    print("failed to searchTags. ItemFeed:", itemFeed)
                    continue
    # Each Post
    for post in itemFeed:
        if post['taken_at'] < stats['timestamp'].max():  # device_timestamp < taken_at < current
            print("  too old: ", datetime.datetime.fromtimestamp(post['taken_at']        ).strftime('%Y-%m-%d %H:%M:%S'))
            print("  cut-off: ", datetime.datetime.fromtimestamp(stats['timestamp'].max()).strftime('%Y-%m-%d %H:%M:%S'))
            #print(int(stats['timestamp'].max()-post['device_timestamp']), "s")
            break # Only look at new => skip rest
        else:
            if post['caption'] is None: continue
            if post['user']['username'] == accName: continue
            contestScore, postTags = checkForContest(post, minScore)
            userPostCount += 1
            # Check if already entered => Next loop
            if post['has_liked']: print("    [x] Contest already entered."); break # Stop when reached old one
            if contestScore >= minScore:  # if contest detected in
                print("  Contest Found: ", datetime.datetime.fromtimestamp(post['taken_at']).strftime('%Y-%m-%d %H:%M:%S'))
                # Print hit (username uncoded or hashtag)
                if type(searchTerm) is int: print("   ", post['user']['username'])
                else:                       print("   ", searchTerm)
                # Print User
                print("    User: %s (%s)" %(post['user']['full_name'], post['user']['username']))
                # Comment = Most Common > minComments | else 'yes ❤️'
                baseComment = getBaseComment(baseComments)
                commented = mostCommonComment(instagram, post, minComments)
                # Create Caption
                caption = ""
                if check4Repost(post):
                    caption = commented + " " + " ".join(postTags) + " @" + post['user']['username'] + "\n.......\n" + post['caption']['text']
                # Add People Tags       | 'yes @friend1 @friend2'
                numPeopleToTag = searchPost4PeopleTag(post)
                commented = commented + " " + addPeopleTags(post, numPeopleToTag, instagram)
                # Add Hashtags          | 'yes @friend1 @friend2 #cool #love'
                commented = commented + " " + " ".join(postTags[:maxTagsCopy-1])
                # Get People Follows
                usernameList = getPeopleTagged(post)
                # Double Check Manually for testing
                print("  TEXT: ", post['caption']['text'][:maxLength].strip().replace('\n','  '))
                print("  Comment: ", commented)
                #print("  Caption: ", caption)
                # Just do it
                if commented.find(baseComment) == -1 and contestScore > 5:
                    contests = enterContest(instagram, sleepCounter, contests, post, commented, usernameList, caption)
                elif testing < 2:
                    if   caption == "" and numPeopleToTag > 0: contests = enterContest(instagram, sleepCounter, contests, post, commented, usernameList, caption)
                    elif testing == 0  and numPeopleToTag > 0: contests = enterContest(instagram, sleepCounter, contests, post, commented, usernameList, caption)
                    else: continue
                else: # Confirm Manually
                    done = False
                    while not done:
                        confirm = input("Confirm [Y/N] or write new Comment: ")
                        if confirm.lower() == 'y':
                            # Comment, Like, Repost, Follow
                            contests = enterContest(instagram, sleepCounter, contests, post, commented, usernameList, caption)
                            done = True
                        elif confirm.lower() == 'n':        print("  Aborted."); done = True
                        elif confirm.lower() == 'cancel':   import sys; sys.exit("cancelled")
                        elif confirm.lower() == 'finish':   saveSettings(filenames[0], contests); saveSettings(filenames[1], stats); print("Successfully saved new stats"); import sys; sys.exit("cancelled")
                        elif confirm.lower() == 'ignore':   instagram.like(post['pk']); print("liked. ignored in future."); done = True
                        elif confirm.lower() == 'unfollow': instagram.unfollow(post['user']['pk']); print("unfollowed."); done=True
                        elif confirm.lower() == 'break':    break
                        elif confirm.lower() == 'comments': mostCommonComment(instagram, post, minComments=1, minCount=1)
                        elif confirm.lower() == 'help':     print("cancel, finish, ignore, unfollow, break, comment")
                        else:  # not approved
                            commented = confirm
                            print("  Comment: ", commented)
            # Post complete
        # Post too old
        print("  Searched: ", userPostCount, "/", totPosts)
    # User Feed Complete
    searchDict[searchTerm] = userPostCount
    totalPostCount +=userPostCount      # update overall count
    print("  Posts searched for:   User", userPostCount, "  Total", totalPostCount)
    sleepCounter += randomSleepTimer(10,20)
    # TODO: Save after X posts searched, or thousands might get lost
    # THIS CREATED A LOOP AT THE END OF THE FIRST WHILE
    #atexit.unregister(crashSave)
    #atexit.register(crashSave(contests, stats, prevContests, totalPostCount, newFollows, totalFollowingIdLists, searchTagList))


# Check captions for missing text -> working again
#checkCaptions(contests)
# All done.
cycleFinishTime = time.time()
# Wrap up
newContests = pd.concat([contests, prevContests]).drop_duplicates(keep=False)
if len(newContests)!=0:
    print(newContests[['username', 'liked', 'shared']])
# Save Files
newRow = {'timestamp':cycleStartTime, 'entered':len(newContests), 'newFollows':newFollows, 'searchUserIdList':totalFollowingIdList, 'searchHashTagList':searchTagList, 'searched':totalPostCount}
stats  = stats.append(newRow, ignore_index = True)
saveSettings(filenames[0], contests)
saveSettings(filenames[1], stats)
print("successfully saved new stats!")

# Show Statistics
print()
print("Successfully finished cycle.")
print("-----------------------------------")
#print("".join(["{0:25}: {1:>4} \n".format(str(searchTerm), str(searchDict[searchTerm])) for searchTerm in searchDict.keys()]), end="")
#print("{0:25}k: {1:>4}".format("total searched", totalPostCount))
print("----------- Cycle Stats -----------")
print("Cycle Time:     {:10,.2f} sec      ".format((cycleFinishTime - cycleStartTime)) )
print("Slept For:      {:10,.2f} sec      ".format(   sleepCounter))
print("Seconds/post:   {:10,.2f} sec/post ".format((cycleFinishTime-cycleStartTime-sleepCounter)/totalPostCount))
print("Posts searched: {:10,.0f} posts    ".format(totalPostCount))
print("---------- Contest Stats ----------")
print("Contests entered:{:9,.0f} contests ".format(len(newContests)))
print("Newly followed: {:10,.0f} users    ".format(len(newFollows)))
print("Shared Posts:   {:10,.0f} posts    ".format(len(newContests[newContests['shared'] == True])))
print("---------- Account Stats ----------")
instagram.getUsernameInfo(instagram.username_id)
userInfoDic = instagram.LastJson['user']
print("Following:      {:10,.0f} users    ".format(userInfoDic['following_count'])) #len(totalFollowingIdList)+len(newFollows)))
print("Followers:      {:10,.0f} users    ".format(userInfoDic['follower_count']))  #len(instagram.getTotalSelfFollowers())))
print("Posts:          {:10,.0f} posts    ".format(userInfoDic['media_count']))     #len(instagram.getTotalSelfUserFeed())))
print("-----------------------------------")
print("Lifetime Score: {:10,.0f} contests ".format(len(contests)))
print("Lifetime Search:{:10,.0f} posts    ".format(stats['searched'].sum()+totalPostCount))
print("Lifetime Cycles:{:10,.0f} cycles   ".format(len(stats)))
print("First Run:          {:%d %b %Y}    ".format(datetime.datetime.fromtimestamp(stats['timestamp'][0])))
print()




# TODO: Accelerate checking of very active tags
#randomSleepTimer(240,360)
#with open("instagramBot.py", encoding='utf8') as f:
#    code = compile(f.read(), "instagramBot.py", 'exec')
#    exec(code)
