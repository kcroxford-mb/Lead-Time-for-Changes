import argparse
import sys 
import os 
import pandas as pd
import datetime
from typing import List,Dict
from github import Github

def convert_time(ts):
    '''
    Converts the timestamps that are strings to datetime.strptime object 
    '''
    if not ts:
        return None
    return datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ')

def print_results(results: List) -> None:
    print ("-" * 30 )
    print ("Results:")
    for result in results:
        repo = result.get('repo')
        lt = result.get('lead_time')

        print (f"---repo: {repo}, lead_time {lt.days}d {lt.seconds // 3600}h ")
    print ("-" * 30 )


def main(args):
    # define args from the CLI 
    org = args.org
    target_branch = args.targetBranch
    ref_string = args.refString
    excluded_repos = args.excludedRepos
    max_days = args.maxDays
    repo = args.repo
    verbose = args.verbose

    base_url = 'https://api.github.com'
    token = os.environ['GITHUB_ACCESS_TOKEN']

    g = Github(token, org)

    # If a specific repo is defined add it to the repos list. Otherwise, get the list of repos from the API
    if repo:
        repos = [repo]
    else:
        params = {'state' : "closed", 'per_page': 100}
        repos = g.get_repo_list(params) 

    if not excluded_repos:
        excluded_repos = []
    
    results = []
    now = datetime.datetime.now()
    for repo in repos: 
        if verbose:
            print(f"repo: {repo}")

        if repo not in excluded_repos:
            params = {'state' : "closed", 'per_page': 100, 'base': target_branch }
            prs = g.get_pr_list(repo, params)
            times = []
            included_releases = []
            
            for pr_list in prs['data']: 
                
                for pr in pr_list:
                    created_at = convert_time(pr.get("created_at"))
                    merged_at = convert_time(pr.get("merged_at"))
                    closed_at = convert_time(pr.get("closed_at"))
                    # Ignore PRs that are not merged
                    if merged_at:
                        days =  now - created_at # check when the PR was created
                        # only continue if the PR was created less than max_days days ago 
                        
                        if days.days <= max_days:
                            h = pr.get('head')
                            # Search for PRs where 'release' is in the reference field
                            # TODO change to regex 
                            
                            if ref_string in h.get('ref').lower():  
                                included_releases.append(h.get('ref').lower())
                                params = {}
                                if verbose:
                                    print(f"-release: {h.get('ref').lower()}")
                                
                                #Get all of the commits 
                                c = g.get_commit_list(repo, pr.get('number'), params )

                                for commit in c['data'][0]:
                                    try:
                                        if verbose:
                                            print(f"--commit_message: {commit.get('message')}") 
                                            print(f"--author: {commit.get('commit').get('author')}")
                                            print(f"--date: {commit.get('commit').get('author').get('date')}")
                                        # Get the date of the commit 
                                        c = commit.get('commit').get('author').get('date')
                                        c = convert_time(c)
                                        # subtract the PR merge time from the commit creation date. 
                                        times.append(merged_at - c)
                                        
                                    except AttributeError:
                                        #TODO add better error handling. For now skip the PR
                                        pass
                                    
            # Skip if no commits added to times list
            if len(times) != 0:
                lt = pd.to_timedelta(pd.Series(times)).quantile(.90)
                #lt = pd.to_timedelta(pd.Series(times)).mean()
                if lt is not pd.NaT: 
                    result = {
                        'repo' : repo,
                        'releases' : included_releases,
                        'lead_time' : lt
                    }
                    results.append(result)

    print_results(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument( 
        '-t', 
        '--targetBranch',
        type=str, 
        required=True,
        help="this is the branch that reflects a production deploymen. Typically 'main'"
    ) 

    parser.add_argument( 
        '-rs', 
        '--refString',
        type=str, 
        required=True,
        help="string to search for in a refering branch. If using gitflow, 'release' might be the string to match by "
    ) 

    parser.add_argument( 
        '-e', 
        '--excludedRepos',
        type=str, 
        required=False,
        action='append',
        help="list of repos to exclude "
    ) 

    parser.add_argument( 
        '-md', 
        '--maxDays',
        type=int, 
        required=True,
        help="maximum number of days to search (from now)"
    ) 

    parser.add_argument( 
        '-o', 
        '--org',
        type=str, 
        required=True,
        help="name of the organization in github"
    ) 

    parser.add_argument( 
        '-r', 
        '--repo',
        type=str, 
        required=False,
        help="Specify a specifc repo. Default is all in the org."
    ) 

    parser.add_argument( 
        '-v', 
        '--verbose',
        type=bool, 
        required=False,
        help="Print out more details"
    ) 

    args = parser.parse_args()
    main(args)

