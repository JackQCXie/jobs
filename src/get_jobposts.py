# %%
import os
import time
from lxml import html
import regex

import requests
from datetime import datetime
import pandas
import argparse

# %%
parser = argparse.ArgumentParser(
                    prog='get_linkedin_jobposts',
                    description='Scrapes LinkedIn job posts for a given city'
                    )

parser.add_argument('-l', '--location', default='vancouver')

# set default date to today
today = datetime.now().strftime('%Y%m%d')
parser.add_argument('-d', '--date', default=today)

args, unknown = parser.parse_known_args()

# global arguments
location = args.location
date = args.date

# destination file
loc = ''.join(c for c in location if c.isalpha())
dst = os.path.abspath(f'../data/jobposts/{date}-{loc}.csv')
print('dst:', dst)

# %%
def search_jobs(params):
    """
    Generator function to scrape job posts from LinkedIn.
    Note: Linkedin limits outputs to 1000 results per search parameter.
    """
    
    # URL for LinkedIn job posts
    # Note: This URL may change, and scraping LinkedIn may violate their terms of service.
    # Use responsibly and consider using their official API if available.
    url = 'https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search'
    headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36'
        }
    
    # request the job postings
    sleep = 1
    while True:
        resp = requests.get(url, params=params, headers=headers)
        if resp.status_code == 429: # too many requests
            time.sleep(sleep)
            sleep += 1
        else:
            break
        

    print('resp-url:', resp.url)

    # exit function if bad response or empty HTML document
    if (not resp) or ('<!DOCTYPE html>\n\n<!---->' in resp.text):
        print('-'*50)
        print(f'request-url [status {resp.status_code}]: {resp.url}')
        print('Bad request or no more jobs found.') # TODO: 
        yield

    # iterate over job list items
    doc = html.fromstring(resp.content)
    lis = doc.xpath('//li')
    
    for li in lis:

        # get the text content of the job posting
        texts = li.xpath('.//text()')
        texts = [regex.sub(r'\s+', ' ', x).strip() for x in texts]
        
        # remove empty strings
        texts = [x for x in texts if x] 

        # remove duplicate text
        texts = list(dict.fromkeys(texts))

        # get links of job postings
        anchors = li.xpath('.//a')
        hrefs = [a.get('href') for a in anchors]

        # yield result
        res = {
            'position' : texts[0]   if len(texts) > 0 else None,
            'company' : texts[1]    if len(texts) > 1 else None,
            'location' : texts[2]   if len(texts) > 2 else None,
            'status' : texts[3]     if len(texts) > 3 else None,
            'job_url' : hrefs[0].split('?')[0],
            'firm_url': hrefs[1]    if len(hrefs) > 1 else None,
            'search_keyword' : params['keywords'],
        }

        yield res

# %%
def get_number_jobs(location):
    '''
    Get number of jobs from search page
    '''
    
    # approx. number of job postings
    url = f'https://www.linkedin.com/jobs/search?location={location}'
    resp = requests.get(url)
    doc = html.fromstring(resp.content)
    njobs = doc.xpath('//span[@class="results-context-header__job-count"]//text()')[0]

    return int(''.join(c for c in njobs if c.isnumeric()))

# %%
def save_data(data, dst=dst):
    '''
    Save data
    '''

    df = pandas.DataFrame(data)
    
    df.to_csv(dst, index=False)

    print(f'Saved {df.shape}:', dst)
    print('Now:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

# %%
def get_freq(data):
    '''
    Get keyword frequency from job post and companies
    
    TODO: create filter for searched keywords
    '''
    
    df = pandas.DataFrame(data)

    # get keywords from job postings
    pos_str = ' '.join(df['position'].tolist())
    comp_str = ' '.join(df['company'].tolist())
    join_str = pos_str + ' ' + comp_str
    join_str = join_str.lower()

    # remove non-alphabetic characters
    remove = [c for c in set(join_str) if not c.isalpha()]
    for c in remove:
        join_str = join_str.replace(c, ' ')

    words = join_str.split()

    # get word frequencies
    res = [{'keyword' : w, 'count' : words.count(w)} for w in set(words) if len(w) > 2]
    return res
    

# %%
# initialize
if __name__ == '__main__':
    
    print('Location:', location)
    print('Start time:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    njobs = get_number_jobs(location)

    if not os.path.exists(dst):
        
        # initialize empty data structures
        data = []
        job_urls = set()
        searched_kws = set()
        kw = ''

    else:
        
        # initialized from saved data
        df = pandas.read_csv(dst)
        
        data = df.to_dict(orient='records')
        job_urls = set(df['job_url'])
        searched_kws = set(df['search_keyword'].dropna())
        kw = df['search_keyword'].dropna().iloc[-1]

        print(f'Continue from previous {len(data):,} records')

# %%
if __name__ == '__main__':

    # break outer loop if most jobs found or no new keywords found
    while True:

        print('*'*50)
        print(f'search-keyword ({len(searched_kws):,}):', kw)

        # break inner loop if no more results in page (usually 10 results)
        run_search, start = True, 0
        while run_search:

            params = {
                'location': location,
                'start': start,
                'keywords' : kw,
                }
            
            search_results = search_jobs(params)
            for search_res in search_results:

                start += 1 # local counter (inner loop)

                # break inner loop if no more results
                if not search_res:
                    run_search = False
                    break

                # add to data if new job url
                job_url = search_res['job_url'].split('?')[0]
                
                if job_url not in job_urls:
                    job_urls.add(job_url)
                    data.append(search_res)

                    # report progress
                    print(f'[job {len(data):,} of {njobs:,}+]', datetime.now(), job_url)

        # save data
        save_data(data)

        # break outer loop if most jobs found
        if len(data) >= njobs:
            print('Most jobs found.')
            break

        # get word frequencies
        freq = get_freq(data)

        # filter top unsearched keyword
        wf = pandas.DataFrame(freq)
        wf = wf.sort_values(by='count', ascending=False)
        cond = ~wf['keyword'].isin(searched_kws)
        kws = wf[cond]

        # break outer loop if no new keywords found
        if kws.empty:
            print('No more keywords found.')
            break

        # add new keyword to list of searched
        kw = kws.iloc[0]['keyword']
        searched_kws.add(kw)


    print('=' * 50)
    print('Script complete.')

# %%



