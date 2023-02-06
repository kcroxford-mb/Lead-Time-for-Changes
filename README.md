# Lead-Time-for-Changes
Determine the lead time for changes from Github repo.  This works best with repos where a release branch is merged back into main


# Requirements
- Python 3.10
- pipenv

# Setup 
git clone https://github.com/kcroxford-mb/Lead-Time-for-Changes.git
cd Lead-Time-for-Change 
pipenv shell
pip install  -r requirements.txt

Create a github access token and save it as an environment variable named GITHUB_ACCESS_TOKEN

# Running the script 
There are a few command line options that need to be set 

    -t : this is the branch that reflects a production deploymen. Typically 'main
    -rs: string to search for in a refering branch. If using gitflow, 'release' might be the string to match by
    -e : Repo to exclude
    -md : maximum number of days to go back (based on the PR created_at value)
    -o : The github organization 
    -r : If you want to get data on a specific repo, specify it with this flag 
    -v : run "-v true" if you want to see the matching reference branches, and the commits within

## Gathering for a single repo 
python3 main.py \
 -o MY_ORG\
 -t main \
 -rs release \
 -md 31  \
 --repo MY_REPO


## Gathering for all repos under an organization
python3 main.py \
 -o MY_ORG\
 -t main \
 -rs release \
 -md 31  \
 -e EXCLUDED_REPO \
 -e EXCLUDED_REPO


