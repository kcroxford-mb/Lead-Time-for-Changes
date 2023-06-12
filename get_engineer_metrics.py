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

def print_results(results: List, start_date, end_date, target_branch) -> None:
    print ("-" * 30 )  
    print ("Results:")
    print (f"-Date Range: {start_date} - {end_date}")
    print (f"-Merged To Branch: {target_branch}")
    for result in results:
        repo = result.get('repo')
        print (f'- Repo : {repo}')
        for k,v in result.get('stats').items():
            engineer = k
            commit_count = v.get('commit_count')
            pr_opened_count = v.get('pr_count')

            if pr_opened_count is None:
                pr_opened_count = 0 
            pr_merged_count = v.get('prs_merged')
            if pr_merged_count is None:
                pr_merged_count = 0 
            pr_closed_count = v.get('prs_closed')
            if pr_closed_count is None:
                pr_closed_count = 0 
            p90_merge = v.get('p90_merge')
            if p90_merge is None:
                p90_merge = 'N/A'
            print (f'-- engineer:{engineer}, commits:{commit_count}, prs_opened:{pr_opened_count}, prs_merged:{pr_merged_count}, prs_closed:{pr_closed_count}, p90_days_to_merge:{p90_merge} ')
    print ("-" * 30 )

    
def process_commits(commits,stats,start_date,end_date)->List[Dict]:
    for commit_list in commits['data']:
        for commit in commit_list:
            created_at = convert_time(commit.get("commit").get('author').get('date'))
            if start_date <= created_at <= end_date:
                try:
                    engineer = (commit.get('author').get('login'))
                    if stats.get(engineer) is None:
                        stats[engineer] = {}
                        stats[engineer]['commit_count'] = 1
                    else:
                        stats[engineer]['commit_count'] += 1 
                except AttributeError:
                    #TODO add better error handling. For now skip the PR
                    pass
    return stats

def process_ttm(stats: List, ttm:List )->List[Dict]:
    for k, v in ttm.items():
        p90 = round(pd.Series(v).quantile(.90))
        stats[k]['p90_merge'] = p90
    return stats


def process_prs(prs: List ,
                stats :List ,
                start_date : datetime.datetime,
                end_date: datetime.datetime)->List[Dict]:
    # Gather the p90 time to merge into develop
    e = {}
    for pr_list in prs['data']: 
        for pr in pr_list:
            created_at = convert_time(pr.get("created_at"))
            merged_at = convert_time(pr.get("merged_at"))
            closed_at = convert_time(pr.get("closed_at"))
            if start_date <= created_at <= end_date:
                engineer = (pr.get('user').get('login'))
                if stats.get(engineer) is None:
                    stats[engineer] = {}
                    stats[engineer]['pr_count'] = 1
                else:
                    if stats[engineer].get('pr_count') is None:
                        stats[engineer]['pr_count'] = 1
                    else:
                        stats[engineer]['pr_count'] += 1 
                
                # get the time to merge on the PR
                if merged_at: 
                    if stats[engineer].get('prs_merged') is None:
                        stats[engineer]['prs_merged'] = 1
                    else:
                        stats[engineer]['prs_merged'] += 1            
                    time_to_merge = merged_at - created_at

                    if not e.get(engineer):
                        e[engineer] = []
                        e[engineer].append(time_to_merge.days)
                    else:
                        e[engineer].append(time_to_merge.days)

                # Check if there are PRs that have been closed
                if closed_at and not merged_at: 
                    if stats[engineer].get('prs_closed') is None:
                        stats[engineer]['prs_closed'] = 1
                    else:
                        stats[engineer]['prs_closed'] += 1            


    stats = process_ttm(stats, e) 
    return stats
    

def main(args):
    # define args from the CLI 
    org = args.org
    excluded_repos = args.excludedRepos
    verbose = args.verbose
    start_date = convert_time(args.startDate)
    end_date = convert_time(args.endDate)
    target_branch = args.targetBranch

    token = os.environ['GITHUB_ACCESS_TOKEN']
    g = Github(token, org)

    params = {'per_page': 100}
    repos = g.get_repo_list(params) 

    if not excluded_repos:
        excluded_repos = []

    results = []
    for repo in repos: 

        stats = {}
        if verbose:

            print(f"repo: {repo}")

        if repo not in excluded_repos:

            params = {'state' : "all",'per_page': 100, 'base': target_branch }
            
            # Process the commits
            commits = g.get_commit_list(repo, params)
            stats = process_commits(commits,stats,start_date, end_date)

            #Process the PRs 
            prs = g.get_pr_list(repo, params)   
            stats =  process_prs(prs,stats,start_date, end_date) 

        r = {'repo' : repo, 'stats' : stats}
        results.append(r)

    print_results(results, start_date, end_date, target_branch)
                      
                    

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

