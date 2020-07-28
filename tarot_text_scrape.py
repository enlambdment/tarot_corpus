import requests 
import bs4 
import re
import os
from pathlib import Path
import copy



def url_to_soup(url):
	'''
	Given the url for a text's front page, get its parsed HTML.
	'''
	url_r = requests.get(url)
	url_soup = bs4.BeautifulSoup(url_r.text, 'html.parser')
	return url_soup

def get_text_name(url):
	'''
	Given a str 'url' specifying a path to a document's front page from
	https://www.sacred-texts.com/tarot/index.htm online archive, get the 
	portion landing after the last '/' to occur (so that I can use it to name the file.)
	'''
	slash_idx = url[::-1].find('/')
	return url[-slash_idx:]

def name_htm_search(name):
	'''
	Given a str 'name' denoting a specific text to scrape together for the corpus,
	returns a compiled regex for matching 'a'-tag 'href' attributes against, so as
	to spot which ones denote subsections of the text to be scraped.
	'''
	re1 = name + '.+' + '\.htm'
	re2 = name[0] + 'tar' + '.+' + '\.htm'
	name_re = re1 + '|' + re2 
	name_comp = re.compile(name_re)
	return name_comp

def get_sub_htms(url):
	'''
	Given the front page of a text, extract all the subsection .htm suffixes
	(to append onto the root path later)
	'''
	# fix url, if not in suitable format
	url = url.replace("/index.htm", "")

	txt_name = get_text_name(url)
	valid_htms_search = name_htm_search(txt_name)

	index_soup = url_to_soup(url)
	index_as = index_soup.find_all('a')

	valid_htms = []
	for a in index_as:
		if ('href' in a.attrs and valid_htms_search.match(a['href'])):
			a_href = a['href']
			if a_href not in valid_htms:
				valid_htms.append(a_href)

	return valid_htms 

def sub_htm_to_full_sub_url(htm, url):
	'''
	Given a subsection htm suffix, and the base path url, return the full 
	subsection url.
	'''
	# fix url, if not in suitable format
	url = url.replace("/index.htm", "")
	return url + '/' + htm

def person_name_search(person):
	'''
	Given a person's full name as a string, returns a compiled regex to look for
	that person's name, either in full e.g. "First Middle Last" or in abbreviated
	form e.g. "F M Last", within strings.
	'''
	person_parts = person.split()
	l = len(person_parts)
	# abbreviate all but the last name
	person_abrvs = [(person_parts[j][0] if j < l-1 else person_parts[j]) 
					for j in range(l)]
	# prepare regular expression
	person_regex = '.+'.join(person_abrvs)
	person_comp = re.compile(person_regex)
	return person_comp

tarot_text_redactor = "John Bruno Hare"
redactor_search = person_name_search(tarot_text_redactor)

def is_table_tag(tag):
	return (tag.name == 'table')

def is_bad_tag(tag, htms):
	'''
	A Tag is bad (*not* usable for corpus text) if the following is true:
		*	It is a 'center' tag having an 'a' element whose 'href' is in
			htms (these are navigation elements); or
		*	It is a 'font' tag having a 'color' attribute such that
			tag['color'].lower() == 'green' (these are editorial insertions)
			!	*unless the redactor's name appears in the tag's text* - 
				these attributions must not be removed. 
	'''
	if (tag.name == 'center' 		and tag.a 
		and 'href' in tag.a.attrs 	and tag.a['href'] in htms):
		return True
	elif (tag.name == 'font' and 'color' in tag.attrs 
		and tag['color'].lower() == 'green'):
		# If redactor's name appears in tag.text, then not a bad tag - 
		# include in corpus text. (search, NOT match)
		if redactor_search.search(tag.text):
			return False
		else:
			return True
	else:
		return False

