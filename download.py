import git
import requests
import os, time
from os import path as osp
import threading
import shutil
import argparse

latency = 7
cwd = os.getcwd()
perpage = 100

semaphore = threading.Semaphore(20)
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
        semaphore.acquire()
        if osp.exists(path):
            print("Removing %s" % local_fullname)
            shutil.rmtree(path)

        git.Repo.clone_from(self.repo["html_url"], path, )
        downloaded.write("%s\n" % self.repo["full_name"])
        downloaded.flush()
        semaphore.release()
        print("Done %s" % local_fullname)

downloaded_set = set()
scheduled_set = set()
if osp.exists("downloaded.txt"):
    downloaded_set = set([str(line).strip() for line in open("downloaded.txt").readlines()])
    print("Preloaded %s repos" % len(downloaded_set))
if not osp.exists("data"):
    os.mkdir("data")
threads = []
for page in range(100):
    semaphore.acquire()
    result = requests.get("https://api.github.com/search/repositories", params=
    dict(sort="stars", order="desc", q="language:python", perpage=perpage, page=page)).json()
    if 'items' in result:
        print("Page %s read" % page)
    else:
        print("Wait a bit")

    for repo in result["items"]:

        if repo["full_name"]  in downloaded_set:
            print("Already exists %s" % repo["full_name"])
        elif repo["full_name"]  in scheduled_set:
            print("Already scheduled %s" % repo["full_name"])
        else:
            t = MyThread(repo)
            t.start()
            threads.append(t)
            scheduled_set.add(repo["full_name"])


    semaphore.release()
    time.sleep(latency)

for t in threads:
    t.join()



