import argparse
import sys 
import os 
import pandas as pd
import datetime
import re
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

def parse_result_method(r):
    m = re.compile(r'(percentile)(\d{2})')
    m = m.match(r)
    if m:
        return [m.group(1), int(m.group(2)) / 100 ]
    else:
        return ['mean']
    

def main(args):
    # define args from the CLI 
    org = args.org
    target_branch = args.targetBranch
    excluded_repos = args.excludedRepos
    verbose = args.verbose
    start_date = convert_time(args.startDate)
    end_date = convert_time(args.endDate)

    base_url = 'https://api.github.com'
    token = os.environ['GITHUB_ACCESS_TOKEN']

    g = Github(token, org)

    params = {'per_page': 100}
    repos = g.get_repo_list(params) 
    repos = ['voice', 'numbers']

    if not excluded_repos:
        excluded_repos = []
    stats = {} 
    now = datetime.datetime.now()
    for repo in repos: 

        if verbose:

            print(f"repo: {repo}")

        if repo not in excluded_repos:

            params = {'state' : "all",'per_page': 100, 'base': target_branch }

            commits = g.get_commit_list(repo, params)
            # process the commits
            for commit in commits['data'][0]:

                try:

                    #commit.get('commit').get('author').get('name')
                    author = (commit.get('author').get('login'))
                    print (author)
                    if stats.get(author) is None:

                        stats[author] = {}
                        stats[author]['commit_count'] = 1
                    else:

                        stats[author]['commit_count'] += 1 

                except AttributeError:

                    #TODO add better error handling. For now skip the PR
                    pass
                
            prs = g.get_pr_list(repo, params)      
            for pr_list in prs['data']: 
                
                for pr in pr_list:
                    created_at = convert_time(pr.get("created_at"))
                    merged_at = convert_time(pr.get("merged_at"))
                    closed_at = convert_time(pr.get("closed_at"))
                    #print(pr.get('user').get('login'))

        print(stats)
                      
                    

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
        required=False,
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
        required=False,
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

    parser.add_argument( 
        '-rm', 
        '--resultMethod',
        type=str, 
        required=False,
        help="Options are percentile[0-9][0-9] or mean.  Example --rm percentile90  "
    ) 

    parser.add_argument( 
        '-sd', 
        '--startDate',
        type=str, 
        required=True,
        help=""
    ) 

    parser.add_argument( 
        '-ed', 
        '--endDate',
        type=str, 
        required=True,
        help=""
    ) 

    args = parser.parse_args()
    main(args)

