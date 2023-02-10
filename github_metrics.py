#!/usr/bin/env python
# coding: utf-8


# In[394]:

# This is an export from a Jupyter Notebook. The code should be cleaned up

import os
import json
import requests
import datetime
from typing import List,Dict
import pandas as pd


class Github:
    def __init__(self,base_url: str,token: str, org: str) -> None:
        self.token = token
        self.base_url = base_url
        self.org = org
        self.headers = {
            "Accept": "application/vnd.github+json", 
            "Authorization" : f"Bearer {self.token}", 
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.s = requests.Session()
        self.s.headers.update(self.headers)
        
        
    def get_repo_list(self, params: dict ) -> List:
        '''
        gets a list of all of the repos under the org
        '''
        req = self.s.get(
            f"{self.base_url}/orgs/{self.org}/repos", 
            params=params
        )
        
        d = self.paginate(req)
        
        res = []
        for l in d['data']:
            for entry in l:
                res.append(entry['name'])
        return res

   
    def get_pr(self, repo: str, pr_num: int, params: dict ) -> List:
        '''
        gathers all of the PRs that match the query params
        '''
        req = self.s.get(
                f"{self.base_url}/repos/{org}/{repo}/pulls/{pr_num}", 
                params=params, 
        )

        return self.paginate(req)
    
    def get_pr_comment_list(self, repo: str, pr_num: int, params: dict ) -> List:
        '''
        gathers all of the PRs that match the query params
        '''
        req = self.s.get(
                f"{self.base_url}/repos/{org}/{repo}/pulls/{pr_num}/comments", 
                params=params, 
        )

        return self.paginate(req)

    def get_pr_review_list(self, repo: str, pr_num: int, params: dict ) -> List:
        '''
        gathers all of the PRs that match the query params
        '''
        req = self.s.get(
                f"{self.base_url}/repos/{org}/{repo}/pulls/{pr_num}/reviews", 
                params=params, 
        )

        return self.paginate(req)
    
    
    
    def get_pr_list(self, repo: str, params: dict ) -> List:
        '''
        gathers all of the PRs that match the query params
        '''
        req = self.s.get(
                f"{self.base_url}/repos/{org}/{repo}/pulls", 
                params=params, 
        )

        return self.paginate(req, 'pr')

    def get_commit_list(self, repo: str, number: int, params: dict ) -> List:
        '''
        gathers all of the PRs that match the query params
        '''
        req = self.s.get(
                f"{self.base_url}/repos/{org}/{repo}/pulls/{number}/commits", 
                params=params, 
        )

        return self.paginate(req)
    
    def get_pr_count(self, repo: str, params: dict) -> int:
        '''
        returns a count of how many PRs match the query params
        '''
        req = self.get_pr_list(repo, params)
        total = 0
        if req['pages'] != 1:
            for page in req['data']:
                total += len(page)
        else:   
            total = len(req['data'][0])
        
        return total
    
      
    def paginate(self, d: requests.models.Response, r_type=None ) -> Dict:
        '''
        Github's API uses the links for replies with multiple pages.
        '''
        resp = {'pages': 0, 'data' : []}
        next_page = None
        next_page = d.links.get('next')
        
        # without a next page, return
        if not next_page:
            resp['pages'] += 1 
            resp['data'].append(d.json())
            return resp
        
        # increment as the 1st page is already obtained
        resp['pages'] += 1
        resp['data'].append(d.json())

        # Iterate over the linked pagination
        while next_page is not None: 
            req = self.s.get(next_page.get('url'))
            if r_type == "pr":
                if self._exceeds_max_days(req, 30):
                    resp['data'].append(req.json())
                    break
            resp['data'].append(req.json()) 
            next_page = req.links.get('next') 
            resp['pages'] += 1 

        return resp
    
    def _exceeds_max_days(self, req, max_days) -> bool:
        created_at = req.json()[-1].get('created_at')
        #print (created_at)
        days = datetime.datetime.now() - convert_time(created_at)
        if  days.days >= max_days:
            #print ('Reached PRs that exceed max_days')
            return True
        
def convert_time(ts):
    '''
    Converts the timestamps that are strings to datetime.strptime object 
    '''
    if not ts:
        return None
    return datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ')


def time_to_merge(repo : List, q: float, max_days: int ) :
    '''
    function takes the list of PRs and calucates the time between
    the PR creation, until a merge event occurs. Will eventually be replaced by a 
    "lead time for change" function which will provide a better story about how long to takes for 
    a commit to make it into production. 
    '''
    times = []
    now = datetime.datetime.now()
    for prs in repo.get('data') :
        for pr in prs:
            create = convert_time(pr.get("created_at"))
            closed = convert_time(pr.get("closed_at")) 
            merged = convert_time(pr.get("merged_at"))
            days =  now - create # check when the PR was created
            if days.days <= max_days:
                try:
                    times.append(merged - create)
                except Exception:
                    # TODO create better error handling. 
                    pass
        if times: 
            return pd.to_timedelta(pd.Series(times)).quantile(q)       
        

def print_results(results: List) -> None:
    for result in results:
        repo = result.get('repo')
        lt = result.get('lead_time')
        print (f"---repo: {repo}, lead_time {lt.days}d {lt.seconds // 3600}h ")
          
               
def filter_by_date(prs: Dict, max_days ) -> List:
    resp = []
    for pr_list in prs['data']:
        for pr in pr_list:
            pr_created_at = convert_time(pr.get("created_at"))
            days = datetime.datetime.now() - pr_created_at 

            if days.days <= max_days:
                resp.append(pr)
    return resp


def filter_by_ref(prs: Dict, ref: str ) -> List:
    resp = []
    for pr_list in prs['data']:
        for pr in pr_list:
            pr_created_at = convert_time(pr.get("created_at"))
            days = datetime.datetime.now() - pr_created_at 
            h = pr.get('head')
            if ref_string in h.get('ref').lower():  
                resp.append(pr)
    return resp
        

def calc_repo_stats(repo : str, prs: List, max_days : int, debug=False ):
    ttrs = []
    discussions = []
    approvals = []
    for pr in prs:
        # Temp vars for each PR iteration
        t = False
        
        params = {}    
        pr_created_at = convert_time(pr.get("created_at"))
        days = datetime.datetime.now() - pr_created_at 
        pr_num = pr.get("number")
        if debug:
            print (f"-pr_number:{pr_num}")
        params = {}
        
        # Get Comments on the PR
        comments = g.get_pr_comment_list(repo, pr_num , params)
        _count = len(comments.get("data")[0])
        previous = None
        if _count != 0:
            for comment in comments.get('data')[0]:
                comment_date = convert_time(comment.get('created_at'))
                if not t:
                    ttr = comment_date - pr_created_at
                    ttrs.append(ttr)
                    previous = comment_date
                    if debug:
                        print ("--ttfr found in comments")
                    t = True 
                    continue
                dis = comment_date - previous
                discussions.append(dis)
                previous = comment_date
                
                
        # get PR Reviews if no comments.  
        reviews = g.get_pr_review_list(repo, pr_num , params)
        _count = len(reviews.get("data")[0])
        if _count != 0:
            for review in reviews.get('data')[0]:
                review_date = convert_time(review.get('submitted_at'))
                
                # Check if the PR is approved.  
                state = review.get('state')
                if state == 'APPROVED':
                    days_open = review_date - pr_created_at
                    if debug:
                        print (f"pr open for {days_open}" )
                    approvals.append(days_open)
                
                if not t:
                    ttr = review_date - pr_created_at
                    ttrs.append(ttr)
                    previous = review_date
                    if debug:
                        print ("--ttfr found in reviews")
                    t = True 
                    continue
                dis = review_date - previous
                discussions.append(dis)
                previous = review_date

    return { 
        'total_prs' : len(prs),
        'p90_ttfr' : pd.Series(ttrs).quantile(.90),
        'mean_ttfr' : pd.Series(ttrs).mean(),
        'max_ttfr' : pd.Series(ttrs).max(),
        'p90_discussion' : pd.Series(discussions).quantile(.90),
        'mean_discussion' : pd.Series(discussions).mean(),
        'max_discussion' : pd.Series(discussions).max(),
        'p90_pr_lifetime' : pd.Series(approvals).quantile(.90),
        'mean_pr_lifetime' : pd.Series(approvals).mean(),
        'max_pr_lifetime' : pd.Series(approvals).max()
    } 


# In[395]:

token = os.environ['GITHUB_ACCESS_TOKEN']
org = os.environ['GITHUB_ORG']
base_url = 'https://api.github.com'
target_branch = 'main'
max_days = 30

# Avoid a deprecation warning from Pandas
pd.Series(dtype='float64')

# Repos to exclude
excluded = [] 

g = Github(base_url, token, org)

params = {}
repos = g.get_repo_list(params)

target_branch = 'develop'
ref_string =  None #set this to a branch you want to match, like 'release' or 'rfc'
max_days = 30
stats = {}

# (Mean) Time to First Response
# (Mean) Discussion Response Time
# (mean) Lead time for changes

r = []

for repo in repos: 
    d = {}
    print (repo)
    if repo in excluded:
        continue

    params = {'state' : "closed", 'per_page': 100, 'base': target_branch }
    prs = g.get_pr_list(repo, params)
    f = filter_by_date(prs,  max_days )
    if ref_string:
        f = filter_by_ref(prs, ref_string )
        stats = calc_repo_stats(repo, f, max_days,debug=True)
    # GET TIME TO FIRST RESPONSE
    else:
        stats = calc_repo_stats(repo, f, max_days, debug=True)
    try:
        
        d['repo'] = repo 
        d['total_prs'] = stats.get('total_prs')
        
        d['p90_ttfr'] = stats.get('p90_ttfr')
        d['mean_ttfr'] = stats.get('mean_ttfr')
        d['max_ttfr'] = stats.get('max_ttfr')
        
        d['p90_dis'] = stats.get('p90_discussion')
        d['mean_dis'] = stats.get('mean_discussion')
        d['max_dis'] = stats.get('max_discussion')
        
        d['p90_lifetime'] = stats.get('p90_pr_lifetime')
        d['mean_lifetime'] = stats.get('mean_pr_lifetime')
        d['max_lifetime'] = stats.get('max_pr_lifetime')
        r.append(d) 
    except Exception as e:
        pass


# In[396]:

df = pd.DataFrame(r)
pd.set_option('display.max_rows', None)
filtered = df[df['total_prs']!=0]
filtered.sort_values(by='total_prs', ascending=False)




