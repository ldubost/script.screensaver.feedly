#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#    Feedly screensaver by Ludovic Dubost
#    Inspired by Feedreader screensaver by Aslak Grinsted
#
#The MIT License (MIT)
#
#Copyright (c) 2014 Aslak Grinsted
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in
#all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#THE SOFTWARE.
#

import xbmcaddon
import xbmcgui
import xbmc

import json
import pickle
import random
import feedparser
import re
#from threading import Timer
import urllib
import HTMLParser #alternative: http://fredericiana.com/2010/10/08/decoding-html-entities-to-text-in-python/
import time
import datetime
import requests
import urlparse
import traceback

CONFIG_FILE_NAME = "special://userdata/feedly.conf";
FEEDLY_REDIRECT_URI = "http://localhost"
FEEDLY_CLIENT_ID="sandbox"
FEEDLY_CLIENT_SECRET="YNXZHOH3GPYO6DF7B43K"


addon = xbmcaddon.Addon()
addon_name = addon.getAddonInfo('name')
addon_path = addon.getAddonInfo('path')


CONTROL_BACKGROUND = 30001
CONTROL_HEADLINE = 30002
CONTROL_MAINSTORY = 30003
CONTROL_DATE = 30004
CONTROL_DEBUG = 30005
CONTROL_IMAGE = 30006
CONTROL_CLOCK = 30007

def json_fetch(url, method, params={}, data={}, headers={}):
    response = requests.request(
        method, url, params=params, data=json.dumps(data), headers=headers)
    return response.json()


class FeedlyClient(object):

    def __init__(self, **options):
        self.client_id = options.get('client_id')
        self.client_secret = options.get('client_secret')
        self.sandbox = options.get('sandbox', True)
        if self.sandbox:
            default_service_host = 'sandbox.feedly.com'
        else:
            default_service_host = 'cloud.feedly.com'
        self.service_host = options.get('service_host', default_service_host)
        self.additional_headers = options.get('additional_headers', {})
        self.token = options.get('token')
        self.secret = options.get('secret')

        self.info_urls = {
            'preferences': '/v3/preferences',
            'categories': '/v3/categories',
            'topics': '/v3/topics',
            'tags': '/v3/tags',
            'subscriptions': '/v3/subscriptions',
            'mixes': '/v3/mixes/contents?streamId=user%2Faee936c6-6615-43b0-9ee1-36080d572bd7%2Fcategory%2Fglobal.all&count=20'
        }

    def get_user_profile(self, access_token):
        """
        return user's profile
        :param access_token:
        :return:
        """
        headers = {'content-type': 'application/json',
                   'Authorization': 'OAuth ' + access_token
                   }
        request_url = self._get_endpoint('/v3/profile')

        return json_fetch(request_url, "get", headers=headers)

    def get_code_url(self, callback_url):
        """

        :param callback_url:
        :return:
        """
        scope = 'https://cloud.feedly.com/subscriptions'
        response_type = 'code'

        request_url = '%s?client_id=%s&redirect_uri=%s&scope=%s&response_type=%s' % (
            self._get_endpoint('v3/auth/auth'),
            self.client_id,
            callback_url,
            scope,
            response_type
        )
        return request_url

    def get_access_token(self, redirect_uri, code):
        """

        :param redirect_uri:
        :param code:
        :return:
        """
        params = dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            grant_type='authorization_code',
            redirect_uri=redirect_uri,
            code=code
        )

        quest_url = self._get_endpoint('v3/auth/token')
        print quest_url
        res = requests.post(url=quest_url, params=params)
        return res.json()

    def refresh_access_token(self, refresh_token):
        """
        obtain a new access token by sending a refresh token to the feedly Authorization server
        :param refresh_token:
        :return:
        """

        params = dict(
            refresh_token=refresh_token,
            client_id=self.client_id,
            client_secret=self.client_secret,
            grant_type='refresh_token',
        )
        quest_url = self._get_endpoint('v3/auth/token')
        print quest_url
        res = requests.post(url=quest_url, params=params)
        return res.json()

    def get_user_subscriptions(self, access_token):
        """
        return list of user subscriptions
        :param access_token:
        :return:
        """
        return self.get_info_type(access_token, 'subscriptions')

    def get_feed_content(self, access_token, streamId, unreadOnly=None, newerThan=None, count=None, continuation=None,ranked=None):
        """
        return contents of a feed
        :param access_token:
        :param streamId:
        :param unreadOnly:
        :param newerThan:
        :param count:
        :param continuation:
        :param ranked:
        :return:
        """

        headers = {'Authorization': 'OAuth ' + access_token}
        quest_url = self._get_endpoint('v3/streams/contents')
        params = dict(
            streamId=streamId
        )
        # Optional parameters
        if unreadOnly is not None:
            params['unreadOnly'] = unreadOnly
        if newerThan is not None:
            params['newerThan'] = newerThan
        if count is not None:
            params['count'] = count
        if continuation is not None:
            params['continuation'] = continuation
        if ranked is not None:
            params['ranked'] = ranked
        res = requests.get(url=quest_url, params=params, headers=headers)
        return res.json()

    def mark_article_read(self, access_token, entryIds):
        """
        Mark one or multiple articles as read
        :param access_token:
        :param entryIds:
        :return:
        """
        headers = {'content-type': 'application/json',
                   'Authorization': 'OAuth ' + access_token
                   }
        quest_url = self._get_endpoint('v3/markers')
        params = dict(
            action="markAsRead",
            type="entries",
            entryIds=entryIds,
        )
        res = requests.post(
            url=quest_url, data=json.dumps(params), headers=headers)
        return res

    def save_for_later(self, access_token, user_id, entryIds):
        """
        saved for later.entryIds is a list for entry id
        :param access_token:
        :param user_id:
        :param entryIds:
        :return:
        """
        headers = {
            'content-type': 'application/json',
            'Authorization': 'OAuth ' + access_token
        }
        request_url = self._get_endpoint(
            'v3/tags') + '/user%2F' + user_id + '%2Ftag%2Fglobal.saved'

        params = dict(
            entryIds=entryIds
        )
        res = requests.put(
            url=request_url, data=json.dumps(params), headers=headers)
        return res

    def _get_endpoint(self, path=None):
        """
        :param path:
        :return:
        """
        url = "https://%s" % self.service_host
        if path is not None:
            url += "/%s" % path
        return url

    def _get_info(self, access_token, url_endpoint):
        headers = {'Authorization': 'OAuth ' + access_token}
        quest_url = self._get_endpoint(url_endpoint)
        res = requests.get(url=quest_url, headers=headers)
        return res.json()

    def get_info_type(self, access_token, type):
        if type in self.info_urls.keys():
            return self._get_info(access_token, self.info_urls.get(type))
            
    def get_user_categories(self, access_token):
        """
        return list of user categories
        :param access_token:
        :return:
        """
        return self.get_info_type(access_token, 'categories')

    def get_user_mixes(self, access_token):
        """
        return list of user categories
        :param access_token:
        :return:
        """
        return self.get_info_type(access_token, 'mixes')
            
            
