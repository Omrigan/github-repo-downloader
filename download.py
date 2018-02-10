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

threads = []

semaphore = None
downloaded = open("downloaded.txt", "a")


def get_local_filename(fullname):
    user, name = tuple(fullname.split("/"))
    local_fullname = "%s@%s" % (user, name)
    path = osp.join(osp.join(cwd, 'data'), local_fullname)
    return path


def get_github_filename(fullname):
    user, name = tuple(fullname.split("@"))
    return "%s/%s" % (user, name)


class MyThread(threading.Thread):
    def __init__(self, repo):
        self.repo = repo
        super(MyThread, self).__init__()

    def run(self):
        path = get_local_filename(self.repo["full_name"])
        semaphore.acquire()
        if osp.exists(path):
            print("Removing %s" % self.repo["full_name"])
            shutil.rmtree(path)

        git.Repo.clone_from(self.repo["html_url"], path, )
        downloaded.write("%s\n" % self.repo["full_name"])
        downloaded.flush()
        semaphore.release()
        print("Done %s" % self.repo["full_name"])


downloaded_set = set()


def parse(number):
    scheduled_set = set()

    for page in range(100):
        semaphore.acquire()
        result = requests.get("https://api.github.com/search/repositories", params=
        dict(sort="stars", order="desc", q="language:python", perpage=perpage, page=page)).json()
        if 'items' in result:
            print("Page %s read" % page)
        else:
            print("Wait a bit")

        for repo in result["items"]:
            if number is not None and (len(downloaded_set) + len(scheduled_set)) >= number:
                return
            if repo["full_name"] in downloaded_set:
                print("Already exists %s" % repo["full_name"])
            elif repo["full_name"] in scheduled_set:
                print("Already scheduled %s" % repo["full_name"])
            else:
                t = MyThread(repo)
                t.start()
                threads.append(t)
                scheduled_set.add(repo["full_name"])

        semaphore.release()
        time.sleep(latency)


def clear():
    for local_filename in os.listdir("data"):
        fullname = get_github_filename(local_filename)
        if fullname not in downloaded_set:
            print("Removing %s" % local_filename)
            shutil.rmtree(get_local_filename(fullname))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download repos from github.')
    parser.add_argument('--repos_number', type=int, help="Number of repos which will be downloaded")
    parser.add_argument('--jobs', default=20)
    parser.add_argument('--clear', action="store_true")

    args = parser.parse_args()

    semaphore = threading.Semaphore(args.jobs)
    if osp.exists("downloaded.txt"):
        downloaded_set = set([str(line).strip() for line in open("downloaded.txt").readlines()])
        print("Preloaded %s repos" % len(downloaded_set))
    if not osp.exists("data"):
        os.mkdir("data")
    if not args.clear:
        parse(number=args.repos_number)
        for t in threads:
            t.join()
    else:
        clear()
