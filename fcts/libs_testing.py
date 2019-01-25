
count = 0
for m in ["timeout_decorator","mysql","discord","frmc_lib","requests","re","asyncio","feedparser","datetime","time","importlib","traceback","sys"]:
    try:
        exec("import "+m)
    except ModuleNotFoundError:
        print("Library {} manquante".format(m))
        count +=1
if count>0:
    raise


import timeout_decorator, mysql, discord, frmc_lib, requests, re, asyncio, feedparser, datetime, time, importlib, traceback, sys


#Test traceback / sys :
def test_error(error):
    try:
        print("""```python
Traceback (most recent call last):
{T} {S}
```""".format(T=" ".join(traceback.format_tb(sys.exc_info()[2])),S=str(sys.exc_info()[0]).split("<class '")[1].split("'>")[0]+' : '+str(sys.exc_info()[1])) )
    except Exception as e:
        print(e)

#Test timeout_decorator :
@timeout_decorator.timeout(3)
def infinite_loop():
    while True:
        pass
def test_timeout():
    try:
        infinite_loop()
    except timeout_decorator.timeout_decorator.TimeoutError:
        print("Success")

#test discord :
def test_discord():
    if discord.__version__ != "1.0.0a":
        print("Mauvaise version de Discord ^^")
    help(discord.Guild.get_role)

#test importlib :
def test_importlib():
    importlib.reload(frmc_lib)
    print("Success")

#test frmc_lib :
def test_frmc():
    objet = frmc_lib.main(input("nom ? "),input("Type ? (Entité, Bloc, Item...) "))
    return objet

#test requests
def test_requests():
    mojang_status = requests.get("https://status.mojang.com/check").json()
    return mojang_status

#test re:
def test_re(text):
    r = re.search(r'Z_runner',text)
    return r!=None

#test asyncio / feedparser / datetime / time:
async def test_feedparser():
    url = 'https://www.youtube.com/feeds/videos.xml?channel_id=UC1sELGmy5jp5fQUugmuYlXQ'
    feeds = feedparser.parse(url)
    feed = feeds.entries[0]
    date = feed["published_parsed"]
    print(date)
    date = datetime.datetime(*date[:6])
    print(date)

def test_asyncio():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_feedparser())
    loop.close()


def main():
    print("Test 1 - traceback/sys")
    test_error(KeyError)
    print("\nTest 2 - timeout_decorator")
    test_timeout()
    print("\nTest 3 - discord")
    test_discord()
    print("\nTest 4 - importlib")
    test_importlib()
    print("\nTest 5 - frmc_lib")
    test_frmc()
    print("\nTest 6 - requests")
    test_requests()
    print("\nTest 7 - re")
    test_re(input("text : "))
    print("\nTest 8 - asyncio/feedparser/datetime/time")
    test_asyncio()

main()