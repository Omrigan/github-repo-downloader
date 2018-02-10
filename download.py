import git, plumbum
import requests
import os, asyncio, time
from os import path as osp
import threading
import shutil

latency = 7
cwd = os.getcwd()
perpage = 100

downloaded = open("downloaded.txt", "a")


class MyThread(threading.Thread):
    def __init__(self, repo):
        self.repo = repo
        super(MyThread, self).__init__()

    def run(self):
        name = self.repo["name"]
        user = self.repo["owner"]["login"]
        local_fullname = r"%s@%s" % (user, name)
        path = osp.join(osp.join(cwd, 'data'), local_fullname)
        if osp.exists(path):
            print("Removing %s" % local_fullname)
            shutil.rmtree(path)

        git.Repo.clone_from(self.repo["html_url"], path, )
        downloaded.write("%s\n" % self.repo["full_name"])
        downloaded.flush()
        print("Done %s" % local_fullname)

downloaded_set = set()
scheduled_set = set()
if osp.exists("downloaded.txt"):
    downloaded_set = set(open("downloaded.txt").readlines())
    print("Preloaded %s repos" % len(downloaded_set))
if not osp.exists("data"):
    os.mkdir("data")
threads = []
for page in range(100):
    result = requests.get("https://api.github.com/search/repositories", params=
    dict(sort="stars", order="desc", q="language:python", perpage=perpage, page=page)).json()
    if 'items' in result:
        print("Page %s read" % page)
    else:
        print("Wait a bit")

    for repo in result["items"]:
        if repo["full_name"] not in downloaded_set and repo["full_name"] not in scheduled_set:
            t = MyThread(repo)
            t.start()
            threads.append(t)
            scheduled_set.add(repo["full_name"])
        else:
            print("Already exists %s" % repo["full_name"])
    time.sleep(latency)

for t in threads:
    t.join()
