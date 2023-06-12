import json
import requests
import datetime
from typing import List,Dict
import pandas as pd
from github import Github

pd.Series(dtype='float64')

class Github:
    def __init__(self,token: str, org: str) -> None:
        self.token = token
        self.base_url = "https://api.github.com"
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

    
    def get_pr_list(self, repo: str, params: dict ) -> List:
        '''
        gathers all of the PRs that match the query params
        '''
        req = self.s.get(
                f"{self.base_url}/repos/{self.org}/{repo}/pulls", 
                params=params, 
        )
        return self.paginate(req)

    #'commits_url': 'https://api.github.com/repos/messagebird-dev/numbers/pulls/180/commits',
    def get_pr_commit_list(self, repo: str, number: int, params: dict ) -> List:
        '''
        gathers all of the PRs that match the query params
        '''
        req = self.s.get(
                f"{self.base_url}/repos/{self.org}/{repo}/pulls/{number}/commits", 
                params=params, 
        )
        return self.paginate(req)
    
    def get_commit_list(self, repo: str, params: dict ) -> List:
        '''
        gathers all of the commits that match the query params
        '''
        req = self.s.get(
                f"{self.base_url}/repos/{self.org}/{repo}/commits", 
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
    
      
    def paginate(self, d: requests.models.Response ) -> Dict:
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
            resp['data'].append(req.json()) 
            next_page = req.links.get('next') 
            resp['pages'] += 1 

        return resp
