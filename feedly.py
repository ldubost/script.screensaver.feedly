# -*- encoding: utf-8 -*-

import json
import requests
import pickle

# https://sandbox.feedly.com/v3/auth/auth?client_id=sandbox&redirect_uri=http%3A%2F%2Flocalhost&scope=https://cloud.feedly.com/subscriptions&response_type=code

CONFIG_FILE_NAME = "feedly.conf";
FEEDLY_REDIRECT_URI = "http://localhost"
FEEDLY_CLIENT_ID="sandbox"
FEEDLY_CLIENT_SECRET="YNXZHOH3GPYO6DF7B43K"

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
            'mixes': '/v3/mixes/contents?streamId=user%2Faee936c6-6615-43b0-9ee1-36080d572bd7%2Fcategory%2Fglobal.all'
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
	##user_subscriptions = feedly.get_user_categories(access_token)
	##print user_subscriptions
	##   entries = feedly.get_user_mixes(access_token, "user/00000-000-000-000000/tag/global.all")
	entries = feedly.get_user_mixes(access_token)
	print entries
	if not entries:
	    return -1
	if "errorCode" in entries:
   		return entries["errorCode"]
   	else:
		return 0

def readConf(FILE_NAME):
	fileObject = open(FILE_NAME,'rb') 
	object = pickle.load(fileObject)   
	fileObject.close()
	return object
	
def saveConf(FILE_NAME, object):
	fileObject = open(FILE_NAME,'wb') 
	pickle.dump(object,fileObject)   
	fileObject.close()

try:
	config = readConf(CONFIG_FILE_NAME)   
except:
	print "Error reading configuration. Loading alternate configuration"
	config = {'code': '','token': 'AoJn_gGmoTOyRkbHT1gp-MTxBTZ8tbyxFdCwWR2AoUtvVU63q5a9x-yp6QO6AoDjXeVoAmbmuA7IoAUO8XgpVmhBEIp0j1LGmrGHpBAMgMDeT9MMVg1FmU4tKwwPazV-GuYrHwxBwXxMFXz_l-8v92NCzUD5vOycbkb6XvmdDwHMmN0D4VtvbHqToXlRejEi-ksIBiAC:sandbox','refreshToken': 'AtHRTup7ImkiOiJhZWU5MzZjNi02NjE1LTQzYjAtOWVlMS0zNjA4MGQ1NzJiZDciLCJjIjoxNDQyMDQ2MTM3NzYyLCJ1IjoiMTA3OTUyNzc3OTMzNTI4ODY4MzE2IiwiYSI6IkZlZWRseSBzYW5kYm94IGNsaWVudCIsInAiOjYsInYiOiJzYW5kYm94IiwibiI6ImVWYjlnOTJmRDVhSEh1cDYifQ:sandbox'}
	saveConf(CONFIG_FILE_NAME, config)

       
feedly = get_feedly_client()

if config["token"]:
	failed = feed(feedly, config["token"])

if failed==401:
	print "Request failed. Refreshing token"
	result = feedly.refresh_access_token(config["refreshToken"]);
	print result
	if "access_token" in result:
 		config["token"] = result['access_token']
 	else:
 		config["token"] = ""

	if config["token"] == "": 
		print "Refresh token failed. Getting request and refresh token from code"
		result = feedly.get_access_token(FEEDLY_REDIRECT_URI, config["code"])
		if "access_token" in result:
			config["token"] = result['access_token']

	if config["token"]:
		saveConf(CONFIG_FILE_NAME, config)
		feed(feedly, config["token"])
	else:
		print "Failed to retrieve token. Re-authentication is needed. Here is URL"            
		print feedly.get_code_url(FEEDLY_REDIRECT_URI)
