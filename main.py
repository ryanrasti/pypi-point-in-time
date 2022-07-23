#!/bin/env python3
import contextlib
import subprocess
from concurrent import futures
import logging
import os
import queue
import re
import shutil
import tempfile
import threading
import urllib3
import time
import sys


import bs4
import requests
import tenacity

def main():
  out_dir = 'pypi.org/simple/'
  index = f'https://{out_dir}'
  
  logging.info('Downloading and parsing: %s', index)
  simple_root = bs4.BeautifulSoup(requests.get(index).text, 'lxml')

  items = []

  logging.info('Fixing up index')
  for link in simple_root.find_all('a'):
    href = link.get('href')
    if href:
      if href.startswith('/simple/'):
        link['href'] = href.lstrip('/')
      

      href = link['href']
      if m:= re.match('simple/([^/]+)', href):
        items.append((m.group(1)))

  logging.info('Writing out index')
  if os.path.exists(out_dir):
    subprocess.check_call(['rm', '-rf', out_dir])
  subprocess.check_call(['mkdir', '-p', out_dir])
  with open(os.path.join(out_dir, 'index.html'), 'w') as f:
    f.write(str(simple_root))

  def download(session, name):
    with open(os.path.join(out_dir, name), 'wb') as f:
      page = session.get(f'{index}{name}', stream=True)
      page.raise_for_status()
      page.raw.decode_content = True
      shutil.copyfileobj(page.raw, f)
      return f.tell()

  logging.info('Downloading all %d package pages' % len(items))

  q = queue.Queue()
  for item in items:
    q.put(item)

  with futures.ThreadPoolExecutor(max_workers=100) as ex:
    @tenacity.retry(stop=tenacity.stop_after_attempt(10), wait=tenacity.wait_fixed(2))
    def download_all():
      session = requests.Session()
      for item in iter(q.get_nowait, False):
        try:
          logging.debug('Downloading %s', item)
          download(session, item)
        except:
          q.put(item)
          logging.exception('Failure downloading:')
          raise


    def print_info():
      while q.qsize() > 0:
        time.sleep(1)
        logging.info('%.2f %% done', 1 - q.qsize() / len(items))

    for _ in range(99):
      ex.submit(download_all)

    ex.submit(print_info)


  logging.info('Done!')


if __name__ == '__main__':
  logging.basicConfig(level=logging.INFO)
  main()