def get_feedly_client(token=None):
  if token:
   return FeedlyClient(token=token, sandbox=True)
  else:
   return FeedlyClient(
   client_id=FEEDLY_CLIENT_ID, 
   client_secret=FEEDLY_CLIENT_SECRET,
   sandbox=True
  )


def callback(request):
   code=request.GET.get('code','')
   if not code:
    return HttpResponse('The authentication is failed.')

   feedly = get_feedly_client()

   #response of access token
   res_access_token = feedly.get_access_token(FEEDLY_REDIRECT_URI, code)
   # user id
   if 'errorCode' in res_access_token.keys():
    return HttpResponse('The authentication is failed.')

   id = res_access_token['id']
   access_token=res_access_token['access_token']

# get user's subscription
def feed(feedly, access_token):
	entries = feedly.get_user_mixes(access_token)
	#print entries
	if not entries:
	    return -1
	if "errorCode" in entries:
   		return entries["errorCode"]
   	else:
		return entries


class Screensaver(xbmcgui.WindowXMLDialog):


    class ExitMonitor(xbmc.Monitor):

        def __init__(self, exit_callback):
            self.exit_callback = exit_callback

        def onScreensaverDeactivated(self):
            self.exit_callback()

    def onInit(self):
        self.exit_monitor = self.ExitMonitor(self.exit)
        self.handle_settings()

    def reportError(self):
        print "In Report Error"
        print(traceback.format_exc())
        if addon.getSetting('DebugModeß') == 'true':
            print(traceback.format_exc())
	    #self.getControl(CONTROL_DEBUG).setText(traceback.format_exception(sys.exc_info()[2]))
            self.getControl(CONTROL_DEBUG).setText(repr(traceback.format_exc()))

    def readConf(self, FILE_NAME):
	fileObject = open(xbmc.translatePath(FILE_NAME),'rb') 
	object = pickle.load(fileObject)   
	fileObject.close()
	return object
	
    def saveConf(self, FILE_NAME, object):
	fileObject = open(xbmc.translatePath(FILE_NAME),'wb') 
	pickle.dump(object,fileObject)   
	fileObject.close()

    def displayNext(self):
        try:
            self.lastDisplayTime = datetime.datetime.now() 
            print "Nb entries: "
            print len(self.entries)
            self.curitem=(self.curitem + 1) % len(self.entries);
            item = self.entries[self.curitem] 
	    print "Displaying " 
            print self.curitem
	    self.getControl(CONTROL_HEADLINE).setLabel(item["title"])
            desc = 'n/a'
            if 'description' in item:
                desc = item["description"]
            if 'summary' in item:
                desc = item["summary"]["content"]
               
            cimg=''
            imgsrc = re.search('img[^<>\\n]+src=[\'"]([^"\']+)[\'"]',desc)
            if imgsrc:
                cimg=imgsrc.group(1)
            #convert news text into plain text
            desc = re.sub('<p[^>\\n]*>','\n\n',desc)
            desc = re.sub('<br[^>\\n]*>','\n',desc)
            desc = re.sub('<[^>\\n]+>','',desc)
            desc = re.sub('\\n\\n+','\n\n',desc)
            desc = re.sub('(\\w+,?) *\\n(\\w+)','\\1 \\2',desc)  
            desc = HTMLParser.HTMLParser().unescape(desc) 
            self.getControl(CONTROL_MAINSTORY).setText(desc.strip() + '\n')
            if 'published' in item:
                sdate=item["published"]  
            else: sdate=''
            self.getControl(CONTROL_DATE).setText('%s\n%s' % (item["feedtitle"],sdate))
            try:
                maxwidth=0
                if 'thumbnail' in item:
                    for img in item["thumbnail"]:
                        w=1
                        if 'width' in img: w=img['width']
                        if w>maxwidth:
                            cimg=img['url']
                            maxwidth=w
                if 'enclosure' in item:
                    for img in item["enclosure"]:
                        if re.search('\.(png|jpg|jpeg|gif)',img["href"].lower()):
                            cimg = img["href"]
                        elif 'type' in img:
                            if img["type"].lower().find('image') >= 0:
                                cimg = img["href"]
            except:
                pass
            if cimg:
                cimg = cimg.replace('&amp;','&') #workaround for bug in feedparser
                ##bing-news rss urlparser
                #if cimg.find('imagenewsfetcher.aspx') >= 0:
                #    imgparsed = urlparse.urlparse(cimg)
                #    imgparsed = urlparse.parse_qs(imgparsed.query)
                #    if 'q' in imgparsed: cimg = imgparsed['q']
                self.getControl(CONTROL_BACKGROUND).setImage(cimg)
                self.getControl(CONTROL_IMAGE).setImage(cimg)
                #self.getControl(CONTROL_DEBUG).setText('test: %s' % cimg)
        except:
		print "Display item failed"
		self.reportError()
        #self.getControl(CONTROL_DEBUG).setText('%d' % len(desc))
        #self.itemtimer = Timer(float(addon.getSetting('Time')), self.displayNext)
        #self.itemtimer.start()

    def processEvents(self):
        self.clockblink = not self.clockblink
        try:
            if self.clockblink:
                self.getControl(CONTROL_CLOCK).setText(time.strftime('%d %b %H:%M'))
            else:
                self.getControl(CONTROL_CLOCK).setText(time.strftime('%d %b %H %M'))
            if self.abort_requested: return
            #if abs(time.time()-self.lastDisplayTime) >= self.delayTime:
            if datetime.datetime.now() >= self.lastDisplayTime + datetime.timedelta(seconds=self.delayTime):
                self.displayNext()
        except:
            self.reportError()

    def showEntries(self, entries):
		for ii, item in enumerate(entries['items']):
			item.update({'feedtitle': "feedly", 'itemno': ii, 'feedno': 0, 'globalitemno': 0.})
		self.entries = entries['items']
		self.displayNext()
	

    def addFeedly(self):
    	try:
			config = self.readConf(CONFIG_FILE_NAME)
	except:
			print "Error reading configuration. Loading alternate configuration"
			config = {'code': '','token': '' ,'refreshToken': ''}
			self.saveConf(CONFIG_FILE_NAME, config)

	try:
			feedly = get_feedly_client()
			
			if config["token"]:
				entries = feed(feedly, config["token"])

			if entries==401:
				print "Request failed. Refreshing token"
				result = feedly.refresh_access_token(config["refreshToken"]);
				print result
				if "access_token" in result:
 					config["token"] = result['access_token']
 				else:
 					config["token"] = ""
 			else:
 				self.showEntries(entries)

			if config["token"] == "": 
				print "Refresh token failed. Getting request and refresh token from code"
				result = feedly.get_access_token(FEEDLY_REDIRECT_URI, config["code"])
				if "access_token" in result:
					config["token"] = result['access_token']
	
			if config["token"]:
				self.saveConf(CONFIG_FILE_NAME, config)
				entries = feed(feedly, config["token"])
				self.showEntries(entries)
			else:
				print "Failed to retrieve token. Re-authentication is needed. Here is URL"            
				print feedly.get_code_url(FEEDLY_REDIRECT_URI)
						
	except:
			self.reportError()


    def handle_settings(self):
        self.lastDisplayTime = datetime.datetime.now() - datetime.timedelta(hours=24)
        self.clockblink = True
        self.abort_requested = False
        self.curitem = -1
        self.feedcounter = -1.
        self.getControl(CONTROL_MAINSTORY).setText('')
        self.delayTime=float(addon.getSetting('Time'));
        if not self.abort_requested:
        	self.addFeedly()
                xbmc.sleep(10)
                self.processEvents()
        while not self.abort_requested:
            xbmc.sleep(10)
            self.processEvents()



    def exit(self):
        #self.itemtimer.stop()
        self.abort_requested = True
        self.exit_monitor = None
        self.log('exit')
        self.close()

    def log(self, msg):
        xbmc.log(u'Feedly screensaver: %s' % msg)


if __name__ == '__main__':

    screensaver = Screensaver(
        'script-%s-Main.xml' % addon_name,
        addon_path,
        'default',
    )
    screensaver.doModal()
    del screensaver
    sys.modules.clear()
