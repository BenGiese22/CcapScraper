#pulls information from the Wisconsin department of financial institution's website (WDFI.org)
#
#                                       /!\WARNING/!\
#                This greatly violates the WDFI site TOS. Use at your own discretion
#                               As such THIS PROGRAM REQUIRES TOR.
#         Tor is included in this package and will automatically run when a WDFI object is instantiated
#
#
#Uncomment these lines in the torrc configuration located at /AppData/Roaming (windows)
#ControlPort 9051
#HashedControlPassword xxxxxxxxxx:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx (whatever your key may be)
#CookieAuthentication 1
#
#if the torrc file does not exist, copy the one in this package to the directory listed above
#updated 5-5-2018


from stem import Signal
from stem.control import Controller
import subprocess
import requests
import tempfile
import random
import re
import os
import time



queryURL = "https://www.wdfi.org/apps/CorpSearch/Results.aspx?type=Simple&q=" #initial query URL
query2URL = "https://www.wdfi.org/apps/CorpSearch/" #URL after initial query, gets the LLC info
urlRegex = '<a href="Details.*'
agentRegexBegin = 'Registered Agent<br \/>'
agentRegexEnd = '<div id="ctl00_cpContent_pnlRegisteredAgentActions"'

#requests session properties, needed to tor can be used
session = requests.session()
session.proxies = {}
session.proxies['http'] = 'socks5h://localhost:9050'
session.proxies['https'] = 'socks5h://localhost:9050'
TOR_KEY = "16:872860B76453A77D60CA2BB8C1A7042072093276A3D701AD684053EC4C"

TIMEOUT_SEARCH = 0
TIMEOUT_CLICK_ON_SEARCH_RESULT = 0

#user agent to mask the fact that we are a robot...
header = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36'}


class wdfi:

    """
    This is a library for accessing data from the Wisconsin Department of Financial Institutions (WDFI_). This
    module will fetch data for an LLC's registered agent.

    .. warning:: WDFI puts ridiculous limits on how fast data can be searched from there website, as well as how
     often that data is retrieved.

     This program uses TOR to get around this.
     That also means this program may not run in AWS (See best practices)

     Since this program uses TOR, there is some setup required. You will need:
      * the STEM library
      * access to the tor configuration file (under windows this is located at C:/users/<username>/AppData/Roaming)
      * the included torrc configuration file

     You should be able to copy the configuration file to the directory listed above

    :Quickstart Example:

    The following code will give the Registered Agent for an LLC. This is all that is needed to find a registered agent.

    .. code-block:: python

        from wdfi import wdfi
        wd = wdfi.wdfi()
        print(wd.getRegAgent("MCCULLER AND MCCULLER"))

    .. note:: There is a 30 second timeout between when the WDFI lookup object is instantiated and when it is ready
     to use. This allows time for the TOR subprocess to initialize.


    .. _WDFI: https://www.wdfi.org/apps/CorpSearch/Search.aspx

    """

    def __init__(self):
        self.last_companyName = ""
        self.last_reg_agent = ""

        self.last_reg_agent_by_cmp = {}

        cwd = os.getcwd()
        timeout = 15
        #print(cwd + r"\wdfi\tor_win\Tor\tor.exe")
        print("Script Start...")
        print("Please wait " + str(timeout) + " seconds for Tor to startup\n")
        # for now this will only work in windows,
        p = subprocess.Popen(cwd + r"\wdfi\tor_win\Tor\tor.exe", stdout=tempfile.TemporaryFile(),
                             stderr=tempfile.TemporaryFile(), creationflags=0x08000000)
        # wait for tor to start and create circuit
        time.sleep(timeout)

    #try to get a new TOR identity
    def getIdent(self):

        """
        Sets a new TOR identity (IP address) for the current connection

        This can especially be useful if WDFI blocks the current IP address
        """

        success = False
        count = 0
        #if we couldn't get a new identity, retry 5 times before moving on
        while(not success):
            try:
                with Controller.from_port(port=9051) as controller:
                    controller.authenticate(TOR_KEY)
                    controller.signal(Signal.NEWNYM)

                r = session.get("http://httpbin.org/ip", headers={'Connection':'close'})
                #print(r.text)
                success = True
            except requests.ConnectionError:
                #print("Retrying tor connection...")
                time.sleep(5)
                count = count + 1
                if(count >= 5):
                    break

    #gets the query URL for a LLC
    def getUrl(self, companyName):

        """
        Forms the query URL for a WDFI search.

        :param companyName: The company name to search
        :return: WDFI query URL
        :rtype: string
        """

        companyName = companyName.replace(' ', '+')
        return queryURL+companyName

    #returns the HTML page for a LLC found on WDFI
    def getRecordsHtml(self,companyName):

        """
        Returns the full http response for a query of the company name.

        ..note:: This is a request object, not raw HTML.

        :param companyName: The company name to query
        :return: HTTP response
        :rtype: requests.response
        """

        #print(TIMEOUT_SEARCH + (random.randint(0, 1000) / 250))
        time.sleep(TIMEOUT_SEARCH + (random.randint(0, 1000) / 250))  # prevent us from being flagged as a bot
        resp = session.post(self.getUrl(companyName), data = header, timeout = 5, headers={'Connection':'close'})

        regText = re.search(urlRegex, resp.text)

        if(regText is None):
            return "null"

        if(not(regText.group(0) is None)):
            retText = regText.group(0)
            retText = retText[9:retText.__len__()-3]
            time.sleep(TIMEOUT_CLICK_ON_SEARCH_RESULT + (random.randint(0, 1000) / 250))
            resp2 = session.post(query2URL+retText, data = header, timeout = 5, headers={'Connection':'close'})
            return resp2

        else:
            return "null"

    #finds a registered agent for a company
    def getRegAgent(self, companyName):

        """
        Returns the registered agent and address for a company

        :param companyName: the company name to get the registered agent for
        :return: A list containing [agent name, agent address]
        :rtype: list
        """

        #print(companyName)
        if(companyName in self.last_reg_agent_by_cmp):
            return self.last_reg_agent_by_cmp[companyName]
        resp = self.getRecordsHtml(companyName)

        try:
            html = resp.text
        except:
            self.last_reg_agent_by_cmp[companyName] = ["No Record Found", "No Address"]
            return ["No Record Found", "No Address"]

        regTextStart = re.search(agentRegexBegin, html)
        regTextEnd = re.search(agentRegexEnd, html)
        retText = html


        if(regTextStart is None):
            #print(companyName + "------------WDFI-------> null")
            return "null"

        spanStart = regTextStart.span()
        spanEnd = regTextEnd.span()
        retText = retText[spanStart[1]:spanEnd[1]]

        regTextStart = re.search('<div>', retText)
        regTextEnd = re.search('<\/div>', retText)
        spanStart = regTextStart.span()
        spanEnd = regTextEnd.span()
        name = retText[spanStart[1]:spanEnd[0]].replace(",", " ").replace("&amp;", "&").strip()

        regTextStart = re.search('<address>', retText)
        regTextEnd = re.search('<\/address>', retText)
        spanStart = regTextStart.span()
        spanEnd = regTextEnd.span()
        address = retText[spanStart[1]:spanEnd[0]]

        address = address.replace("<br />"," ")
        address = address.replace("\r\n", " ")
        address = re.sub(' +', ' ', address)

        address = address.replace(",", " ").strip()
        #print(name+","+address)
        #save list into dict for quick lookup later
        self.last_reg_agent_by_cmp[companyName] = [name,address]
        return [name,address] #return these as a list, so they can be seperate columns
