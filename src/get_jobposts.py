# %%
import time
from lxml import html
import regex

import requests
from datetime import datetime
import pandas

# %%
def search_jobs(params):
    """
    Generator function to scrape job posts from LinkedIn. Limited to 1000 results search parameter.
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
        if resp.status_code == 429:
            time.sleep(sleep)
            sleep += 1
        else:
            break


    print('-'*50)
    print(f'request-url [status {resp.status_code}]: {resp.url}')

    # exit function if bad response or empty HTML document
    if (not resp) or ('<!DOCTYPE html>\n\n<!---->' in resp.text):
        print('No more jobs found or an error occurred.')
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
        }

        yield res

# %%
def get_freq(data):
    
    # df = pandas.DataFrame(data)
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
location = 'vancouver'

# def get_jobs_by_location(location):
#     """
#     Get job postings for a specific location.
#     """


# approx. number of job postings
url = f'https://www.linkedin.com/jobs/search?location={location}'
resp = requests.get(url)
doc = html.fromstring(resp.content)
njobs = doc.xpath('//span[@class="results-context-header__job-count"]//text()')[0]

nskip, ncount = 0, 0

# initialize data structures
data = []
job_urls = set()
searched_kws = set()
kw = ''

# outer loop
while True:

    # inner loop
    run_search, start = True, 0

    while run_search:

        params = {
            'location': location,
            'start': start,
            'keywords' : kw,
            }
        
        search_results = search_jobs(params)
        
        for search_res in search_results:

            # break inner loop if no more results
            start += 1
            ncount += 1
            if not search_res:
                run_search = False
                break

            # check if the job url is already added
            job_url = search_res['job_url'].split('?')[0]
            
            if job_url not in job_urls:
                job_urls.add(job_url)
                data.append(search_res)
                print(f'[job {len(data):,} of {njobs}]', job_url)

            # else:
            #     nskip += 1
            #     print(f'[skip {nskip:,} of {ncount:,}]', job_url)

    # save data
    df = pandas.DataFrame(data)
    
    date = datetime.now().strftime('%Y%m%d')
    loc = ''.join(c for c in location if c.isalpha())
    
    dst = f'../data/jobposts/{date}-{loc}.csv'
    df.to_csv(dst, index=False)

    print(f'Saved {df.shape}:', dst)
    print('Now:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    # get word frequencies
    freq = get_freq(data)

    # filter top unsearched keyword
    wf = pandas.DataFrame(freq)
    wf = wf.sort_values(by='count', ascending=False) 
    cond = ~wf['keyword'].isin(searched_kws)
    kws = wf[cond]

    # break outer loop if no more new keywords found
    if kws.empty:
        print('No more keywords found.')
        break

    kw = kws.iloc[0]['keyword']
    searched_kws.add(kw)

    print('*'*50)
    print(f'search-keyword ({len(searched_kws):,}):', kw)

# %%
# locations = [
#     'vancouver', 'montreal', 'toronto', 'ottawa',
#     'stockholm', 'paris', 'berlin', 'london',
#     'new york, NY', 'san francisco',
# ]

location = 'vancouver'

# if __name__ == '__main__':
    
#     print('='*50)
#     print('Location:', location)
#     print('Start time:', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

#     get_jobs_by_location(location)


