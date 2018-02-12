import git
import requests
import os, time
import threading
import shutil
import argparse
import codecs
import json
import sys

from collections import Counter

from os import path as osp

REPOS_DIR = 'data/repos'
DATA_DIR = 'data/prepared'
DOWNLOADED_FILE = "data/downloaded.txt"

if not osp.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
if not osp.exists(REPOS_DIR):
    os.makedirs(REPOS_DIR)

latency = 7
cwd = os.getcwd()
perpage = 100

threads = []

semaphore = None
downloaded = open(DOWNLOADED_FILE, "a")


def get_local_fullname(fullname):
    user, name = tuple(fullname.split("/"))
    return "%s@%s" % (user, name)


def get_local_filename(fullname):
    path = osp.join(osp.join(cwd, REPOS_DIR), get_local_fullname(fullname))
    return path


def get_github_filename(fullname):
    user, name = tuple(fullname.split("@"))
    return "%s/%s" % (user, name)


class RepoCloneThread(threading.Thread):
    def __init__(self, repo, num_latest_commits=100):
        self.repo = repo
        self._num_latest_commits = num_latest_commits
        super(RepoCloneThread, self).__init__()

    @staticmethod
    def _get_readme_content(repo):
        repo_dir = os.path.dirname(repo.git_dir)
        readme_file = next(
            (os.path.join(root, filename)
             for root, _, files in os.walk(repo_dir) for filename in files
             if osp.splitext(filename)[0] == 'README'),
            None
        )
        if not readme_file:
            print('README not found in %s' % repo_dir)
            result = ''
        else:
            with open(readme_file) as f:
                result = f.read()
                if sys.version_info[0] == 2:
                    result = result.decode('utf-8')
        return result

    @staticmethod
    def _dump_data(name, **kwargs):
        with codecs.open(os.path.join(DATA_DIR, name), mode='w', encoding='utf-8') as fout:
            fout.write(json.dumps(kwargs, sort_keys=True, indent=4))

    def run(self):
        print("Started %s" % self.repo["full_name"])
        path = get_local_filename(self.repo["full_name"])
        if osp.exists(path):
            print("Removing %s" % self.repo["full_name"])
            shutil.rmtree(path)

        repo = git.Repo.clone_from(self.repo["html_url"], path)
        authors = Counter(
            (commit.author.name, commit.author.email)
            for commit in repo.iter_commits(max_count=self._num_latest_commits)
        )
        self._dump_data(
            name=get_local_fullname(self.repo["full_name"]),
            readme_content=self._get_readme_content(repo),
            main_contributor=dict(zip(('name', 'email'), authors.most_common(1)[0][0]))
        )
        downloaded.write("%s\n" % self.repo["full_name"])
        downloaded.flush()
        semaphore.release()
        print("Done %s" % self.repo["full_name"])


downloaded_set = set()


def get_page(page):
    """Get a part of a list of popular repositories"""
    while True:
        result = requests.get("https://api.github.com/search/repositories", params=
        dict(sort="stars", order="desc", q="language:python", perpage=perpage, page=page)).json()
        if 'items' in result:
            print("Page %s read" % page)
            return result
        else:
            print("Error")
            print(result)
            time.sleep(20)


def parse(number):
    '''Download #number repos'''
    scheduled_set = set()

    for page in range(100):
        result = get_page(page)
        for repo in result["items"]:
            if number is not None and (len(downloaded_set) + len(scheduled_set)) >= number:
                return
            if repo["full_name"] in downloaded_set:
                print("Already exists %s" % repo["full_name"])
            elif repo["full_name"] in scheduled_set:
                print("Already scheduled %s" % repo["full_name"])
            else:
                semaphore.acquire()
                t = RepoCloneThread(repo)
                t.start()
                threads.append(t)
                scheduled_set.add(repo["full_name"])

        time.sleep(latency)


def clear():
    for local_filename in os.listdir(REPOS_DIR):
        fullname = get_github_filename(local_filename)
        if fullname not in downloaded_set:
            print("Removing %s" % local_filename)
            shutil.rmtree(get_local_filename(fullname))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download repos from github.')
    parser.add_argument('--repos_number', type=int, help="Number of repos which will be downloaded")
    parser.add_argument('--jobs', type=int, default=20)
    parser.add_argument('--clear', action="store_true")

    args = parser.parse_args()

    semaphore = threading.Semaphore(args.jobs)
    if osp.exists(DOWNLOADED_FILE):
        downloaded_set = set([str(line).strip() for line in open(DOWNLOADED_FILE).readlines()])
        print("Preloaded %s repos" % len(downloaded_set))
    if not args.clear:
        parse(number=args.repos_number)
        for t in threads:
            t.join()
    else:
        clear()
