#!/usr/bin/env python
#
# OkCupid library. Currently parses messages, will also parse/cache user
# profiles.
#
# TODO:
# * utf8 (chinese) output isn't working. parsing seems to work fine not sure
# why the output is fucked.
# * profiles
#   * cache in redis
#   * try and pull down star ratings given (it's in javascript so it may not be possible)
# * feature extraction for messages:
#   * number of words
#   * number of questions
#   * avg. word length
#   * emoticons
#   * match percentages
#   * message/profile similarity
#   * profile similarity
#   * message deltas
#   * mutually chosen
#   * I/me vs. you
# * measures of success
#   * # of replies
#   * got name
#   * got phone number
# * tab-delimited output
#

import sys
from optparse import OptionParser
from getpass import getpass
import re
import traceback

from dateutil.parser import parse
from scrape import *

replycolormap = {'red': 'very selectively', 'yellow': 'selectively', 'green': 'often', '': 'contacted'}

def getselectivity(profpage):
    distance = int(profpage.find(re.compile('\d+ miles')).text.split()[0])

    replies = ''
    for color in ['red', 'yellow', 'green']:
        try:
            replies = profpage.first('span', class_=color)
            replies = color
        except ScrapeError:
            pass

    return replycolormap[replies]

def parseprofile(profpage):
    """Parse user's profile (both for archival and statistics purposes."""
    # This has annoying JSON encoding (\u2019 for '). Fix it.
    essays = [(atag.text, atag.next('div').text) for atag in profpage.all('a', class_='essay_title')]
    detailsdiv = profpage.first('div', id='profile_details')
    profdetails = [(x.text, y.text) for (x, y) in zip(detailsdiv.all('dt'), detailsdiv.all('dd'))]

    match = int(profpage.first('span', class_='match').content.split('%')[0])
    friend = int(profpage.first('span', class_='friend').content.split('%')[0])
    enemy = int(profpage.first('span', class_='enemy').content.split('%')[0])

    username, age, gender, orientation, relationshipstatus, city, state = \
            filter(lambda x: x != '/', profpage.first('div', class_='details').text.split())

    replies = getselectivity(profpage)

    return {'essays': dict(essays),
            'profdetails': dict(profdetails),
            'match': match,
            'friend': friend,
            'enemy': enemy,
            'username': username,
            'age': age,
            'gender': gender,
            'orientation': orientation,
            'relationshipstatus': relationshipstatus,
            'city': city,
            'state': state,
            'replies': replies}

def messageurls(messagepage):
    return ['http://www.okcupid.com/messages?readmsg=true&threadid=%s&folder=1' % x.content
            for x in messagepage.findall(re.compile(r'threadid=(\d+)'), group=1)]

def skip(msg):
    try:
        heading = msg.first('strong', id='message_heading').content
        if heading == u"How'd You Like to Help Moderate the Site?":
            return True
    except ScrapeError:
        return False

def nextpage(inbox):
    """Call to find 'li' will fail with ScrapeError if we're at the end of the
    inbox."""
    nextli = inbox.first('li', class_='next')
    atag = nextli.first('a')
    return s.go('http://www.okcupid.com%s' % atag['href'])

def parsemessage(msg):
    msgtexts = [x.content for x in msg.all('div', class_='message_body')]
    msgmobilep = ['<em class="mobilemsg">' in x for x in msgtexts]
    # Remove contiguous spaces, HTML tags and mobile text
    msgtexts = [re.sub(re.compile('\s\s'), ' ', re.sub(re.compile('<.*?>|Sent from the OkCupid app'), '', x)).strip() for x in msgtexts]

    try:
        match = int(msg.first('span', class_='match').content.split('%')[0]),
        friend = int(msg.first('span', class_='friend').content.split('%')[0]),
        enemy = int(msg.first('span', class_='enemy').content.split('%')[0]),
        activep = True
    except ScrapeError:
        match = 'NA'
        friend = 'NA'
        enemy = 'NA'
        activep = False

    return {
            'msgtexts': msgtexts,
            'msgauthors': [x['title'] for x in msg.all('a', class_='photo')],
            'msgdates': [parse(x.content.replace('&ndash; ', '')) for x in msg.all('span', class_='fancydate')],
            'msgmobilep': msgmobilep,

            'match': match,
            'friend': friend,
            'enemy': enemy,
            'activep': activep,
            'wechosep': 'We chose each other!Reply to this message to contact me.' in msgtexts[0],


            'buddyname': msg.first('title').content.split(' ')[-1],
            }

def printparsedmsg(parsedmsg):
    print('== %s ==' % parsedmsg['buddyname'])
    if parsedmsg['activep']:
        print('match: %d%%' % parsedmsg['match'])
        print('friend: %d%%' % parsedmsg['friend'])
        print('enemy: %d%%' % parsedmsg['enemy'])

    print('is active: %s' % parsedmsg['activep'])
    print('both chose: %s' % parsedmsg['wechosep'])

    for text, author, date, mobilep in zip(parsedmsg['msgtexts'],
                                           parsedmsg['msgauthors'],
                                           parsedmsg['msgdates'],
                                           parsedmsg['msgmobilep']):
        print('%s <%s>: %s' % (author, str(date), text))
    print('')

def features(parsedmsg):
    pass

def printtabline(parsedmsg):
    pass

def main():
    """main function for standalone usage"""
    usage = "usage: %prog [options] > stats"
    parser = OptionParser(usage=usage)
    parser.add_option('-u', '--username', default='')
    parser.add_option('-p', '--password', default='')

    (options, args) = parser.parse_args()

    if len(args) != 0:
        parser.print_help()
        return 2

    # do stuff
    creds = {'username': options.username if options.username else raw_input('username: '),
             'password': options.password if options.password else getpass('password: ')}

    login = s.go('http://www.okcupid.com')
    userpage = s.submit(login.first('form'), paramdict=creds)
    inbox = s.go('http://www.okcupid.com/messages')

    while True:
        for url in messageurls(inbox):
            msg = s.go(url)
            if skip(msg): continue

            try:
                parsedmsg = parsemessage(msg)
                printparsedmsg(parsedmsg)
            except:
                sys.stderr.write('Failed to parse message "%s"\n' % url)
                traceback.print_exc()

            s.back()

        try:
            inbox = nextpage(inbox)
        except ScrapeError: # Fully parsed inbox!
            sys.stderr.write('Done\n')
            break

if __name__ == '__main__':
    sys.exit(main())
