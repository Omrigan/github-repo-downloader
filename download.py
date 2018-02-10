import git, plumbum
import requests
import os, asyncio, time
from os import path as osp
import threading

latency = 7
cwd = os.getcwd()
perpage = 100


class MyThread(threading.Thread):
    def __init__(self, repo):
        self.repo = repo
        super(MyThread, self).__init__()

    def run(self):
        name = self.repo["name"]
        user = self.repo["owner"]["login"]
        fullname = "(%s)%s" % (user, name)
        path = osp.join(osp.join(cwd, 'data'), fullname)
        if osp.exists(path):
            print("Already exists %s" % fullname)
        else:
            git.Repo.clone_from(repo["html_url"], path)
            print("Done %s" % fullname)


loop = asyncio.get_event_loop()
threads = []
for page in range(1):
    result = requests.get("https://api.github.com/search/repositories", params=
    dict(sort="stars", order="desc", q="language:python", perpage=perpage, page=page)).json()
    if 'items' in result:
        print("Page %s read" % page)

    for repo in result["items"]:
        t = MyThread(repo)
        t.start()
        threads.append(t)
    time.sleep(latency)

for t in threads:
    t.join()