def process_soup(soup, htms):	# -> (str, List[bs4.element.Tag])
	'''
	Given a bs4.BeautifulSoup object from the page of interest that I am trying
	to extract into a text for the corpus, and the htm suffixes for the text
	subsections:

	0. 	Identify the first header to appear whose tag matches the regular
		expression pattern of r'h[0-9]'
	1. 	Everything *from* there and after will be iterated through using 
		next_sibling
	2. 	For each sibling at a time:
		a. 	if Tag:
			* 	identify any 'table' tags - set those aside to work on later
			*	identify any bad tags - destroy those in place
			*	once sibling Tag has been cleaned up, get_text() and add to
				text building-up
		b.	if NavigableString:
			* 	just cast to 'str' and add to text building-up
	3. 	Return a pair of the built-up output_str & the list of 'table' tags

	Return the built-up output string from applying the above filtering steps.
	'''
	current_tag = soup.find(re.compile(r'h[0-9]'))

	output_str, output_tbls = "", []
	while current_tag:
		if isinstance(current_tag, bs4.element.Tag):
			# recursive search
			for t in current_tag.find_all(True):
				if is_table_tag(t):
					# Make a copy of 't' unconnected to original parse tree
					t_tbl = copy.copy(t)
					# and add it to 'output_tbls'
					output_tbls.append(t)
				elif is_bad_tag(t, htms):
					# destroy bad tags in place
					t.decompose()
			# get text from the cleaned-up current_tag & add to 'output_str'
			output_str += current_tag.get_text()
		elif isinstance(current_tag, bs4.element.NavigableString):
			# cast to 'str' & add to 'output_str'
			output_str += str(current_tag)
		# continue
		current_tag = current_tag.next_sibling

	return output_str, output_tbls

def make_file_for_corpus(url): # -> None
	'''
	Given an url, produce a file for the corpus text extracted from that
	url, filename based upon final non-"index.htm" section of url path,
	in ./data/tarot_guide corpus directory, if one does not exist.

	Note! For any given 'url', both the main-text & tables-html files are
	essentially written "in parallel" as the parsed Tags from the url's 
	BeautifulSoup are examined & worked on by 'process_soup'. If you end up
	with one but not the other file for any given url, then you should delete
	whichever file you have & re-run 'make_file_for_corpus(url)' in order for
	this to work correctly.

	(Future idea - modify 'process_soup', 'make_file_for_corpus' to accept
	argument selecting txt-only / tbls-only / both as possible modes?)
	'''
	# derive filename & set up Path
	txt_name = get_text_name(url)

	txt_fpath = './data/sacredtext_tarot_guides/' + txt_name + '.txt'
	tbl_fpath = './data/sacredtext_tarot_guides/' + txt_name + '_tbls.txt'
	txt_mkpath, tbl_mkpath = Path(txt_fpath), Path(tbl_fpath)
	# only begin requesting subsection urls & extracting texts if *both* 
	# files do not exist yet
	if not txt_mkpath.is_file() and not tbl_mkpath.is_file():
		# derive subsection htm suffixes
		txt_sub_htms = get_sub_htms(url)

		with txt_mkpath.open(mode='a+') as f_txt, \
			 tbl_mkpath.open(mode='a+') as f_tbl:
			for txt_sub_htm in txt_sub_htms:
				# derive subsection full url
				txt_sub_url = sub_htm_to_full_sub_url(txt_sub_htm, url)
				# extract text / table data
				fsu_soup = url_to_soup(txt_sub_url)
				fsu_text, fsu_tbls = process_soup(fsu_soup, txt_sub_htms)
				# append to f_txt
				f_txt.write(fsu_text)
				# str cast & append tables to f_tbl
				for tbl in fsu_tbls:
					f_tbl.write(str(tbl))

# put this into a separate 'main.py' file?
def make_corpus():
	'''
	Use 'tarot_front_pages.txt', at the same directory level as this Python
	file, to get a list of tarot-text front pages & extract corpus texts from
	each.
	'''
	corpus_urls_fname = './tarot_front_pages.txt'
	with open(corpus_urls_fname, 'rt') as corpus_urls_f:
		corpus_urls = corpus_urls_f.readlines()

	# strip whitespace
	corpus_urls = [url.strip() for url in corpus_urls]

	for corp_url in corpus_urls:
		make_file_for_corpus(corp_url)


